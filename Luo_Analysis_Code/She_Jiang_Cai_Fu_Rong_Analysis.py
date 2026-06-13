
from music21 import *

us = environment.UserSettings()

# Specify the executable file path for MuseScore 4
# Windows ：
us['musescoreDirectPNGPath'] = r'D:\Program Files (x86)\bin\MuseScore4.exe'

# Mac ：
# us['musescoreDirectPNGPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'

# Linux ：
# us['musescoreDirectPNGPath'] = '/usr/bin/mscore'

# Temporary directory
us['directoryScratch'] = r"D:\dev\temp"

import requests
import os
import hashlib
import subprocess

# ==========================
# Configure directories and MuseScore4 paths

temp_dir = r"D:\dev\temp"
os.makedirs(temp_dir, exist_ok=True)

# MuseScore 可执行文件路径
#Path to MuseScore executable file
musescore_path = r"D:\Program Files (x86)\bin\MuseScore4.exe"
if not os.path.isfile(musescore_path):
    raise FileNotFoundError(f"MuseScore executable not found at {musescore_path}")

# ==========================
# Download the MusicXML file from GitHub  https://github.com/Yvonne6475/My-music-Corpus-Library

file_url = "https://raw.githubusercontent.com/Yvonne6475/My-music-Corpus-Library/refs/heads/main/%E6%B6%89%E6%B1%9F%E9%87%87%E8%8A%99%E8%93%89%20She%20Jiang%20Cai%20Fu%20Rong.musicxml"

print("Downloading from:", file_url)
response = requests.get(file_url)
response.raise_for_status()
content = response.content
print("Downloaded bytes:", len(content))

# Generate file hashes to prevent duplicates
file_hash = hashlib.md5(content).hexdigest()[:8]

# save MusicXML in the temporary directory D:\dev\temp
xml_filename = f"SheJiangCai_{file_hash}.musicxml"
xml_path = os.path.join(temp_dir, xml_filename)
with open(xml_path, 'wb') as f:
    f.write(content)

print("Saved MusicXML file:", xml_path)

# ==========================
# 用 MuseScore CLI 生成 PNG
#Generate PNG using MuseScore CLI

png_filename = f"SheJiangCai_{file_hash}.png"
png_path = os.path.join(temp_dir, png_filename)

# 调用 MuseScore CLI 渲染 PNG
#Rendering PNG using the MuseScore CLI
# Rendering PNG using the MuseScore CLI
subprocess.run([
    musescore_path,
    xml_path,
    '-o', png_path
], check=True)

print("Generated PNG at:", png_path)


# ========================== also download the midi format
import requests
import os
import hashlib
import subprocess

# Configuration Directory and MuseScore Path
temp_dir = r"D:\dev\temp"
os.makedirs(temp_dir, exist_ok=True)

# Path to MuseScore4 executable file
musescore_path = r"D:\Program Files (x86)\bin\MuseScore4.exe"
if not os.path.isfile(musescore_path):
    raise FileNotFoundError(f"MuseScore executable not found at {musescore_path}")

# Download MIDI file
file_url = "https://raw.githubusercontent.com/Yvonne6475/My-music-Corpus-Library/refs/heads/main/SheJiangCaiFuRong.mid"

print("Downloading from:", file_url)
response = requests.get(file_url)
response.raise_for_status()
content = response.content
print("Downloaded bytes:", len(content))

# Generate file hashes to prevent duplicates
file_hash = hashlib.md5(content).hexdigest()[:8]

# save MIDI in the temporary directory D:\dev\temp
midi_filename = f"SheJiangCai_{file_hash}.mid"
midi_path = os.path.join(temp_dir, midi_filename)
with open(midi_path, 'wb') as f:
    f.write(content)

print("Saved MIDI file:", midi_path)

# Download and save the mei format file form GitHub by url
# Download MEI file
import requests
import os
import hashlib
from music21 import converter

