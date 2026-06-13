from music21 import *

# === MuseScore path (for display) ===
us = environment.UserSettings()
us['musicxmlPath'] = r"D:\Program Files (x86)\bin\MuseScore4.exe"  # ← 修改为你本地路径

# === Load the score ===
file_path = r"C:\Users\Yvonne wang\OneDrive - Durham University\桌面\webern_dormi_jesu_op_16_no_2 new.mxl"
score = converter.parse(file_path)


