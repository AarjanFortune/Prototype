"""interpreter
"""
from re import A
import numpy as np
import pretty_midi
from matplotlib import lines as mlines, pyplot as plt
import tempfile
import librosa

import os
import pandas as pd
import sys








def jams_to_midi(jam, tempo=120, q=1, quantization=0):
    # q = 1: with pitch bend. q = 0: without pitch bend.
    midi = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    annos = jam.search(namespace='note_midi')
    if quantization > 0:
        note_dur = 60 / tempo / quantization * 4
    elif quantization < 0:
        sys.exit(
            "Quantization parameter must be 0(not qunatize) or integer greater than 1")

    if len(annos) == 0:
        annos = jam.search(namespace='pitch_midi')
    string_name = ['E string', 'A string', 'D string',
                   'G string', 'B string', 'e string']
    for i, anno in enumerate(annos):
        midi_ch = pretty_midi.Instrument(program=25, name=string_name[i])
        for note in anno:
            pitch = int(round(note.value))
            bend_amount = int(round((note.value - pitch) * 4096))
            j = 0
            k = 0
            if quantization != 0:
                while not((j - 1/2) * note_dur < note.time and note.time < (j + 1/2) * note_dur):
                    j = j + 1
                st = j * note_dur

                while not((k - 1/2) * note_dur < note.duration and note.duration < (k + 1/2) * note_dur):
                    k = k + 1
                if k == 0:
                    k = 1
                    #print("duration is 0, ", k)
                dur = k * note_dur

            else:
                st = note.time
                dur = note.duration

            n = pretty_midi.Note(
                velocity=100 + np.random.choice(range(-5, 5)),
                pitch=pitch, start=st,
                end=st + dur
            )
            pb = pretty_midi.PitchBend(pitch=bend_amount * q, time=st)
            midi_ch.notes.append(n)
            midi_ch.pitch_bends.append(pb)
        if len(midi_ch.notes) != 0:
            midi.instruments.append(midi_ch)
    return midi




    style_dict = {0: 'r', 1: 'y', 2: 'b', 3: '#FF7F50', 4: 'g', 5: '#800080'}
    string_dict = {0: 'E', 1: 'A', 2: 'D', 3: 'G', 4: 'B', 5: 'e'}
    s = 0
    handle_list = []
    fig = plt.figure()
    annos = jam.search(namespace='note_midi')
    if len(annos) == 0:
        annos = jam.search(namespace='pitch_midi')
    for string_tran in annos:
        handle_list.append(mlines.Line2D([], [], color=style_dict[s],
                                         label=string_dict[s]))
        for note in string_tran:
            start_time = note[0]
            midi_note = note[2]
            dur = note[1]
            plt.plot([start_time, start_time + dur],
                     [midi_note, midi_note],
                     style_dict[s], label=string_dict[s])
        s += 1
    plt.xlabel('Time (sec)')
    plt.ylabel('Pitch (midi note number)')
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), handles=handle_list)
    plt.title(jam.file_metadata.title)
    plt.xlim(-0.5, jam.file_metadata.duration)
    fig.set_size_inches(6, 3)
    if save_path:
        plt.savefig(save_path)





