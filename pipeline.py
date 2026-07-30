"""
Combined inference pipeline.

This module wires together the three previously-separate scripts
(inference.py, test.py, show.py) into functions that can be called
automatically from a web server, with no manual path editing.

Requires (same as before, must exist alongside this file / on PYTHONPATH):
    - tab_estimator_model.py   (TabEstimator model definition)
    - src/config.yaml          (model config)
    - model/epoch192.model     (guitar tab model checkpoint)
    - model/guitar-gaps.pth    (piano-transcription-style checkpoint)
"""

import os
import math

import numpy as np
import torch
import yaml
import librosa
import pretty_midi
import matplotlib
matplotlib.use("Agg")  # headless/server-safe backend, no display needed
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from tab_estimator_model import TabEstimator
from piano_transcription_inference import PianoTranscription, sample_rate, load_audio

# ------------------ paths (adjust if your layout differs) ------------------
CONFIG_PATH = "src/config.yaml"
TAB_CHECKPOINT_PATH = "model/epoch192.model"
PIANO_CHECKPOINT_PATH = "model/guitar-gaps.pth"
# -----------------------------------------------------------------------------

# Models are expensive to load, so we load them once and reuse across requests.
_cfg = None
_tab_model = None
_piano_transcriptor = None


def get_config():
    global _cfg
    if _cfg is None:
        with open(CONFIG_PATH) as f:
            _cfg = yaml.safe_load(f)
    return _cfg


def get_tab_model():
    global _tab_model
    if _tab_model is None:
        cfg = get_config()
        model = TabEstimator(
            cfg["mode"],
            cfg["use_custom_decimation_func"],
            cfg["use_conv_stack"],
            cfg["cqt_n_bins"],
            cfg["hop_length"],
            cfg["down_sampling_rate"],
            encoder_heads=cfg["encoder_heads"],
            encoder_layers=cfg["encoder_layers"],
        )
        model.load_state_dict(torch.load(TAB_CHECKPOINT_PATH, map_location="cpu"))
        model.eval()
        _tab_model = model
    return _tab_model


def get_piano_transcriptor():
    global _piano_transcriptor
    if _piano_transcriptor is None:
        _piano_transcriptor = PianoTranscription(
            device="cpu",
            checkpoint_path=PIANO_CHECKPOINT_PATH,
            model_type="Regress_onset_offset_frame_velocity_CRNN",
        )
    return _piano_transcriptor


# ---------------------------------------------------------------------------
# Step 1 (from test.py): audio -> MIDI via the piano-transcription model
# ---------------------------------------------------------------------------
def transcribe_to_midi(audio_path, output_midi_path):
    audio, _ = load_audio(audio_path, sr=sample_rate, mono=True)
    transcriptor = get_piano_transcriptor()
    transcriptor.transcribe(audio, output_midi_path)
    return output_midi_path


# ---------------------------------------------------------------------------
# Step 2 (from inference.py): audio -> CQT -> tab predictions (.npz)
# ---------------------------------------------------------------------------
def compute_cqt(audio_path, sr_target, bins_per_octave, n_bins, hop_length):
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    y = librosa.util.normalize(y.astype(float))
    y = librosa.resample(y=y, orig_sr=sr, target_sr=sr_target)
    return compute_cqt_from_signal(y, sr_target, bins_per_octave, n_bins, hop_length)


def compute_cqt_from_signal(y, sr_target, bins_per_octave, n_bins, hop_length):
    cqt = np.abs(
        librosa.cqt(
            y=y,
            hop_length=hop_length,
            sr=sr_target,
            n_bins=n_bins,
            bins_per_octave=bins_per_octave,
        )
    )
    return cqt.T  # (time, n_bins)


def estimate_bpm(audio_path):
    """Auto-detect BPM so nobody has to hand-enter it (original script hardcoded BPM=129)."""
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    return tempo


def get_note_window_steps(cfg):
    bars = int(cfg.get("generated_midi_n_bars", 4))
    return bars * int(cfg["note_resolution"])


def split_into_note_chunks(array_2d_or_3d, chunk_size):
    return [array_2d_or_3d[start:start + chunk_size] for start in range(0, len(array_2d_or_3d), chunk_size)]


