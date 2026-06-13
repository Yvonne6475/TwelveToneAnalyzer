from __future__ import print_function
import librosa.display
import warnings

warnings.filterwarnings('ignore')


import subprocess
import platform
from urllib.request import urlopen
import pathlib
import matplotlib.pyplot as plt
import io

# =========================================
# Download audio to temporary files
url = "https://github.com/Yvonne6475/My-music-Corpus-Library/raw/refs/heads/main/%E6%B6%89%E6%B1%9F%E9%87%87%E8%8A%99%E8%93%89%20She%20Jiang%20Cai%20Fu%20Rong.wav"
temp_dir = r"D:\dev\temp"
temp_file = r"D:\dev\temp\temp_audio.wav"

pathlib.Path(temp_dir).mkdir(parents=True, exist_ok=True)

with open(temp_file, "wb") as f:
    f.write(urlopen(url).read())

# =========================================
# 2. Read audio and plot waveform
y, sr = librosa.load(io.BytesIO(open(temp_file, "rb").read()), sr=22050, mono=True)
duration = len(y) / sr

plt.figure(figsize=(14, 4))
librosa.display.waveshow(y=y, sr=sr)
plt.title("Waveform")
plt.xlabel("Time (s)")
plt.ylabel("Amplitude")
plt.tight_layout()
plt.show()

# =========================================
# 3️. Play audio (system default player)

system = platform.system()
if system == "Windows":
    subprocess.run(["start", temp_file], shell=True)
elif system == "Darwin":  # macOS
    subprocess.run(["open", temp_file])
else:  # Linux
    subprocess.run(["xdg-open", temp_file])


import librosa.display
import numpy as np
import matplotlib.pyplot as plt
import os


hop_length = 1024
segment_duration = 30  # 秒
segment_samples = sr * segment_duration
total_segments = int(np.ceil(len(y) / segment_samples))

# Temporary storage path
temp_dir = r"D:\dev\temp"
os.makedirs(temp_dir, exist_ok=True)

plt.rcParams['figure.figsize'] = (18, 4)

for i in range(total_segments):
    start = i * segment_samples
    end = min((i + 1) * segment_samples, len(y))
    y_segment = y[start:end]

    # 计算频谱
    D = librosa.amplitude_to_db(
        np.abs(librosa.stft(y_segment, hop_length=hop_length)),
        ref=np.max
    )

    # plt the figure
    plt.figure(figsize=(18, 4))
    librosa.display.specshow(
        D,
        y_axis='log',
        sr=sr,
        hop_length=hop_length,
        x_axis='time',
        cmap='jet'
    )

    start_sec = start / sr
    end_sec = end / sr

    plt.title(f"Spectrogram - Segment {i + 1} ({start_sec:.1f} - {end_sec:.1f} sec)")
    plt.colorbar(format='%+2.0f dB')
    plt.tight_layout()

    # Save to the temporary directory
    filename = os.path.join(temp_dir, f"spectrogram_segment_{i+1}.png")
    plt.savefig(filename)
    print(f"Saved {filename}")

    # display
    plt.show()
    plt.close()


import librosa.display
import numpy as np
import matplotlib.pyplot as plt
import os

# =========================================
# 1️⃣ 音频路径或加载音频
# =========================================
audio_file = r"D:\dev\temp\temp_audio.wav"  # 已经下载好的音频

y, sr = librosa.load(audio_file, sr=22050, mono=True)
duration = len(y) / sr
print(f"Sample rate: {sr}, Duration: {duration:.2f} seconds")

# =========================================
# 2️⃣ 设置分段参数
# =========================================
segment_duration = 20  # 秒，可修改
segment_samples = sr * segment_duration
total_segments = int(np.ceil(len(y) / segment_samples))

# 临时目录保存图片
temp_dir = r"D:\dev\temp"
os.makedirs(temp_dir, exist_ok=True)

plt.rcParams['figure.figsize'] = (18, 6)

# =========================================
# 3️⃣ 分段计算 CQT Chromagram 并绘图
# =========================================
for i in range(total_segments):
    start = i * segment_samples
    end = min((i + 1) * segment_samples, len(y))
    y_segment = y[start:end]

    # 计算 CQT chromagram
    C = librosa.feature.chroma_cqt(y=y_segment, sr=sr, n_chroma=12, bins_per_octave=12)

    # 绘制
    plt.figure(figsize=(18, 6))
    librosa.display.specshow(
        librosa.amplitude_to_db(np.abs(C)),
        x_axis='time',
        y_axis='cqt_note',
        cmap='coolwarm'
    )

    start_sec = start / sr
    end_sec = end / sr
    plt.title(f'CQT Chromagram - Segment {i + 1} ({start_sec:.1f} - {end_sec:.1f} sec)')
    plt.colorbar(format='%+2.0f dB')
    plt.tight_layout()

    # 保存图片
    filename = os.path.join(temp_dir, f"chromagram_segment_{i+1}.png")
    plt.savefig(filename)
    print(f"Saved {filename}")

    # 显示
    plt.show()
    plt.close()