mei_url = "https://raw.githubusercontent.com/Yvonne6475/My-music-Corpus-Library/refs/heads/main/%E6%B6%89%E6%B1%9F%E9%87%87%E8%8A%99%E8%93%89%20She%20Jiang%20Cai%20Fu%20Rong.mei"

print("Downloading from:", mei_url)
response = requests.get(mei_url)
response.raise_for_status()
content = response.content
print("Downloaded bytes:", len(content))

# Generate file hash (prevent duplicate filename)
file_hash = hashlib.md5(content).hexdigest()[:8]

# Ensure temp directory exists
temp_dir = r"D:\dev\temp"
os.makedirs(temp_dir, exist_ok=True)

# Save MEI with hash in filename
mei_filename = f"SheJiangCai_{file_hash}.mei"
mei_path = os.path.join(temp_dir, mei_filename)

with open(mei_path, "wb") as f:
    f.write(content)

print("Saved MEI file:", mei_path)

# Parse MEI using music21
score = converter.parse(mei_path)

print("Parsed successfully!")


# ==========================
# # Open Musicxml file using the MuseScore GUI (pop-up window)
# 用 MuseScore GUI 打开 Musicxml（弹出窗口）
subprocess.Popen([
    musescore_path,
    xml_path
])


# =========================
# Generate the necessary graph
from music21 import *
from music21 import graph


score = converter.parse(mei_path)

# Note Quarter Length by Pitch of all parts (figure 1)
p = score.measures(1, 30).plot(show=False)
p.figure.set_size_inches(18, 18)

import matplotlib.pyplot as plt
plt.show()


# Note Quarter Length by Pitch of selected part figure 2
score_part = score.parts[1]
selected_measures = score_part.measures(1, 5)
selected_measures.plot()
plt.show()

#plot histogram and PitchClass Chart figure 3
score.plot('histogram', 'pitchClass')
plt.show()

#plot PitchClassQuarterLength figure 4
p = graph.plot.ScatterWeightedPitchClassQuarterLength(score.measures(1, 10))
p.run()

# Count of Pitch and Quarter Length figure 5
score.measures(1, 10).plot('scatter', 'measure', 'pitchClass')
plt.show()

#Here we can see each part plotted when it plays and with dynamics: figure 6
from music21 import converter

score = converter.parse(midi_path)
score.measures(1,29).plot('horizontalbarweighted')
plt.show()

# show as 3d bars
score.plot('3dbars')


#Mark the pitch class and names and forte class on the .mei file and save it to a temporary file.
from music21 import *
from pathlib import Path
from datetime import datetime

score = converter.parse(mei_path)
excerpt = score.measures(1, 30)

for n in excerpt.recurse().notes:

    # single notes
    if isinstance(n, note.Note):
        # pitch class
        n.addLyric(str(n.pitch.pitchClass))
        # pitch name
        n.addLyric(n.nameWithOctave)

    # chords
    # 和弦
    elif isinstance(n, chord.Chord):
        sorted_pitches = sorted(n.pitches)


        for p in sorted_pitches:
            n.addLyric(str(p.pitchClass))  # pitch class
            n.addLyric(p.nameWithOctave)  # name

        n.addLyric(n.forteClass)


# ==========================
# 自动命名 + 导出 PDF 和 MusicXML
# Automatic Naming + Export to PDF and MusicXML

output_dir = r"D:\dev\temp"
Path(output_dir).mkdir(exist_ok=True)

piece_name = Path(mei_path).stem
start_measure = 1
end_measure = 30
analysis_type = "pc_forte"
date_str = datetime.now().strftime("%Y%m%d")

base_filename = f"{piece_name}_m{start_measure}-{end_measure}_{analysis_type}_{date_str}"

musicxml_path = Path(output_dir) / f"{base_filename}.musicxml"
pdf_path = Path(output_dir) / f"{base_filename}.pdf"

# 导出
#Export
excerpt.write('musicxml', musicxml_path)
excerpt.write('musicxml.pdf', pdf_path)

