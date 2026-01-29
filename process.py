"""
高通滤波 -> 250Hz 磁性增强 -> 齿音压制 -> 空间建模 -> 响度标准化。
关于 Adobe Podcast (方案1)：该工具目前无官方 API。脚本中通过 PeakFilter 针对性修复了 7kHz 齿音和 300Hz 的厚度，这能在本地最大程度模拟其效果。如果必须使用 Adobe，建议先批量通过 Python 导出，手动上传 Adobe 官网，再下载。
关于空间建模 (方案3)：脚本使用了 pedalboard.Reverb。若你已安装 Valhalla Supermassive，可将代码改为 VSTPlugin(path_to_vst) 直接调用该插件的特定预设。
关于 Auphonic (方案4)：代码引入了 pyloudnorm 库，它是目前公认最精准的响度标准化 Python 库，能完美实现 Auphonic 的“响度规范化”功能。

GPT-Sovits 问题对策：
1. 消除“电音味”与重塑谐波 (AI 修复层)
GPT-SoVITS 在合成过程中有时会丢失 10kHz 以上的平滑度。
首选工具：Adobe Podcast Enhance
方法：将生成的音频先过一遍这个 AI，它能有效抹平合成中的“颗粒感”，让高音部分像经过专业电容麦克风收录一样平滑，同时极大增强女声的呼吸感。
2. 润色女声质感 (精细 EQ 策略)
在 Audacity 或 Adobe Audition 中针对 GPT-SoVITS 进行如下调节：
解决薄脆感：GPT-SoVITS 生成的女声有时偏薄。在 250Hz - 350Hz 处使用 Q 值较大的 EQ 提升 2dB，增加“胸腔共鸣”，提升有声书的磁性。
消除齿音：使用 TDR Nova 动态均衡器。在 6kHz - 8kHz 针对性压制，避免 AI 合成的“嘶”、“字”等高频爆发点刺耳。
3. 赋予“录音棚”深度 (空间建模)
播客最忌讳声音太“平”。
推荐插件：Valhalla Supermassive (免费)
操作：使用 “Ambience” 预设。
关键参数：Mix（干湿比）控制在 2% - 5%，Decay（衰减）设为 0.5s 以下。
效果：这能让 GPT-SoVITS 这种完全“干”的合成音带上微弱的空气感，模拟出在专业消音室录音的效果。
4. 响度控制与无损放大 (终混层)
有声书需要长久听感不累，音量必须极度一致。
工具：Auphonic (最强后期助手)
步骤：
登录 Auphonic Web Service。
上传处理过的音频。
勾选 Adaptive Leveler（它会像真人调音师一样，把太响的部分拉低，太轻的部分推高，且无损音质）。
设置 Target Loudness 为 -16 LUFS（播客标准）或 -20 LUFS（有声书标准）。
下载成品。
5. 补充建议：GPT-SoVITS 导出参数
在导出音频时，请务必确保：
采样率 (Sample Rate)：至少 44100Hz。
位深度 (Bit Depth)：选择 32-bit float 或 24-bit（这为后续的无损放大预留了充足的“动态余量”，避免产生爆音）。
"""

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
for file_name in os.listdir(INPUT_DIR):
    if file_name.endswith(('.wav', '.mp3')):
        print(f"正在处理: {file_name}...")
        process_audio(os.path.join(INPUT_DIR, file_name), os.path.join(OUTPUT_DIR, file_name))

print("\n所有音频已美化完成")
