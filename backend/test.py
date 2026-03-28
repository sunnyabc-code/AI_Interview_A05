from gtts import gTTS

text = "你好，这是一个测试语音，用于验证语音识别系统的效果。"

tts = gTTS(text=text, lang='zh')
tts.save("test.mp3")