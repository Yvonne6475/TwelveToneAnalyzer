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

file_url = "https://raw.githubusercontent.com/Yvonne6475/My-music-Corpus-Library/refs/heads/main/Luo's_String_Quartet_No.2_full_score.musicxml"
print("Downloading from:", file_url)
response = requests.get(file_url)
response.raise_for_status()
content = response.content
print("Downloaded bytes:", len(content))

# Generate file hashes to prevent duplicates
file_hash = hashlib.md5(content).hexdigest()[:8]

# save MusicXML in the temporary directory D:\dev\temp
xml_filename = f"String_Quartet{file_hash}.musicxml"
xml_path = os.path.join(temp_dir, xml_filename)
with open(xml_path, 'wb') as f:
    f.write(content)

print("Saved MusicXML file:", xml_path)

# ==========================
# 用 MuseScore CLI 生成 PNG
#Generate PNG using MuseScore CLI

#png_filename = f"Luo_String_Quartet_No.2{file_hash}.png"
#png_path = os.path.join(temp_dir, png_filename)

# 调用 MuseScore CLI 渲染 PNG
#Rendering PNG using the MuseScore CLI
# Rendering PNG using the MuseScore CLI
#subprocess.run([
    #musescore_path,
   # xml_path,
    #'-o', png_path
#], check=True)

#print("Generated PNG at:", png_path)


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
file_url = "https://github.com/Yvonne6475/My-music-Corpus-Library/raw/refs/heads/main/Luo's_String_Quartet_No.2_full_score.mid"

print("Downloading from:", file_url)
response = requests.get(file_url)
response.raise_for_status()
content = response.content
print("Downloaded bytes:", len(content))

# Generate file hashes to prevent duplicates
file_hash = hashlib.md5(content).hexdigest()[:8]

# save MIDI in the temporary directory D:\dev\temp
midi_filename = f"Luo_String_Quartet_No.2{file_hash}.mid"
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

mei_url = "https://github.com/Yvonne6475/My-music-Corpus-Library/raw/refs/heads/main/Luo's_String_Quartet_No.2_full_score.mei"
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
mei_filename = f"Luo_String_Quartet_No.2{file_hash}.mei"
mei_path = os.path.join(temp_dir, mei_filename)

with open(mei_path, "wb") as f:
    f.write(content)

print("Saved MEI file:", mei_path)

# Parse File using music21
score = converter.parse(xml_path)
# 获取总谱最大小节，全局复用
score = converter.parse(xml_path)
# 读取全部小节
all_measures = list(score.flatten().getElementsByClass('Measure'))
if all_measures:
    max_total_measure = max(m.number for m in all_measures)
else:
    # 读取不到小节，设置默认上限272（你原曲总小节）
    max_total_measure = 272
print(f"Parsed successfully! 全曲总小节数：{max_total_measure}")

#Voice Diagnose
from music21 import *
midi_score = converter.parse(midi_path)
print("Score loaded successfully")
print(f"Number of parts detected: {len(midi_score.parts)}\n")

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
diagnostics = []
for i, part in enumerate(midi_score.parts):
    d = diagnose_part(part, i)
    diagnostics.append(d)
    print(f"Part {i + 1}")
    print(f"  编号index: {i} | 名称name: {d['partName']}")
    print(f"  Single notes only: {d['note_only_count']}")
    print()

# ==========================
# # Open Musicxml file using the MuseScore GUI (pop-up window)
subprocess.Popen([
    musescore_path,
    xml_path
])

# =========================
# Generate the necessary graph
from music21 import *
from music21 import graph
import matplotlib.pyplot as plt

main_score = converter.parse(xml_path)

# Figure1 全总谱图
p = main_score.measures(1, max_total_measure).plot(show=False)
p.figure.set_size_inches(18, 18)
plt.show()

# ====================== 交互1：选择声部 + 选择小节区间（第二张图） ======================
print("\n======== 可选择声部列表 ========")
for idx, d in enumerate(diagnostics):
    print(f"编号{idx} | 声部：{d['partName']} | 单音符：{d['note_only_count']}")

# 循环输入，直到找到有音符的声部
while True:
    try:
        SELECT_IDX = int(input("请输入绘图声部编号(0/1/2/3)："))
        # 判断编号合法
        if SELECT_IDX < 0 or SELECT_IDX >= len(diagnostics):
            print("编号超出范围，只能输入0、1、2、3，请重新输入！")
            continue
        # 判断该声部是否存在单音符
        target_info = diagnostics[SELECT_IDX]
        if target_info["note_only_count"] <= 0:
            print(f"警告：声部{SELECT_IDX}没有单音符，无法绘图，请换一个声部！")
            continue
        # 合法且有音符，跳出循环
        break
    except ValueError:
        print("输入不是数字，请重新输入！")

