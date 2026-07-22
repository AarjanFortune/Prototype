import numpy as np
import librosa
import librosa.display
from matplotlib import lines as mlines, pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.patches as mpatches
import seaborn as sns
import librosa
import yaml
import os
import argparse
import glob
from multiprocessing import Pool
from itertools import repeat


def plot_tab(tab, note_resolution, onset=None):
    string_style_dict = {0: 'r', 1: 'y', 2: 'b',
                         3: '#FF7F50', 4: 'g', 5: '#800080'}
    fret_style_dict = {0: '#CC0033', 1: '#3300CC', 2: '#9900CC',
                       3: '#FFCC00', 4: "#00CC99", 5: "#99CC00",
                       6: "#99FF99", 7: "#3366CC", 8: "#006600",
                       9: "#CC9933", 10: "#CC33CC", 11: "#003333",
                       12: "#00CC00", 13: "#999900", 14: "#CC6666",
                       15: "#330066", 16: "#66CCCC", 17: "#663300",
                       18: "#66FFFF", 19: "#9933FF"}
    pitch_style_list = np.array([["#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC", 
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
                                  "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999"]])

    plt.hlines(y=[0,1,2,3,4,5], xmin=0, xmax=64, colors='k', lw=0.15, zorder=0)
    
    for time in range(len(tab)):
        if time % note_resolution == 0:
            plt.vlines(x=time, ymin=0, ymax=5, colors='k', lw=0.3, zorder=0)
        elif time % 4 == 0:
            plt.vlines(x=time, ymin=0, ymax=5, colors='k', lw=0.15, zorder=0)
        else:
            plt.vlines(x=time, ymin=0, ymax=5, colors='k', lw=0.1, ls='dotted', zorder=0)
        for string in range(6):
            fret = np.argmax(tab[time, string])
            if fret != 20:
                # if an onset array is provided, only plot when onset agrees
                try:
                    onset_val = None if onset is None else onset[time, string, fret]
                except Exception:
                    onset_val = None

                if onset is None or (onset_val is not None and onset_val > 0):
                    plt.scatter(time, string, s=50, marker="${}$".format(
                        fret), color=pitch_style_list[string, fret], linewidths=1, zorder=5)
                
            # plot 'not played' as x marker
            """
            else:
                plt.scatter(time, string, s=20, marker='x',
                            color='black', linewidths=0.5)
            """
    plt.vlines(x=time+1, ymin=0, ymax=5.0, colors='k', lw=0.3)
    plt.xticks([i for i in range(0, time+1) if i % note_resolution == 0],
               labels=[i for i in range(0, time//note_resolution+1)])
    plt.yticks(np.arange(6), ('E', 'A', 'D', 'G', 'B', 'e'))
    plt.ylim(-0.5, 5.5)
    plt.xlabel('Bar number')


def midi_to_note_name(midi):
    names = ['C', 'C#', 'D', 'D#', 'E', 'F',
             'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = midi // 12 - 1
    return f"{names[midi % 12]}{octave}"


def plot_piano_roll(tab, note_resolution, onset=None, tuning_midi=None):
    """
    Build a piano-roll view directly from tablature data (same `tab` array
    used by plot_tab: shape [time, string, fret], fret==20 means 'not played').
    Only pitches that are actually played anywhere in the clip get a row.
    """
    if tuning_midi is None:
        # standard guitar tuning, low E to high e, MIDI note numbers
        tuning_midi = [40, 45, 50, 55, 59, 64]
    string_colors = {0: 'r', 1: 'y', 2: 'b',
                      3: '#FF7F50', 4: 'g', 5: '#800080'}
    string_names = ['E', 'A', 'D', 'G', 'B', 'e']

    n_frames, n_strings, n_frets = tab.shape

    active_pitches = set()
    notes = []  # finished note events: {pitch, start, end, string}
    open_notes = {}  # per-string in-progress note: {'pitch':, 'start':}

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
                # no active note and no onset confirmation -> skip (matches plot_tab behavior)
                played = False

            if played:
                pitch = tuning_midi[s] + fret
                active_pitches.add(pitch)

                if s in open_notes:
                    same_pitch = open_notes[s]['pitch'] == pitch
                    retrigger = onset is not None and onset_flag and t > open_notes[s]['start']
                    if same_pitch and not retrigger:
                        # note continues, nothing to do until it ends
                        continue
                    else:
                        # close previous note (new pitch, or explicit re-onset of same pitch)
                        notes.append({'pitch': open_notes[s]['pitch'],
                                      'start': open_notes[s]['start'],
                                      'end': t, 'string': s})
                        open_notes[s] = {'pitch': pitch, 'start': t}
                else:
                    open_notes[s] = {'pitch': pitch, 'start': t}
            else:
                if s in open_notes:
                    notes.append({'pitch': open_notes[s]['pitch'],
                                  'start': open_notes[s]['start'],
                                  'end': t, 'string': s})
                    del open_notes[s]

    for s, note in open_notes.items():
        notes.append({'pitch': note['pitch'], 'start': note['start'],
                      'end': n_frames, 'string': s})

    if not active_pitches:
        plt.text(0.5, 0.5, 'No notes played', ha='center', va='center',
                  transform=plt.gca().transAxes)
        plt.axis('off')
        return

    sorted_pitches = sorted(active_pitches)
    pitch_to_row = {p: i for i, p in enumerate(sorted_pitches)}
    n_rows = len(sorted_pitches)

    plt.hlines(y=list(range(n_rows)), xmin=0, xmax=n_frames,
               colors='gray', lw=0.15, zorder=0)
    for t in range(n_frames + 1):
        if t % note_resolution == 0:
            plt.vlines(x=t, ymin=-0.5, ymax=n_rows - 0.5,
                       colors='k', lw=0.3, zorder=0)
        elif t % 4 == 0:
            plt.vlines(x=t, ymin=-0.5, ymax=n_rows - 0.5,
                       colors='k', lw=0.15, zorder=0)

    for note in notes:
        width = note['end'] - note['start']
        if width <= 0:
            continue
        row = pitch_to_row[note['pitch']]
        color = string_colors.get(note['string'], 'k')
        rect = mpatches.Rectangle((note['start'], row - 0.4), width, 0.8,
                                  facecolor=color, edgecolor='k',
                                  linewidth=0.5, zorder=5)
        plt.gca().add_patch(rect)

    plt.yticks(range(n_rows), [midi_to_note_name(p) for p in sorted_pitches])
    plt.xticks([i for i in range(0, n_frames + 1) if i % note_resolution == 0],
               labels=[i for i in range(0, n_frames // note_resolution + 1)])
    plt.xlim(0, n_frames)
    plt.ylim(-0.5, n_rows - 0.5)
    plt.xlabel('Bar number')
    plt.ylabel('Pitch')

    handles = [mpatches.Patch(color=string_colors[s], label=string_names[s])
              for s in range(n_strings)]
    plt.legend(handles=handles, loc='upper right', fontsize=8, ncol=6)


def visualize(npz_filename_list, kwargs):
    note_resolution = kwargs["note_resolution"]
    down_sampling_rate = kwargs["down_sampling_rate"]
    bins_per_octave = kwargs["bins_per_octave"]
    hop_length = kwargs["hop_length"]
    encoder_layers = kwargs["encoder_layers"]
    encoder_heads = kwargs["encoder_heads"]
    input_feature_type = kwargs["input_feature_type"]
    visualize_dir = kwargs["visualize_dir"]

    npz_filename_list = npz_filename_list.split("\n")

    for npz_filename in npz_filename_list:
        npz_file = np.load(npz_filename)
        # load from saved npz file from src/predict.py
        input_features = npz_file["input_features"]
        frame_pred = npz_file["frame_tab_pred"]
        frame_gt = npz_file["frame_tab_gt"]
        note_pred = npz_file["note_tab_pred"]
        note_gt = npz_file["note_tab_gt"]
        note_tab_onset_pred = npz_file["note_tab_onset_pred"]
        note_tab_onset_gt = npz_file["note_tab_onset_gt"]
        attn_map = npz_file["attn_map"]

        # plotting
        frames_per_second = hop_length / down_sampling_rate
        frames_to_sec_labels = np.arange(len(frame_gt)) / frames_per_second
        # subplots: input features, gt tab, pred tab, gt piano roll, pred piano roll, + attention heads
        n_subplots = 5 + encoder_layers * encoder_heads

        plt.figure(figsize=(10, n_subplots*3), dpi=200)
        plt.rc('axes', labelsize=15) 
        plt.rc('xtick', labelsize=12)
        plt.rc('ytick', labelsize=12)
        subplot_counter = 1
        plt.subplot(n_subplots, 1, subplot_counter)
        plt.title(f"Input Constant-Q Transform")
        cqt = input_features.T
        librosa.display.specshow(librosa.amplitude_to_db(np.abs(cqt)),
                                 x_axis='time',
                                 y_axis='cqt_hz',
                                 sr=down_sampling_rate,
                                 hop_length=hop_length,
                                 bins_per_octave=bins_per_octave,
                                 cmap='magma')
        plt.colorbar(format='%+2.0f dB')
        plt.xlabel('Tims [s]')
        subplot_counter = subplot_counter + 1

        plt.subplot(n_subplots, 1, subplot_counter)
        plt.title('Ground truth note-level tablature')
        plot_tab(note_gt, note_resolution, onset=note_tab_onset_gt)
        subplot_counter = subplot_counter + 1

        plt.subplot(n_subplots, 1, subplot_counter)
        plt.title('Predicted note-level tablature')
        plot_tab(note_pred, note_resolution, onset=note_tab_onset_pred)
        subplot_counter = subplot_counter + 1

        # piano roll derived directly from tab (only pitches actually played)
        plt.subplot(n_subplots, 1, subplot_counter)
        plt.title('Ground truth piano roll (from tab)')
        plot_piano_roll(note_gt, note_resolution, onset=note_tab_onset_gt)
        subplot_counter = subplot_counter + 1

        plt.subplot(n_subplots, 1, subplot_counter)
        plt.title('Predicted piano roll (from tab)')
        plot_piano_roll(note_pred, note_resolution, onset=note_tab_onset_pred)
        subplot_counter = subplot_counter + 1

        # encoder self-attention
        for n_layer in range(encoder_layers):
            for n_head in range(encoder_heads):
                plt.subplot(n_subplots, 1, subplot_counter)
                plt.title(f'Encoder self-attention map')
                cmap = sns.color_palette("ch:s=-.2,r=.6", as_cmap=True)
                sns.heatmap(attn_map[n_layer, n_head], cmap=cmap, 
                            norm=LogNorm(vmin=1e-3))
                plt.xlabel('source sequence')
                plt.ylabel('target sequence')
                subplot_counter = subplot_counter + 1
        
        plt.tight_layout()
        save_filename = os.path.join(
            visualize_dir,  f"{os.path.split(npz_filename)[1][:-4]}.png")
        if os.path.exists(save_filename):
            os.remove(save_filename)
        plt.savefig(save_filename)
        plt.close('all')
        
        print(f"finished {os.path.split(npz_filename)[1][:-4]}")


def main():
    parser = argparse.ArgumentParser(description='code for plotting results')
    parser.add_argument("model", type=str,
                        help="name of trained model: ex) 202201010000")
    parser.add_argument("epoch", type=int,
                        help="number of model epoch to use: ex) 64")
    parser.add_argument("-v", "--verbose", help="option for verbosity: -v to turn on verbosity",
                        action="store_true", required=False, default=False)
    args = parser.parse_args()

    trained_model = args.model
    use_model_epoch = args.epoch
    verbose = args.verbose

    config_path = os.path.join("model", f"{trained_model}", "config.yaml")
    with open(config_path) as f:
        obj = yaml.safe_load(f)
        note_resolution = obj["note_resolution"]
        down_sampling_rate = obj["down_sampling_rate"]
        bins_per_octave = obj["bins_per_octave"]
        hop_length = obj["hop_length"]
        encoder_layers = obj["encoder_layers"]
        encoder_heads = obj["encoder_heads"]
        n_cores = obj["n_cores"]
        input_feature_type = obj["input_feature_type"]

    kwargs = {
        "note_resolution": note_resolution,
        "down_sampling_rate": down_sampling_rate,
        "bins_per_octave": bins_per_octave,
        "hop_length": hop_length,
        "encoder_layers": encoder_layers,
        "encoder_heads": encoder_heads,
        "input_feature_type": input_feature_type
    }

    npz_dir = os.path.join(
        "result", "tab", f"{trained_model}_epoch{use_model_epoch}", "npz")

    for test_num in range(6):
        visualize_dir = os.path.join(
            "result", "tab", f"{trained_model}_epoch{use_model_epoch}", "visualize", f"test_0{test_num}")

        npz_filename_list = glob.glob(
            os.path.join(npz_dir, f"test_0{test_num}", "*"))
        kwargs["visualize_dir"] = visualize_dir
        if not(os.path.exists(visualize_dir)):
            os.makedirs(visualize_dir)
            
        # paralell process
        p = Pool(n_cores)
        p.starmap(visualize, zip(npz_filename_list, repeat(kwargs)))
        p.close()  # or p.terminate()
        p.join()


if __name__ == "__main__":
    main()