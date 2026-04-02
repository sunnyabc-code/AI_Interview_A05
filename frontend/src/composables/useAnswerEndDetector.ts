import { computed, ref } from 'vue'

export type AnswerEndReason = 'silence' | 'keyword' | 'max_duration' | 'manual'

export interface AnswerEndDetectorOptions {
  minSpeechSeconds?: number
  silenceThresholdSeconds?: number
  autoStopOnSilence?: boolean
  maxAnswerSeconds?: number
  volumeThreshold?: number
  keywordPatterns?: string[]
  tickMs?: number
}

export function useAnswerEndDetector(options?: AnswerEndDetectorOptions) {
  const minSpeechSeconds = options?.minSpeechSeconds ?? 3
  const silenceThresholdSeconds = options?.silenceThresholdSeconds ?? 3
  const autoStopOnSilence = options?.autoStopOnSilence ?? true
  const maxAnswerSeconds = options?.maxAnswerSeconds ?? 120
  const volumeThreshold = options?.volumeThreshold ?? 0.02
  const tickMs = options?.tickMs ?? 100

  const keywordPatterns =
    options?.keywordPatterns ?? [
      '我说完了',
      '我讲完了',
      '回答完毕',
      '回答结束',
      '就这些',
      '没了',
    ]

  const isRunning = ref(false)
  const elapsedMs = ref(0)
  const speechMs = ref(0)
  const silenceMs = ref(0)
  const recentRms = ref(0)
  const stopReason = ref<AnswerEndReason | null>(null)

  let timer: number | null = null
  let onStopCallback: ((reason: AnswerEndReason) => void) | null = null

  const inStoppableWindow = computed(() => speechMs.value >= minSpeechSeconds * 1000)

  const clearTimer = () => {
    if (timer) {
      window.clearInterval(timer)
      timer = null
    }
  }

  const finish = (reason: AnswerEndReason) => {
    if (!isRunning.value) return

    isRunning.value = false
    stopReason.value = reason
    clearTimer()

    if (onStopCallback) {
      onStopCallback(reason)
    }
  }

  const reset = () => {
    clearTimer()
    isRunning.value = false
    elapsedMs.value = 0
    speechMs.value = 0
    silenceMs.value = 0
    recentRms.value = 0
    stopReason.value = null
  }

  const start = (onStop: (reason: AnswerEndReason) => void) => {
    reset()
    isRunning.value = true
    onStopCallback = onStop

    timer = window.setInterval(() => {
      if (!isRunning.value) return

      elapsedMs.value += tickMs
      if (elapsedMs.value >= maxAnswerSeconds * 1000) {
        finish('max_duration')
      }
    }, tickMs)
  }

  const markManualStop = () => {
    finish('manual')
  }

  const pushRms = (rms: number) => {
    if (!isRunning.value) return

    recentRms.value = rms

    const isSpeechFrame = rms >= volumeThreshold
    if (isSpeechFrame) {
      speechMs.value += tickMs
      silenceMs.value = 0
      return
    }

    silenceMs.value += tickMs

    if (autoStopOnSilence && inStoppableWindow.value && silenceMs.value >= silenceThresholdSeconds * 1000) {
      finish('silence')
    }
  }

  const pushRecognizedText = (text: string) => {
    if (!isRunning.value || !inStoppableWindow.value) return

    const normalized = (text || '').trim()
    if (!normalized) return

    const matched = keywordPatterns.some((pattern) => normalized.includes(pattern))
    if (matched) {
      finish('keyword')
    }
  }

  return {
    minSpeechSeconds,
    silenceThresholdSeconds,
    maxAnswerSeconds,
    volumeThreshold,
    keywordPatterns,
    isRunning,
    elapsedMs,
    speechMs,
    silenceMs,
    recentRms,
    stopReason,
    inStoppableWindow,
    start,
    reset,
    markManualStop,
    pushRms,
    pushRecognizedText,
  }
}