print(f"\n可选择小节范围：1 ~ {max_total_measure}")
start_fig2 = int(input("输入第二张图起始小节："))
end_fig2 = int(input("输入第二张图结束小节："))

EN_NAMES = ["Violin I", "Violin II", "Viola", "Cello"]
SELECT_EN_PART = EN_NAMES[SELECT_IDX]
melody_part = midi_score.parts[SELECT_IDX]
melody_info = diagnostics[SELECT_IDX]
# =================================================================

# Note Quarter Length by Pitch of selected part figure 2
score_part = main_score.parts[SELECT_IDX]
selected_measures = score_part.measures(start_fig2, end_fig2)
selected_measures.plot()
plt.show()

#plot histogram and PitchClass Chart figure 3
main_score.plot('histogram', 'pitchClass')
plt.show()

# ====================== Figure4 散点图：PitchClassQuarterLength 小节选择 ======================
print(f"\nFigure4 音级-时值散点图，可选小节范围 1 ~ {max_total_measure}")
while True:
    try:
        f4_s = int(input("Figure4 起始小节："))
        f4_e = int(input("Figure4 结束小节："))
        if 1 <= f4_s <= f4_e <= max_total_measure:
            break
        print(f"区间非法，必须 1 ≤ 起始 ≤ 结束 ≤ {max_total_measure}，重输")
    except ValueError:
        print("请输入纯数字小节号")

#plot PitchClassQuarterLength figure 4
p = graph.plot.ScatterWeightedPitchClassQuarterLength(main_score.measures(f4_s, f4_e))
p.run()

# ====================== Figure5 音级散点图 小节选择 ======================
print(f"\nFigure5 小节-音级分布图，可选小节范围 1 ~ {max_total_measure}")
while True:
    try:
        f5_s = int(input("Figure5 起始小节："))
        f5_e = int(input("Figure5 结束小节："))
        if 1 <= f5_s <= f5_e <= max_total_measure:
            break
        print(f"区间非法，必须 1 ≤ 起始 ≤ 结束 ≤ {max_total_measure}，重输")
    except ValueError:
        print("请输入纯数字小节号")

# Count of Pitch and Quarter Length figure 5
main_score.measures(f5_s, f5_e).plot('scatter', 'measure', 'pitchClass')
plt.show()

from music21 import converter
import matplotlib.pyplot as plt

score = converter.parse(midi_path)




print(f"\nFigure6 horizontalbarweighted，可选小节范围 1 ~ {max_total_measure}")
# 循环输入合法区间，无长度限制
while True:
    try:
        f6_s = int(input("Figure6 起始小节："))
        f6_e = int(input("Figure6 结束小节："))
        if 1 <= f5_s <= f5_e <= max_total_measure:
            break
        print(f"区间非法，必须 1 ≤ 起始 ≤ 结束 ≤ {max_total_measure}，重输")
    except ValueError:
        print("请输入纯数字小节号")

# 绘图
slice_score = score.measures(f6_s, f6_e)
slice_score.plot('horizontalbarweighted')
plt.show()

from music21 import converter, graph


score = converter.parse(midi_path)

# 绘制3D音高柱状图，自定义18*18尺寸
plot_3d = score.plot('3dbars', show=False)
plot_3d.figure.set_size_inches(50, 50)
plt.tight_layout()
plt.show()

# ====================== 交互2：选择导出带标记乐谱的小节范围 ======================
print(f"\n导出带音级/福特标签乐谱，小节可选范围 Sheet music with musical notation and Ford labels; selectable bar range：1 ~ {max_total_measure}")
start_export = int(input("输入导出起始小节 Enter the starting bar for export："))
end_export = int(input("输入导出结束小节 End of the Export section："))
# =================================================================

excerpt = main_score.measures(start_export, end_export)
for n in excerpt.recurse().notes:
    if isinstance(n, note.Note):
        n.addLyric(str(n.pitch.pitchClass))
        n.addLyric(n.nameWithOctave)
    elif isinstance(n, chord.Chord):
        sorted_pitches = sorted(n.pitches)
        for p in sorted_pitches:
            n.addLyric(str(p.pitchClass))
            n.addLyric(p.nameWithOctave)
        n.addLyric(n.forteClass)
from pathlib import Path
from datetime import datetime
# 自动命名 + 导出 PDF 和 MusicXML
output_dir = r"D:\dev\temp"
Path(output_dir).mkdir(exist_ok=True)
piece_name = Path(xml_path).stem
analysis_type = "pc_forte"
date_str = datetime.now().strftime("%Y%m%d")
base_filename = f"{piece_name}_m{start_export}-{end_export}_{analysis_type}_{date_str}"
musicxml_path = Path(output_dir) / f"{base_filename}.musicxml"
pdf_path = Path(output_dir) / f"{base_filename}.pdf"
excerpt.write('musicxml', musicxml_path)
excerpt.write('musicxml.pdf', pdf_path)
excerpt.show()
print("\n=== Analysis Export Complete ===")
print("MusicXML saved at:", musicxml_path)
print("PDF saved at:", pdf_path)