# Print the chromagram and the potential boundaries determined by the clustering.
import librosa.segment
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as mpt
import matplotlib.ticker as ticker
from pathlib import Path

# =========================================
audio_file = r"D:\dev\temp\temp_audio.wav"
audio_path = Path(audio_file)

if not audio_path.exists():
    raise FileNotFoundError(f"{audio_file} 不存在，请先下载音频。")

# =========================================
# Play audio

y, sr = librosa.load(audio_file, sr=22050, mono=True)
print(f"Sample rate: {sr}, Duration: {len(y)/sr:.2f} sec")

# =========================================
# Calculate chroma

chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
n_segments = 8  #Todo You can change here to divide it into several sections.
bounds = librosa.segment.agglomerative(chroma, n_segments)

# Convert frame to time
hop_length = 512
bound_times = librosa.frames_to_time(bounds, sr=sr, hop_length=hop_length)
print("Segment boundaries (seconds):", bound_times)

# =========================================
#  Plot and save to the temporary directory

temp_dir = Path(r"D:\dev\temp")
temp_dir.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(18, 6))
trans = mpt.blended_transform_factory(ax.transData, ax.transAxes)

librosa.display.specshow(chroma, y_axis='chroma', x_axis='time', sr=sr, hop_length=hop_length, ax=ax)

# Mark the boundary line
ax.vlines(bound_times, 0, 1, color='lime', linestyle='--',
          linewidth=2, alpha=0.9, transform=trans, label='Segment boundaries')

# Adjust the x-axis scale
ax.xaxis.set_major_locator(ticker.MultipleLocator(30))

# Adjust the y-axis scale
ax.set_yticks(np.arange(12))
ax.set_yticklabels(['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B'])

ax.set(title='Chromagram with Segment Boundaries')
ax.legend()
plt.tight_layout()

# Save image
output_file = temp_dir / "chromagram_segments.png"
plt.savefig(output_file)
print(f"Chromagram saved to {output_file}")

# Display image
plt.show()

# MFCCs
import librosa
import librosa.display
import librosa.segment
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as mpt
import sklearn.preprocessing
from pathlib import Path

# =========================================
audio_file = r"D:\dev\temp\temp_audio.wav"
audio_path = Path(audio_file)

if not audio_path.exists():
    raise FileNotFoundError(f"{audio_file} 不存在，请先下载音频。")

y, sr = librosa.load(audio_file, sr=22050, mono=True)
print(f"Sample rate: {sr}, Duration: {len(y)/sr:.2f} sec")


hop = 256
mfccs = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop)
mfccs = sklearn.preprocessing.scale(mfccs, axis=1)

# =========================================
# agglomerative clustering

n_segments = 8
bounds = librosa.segment.agglomerative(mfccs, n_segments)
bound_times = librosa.frames_to_time(bounds, sr=sr, hop_length=hop)
print("Segment boundaries (seconds):", bound_times)

temp_dir = Path(r"D:\dev\temp")
temp_dir.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(16, 4), dpi=150)
trans = mpt.blended_transform_factory(ax.transData, ax.transAxes)

librosa.display.specshow(mfccs, x_axis='time', sr=sr, hop_length=hop, ax=ax)
ax.vlines(bound_times, 0, 1, color='lime', linestyle='--',
          linewidth=2, alpha=0.9, transform=trans, label='Segment boundaries')

ax.xaxis.set_major_locator(plt.MultipleLocator(10))
ax.xaxis.set_minor_locator(plt.MultipleLocator(2))
ax.grid(True, axis='x', which='both', alpha=0.3)

ax.set(title='MFCC-based structural segmentation')
ax.legend()
plt.tight_layout()

# save figure
output_file = temp_dir / "mfcc_segments.png"
plt.savefig(output_file)
#plt.close(fig)
plt.show()
print(f"MFCC segmentation saved to {output_file}")


# Another representations to calculate the segmenting from tonnetz
import librosa.segment
import matplotlib.pyplot as plt
import matplotlib.transforms as mpt
from pathlib import Path

# Specify the existing audio file
audio_file = r"D:\dev\temp\temp_audio.wav"
audio_path = Path(audio_file)

