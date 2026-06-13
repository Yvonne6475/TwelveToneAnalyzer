# musicxml_fixed.py
import music21
from music21 import *
import requests
import tempfile
import hashlib
import warnings

# 抑制警告
warnings.filterwarnings("ignore", category=music21.exceptions21.MusicXMLWarning)

# 设置路径
env = music21.environment.UserSettings()
env['musicxmlPath'] = r'D:\Program Files (x86)\bin\MuseScore4.exe'
env['graphicsPath'] = r'D:\Program Files (x86)\BandiView\BandiView.exe'

# 修补有问题的函数
import music21.expressions

original_arpeggio_init = music21.expressions.ArpeggioMarkSpanner.__init__


def fixed_arpeggio_init(self, *args, **kwargs):
    # 过滤掉字符串参数，只保留音乐对象
    filtered_args = [arg for arg in args if not isinstance(arg, str)]
    if not filtered_args and args:
        # 如果没有有效的参数，创建一个空的 spanner
        print("警告: 过滤掉了 ArpeggioMarkSpanner 的字符串参数")
        super(music21.expressions.ArpeggioMarkSpanner, self).__init__(**kwargs)
    else:
        original_arpeggio_init(self, *filtered_args, **kwargs)


# 应用修补
music21.expressions.ArpeggioMarkSpanner.__init__ = fixed_arpeggio_init

# 下载文件
file_url = "https://raw.githubusercontent.com/Yvonne6475/My-music-Corpus-Library/refs/heads/main/%E6%B6%89%E6%B1%9F%E9%87%87%E8%8A%99%E8%93%89%20She%20Jiang%20Cai%20Fu%20Rong.musicxml"

print("Downloading from:", file_url)
response = requests.get(file_url)
response.raise_for_status()
content = response.content
print("Downloaded bytes:", len(content))

# 保存到临时文件
file_hash = hashlib.md5(content).hexdigest()[:8]
with tempfile.NamedTemporaryFile(mode='wb', suffix=f'_{file_hash}.musicxml', delete=False) as f:
    f.write(content)
    temp_filename = f.name

print("Using MusicXML file:", temp_filename)
print("File hash:", file_hash)

try:
    # 尝试解析
    score = converter.parse(temp_filename)
    print("解析成功!")

    # 显示前30小节
    excerpt = score.measures(1, 30)
    excerpt.show()

    # 绘制前5小节的图形
    score.measures(1, 5).plot()

except Exception as e:
    print(f"解析失败: {e}")
    print("\n尝试使用 MuseScore 进行解析...")

    # 使用外部程序解析
    try:
        score = converter.parse(temp_filename, format='musicxml', forceSource=True)
        print("使用外部解析成功!")

        excerpt = score.measures(1, 30)
        excerpt.show()
        score.measures(1, 5).plot()

    except Exception as e2:
        print(f"外部解析也失败: {e2}")

        # 最后尝试：创建简单的乐谱示例
        print("\n创建示例乐谱...")
        from music21 import stream, note, meter, tempo, metadata

        # 创建一个简单的乐谱
        s = stream.Score()
        s.metadata = metadata.Metadata()
        s.metadata.title = "示例乐谱"

        # 创建一个声部
        part = stream.Part()
        part.insert(0, meter.TimeSignature('4/4'))
        part.insert(0, tempo.MetronomeMark(number=120))

        # 添加一些音符
        for pitch_name in ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5']:
            n = note.Note(pitch_name)
            n.duration.type = 'quarter'
            part.append(n)

        s.append(part)
        s.show()
        s.measures(1, 4).plot()