def run_tab_inference(audio_path, bpm, out_npz_path, target_note_steps=None):
    cfg = get_config()
    cqt = compute_cqt(
        audio_path,
        cfg["down_sampling_rate"],
        cfg["bins_per_octave"],
        cfg["cqt_n_bins"],
        cfg["hop_length"],
    )

    model = get_tab_model()
    note_window_steps = get_note_window_steps(cfg)

    y, sr = librosa.load(audio_path, sr=None, mono=True)
    y = librosa.util.normalize(y.astype(float))
    y = librosa.resample(y=y, orig_sr=sr, target_sr=cfg["down_sampling_rate"])

    note_dur = 60 / bpm / cfg["note_resolution"] * 4
    chunk_seconds = note_window_steps * note_dur
    chunk_samples = max(1, int(round(chunk_seconds * cfg["down_sampling_rate"])))

    if target_note_steps is None:
        target_note_steps = int(np.ceil(len(y) / chunk_samples) * note_window_steps)

    frame_preds = []
    note_preds = []
    note_onset_preds = []

    for start in range(0, len(y), chunk_samples):
        chunk = y[start:start + chunk_samples]
        if len(chunk) < chunk_samples:
            chunk = np.pad(chunk, (0, chunk_samples - len(chunk)))

        chunk_cqt = compute_cqt_from_signal(
            chunk,
            cfg["down_sampling_rate"],
            cfg["bins_per_octave"],
            cfg["cqt_n_bins"],
            cfg["hop_length"],
        )

        input_features = torch.from_numpy(chunk_cqt).float().unsqueeze(0)
        frame_len = torch.tensor([input_features.shape[1]], dtype=torch.float32)
        note_len = torch.tensor([note_window_steps], dtype=torch.float32)
        bpm_t = torch.tensor([bpm], dtype=torch.float32)

        with torch.no_grad():
            frame_pred, note_pred, note_onset_pred, olens = model(
                input_features, frame_len, note_len, bpm_t
            )

        frame_preds.append(frame_pred.squeeze(0).numpy())
        note_preds.append(note_pred.squeeze(0).numpy())
        note_onset_preds.append(note_onset_pred.squeeze(0).numpy())

    frame_pred = np.concatenate(frame_preds, axis=0) if frame_preds else np.empty((0, 6, 21), dtype=np.float32)
    note_pred = np.concatenate(note_preds, axis=0) if note_preds else np.empty((0, 6, 21), dtype=np.float32)
    note_onset_pred = np.concatenate(note_onset_preds, axis=0) if note_onset_preds else np.empty((0, 6, 21), dtype=np.float32)

    if target_note_steps is not None:
        if frame_pred.shape[0] < target_note_steps:
            pad_len = target_note_steps - frame_pred.shape[0]
            frame_pred = np.pad(frame_pred, [(0, pad_len), (0, 0), (0, 0)], mode="constant")
            note_pred = np.pad(note_pred, [(0, pad_len), (0, 0), (0, 0)], mode="constant")
            note_onset_pred = np.pad(note_onset_pred, [(0, pad_len), (0, 0), (0, 0)], mode="constant")
        else:
            frame_pred = frame_pred[:target_note_steps]
            note_pred = note_pred[:target_note_steps]
            note_onset_pred = note_onset_pred[:target_note_steps]

    olens = np.array([frame_pred.shape[0]], dtype=np.int64)

    os.makedirs(os.path.dirname(out_npz_path) or ".", exist_ok=True)
    np.savez_compressed(
        out_npz_path,
        cqt=cqt,
        frame_tab_pred=frame_pred,
        note_tab_pred=note_pred,
        note_tab_onset_pred=note_onset_pred,
        olens=olens,
        bpm=bpm,
    )
    return out_npz_path