if not audio_path.exists():
    raise FileNotFoundError(f"{audio_file} does not exist. Please download the audio first.")

# Load the audio as mono with 22050 Hz sample rate
y, sr = librosa.load(audio_file, sr=22050, mono=True)
print(f"Sample rate: {sr}, Duration: {len(y)/sr:.2f} sec")

# Compute Tonnetz features
tonnetz = librosa.feature.tonnetz(y=y, sr=sr)

# Agglomerative clustering for structural segmentation into 8 segments
n_segments = 8
bounds = librosa.segment.agglomerative(tonnetz, n_segments)
bound_times = librosa.frames_to_time(bounds, sr=sr)
print("Segment boundaries (seconds):", bound_times)

# Plot the Tonnetz and save to a temporary directory without showing
temp_dir = Path(r"D:\dev\temp")
temp_dir.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(16, 4), dpi=150)
trans = mpt.blended_transform_factory(ax.transData, ax.transAxes)

librosa.display.specshow(tonnetz, y_axis='tonnetz', x_axis='time', sr=sr, ax=ax, cmap='Accent')

# Draw vertical lines for segment boundaries
ax.vlines(bound_times, 0, 1, color='lime', linestyle='--', linewidth=3, alpha=0.9, transform=trans, label='Segment boundaries')

# Set title and add legend
ax.set(title='Tonal centroids (Tonnetz)')
ax.legend()
plt.tight_layout()

# Save the figure and close to avoid displaying
output_file = temp_dir / "tonnetz_segments.png"
plt.savefig(output_file)
#plt.close(fig)
plt.show()
print(f"Tonnetz segmentation saved to {output_file}")



import librosa
import librosa.display
import librosa.segment
import matplotlib.pyplot as plt
import matplotlib.transforms as mpt
from pathlib import Path
import numpy as np

# =========================================
audio_file = r"D:\dev\temp\temp_audio.wav"
audio_path = Path(audio_file)

if not audio_path.exists():
    raise FileNotFoundError(f"{audio_file} does not exist. Please download the audio first.")

# Load audio
y, sr = librosa.load(audio_file, sr=22050, mono=True)
duration = len(y)/sr
print(f"Sample rate: {sr}, Duration: {duration:.2f} sec")

# =========================================
# Parameters
segment_duration = 30  # 每段 30 秒
segment_samples = sr * segment_duration
hop = 1024             # hop_length

# 计算总段数
total_segments = int(np.ceil(len(y) / segment_samples))
all_bound_times = []

# 临时目录
temp_dir = Path(r"D:\dev\temp")
temp_dir.mkdir(parents=True, exist_ok=True)

plt.rcParams['figure.figsize'] = (16, 4)

# =========================================
# 分段计算 tempogram + 聚类
for i in range(total_segments):
    start = i * segment_samples
    end = min((i+1) * segment_samples, len(y))
    y_seg = y[start:end]

    # 计算 tempogram
    tempogram = librosa.feature.tempogram(y=y_seg, sr=sr, hop_length=hop)

    # 聚类成 2-3 段（避免每段矩阵太小）
    n_seg = 2 if i < total_segments-1 else 1  # 最后一段只保留1段
    bounds = librosa.segment.agglomerative(tempogram, k=n_seg, axis=1)

    # 转换成全局时间
    bound_times_seg = librosa.frames_to_time(bounds, sr=sr, hop_length=hop) + start/sr
    all_bound_times.extend(bound_times_seg)

# 去重 & 排序
all_bound_times = np.unique(all_bound_times)
print("Combined segment boundaries (seconds):", all_bound_times)

# =========================================
# 绘图
fig, ax = plt.subplots(figsize=(16, 4), dpi=150)
trans = mpt.blended_transform_factory(ax.transData, ax.transAxes)

# 全局 tempogram
full_tempogram = librosa.feature.tempogram(y=y, sr=sr, hop_length=hop)
librosa.display.specshow(full_tempogram, y_axis='tempo', x_axis='time', sr=sr, hop_length=hop, ax=ax, cmap='magma')

# 标记分段边界
ax.vlines(all_bound_times, 0, 1, color='lime', linestyle='--', linewidth=2, alpha=0.9, transform=trans, label='Segment boundaries')

ax.set(title='Tempogram with Segment Boundaries (Segmented)')
ax.legend()
plt.tight_layout()

# 保存并关闭 figure
output_file = temp_dir / "tempogram_segments_segmented.png"
plt.savefig(output_file)
plt.close(fig)
print(f"Tempogram segmentation saved to {output_file}")

