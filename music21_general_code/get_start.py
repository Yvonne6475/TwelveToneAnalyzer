# get_start_fixed.py
import music21
from music21 import *

# 使用你提供的路径 - 正确的设置方式
env = music21.environment.UserSettings()
env['musicxmlPath'] = r'D:\Program Files (x86)\bin\MuseScore4.exe'
env['graphicsPath'] = r'D:\Program Files (x86)\BandiView\BandiView.exe'

# 你的原始代码
opus132 = corpus.parse('beethoven/opus132')
opus132.measures(1, 60).show()
print("🎵 成功显示乐谱！")
opus132.measures(1, 60).plot()