excerpt.show()
print("\n=== Analysis Export Complete ===")
print("MusicXML saved at:", musicxml_path)
print("PDF saved at:", pdf_path)

#Voice Diagnose

from music21 import *
score = converter.parse(midi_path)
print("Score loaded successfully")
print(f"Number of parts detected: {len(score.parts)}\n")


# ==========================
# 声部诊断函数 Voice Diagnosis Function

def diagnose_part(part, index):
    notes = [n for n in part.recurse().notes]
    pitches = [n.pitch.midi for n in notes if n.isNote]

    return {
        "index": index,
        "partName": part.partName if part.partName else "Unnamed",
        "note_count": len(notes),
        "note_only_count": len([n for n in notes if n.isNote]),
        "chord_count": len([n for n in notes if n.isChord]),
        "avg_pitch": round(sum(pitches) / len(pitches), 2) if pitches else None,
        "pitch_range": (min(pitches), max(pitches)) if pitches else None,
        "staff_count": len(part.getElementsByClass('Staff')),
        "instruments": [i.instrumentName for i in part.getInstruments() if i.instrumentName]
    }

# ==========================
# 打印声部诊断
# Print Part Diagnosis
# ==========================
diagnostics = []
for i, part in enumerate(score.parts):
    d = diagnose_part(part, i)
    diagnostics.append(d)

    print(f"Part {i + 1}")
    print(f"  Name: {d['partName']}")
    print(f"  Instrument(s): {', '.join(d['instruments']) if d['instruments'] else 'Not specified'}")
    print(f"  Staff count: {d['staff_count']}")
    print(f"  Total notes (notes + chords): {d['note_count']}")
    print(f"  Single notes only: {d['note_only_count']}")
    print(f"  Chords: {d['chord_count']}")
    if d["pitch_range"]:
        print(f"  Pitch range (MIDI): {d['pitch_range'][0]} – {d['pitch_range'][1]}")
        print(f"  Average pitch (MIDI): {d['avg_pitch']}")
    else:
        print("  Pitch information: none")
    print()

# Try to find the 12-tone row
# 自动选择旋律声部（单音最多）
# Automatic selection of melody part (single voice maximum)

melody_candidates = [(part, d, d["note_only_count"]) for part, d in zip(score.parts, diagnostics)]
melody_part, melody_info, melody_note_count = max(melody_candidates, key=lambda x: x[2])

print("Automatically selected melody part")
print(f"Part index: {melody_info['index'] + 1}")
print(f"Name: {melody_info['partName']}")
print(f"Number of single notes: {melody_note_count}\n")

# ==========================
# 提取前 12 个音
# Extract the first 12 notes
def extract_first_12_notes(part):
    result = []
    for el in part.recurse():
        if isinstance(el, note.Note):
            result.append((el.pitch.name, el.pitch.pitchClass))
        elif isinstance(el, chord.Chord):
            top = el.sortAscending()[-1]
            result.append((top.pitch.name, top.pitch.pitchClass))
        if len(result) >= 12:
            break
    return result

melody_notes = extract_first_12_notes(melody_part)
print("First 12 notes of the selected melody part")
print("-" * 60)
if melody_notes:
    print(", ".join([f"{name}({pc})" for name, pc in melody_notes]))
else:
    print("No sufficient notes found")

# create 4 forms of 12-tone row
from music21 import stream, note, metadata
from pathlib import Path

# ==========================
# 原始十二音列
#prime form
P = [6, 8, 11, 1, 4, 9, 7, 10, 0, 3, 5, 2]

# 工具函数：把 pitch-class 列表转换为 music21 Stream
# Utility function: Convert pitch-class list to music21 Stream