# ---------------------------------------------------------------------------
# Step 3 (from show.py): npz + midi -> tab visualization (.png)
# ---------------------------------------------------------------------------
def midi_to_F0_onset(midi_path, tempo=120, note_resolution=16):
    midi_file = pretty_midi.PrettyMIDI(midi_path)
    note_dur = 60 / tempo / note_resolution * 4
    len_in_notes = int(
        math.ceil(round(midi_file.get_end_time() / note_dur) / (note_resolution * 4))
        * (note_resolution * 4)
    )

    # F0_onset = np.zeros((len_in_notes, 44))
    # for instrument in midi_file.instruments:
    #     for note in instrument.notes:
    #         t = int(round(note.start / note_dur))
    #         if t >= len_in_notes:
    #             break
    #         pitch = note.pitch - 40
    #         F0_onset[t, pitch] = 1
    F0_onset = np.zeros((len_in_notes, 88)) 
    for instrument in midi_file.instruments:
       for note in instrument.notes:
        t = int(round(note.start / note_dur))
        if t >= len_in_notes:
            break
        
        pitch = note.pitch - 40
        # Optional guard rail to prevent negative indices for pitches below 40
        if 0 <= pitch < 88:
            F0_onset[t, pitch] = 1

    return F0_onset


def plot_tab(tab, note_resolution, F0_onset=None):
    """
    tab: (T, 6, 21) one-hot fret array, class 20 = not played
    F0_onset: (T, 44) pitch-onset array (pitch_idx = midi_pitch - 40), or None
    """
    open_pitch = [40, 45, 50, 55, 59, 64]  # E A D G B e

    pitch_style_list = np.array(
        [
            ["#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC",
             "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999"],
            ["#339900", "#006633", "#009999", "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300",
             "#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000"],
            ["#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999",
             "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900"],
            ["#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000",
             "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC", "#9900CC"],
            ["#009999", "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900",
             "#339900", "#006633", "#009999", "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300"],
            ["#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC",
             "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999"],
        ]
    )

    plt.hlines(y=[0, 1, 2, 3, 4, 5], xmin=0, xmax=len(tab), colors="k", lw=0.15, zorder=0)

    time = 0
    for time in range(len(tab)):
        if time % note_resolution == 0:
            plt.vlines(x=time, ymin=0, ymax=5, colors="k", lw=0.3, zorder=0)
        elif time % 4 == 0:
            plt.vlines(x=time, ymin=0, ymax=5, colors="k", lw=0.15, zorder=0)
        else:
            plt.vlines(x=time, ymin=0, ymax=5, colors="k", lw=0.1, ls="dotted", zorder=0)

        for string in range(6):
            fret = np.argmax(tab[time, string])
            if fret != 20:
                midi_pitch = open_pitch[string] + fret
                pitch_idx = midi_pitch - 40

                onset_present = True
                if F0_onset is not None:
                    if 0 <= pitch_idx < F0_onset.shape[1]:
                        onset_present = F0_onset[time, pitch_idx] > 0
                    else:
                        onset_present = False

                if onset_present:
                    plt.scatter(
                        time, string, s=50, marker="${}$".format(fret),
                        color=pitch_style_list[string, fret], linewidths=1, zorder=5,
                    )

    plt.vlines(x=time + 1, ymin=0, ymax=5.0, colors="k", lw=0.3)
    plt.xticks(
        [i for i in range(0, time + 1) if i % note_resolution == 0],
        labels=[i for i in range(0, time // note_resolution + 1)],
    )
    plt.yticks(np.arange(6), ("E", "A", "D", "G", "B", "e"))
    plt.ylim(-0.5, 5.5)
    plt.xlabel("Bar number")


def plot_wrapped_tab(tab, note_resolution, F0_onset=None, bars_per_row=4, note_spacing=1.0):
    plt.style.use("default")
    open_pitch = [40, 45, 50, 55, 59, 64]  # E A D G B e

    total_frames = len(tab)
    frames_per_row = note_resolution * bars_per_row
    n_rows = max(1, int(np.ceil(total_frames / frames_per_row)))
    note_offset = note_spacing * 1.5
    bar_label_offset = note_spacing

    fig, axes = plt.subplots(
        n_rows, 1,
        figsize=(max(12, bars_per_row * 3.2), max(3.2, n_rows * 2.6)),
        sharey=True,
        constrained_layout=True,
    )
    fig.patch.set_facecolor("white")
    if n_rows == 1:
        axes = [axes]

    for row_index, ax in enumerate(axes):
        ax.set_facecolor("white")
        start = row_index * frames_per_row
        end = min(start + frames_per_row, total_frames)
        row_tab = tab[start:end]
        row_onset = None if F0_onset is None else F0_onset[start:end]
        row_len = len(row_tab)

        ax.hlines(y=[0, 1, 2, 3, 4, 5], xmin=0, xmax=row_len * note_spacing, colors="#cfcfcf", lw=0.9, zorder=0)

        for time in range(row_len):
            x_pos = time * note_spacing + note_offset
            if time % note_resolution == 0:
                ax.vlines(x=x_pos, ymin=0, ymax=5, colors="#5a5a5a", lw=1.0, zorder=0)
            elif time % 4 == 0:
                ax.vlines(x=x_pos, ymin=0, ymax=5, colors="#a2a2a2", lw=0.7, zorder=0)
            else:
                ax.vlines(x=x_pos, ymin=0, ymax=5, colors="#d6d6d6", lw=0.45, ls="dotted", zorder=0)

            for string in range(6):
                fret = np.argmax(row_tab[time, string])
                if fret != 20:
                    midi_pitch = open_pitch[string] + fret
                    pitch_idx = midi_pitch - 40

                    onset_present = True
                    if row_onset is not None:
                        if 0 <= pitch_idx < row_onset.shape[1]:
                            onset_present = row_onset[time, pitch_idx] > 0
                        else:
                            onset_present = False

                    if onset_present:
                        ax.text(
                            x_pos, string, str(fret),
                            ha="center", va="center",
                            color="#111111", fontsize=12, fontweight="600",
                            family="DejaVu Sans", zorder=5,
                        )

        ax.vlines(x=row_len * note_spacing, ymin=0, ymax=5.0, colors="#5a5a5a", lw=1.0)
        ax.set_yticks(np.arange(6))
        ax.set_yticklabels(("E", "A", "D", "G", "B", "e"))
        ax.set_ylim(-0.5, 5.5)
        ax.set_xlim(0, max(row_len * note_spacing + note_offset, note_spacing))
        ax.tick_params(axis="y", labelsize=12, length=0, colors="#333333")
        ax.tick_params(axis="x", labelsize=11, length=0, pad=8, colors="#333333")
        for spine in ax.spines.values():
            spine.set_visible(False)

        bar_ticks = [i * note_resolution * note_spacing + bar_label_offset for i in range((row_len // note_resolution) + 1)]
        bar_labels = [start // note_resolution + i for i in range(len(bar_ticks))]
        ax.set_xticks(bar_ticks)
        ax.set_xticklabels(bar_labels)
        ax.set_xlabel("Bar number")

        if row_index == 0:
            ax.set_title("Guitar Tablature", fontsize=18, pad=16, color="#111111")


def midi_to_note_name(midi):
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = midi // 12 - 1
    return f"{names[midi % 12]}{octave}"


def plot_piano_roll(ax, tab, note_resolution, onset=None, tuning_midi=None):
    if tuning_midi is None:
        tuning_midi = [40, 45, 50, 55, 59, 64]

    string_colors = {0: "#e76f51", 1: "#e9c46a", 2: "#4d96ff", 3: "#ff7f50", 4: "#2a9d8f", 5: "#8e44ad"}
    string_names = ["E", "A", "D", "G", "B", "e"]

    n_frames, n_strings, _ = tab.shape
    active_pitches = set()
    notes = []
    open_notes = {}

    for t in range(n_frames):
        for s in range(n_strings):
            fret = int(np.argmax(tab[t, s]))
            played = fret != 20

            onset_flag = False
            if played and onset is not None:
                try:
                    onset_flag = onset[t, s, fret] > 0
                except Exception:
                    onset_flag = False

            if played and onset is not None and not onset_flag and s not in open_notes:
                played = False

            if played:
                pitch = tuning_midi[s] + fret
                active_pitches.add(pitch)

                if s in open_notes:
                    same_pitch = open_notes[s]["pitch"] == pitch
                    retrigger = onset is not None and onset_flag and t > open_notes[s]["start"]
                    if same_pitch and not retrigger:
                        continue
                    notes.append({"pitch": open_notes[s]["pitch"], "start": open_notes[s]["start"], "end": t, "string": s})
                    open_notes[s] = {"pitch": pitch, "start": t}
                else:
                    open_notes[s] = {"pitch": pitch, "start": t}
            elif s in open_notes:
                notes.append({"pitch": open_notes[s]["pitch"], "start": open_notes[s]["start"], "end": t, "string": s})
                del open_notes[s]

    for s, note in open_notes.items():
        notes.append({"pitch": note["pitch"], "start": note["start"], "end": n_frames, "string": s})

    if not active_pitches:
        ax.text(0.5, 0.5, "No notes played", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        return

    sorted_pitches = sorted(active_pitches)
    pitch_to_row = {p: i for i, p in enumerate(sorted_pitches)}
    n_rows = len(sorted_pitches)

    ax.hlines(y=list(range(n_rows)), xmin=0, xmax=n_frames, colors="#d0d0d0", lw=0.8, zorder=0)
    for t in range(n_frames + 1):
        if t % note_resolution == 0:
            ax.vlines(x=t, ymin=-0.5, ymax=n_rows - 0.5, colors="#666666", lw=0.9, zorder=0)
        elif t % 4 == 0:
            ax.vlines(x=t, ymin=-0.5, ymax=n_rows - 0.5, colors="#aaaaaa", lw=0.6, zorder=0)

    for note in notes:
        width = note["end"] - note["start"]
        if width <= 0:
            continue
        row = pitch_to_row[note["pitch"]]
        color = string_colors.get(note["string"], "#222222")
        rect = mpatches.Rectangle((note["start"], row - 0.42), width, 0.84, facecolor=color, edgecolor="#222222", linewidth=0.5, zorder=5)
        ax.add_patch(rect)

    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([midi_to_note_name(p) for p in sorted_pitches])
    ax.set_xticks([i for i in range(0, n_frames + 1) if i % note_resolution == 0])
    ax.set_xticklabels([i for i in range(0, n_frames // note_resolution + 1)])
    ax.set_xlim(0, n_frames)
    ax.set_ylim(-0.5, n_rows - 0.5)
    ax.set_xlabel("Bar number")
    ax.set_ylabel("Pitch")
    ax.tick_params(axis="x", labelsize=10, length=0, pad=6, colors="#333333")
    ax.tick_params(axis="y", labelsize=10, length=0, colors="#333333")
    for spine in ax.spines.values():
        spine.set_visible(False)

    handles = [mpatches.Patch(color=string_colors[s], label=string_names[s]) for s in range(n_strings)]
    ax.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        borderaxespad=0,
        fontsize=9,
        ncol=1,
        frameon=False,
        title="String",
        title_fontsize=9,
    )


def generate_visualization(npz_path, midi_path, bpm, out_png_path, note_resolution=16):
    d = np.load(npz_path, allow_pickle=True)
    tab = d["note_tab_pred"]
    note_onset = d.get("note_tab_onset_pred")

    F0_onset_from_midi = midi_to_F0_onset(midi_path, tempo=bpm, note_resolution=note_resolution)

    n_frames = tab.shape[0]
    F0_onset_aligned = F0_onset_from_midi[:n_frames]
    note_onset_aligned = None if note_onset is None else note_onset[:n_frames]

    total_frames = len(tab)
    frames_per_row = note_resolution * 4
    n_tab_rows = max(1, int(np.ceil(total_frames / frames_per_row)))

    fig_height = max(6.0, n_tab_rows * 2.2 + 5.2)
    fig = plt.figure(figsize=(max(16, 4 * 3.5 + 2), fig_height))
    fig.patch.set_facecolor("white")
    # Extra row (index n_tab_rows) is a blank spacer that guarantees vertical
    # breathing room between the last tab row's x-axis labels/title and the
    # piano roll's title, instead of relying on a single uniform hspace.
    grid = fig.add_gridspec(
        n_tab_rows + 2,
        1,
        height_ratios=[1] * n_tab_rows + [0.35, 1.5],
        hspace=0.45,
    )

    tab_axes = [fig.add_subplot(grid[i, 0]) for i in range(n_tab_rows)]
    for ax in tab_axes:
        ax.set_facecolor("white")

    # Render wrapped tab rows.
    for row_index, ax in enumerate(tab_axes):
        start = row_index * frames_per_row
        end = min(start + frames_per_row, total_frames)
        row_tab = tab[start:end]
        row_onset = None if F0_onset_aligned is None else F0_onset_aligned[start:end]
        row_len = len(row_tab)

        note_spacing = 1.5
        note_offset = note_spacing * 1.5
        bar_label_offset = note_spacing

        ax.hlines(y=[0, 1, 2, 3, 4, 5], xmin=0, xmax=row_len * note_spacing, colors="#cfcfcf", lw=0.9, zorder=0)
        for time in range(row_len):
            x_pos = time * note_spacing + note_offset
            if time % note_resolution == 0:
                ax.vlines(x=x_pos, ymin=0, ymax=5, colors="#5a5a5a", lw=1.0, zorder=0)
            elif time % 4 == 0:
                ax.vlines(x=x_pos, ymin=0, ymax=5, colors="#a2a2a2", lw=0.7, zorder=0)
            else:
                ax.vlines(x=x_pos, ymin=0, ymax=5, colors="#d6d6d6", lw=0.45, ls="dotted", zorder=0)

            for string in range(6):
                fret = np.argmax(row_tab[time, string])
                if fret != 20:
                    midi_pitch = [40, 45, 50, 55, 59, 64][string] + fret
                    pitch_idx = midi_pitch - 40
                    onset_present = True
                    if row_onset is not None:
                        onset_present = 0 <= pitch_idx < row_onset.shape[1] and row_onset[time, pitch_idx] > 0
                    if onset_present:
                        ax.text(
                            x_pos, string, str(fret),
                            ha="center", va="center",
                            color="#111111", fontsize=12, fontweight="600",
                            family="DejaVu Sans", zorder=5,
                        )

        ax.vlines(x=row_len * note_spacing, ymin=0, ymax=5.0, colors="#5a5a5a", lw=1.0)
        ax.set_yticks(np.arange(6))
        ax.set_yticklabels(("E", "A", "D", "G", "B", "e"))
        ax.set_ylim(-0.5, 5.5)
        ax.set_xlim(0, max(row_len * note_spacing + note_offset, note_spacing))
        ax.tick_params(axis="y", labelsize=12, length=0, colors="#333333")
        ax.tick_params(axis="x", labelsize=11, length=0, pad=8, colors="#333333")
        for spine in ax.spines.values():
            spine.set_visible(False)

        bar_ticks = [i * note_resolution * note_spacing + bar_label_offset for i in range((row_len // note_resolution) + 1)]
        bar_labels = [start // note_resolution + i for i in range(len(bar_ticks))]
        ax.set_xticks(bar_ticks)
        ax.set_xticklabels(bar_labels)
        ax.set_xlabel("Bar number")
        if row_index == 0:
            ax.set_title("Guitar Tablature", fontsize=18, pad=16, color="#111111")

    spacer_ax = fig.add_subplot(grid[n_tab_rows, 0])
    spacer_ax.axis("off")

    piano_roll_ax = fig.add_subplot(grid[n_tab_rows + 1, 0])
    piano_roll_ax.set_facecolor("white")
    plot_piano_roll(piano_roll_ax, tab, note_resolution, onset=note_onset_aligned)
    piano_roll_ax.set_title("Piano Roll View", fontsize=16, pad=14, color="#111111")

    os.makedirs(os.path.dirname(out_png_path) or ".", exist_ok=True)
    plt.savefig(out_png_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close()
    return out_png_path


# ---------------------------------------------------------------------------
# Full pipeline: this is the single entry point the web server should call.
# ---------------------------------------------------------------------------
def run_full_pipeline(audio_path, work_dir, bpm=None, note_resolution=16):
    """
    Runs everything automatically for one uploaded audio file:
      1. piano-transcription-style model -> MIDI
      2. CQT + TabEstimator -> tab predictions (.npz)
      3. visualization -> .png

    Returns a dict of output file paths + the bpm used.
    """
    os.makedirs(work_dir, exist_ok=True)

    if bpm is None:
        bpm = estimate_bpm(audio_path)

    midi_path = os.path.join(work_dir, "output.mid")
    transcribe_to_midi(audio_path, midi_path)

    target_note_steps = midi_to_F0_onset(
        midi_path, tempo=bpm, note_resolution=note_resolution
    ).shape[0]

    npz_path = os.path.join(work_dir, "prediction.npz")
    run_tab_inference(audio_path, bpm, npz_path, target_note_steps=target_note_steps)

    png_path = os.path.join(work_dir, "tab_visualization.png")
    generate_visualization(npz_path, midi_path, bpm, png_path, note_resolution=note_resolution)

    return {
        "bpm": bpm,
        "midi_path": midi_path,
        "npz_path": npz_path,
        "png_path": png_path,
    }