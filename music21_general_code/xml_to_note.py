from music21 import converter, note
from music21.braille.lookup import intervals

# 读取 MusicXML 文件（你可以把路径换成你实际的 XML 文件路径）
score = converter.parse("C:\\Users\\Yvonne wang\\OneDrive - Durham University\\桌面\\_Luo's String Quartet No 2 latest_.musicxml")

# 提取所有的音符
all_notes = score.recurse().getElementsByClass(note.Note)
# all_notes = score.recurse().getElementsByClass(intervals.Interval)

# 打印分析结果
for n in all_notes:
    print(f"音高: {n.nameWithOctave}")        # 如 C4
    print(f"时值: {n.quarterLength} 四分音符时值")  # 如 1.0 表示四分音符
    print(f"音名: {n.name}")                  # 如 C
    print(f"八度: {n.octave}")                # 如 4
    print('-' * 30)