def make_stream(pc_list, name):
    s = stream.Part()
    s.insert(0, metadata.Metadata())
    s.metadata.title = name

    for pc in pc_list:
        n = note.Note()
        n.pitch.midi = pc + 60  # 映射到 C4 附近
        n.quarterLength = 1

        # 添加歌词：第一行整数，第二行音名
        n.addLyric(str(pc))
        n.addLyric(n.pitch.name)

        s.append(n)
    return s

# 生成四种形式
#Generate four forms
P_row = P
P_label = f"P{P_row[0]}"

pivot = P[0]
I_row = [(2 * pivot - p) % 12 for p in P]
I_label = f"I{I_row[0]}"

R_row = list(reversed(P))
R_label = f"R{R_row[0]}"

RI_row = [(2 * pivot - p) % 12 for p in R_row]
RI_label = f"RI{RI_row[0]}"

# 保存到字典方便循环
#Save to dictionary for convenient iteration
forms = {
    P_label: P_row,
    R_label: R_row,
    I_label: I_row,
    RI_label: RI_row
}

# 打印四个形式
#Print four forms
# ==========================
print("=== Twelve-Tone Forms ===\n")
for label, row in forms.items():
    print(f"{label} = {row}")
print("\n=== End of Forms ===\n")

# 输出 PNG
# Output PNG
output_dir = Path("D:/dev/temp")
output_dir.mkdir(exist_ok=True)

for label, row in forms.items():
    part = make_stream(row, label)

    png_path = output_dir / f"{label}.png"

    # 导出 PNG
    # Export PNG
    part.write("musicxml.png", png_path)

    print(f"{label} PNG saved at: {png_path}")

print("\nAll four forms exported successfully.")

# create the 12-tone matrix
ttr = serial.TwelveToneRow([6, 8, 11, 1, 4, 9, 7, 10, 0, 3, 5, 2])
aMatrix = ttr.matrix()
print(aMatrix)         # A = 10  B = 11 0 == 12

#to do inclusion lattice
# Generate a visualised 12-tone row matrix diagram

import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Prime Row
prime_row = [6, 8, 11, 1, 4, 9, 7, 10, 0, 3, 5, 2]
note_names = ['C', 'C#', 'D', 'D#', 'E', 'F',
              'F#', 'G', 'G#', 'A', 'A#', 'B']

# -----------------------------
# 生成 12 音矩阵
#Generate a 12-tone matrix
def generate_12tone_matrix(row):
    matrix = np.zeros((12,12), dtype=int)
    matrix[0,:] = row  # 第一行 = Prime Row
    for i in range(1,12):
        interval = (row[i] - row[0]) % 12
        for j in range(12):
            matrix[i,j] = (row[j] - interval) % 12
    return matrix

matrix = generate_12tone_matrix(prime_row)

# -----------------------------
# Visualisation Matrix
fig, ax = plt.subplots(figsize=(8,8))  # 调小 figure
cax = ax.matshow(matrix, cmap='tab20', vmin=0, vmax=11)

# Set scale (1–12)
ax.set_xticks(range(12))
ax.set_yticks(range(12))
ax.set_xticklabels(range(1,13))
ax.set_yticklabels(range(1,13))

# Add P/I/R/RI annotations
# row_labels = ['P'] + ['I'+str(i) for i in range(1,12)]
# col_labels = ['P'] + ['R'+str(i) for i in range(1,12)]
# ax.set_yticklabels(row_labels, rotation=0)
# ax.set_xticklabels(col_labels, rotation=90)
prime_start = prime_row[0]  # Prime Row 的起始音，例如 6 -> F#

# 行标签 label：P/I
row_labels = ['P'+str(prime_start)] + ['I'+str(matrix[i,0]) for i in range(1,12)]
# 列标签：P/R
col_labels = ['P'+str(prime_start)] + ['R'+str(matrix[0,j]) for j in range(1,12)]

ax.set_yticklabels(row_labels, rotation=0)
ax.set_xticklabels(col_labels, rotation=90)

# Display the note name + integer in each cell
for i in range(12):
    for j in range(12):
        ax.text(j, i, f"{note_names[matrix[i,j]]}\n({matrix[i,j]})",
                va='center', ha='center', fontsize=10, color='black')

