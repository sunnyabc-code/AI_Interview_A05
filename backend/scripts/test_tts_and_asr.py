#!/usr/bin/env python
"""
TTS + ASR 语音链路测试
用法:
    python scripts/test_tts_and_asr.py              # 生成测试语音
    python scripts/test_tts_and_asr.py --play       # 生成并尝试播放（Windows）
"""
import argparse
import os
import sys

# 将 backend 目录加入 sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Interview.settings')
import django
django.setup()


def generate_test_audio(output_path: str = 'test_interview_audio.mp3') -> str:
    """使用 gTTS 生成中文测试语音"""
    try:
        from gtts import gTTS
    except ImportError:
        print('[ERROR] gTTS 未安装。运行: pip install gtts')
        return ''

    texts = [
        '你好，我是一名Java后端开发工程师，有三年的项目经验。',
        '我最熟悉的技术栈是Spring Boot和MySQL。',
        '在之前的项目中，我负责设计并实现了订单系统的微服务架构。',
    ]

    print('=== TTS 语音生成测试 ===')
    print(f'生成 {len(texts)} 段测试语音到: {output_path}')

    # 合并多段文本
    combined = '。\n'.join(texts)
    try:
        tts = gTTS(text=combined, lang='zh-cn', slow=False)
        tts.save(output_path)
        size_kb = os.path.getsize(output_path) / 1024
        print(f'[OK] 语音文件已生成: {output_path} ({size_kb:.1f} KB)')
        return output_path
    except Exception as e:
        print(f'[ERROR] TTS 生成失败: {e}')
        return ''


def test_audio_properties(filepath: str):
    """检查音频文件属性"""
    print(f'\n=== 音频文件属性 ===')
    print(f'文件: {filepath}')
    print(f'大小: {os.path.getsize(filepath) / 1024:.1f} KB')

    try:
        import wave
        with wave.open(filepath, 'rb') as wf:
            print(f'声道数: {wf.getnchannels()}')
            print(f'采样宽度: {wf.getsampwidth()} bytes')
            print(f'采样率: {wf.getframerate()} Hz')
            print(f'帧数: {wf.getnframes()}')
            duration = wf.getnframes() / wf.getframerate()
            print(f'时长: {duration:.2f} 秒')
    except Exception:
        print('[INFO] 非 WAV 格式，跳过波形分析（MP3 为正常格式）')


def play_audio(filepath: str):
    """在 Windows 上尝试播放音频"""
    try:
        import winsound
        # winsound 只支持 WAV，MP3 需转换或使用其他方式
        print('[INFO] winsound 仅支持 WAV 格式，MP3 请手动播放')
    except ImportError:
        pass

    try:
        os.startfile(filepath)
        print('[OK] 已调用系统默认播放器打开文件')
    except Exception:
        print('[INFO] 请手动打开文件播放: ' + filepath)


def main():
    parser = argparse.ArgumentParser(description='TTS + ASR 语音链路测试')
    parser.add_argument('--output', default='test_interview_audio.mp3', help='输出音频路径')
    parser.add_argument('--play', action='store_true', help='生成后播放')
    args = parser.parse_args()

    filepath = generate_test_audio(args.output)
    if not filepath:
        return 1

    test_audio_properties(filepath)

    if args.play:
        play_audio(filepath)

    print('\n[完成] 语音测试文件可用于验证:')
    print('  1. gTTS → 中文语音合成正确性')
    print('  2. ASR 引擎 → 语音转文字准确率')
    print('  3. 语音面试流程 → 录音→上传→识别→分析 全链路')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
