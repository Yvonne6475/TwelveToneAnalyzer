import random

twelve_tone_row = random.sample(range(12), 12)
print(twelve_tone_row)

from music21 import *

# Create pitch class list of 12-tone row
names = []

for pc in twelve_tone_row:
        p = pitch.Pitch()
        p.pitchClass = pc
        p.octave = 4
        names.append(p.nameWithOctave)
print(names)


#Create the midi note list of 12-tone row
midi_list = [pitch.Pitch(n).midi for n in names]
print(midi_list)

#Generate four transposition rows
Prime_row = twelve_tone_row
Prime_label = f"P{Prime_row[0]}"
print(f"Prime_row:{Prime_label} = {Prime_row}")



pivot = Prime_row[0]
Inversion_row = [(2 * pivot - pc) % 12 for pc in Prime_row]
I_label = f"I{Inversion_row[0]}"
print(f"Inversion_row:{I_label}={Inversion_row}")

Retrograde_row = list(reversed(Prime_row))
R_label = f"R{Retrograde_row[0]}"
print(f"Retrograde_row:{R_label}={Retrograde_row}")

Retrograde_Inversion_row = [(2 * pivot - pc) % 12 for pc in Retrograde_row]
RI_label = f"RI{Retrograde_Inversion_row[0]}"
print(f"Retrograde_Inversion_row:{RI_label}={Retrograde_Inversion_row}")

#Generate 12-tone matrix
ttr = serial.TwelveToneRow(twelve_tone_row)
aMatrix = ttr.matrix()
print(aMatrix)


matrix = [[n.pitch.pitchClass for n in row] for row in aMatrix]

print("\nPrime rows (I0-I11):")
for row in matrix:
    print("P"+str(row[0]), row)

print("\nInversion rows (I0-I11):")
for col_index in range(12):
    I_row = [row[col_index] for row in matrix]
    label = f"I{I_row[0]}"
    print(f"{label} = {I_row}")

print("\nRetrograde rows (R0-R11):")
for row in matrix:
    R_row = list(reversed(row))
    label = f"R{R_row[0]}"  # Retrograde 的编号用首音
    print(f"{label} = {R_row}")

print("\nRetrograde Inversion rows (RI0-RI11):")
for col_index in range(12):
    RI_row = [row[col_index] for row in matrix][::-1]  # 先取列，再倒序
    label = f"RI{RI_row[0]}"
    print(f"{label} = {RI_row}")

P_rows = [[n for n in row] for row in matrix]
I_rows = [[row[col] for row in matrix] for col in range(12)]
R_rows = [list(reversed(row)) for row in matrix]
RI_rows = [list(reversed([row[col] for row in matrix])) for col in range(12)]

# 48 rows
all_rows = P_rows + I_rows + R_rows + RI_rows

def pc_to_midi(row, base=60):
    """
    convert pitch class list to MIDI note list
    """
    return [base + pc for pc in row]

all_rows_midi = [pc_to_midi(row, base=60) for row in all_rows]



def row_to_text(label1, row):
    row_text = " ".join(str(pc) for pc in row)
    return f"{label1}: {row_text}"

labels1 = []

# P rows
for row in P_rows:
    labels1.append(row_to_text(f"P{row[0]}", row))

# I rows
for row in I_rows:
    labels1.append(row_to_text(f"I{row[0]}", row))

# R rows
for row in R_rows:
    labels1.append(row_to_text(f"R{row[0]}", row))

# RI rows
for row in RI_rows:
    labels1.append(row_to_text(f"RI{row[0]}", row))




import mido
from mido import MidiFile, MidiTrack, Message,MetaMessage

mid = MidiFile()
track = MidiTrack()
mid.tracks.append(track)

track.append(MetaMessage('set_tempo', tempo=1000000))
track.append(MetaMessage('time_signature', numerator=6, denominator=8))
track.append(MetaMessage('key_signature', key='C'))
note_duration = int(mid.ticks_per_beat / 4)

for row, label in zip(all_rows_midi, labels1):

    track.append(MetaMessage('lyrics', text=label, time=0))

    for note in row:
        track.append(Message('note_on', note=note, velocity=64, time=0))
        track.append(Message('note_off', note=note, velocity=64, time=note_duration))

mid.save("twelve_tone_48_bars.mid")
