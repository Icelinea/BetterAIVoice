import os
from pedalboard import Pedalboard, Compressor, HighpassFilter, PeakFilter, Reverb, Gain
from pedalboard.io import AudioFile
import pyloudnorm as pyln # 用于精确响度控制

# --- 配置区 ---
INPUT_DIR = "./input"      # GPT-SoVITS 原始输出目录
OUTPUT_DIR = "./output"      # 最终成品目录

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)


def process_audio(file_path, output_path):
    with AudioFile(file_path) as f:
        audio = f.read(f.frames)
        sample_rate = f.samplerate

    # 1. 构建美化链 (对应方案 2 & 3)
    board = Pedalboard([
        # 去除低频浑浊
        HighpassFilter(cutoff_frequency_hz=80),
        
        # 增加女声磁性：250Hz-350Hz 提升 (方案2.1)
        PeakFilter(cutoff_frequency_hz=300, gain_db=2.5, q=1.0),
        
        # 压制 AI 齿音：6kHz-8kHz 微微削减 (方案2.2)
        PeakFilter(cutoff_frequency_hz=7000, gain_db=-3.0, q=2.0),
        
        # 稳定动态：防止有声书音量忽大忽小 (方案4)
        Compressor(threshold_db=-18, ratio=3.5),
        
        # 赋予录音棚空间感 (方案3)
        # 使用内建 Reverb 模拟 Ambience 预设 (Mix 3%, 极小衰减)
        Reverb(room_size=0.1, dry_level=0.97, wet_level=0.03, damping=0.5),
        
        # 最终增益补偿
        Gain(gain_db=2)
    ])

    # 2. 执行处理
    effected = board(audio, sample_rate)

    # 3. 响度标准化 (对应方案 4：Auphonic 的本地替代方案)
    # 测量当前响度
    meter = pyln.Meter(sample_rate) 
    loudness = meter.integrated_loudness(effected.T)
    # 将响度统一调整至 -18.0 LUFS (播客标准)
    normalized_audio = pyln.normalize.loudness(effected.T, loudness, -18.0).T

    # 4. 无损导出 (方案 5：32-bit float)
    with AudioFile(output_path, 'w', sample_rate, normalized_audio.shape[0]) as f:
        f.write(normalized_audio)

# --- 批量执行 ---
output_lists = os.listdir(OUTPUT_DIR)
for file_name in os.listdir(INPUT_DIR):
    if file_name.endswith(('.wav', '.mp3')) and file_name not in output_lists:
        print(f"正在处理: {file_name}...")
        process_audio(os.path.join(INPUT_DIR, file_name), os.path.join(OUTPUT_DIR, file_name))

print("\n----- 所有音频已美化完成 -----")