# Title & Colour Bar
plt.title("12-Tone Matrix (Prime Row Visualization)", fontsize=14)
plt.colorbar(cax, ticks=range(12), label="Pitch Class (0=C ... 11=B)")

plt.tight_layout()

# -----------------------------
# Save as a PNG file, high resolution
output_file = "../homework_code/12_tone_matrix.png"
plt.savefig(output_file, dpi=300)
print(f"Saved 12-tone matrix as '{output_file}'")

plt.show()


#Dividing the twelve-tone row into four sets of tritones
aRow =[6, 8, 11, 1, 4, 9, 7, 10, 0, 3, 5, 2]
bStream = stream.Stream()
for i in range(0, 12, 3):
    c = chord.Chord(aRow[i:i + 3])
    c.addLyric(c.primeFormString)
    c.addLyric(c.forteClass)
    bStream.append(c)
bStream.show()

#Dividing the twelve-tone row into three sets of tetrachords
aRow =[6, 8, 11, 1, 4, 9, 7, 10, 0, 3, 5, 2]
bStream2 = stream.Stream()
for i in range(0, 12, 4):
    c = chord.Chord(aRow[i:i + 4])
    c.addLyric(c.primeFormString)
    c.addLyric(c.forteClass)
    bStream2.append(c)
bStream2.show()



from music21 import converter, chord

# Manually setting the Part name (because mei format lack part information)
# You can set the parts using the information shows in the last block which diagnose the parts
custom_part_names = [
    "Soprano",
    "Piano RH",
    "Piano LH"
]
# Analyse only these parts (leave blank to analyse all parts)
selected_parts = ["Piano RH", "Piano LH"]  #todo: you can change parts here

# Analyse only the sections within these ranges (start_bar, end_bar); leaving blank indicates all.
bar_range = (1, 30)  #todo:you can change bar range here


score = converter.parse(mei_path)



for i, p in enumerate(score.parts):
    if i < len(custom_part_names):
        p.partName = custom_part_names[i]
    else:
        p.partName = f"Part {i+1}"

# 2. Extraction and analysis of chord data
results = []

for part in score.parts:
    part_name = part.partName

    if selected_parts and part_name not in selected_parts:
        continue

    for measure in part.getElementsByClass('Measure'):
        bar_number = measure.measureNumber

        if bar_range:
            start_bar, end_bar = bar_range
            if bar_number < start_bar or bar_number > end_bar:
                continue

        for element in measure.recurse():
            if isinstance(element, chord.Chord):
                notes = " ".join(p.nameWithOctave for p in element.pitches)
                normal_order = element.normalOrder
                forte = element.forteClass
                forte_tni = element.forteClassTnI
                pitch_range = (min(p.midi for p in element.pitches),
                               max(p.midi for p in element.pitches))

                results.append({
                    "bar": bar_number,
                    "offset": round(element.offset, 3),
                    "part_name": part_name,
                    "notes": notes,
                    "pc_set": normal_order,
                    "forte": forte,
                    "forte_tni": forte_tni,
                    "pitch_range": pitch_range
                })

# 3. Generate Markdown tables
md_lines = []
md_lines.append("| Bar | Offset | Part Name | Notes | Normal Order | Forte | Forte Tn/TnI | Pitch Range |")
md_lines.append("|-----|--------|-----------|-------|--------------|-------|---------------|-------------|")

for r in results:
    md_lines.append(
        f"| {r['bar']} | {r['offset']} | {r['part_name']} | "
        f"{r['notes']} | {r['pc_set']} | {r['forte']} | {r['forte_tni']} | "
        f"{r['pitch_range'][0]}–{r['pitch_range'][1]} |"
    )

markdown_output = "\n".join(md_lines)

print("\n=== Markdown Output (Filtered Chords) ===\n")
print(markdown_output)





