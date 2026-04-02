import { ref, onUnmounted } from 'vue'

export type TTSFinishReason = 'ended' | 'cancelled' | 'error' | 'unsupported'

export function useQuestionTTS() {
  const ttsEnabled = ref(true)
  const isSpeaking = ref(false)
  const currentText = ref('')
  const lastError = ref('')

  let currentUtterance: SpeechSynthesisUtterance | null = null
  let finishResolver: ((reason: TTSFinishReason) => void) | null = null

  const supportsTTS = () => {
    return typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window
  }

  const resolveFinish = (reason: TTSFinishReason) => {
    if (finishResolver) {
      finishResolver(reason)
      finishResolver = null
    }
  }

  const pickVoice = () => {
    if (!supportsTTS()) return null
    const voices = window.speechSynthesis.getVoices()
    if (!voices.length) return null

    return (
      voices.find((v) => v.lang.toLowerCase().includes('zh-cn')) ||
      voices.find((v) => v.lang.toLowerCase().startsWith('zh')) ||
      voices[0]
    )
  }

  const stopSpeaking = () => {
    if (!supportsTTS()) return
    window.speechSynthesis.cancel()
    currentUtterance = null
    isSpeaking.value = false
    resolveFinish('cancelled')
  }

  const speak = (text: string): Promise<TTSFinishReason> => {
    const normalized = (text || '').trim()
    currentText.value = normalized
    lastError.value = ''

    if (!ttsEnabled.value || !normalized) {
      return Promise.resolve('cancelled')
    }

    if (!supportsTTS()) {
      lastError.value = '当前浏览器不支持语音播报。'
      return Promise.resolve('unsupported')
    }

    stopSpeaking()

    return new Promise<TTSFinishReason>((resolve) => {
      finishResolver = resolve

      const utterance = new SpeechSynthesisUtterance(normalized)
      utterance.lang = 'zh-CN'
      utterance.rate = 1
      utterance.pitch = 1
      utterance.volume = 1

      const voice = pickVoice()
      if (voice) {
        utterance.voice = voice
      }

      utterance.onstart = () => {
        isSpeaking.value = true
      }

      utterance.onend = () => {
        isSpeaking.value = false
        currentUtterance = null
        resolveFinish('ended')
      }

      utterance.onerror = () => {
        isSpeaking.value = false
        currentUtterance = null
        lastError.value = '语音播报失败，请改为阅读文字。'
        resolveFinish('error')
      }

      currentUtterance = utterance
      window.speechSynthesis.speak(utterance)
    })
  }

  const replay = () => {
    if (!currentText.value.trim()) {
      return Promise.resolve('cancelled' as TTSFinishReason)
    }

    return speak(currentText.value)
  }

  const setTTSEnabled = (enabled: boolean) => {
    ttsEnabled.value = enabled
    if (!enabled) {
      stopSpeaking()
    }
  }

  onUnmounted(() => {
    stopSpeaking()
  })

  return {
    ttsEnabled,
    isSpeaking,
    currentText,
    lastError,
    supportsTTS,
    speak,
    replay,
    stopSpeaking,
    setTTSEnabled,
  }
}