# 提取前 12 音函数
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

# 固定读取第0声部
melody_notes = extract_first_12_notes(midi_score.parts[0])
print("First 12 notes of part 0 (Violin I)")
print("-" * 60)
if melody_notes:
    print(", ".join([f"{name}({pc})" for name, pc in melody_notes]))
else:
    print("No notes found in part 0")

# ========== 自动提取音列 + 确认正误交互 ==========
# 先提取现有音级
if len(melody_notes) >= 12:
    auto_row = [pc for name, pc in melody_notes[:12]]
    print(f"\n自动提取十二音原型音列：{auto_row}")
else:
    auto_row = []
    print(f"\n第0声部音符不足12个，无自动音列")

# 确认是否正确，循环直到输入y/n
while True:
    confirm = input("当前音列是否正确？正确输入 y，错误输入 n：").strip().lower()
    if confirm in ("y", "n"):
        break
    print("输入无效，请只输入 y 或 n")

row_pc_list = []
if confirm == "y":
    # 使用自动提取的音列
    row_pc_list = auto_row
    print(f"确认使用自动提取音列：{row_pc_list}")
else:
    # 手动输入完整12个音级
    print("\n请手动输入12个音级数字（0~11，空格分隔）")
    while True:
        try:
            input_str = input("一次性输入12个数字：")
            nums = list(map(int, input_str.strip().split()))
            if len(nums) != 12:
                print(f"需要恰好12个数字，当前输入{len(nums)}个，重新输入")
                continue
            if not all(0 <= x <= 11 for x in nums):
                print("数字范围必须是 0~11，重新输入")
                continue
            row_pc_list = nums
            print(f"手动输入音列已保存：{row_pc_list}")
            break
        except ValueError:
            print("包含非数字字符，请输入纯数字")

# create 4 forms of 12-tone row
from music21 import stream, note, metadata
P = row_pc_list

def make_stream(pc_list, name):
    s = stream.Part()
    s.insert(0, metadata.Metadata())
    s.metadata.title = name
    for pc in pc_list:
        n = note.Note()
        n.pitch.midi = pc + 60
        n.quarterLength = 1
        n.addLyric(str(pc))
        n.addLyric(n.pitch.name)
        s.append(n)
    return s

P_row = P
P_label = f"P{P_row[0]}"
pivot = P[0]
I_row = [(2 * pivot - p) % 12 for p in P]
I_label = f"I{I_row[0]}"

R_row = list(reversed(P))
R_label = f"R{R_row[0]}"

RI_row = [(2 * pivot - p) % 12 for p in R_row]
RI_label = f"RI{RI_row[0]}"

forms = {
    P_label: P_row,
    R_label: R_row,
    I_label: I_row,
    RI_label: RI_row
}

print("=== Twelve-Tone Forms ===\n")
for label, row in forms.items():
    print(f"{label} = {row}")
print("\n=== End of Forms ===\n")

# 输出四种音列PNG
output_dir = Path("D:/dev/temp")
output_dir.mkdir(exist_ok=True)
for label, row in forms.items():
    part = make_stream(row, label)
    png_path = output_dir / f"{label}.png"
    part.write("musicxml.png", png_path)
    print(f"{label} PNG saved at: {png_path}")
print("\nAll four forms exported successfully.")


from pathlib import Path
save_dir = Path(r"D:\dev\temp")
save_dir.mkdir(exist_ok=True)

# 使用前面确认好的十二音序列（自动提取/手动输入统一变量 row_pc_list）
aRow = row_pc_list





# create the 12-tone matrix
ttr = serial.TwelveToneRow(row_pc_list)
aMatrix = ttr.matrix()
print(aMatrix)

# 绘制十二音矩阵图
import numpy as np
import matplotlib.pyplot as plt

prime_row = row_pc_list
note_names = ['C', 'C#', 'D', 'D#', 'E', 'F',
              'F#', 'G', 'G#', 'A', 'A#', 'B']

def generate_12tone_matrix(row):
    matrix = np.zeros((12,12), dtype=int)
    matrix[0,:] = row
    for i in range(1,12):
        interval = (row[i] - row[0]) % 12
        for j in range(12):
            matrix[i,j] = (row[j] - interval) % 12
    return matrix

matrix = generate_12tone_matrix(prime_row)

fig, ax = plt.subplots(figsize=(8,8))
cax = ax.matshow(matrix, cmap='tab20', vmin=0, vmax=11)
ax.set_xticks(range(12))
ax.set_yticks(range(12))
ax.set_xticklabels(range(1,13))
ax.set_yticklabels(range(1,13))

prime_start = prime_row[0]
row_labels = ['P'+str(prime_start)] + ['I'+str(matrix[i,0]) for i in range(1,12)]
col_labels = ['P'+str(prime_start)] + ['R'+str(matrix[0,j]) for j in range(1,12)]

ax.set_yticklabels(row_labels, rotation=0)
ax.set_xticklabels(col_labels, rotation=90)

for i in range(12):
    for j in range(12):
        ax.text(j, i, f"{note_names[matrix[i,j]]}\n({matrix[i,j]})",
                va='center', ha='center', fontsize=10, color='black')

plt.title("12-Tone Matrix (Prime Row Visualization)", fontsize=14)
plt.colorbar(cax, ticks=range(12), label="Pitch Class (0=C ... 11=B)")
plt.tight_layout()

matrix_folder = Path(r"D:\dev\temp")
matrix_folder.mkdir(exist_ok=True)
output_file = matrix_folder / "12_tone_matrix.png"
plt.savefig(output_file, dpi=300)
print(f"Saved 12-tone matrix as '{output_file}'")
plt.show()


from music21 import converter, chord

# ======================交互三 和弦分析：自定义小节区间 + 多选声部 ======================
print(f"\n===== 和弦提取设置 =====")
print(f"全曲可用小节范围：1 ~ {max_total_measure}")

# 1. 循环输入合法小节区间
while True:
    try:
        chord_start = int(input("请输入和弦分析【起始小节】："))
        chord_end = int(input("请输入和弦分析【结束小节】："))
        # 区间校验
        if 1 <= chord_start <= chord_end <= max_total_measure:
            break
        else:
            print(f"输入区间非法！必须满足：1 ≤ 起始 ≤ 结束 ≤ {max_total_measure}，请重新输入\n")
    except ValueError:
        print("输入不是数字，请输入纯数字小节号\n")

# 定义区间变量，供下方循环解包使用
bar_range = (chord_start, chord_end)

# 2. 打印全部声部，支持多选输入
print("\n可选声部列表：")
for idx, name in enumerate(EN_NAMES):
    print(f"编号 {idx}  →  {name}")
print("多声部同时分析：空格隔开编号，示例：0 2 3")

# 循环校验声部输入
while True:
    input_part_str = input("输入需要提取和弦的声部编号：").strip()
    try:
        idx_list = list(map(int, input_part_str.split()))
        # 校验每个编号在0~3之间
        valid_flag = True
        for num in idx_list:
            if num < 0 or num > 3:
                valid_flag = False
                break
        if not valid_flag:
            print("存在无效声部编号，仅支持 0/1/2/3，请重新输入\n")
            continue
        # 编号转英文声部名
        selected_parts = [EN_NAMES[i] for i in idx_list]
        print(f"已选中分析声部：{selected_parts}")
        break
    except ValueError:
        print("包含非数字字符，仅输入数字、空格分隔\n")

# 加载总谱，统一标准化声部名称
score = converter.parse(xml_path)
for i, p in enumerate(score.parts):
    if i < len(EN_NAMES):
        p.partName = EN_NAMES[i]
    else:
        p.partName = f"Part {i+1}"

# 遍历提取和弦
results = []
start_bar, end_bar = bar_range
for part in score.parts:
    part_name = part.partName
    # 只保留选中声部
    if part_name not in selected_parts:
        continue
    for measure in part.getElementsByClass('Measure'):
        bar_number = measure.number
        # 过滤小节范围
        if not (start_bar <= bar_number <= end_bar):
            continue
        # 遍历小节内所有和弦
        for elem in measure.recurse():
            if isinstance(elem, chord.Chord):
                note_names = " ".join(p.nameWithOctave for p in elem.pitches)
                normal_form = elem.normalOrder
                forte_set = elem.forteClass
                pitch_min = min(p.midi for p in elem.pitches)
                pitch_max = max(p.midi for p in elem.pitches)
                results.append({
                    "bar": bar_number,
                    "offset": round(elem.offset, 3),
                    "part_name": part_name,
                    "notes": note_names,
                    "pc_set": normal_form,
                    "forte": forte_set,
                    "pitch_range": f"{pitch_min}~{pitch_max}"
                })

# 生成Markdown表格
md_lines = [
    "| Bar | Offset | Part Name | Notes | Normal Order | Forte Class | Pitch Range |",
    "|-----|--------|-----------|-------|--------------|-------------|-------------|"
]
for row in results:
    line = (
        f"| {row['bar']} | {row['offset']} | {row['part_name']} | {row['notes']} "
        f"| {row['pc_set']} | {row['forte']} | {row['pitch_range']} |"
    )
    md_lines.append(line)

markdown_output = "\n".join(md_lines)
print("\n===== 和弦分析结果 Markdown 表格 =====")
print(markdown_output)