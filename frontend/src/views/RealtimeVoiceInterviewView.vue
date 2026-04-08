<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuestionTTS } from '../composables/useQuestionTTS'
import { useAnswerEndDetector } from '../composables/useAnswerEndDetector'

type AnswerEndReason = 'silence' | 'keyword' | 'max_duration' | 'manual'
type MainTalkMode = 'click' | 'hold'

const router = useRouter()
const route = useRoute()
const API_BASE_URL = 'http://localhost:8000'

const {
  ttsEnabled,
  isSpeaking,
  currentText,
  lastError,
  supportsTTS,
  speak,
  stopSpeaking,
  setTTSEnabled,
} = useQuestionTTS()

const endDetector = useAnswerEndDetector({
  minSpeechSeconds: 3,
  silenceThresholdSeconds: 2,
  autoStopOnSilence: false,
  maxAnswerSeconds: 120,
  volumeThreshold: 0.02,
})

const interview = ref<any>(null)
const currentRoundNumber = ref(1)
const currentRoundId = ref<number | null>(null)
const infoError = ref('')
const questionText = ref('')
const fallbackAnswerText = ref('')
const autoStartRecording = ref(true)
const mainTalkMode = ref<MainTalkMode>('click')
const recordingState = ref<'idle' | 'recording'>('idle')
const isPaused = ref(false)
const isSilenceEnding = ref(false)
const silenceFinalizeCountdown = ref(3)
const roundProgressText = ref('')
const showAutoStartPrompt = ref(false)
const autoStartCountdown = ref(3)
const isAdvancingRound = ref(false)
const flowLog = ref<string[]>([])
const monitorError = ref('')
const networkOnline = ref(typeof navigator !== 'undefined' ? navigator.onLine : true)
const micStatus = ref<'unknown' | 'ready' | 'recording' | 'denied'>('unknown')

let mediaRecorder: any = null
let mediaStream: MediaStream | null = null
let audioContext: AudioContext | null = null
let analyser: AnalyserNode | null = null
let sourceNode: MediaStreamAudioSourceNode | null = null
let analysisTimer: number | null = null
let recognition: any = null
let audioChunks: BlobPart[] = []
let recordingStartedAtMs = 0
let lastRecordingDurationSeconds = 0
let autoStartTimer: number | null = null
let silenceFinalizeTimer: number | null = null

const SILENCE_TRIGGER_SECONDS = 2
const SILENCE_FINALIZE_SECONDS = 3
const FORCED_STOPPABLE_AFTER_SECONDS = 5

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }
}

const addLog = (message: string) => {
  flowLog.value.unshift(`${new Date().toLocaleTimeString()}  ${message}`)
}

const clearAutoStartTimer = () => {
  if (autoStartTimer) {
    window.clearInterval(autoStartTimer)
    autoStartTimer = null
  }
}

const clearSilenceFinalizeTimer = () => {
  if (silenceFinalizeTimer) {
    window.clearInterval(silenceFinalizeTimer)
    silenceFinalizeTimer = null
  }
}

const cancelSilenceFinalize = (log = false) => {
  if (!isSilenceEnding.value) return
  clearSilenceFinalizeTimer()
  isSilenceEnding.value = false
  silenceFinalizeCountdown.value = SILENCE_FINALIZE_SECONDS
  if (log) {
    addLog('继续说话，已取消自动结束。')
  }
}

const beginSilenceFinalize = () => {
  if (isSilenceEnding.value || recordingState.value !== 'recording') return
  isSilenceEnding.value = true
  silenceFinalizeCountdown.value = SILENCE_FINALIZE_SECONDS
  addLog('检测到停顿，即将结束录音。继续说话可取消结束。')

  silenceFinalizeTimer = window.setInterval(() => {
    silenceFinalizeCountdown.value -= 1
    if (silenceFinalizeCountdown.value <= 0) {
      clearSilenceFinalizeTimer()
      isSilenceEnding.value = false
      stopRecording('silence')
    }
  }, 1000)
}

const cancelAutoStartPrompt = (reason?: string) => {
  clearAutoStartTimer()
  if (showAutoStartPrompt.value && reason) {
    addLog(reason)
  }
  showAutoStartPrompt.value = false
  autoStartCountdown.value = 3
}

const startRecordingNow = async () => {
  cancelAutoStartPrompt()
  await startRecording()
}

const startAutoCountdown = () => {
  if (isPaused.value) {
    addLog('当前为暂停状态，已跳过自动开录。')
    return
  }

  cancelAutoStartPrompt()
  showAutoStartPrompt.value = true
  autoStartCountdown.value = 3
  addLog('即将开始录音，可选择立即开始或稍后开始。')

  autoStartTimer = window.setInterval(async () => {
    autoStartCountdown.value -= 1
    if (autoStartCountdown.value <= 0) {
      clearAutoStartTimer()
      showAutoStartPrompt.value = false
      await startRecording()
    }
  }, 1000)
}

const errorMessage = (err: unknown) => {
  if (typeof err === 'object' && err && 'message' in err) {
    return String((err as any).message || '未知错误')
  }
  return '未知错误'
}

const interviewId = computed(() => String(route.params.id || ''))

const handleUnauthorized = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  router.push('/auth')
}

const postJson = async (url: string, payload: any = {}) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  })

  if (response.status === 401) {
    handleUnauthorized()
    throw new Error('未登录或登录已过期')
  }

  const data = await response.json().catch(() => ({}))
  if (!response.ok || (data.code && ![200, 201].includes(data.code))) {
    throw new Error(data.message || '请求失败')
  }
  return data
}

const interviewNameText = computed(() => interview.value?.name || '未命名面试')
const interviewPositionText = computed(() => interview.value?.position_name || '未设置岗位')
const interviewStatusText = computed(() => {
  const status = interview.value?.status
  const statusMap: Record<string, string> = {
    pending: '待开始',
    in_progress: '进行中',
    paused: '已暂停',
    completed: '已完成',
    cancelled: '已取消',
  }
  return statusMap[status] || '未知'
})
const networkStatusText = computed(() => (networkOnline.value ? '网络在线' : '网络离线'))
const micStatusText = computed(() => {
  const map: Record<string, string> = {
    unknown: '待检测',
    ready: '麦克风可用',
    recording: '麦克风采集中',
    denied: '麦克风不可用',
  }
  return map[micStatus.value]
})
const sceneStatus = computed(() => {
  if (isSpeaking.value) return 'speaking'
  if (recordingState.value === 'recording') return 'listening'
  if (isPaused.value) return 'paused'
  return 'thinking'
})
const sceneStatusText = computed(() => {
  const map: Record<string, string> = {
    speaking: '正在播报',
    listening: '正在聆听',
    thinking: '正在思考',
    paused: '已暂停',
  }
  return map[sceneStatus.value]
})
const currentRoundLabel = computed(() => {
  return currentRoundNumber.value ? `第 ${currentRoundNumber.value} 轮` : '等待生成'
})
const interviewerWaveBars = computed(() => {
  const baseBars = isSpeaking.value ? [16, 24, 20, 28, 18] : [10, 14, 12, 15, 11]
  const boost = isSpeaking.value ? Math.min(8, Math.max(0, Math.round(currentText.value.length / 12))) : 0

  return baseBars.map((height, index) => Math.min(40, height + boost + (isSpeaking.value ? index % 2 * 2 : 0)))
})
const candidateWaveBars = computed(() => {
  const active = candidateWaveActive.value
  const intensity = active ? Math.max(0.35, Math.min(1.1, endDetector.recentRms.value * 10)) : 0
  const idleBars = [8, 12, 10, 14, 9]

  return idleBars.map((height, index) => {
    const gain = active ? Math.round((10 + index * 3) * intensity) : 0
    return Math.min(40, height + gain)
  })
})
const candidateWaveActive = computed(() => {
  return recordingState.value === 'recording' && endDetector.recentRms.value > endDetector.volumeThreshold
})
const speechSecondsText = computed(() => (endDetector.speechMs.value / 1000).toFixed(1))
const silenceSecondsText = computed(() => (endDetector.silenceMs.value / 1000).toFixed(1))
const elapsedSecondsText = computed(() => (endDetector.elapsedMs.value / 1000).toFixed(1))
const remainingAnswerSecondsText = computed(() => {
  const left = Math.max(endDetector.maxAnswerSeconds - Math.floor(endDetector.elapsedMs.value / 1000), 0)
  return `${left}s`
})

const recordingGuideText = computed(() => {
  if (recordingState.value !== 'recording') return ''
  if (isSilenceEnding.value) {
    return `检测到停顿，即将结束...（倒计时 ${silenceFinalizeCountdown.value} 秒）`
  }
  return '正在聆听...'
})

const recordingGuideSubText = computed(() => {
  if (recordingState.value === 'recording' && isSilenceEnding.value) {
    return '继续说话可取消结束'
  }
  return ''
})

const reasonText = (reason: AnswerEndReason) => {
  const map: Record<AnswerEndReason, string> = {
    silence: '连续静音达到阈值',
    keyword: '命中结束关键词',
    max_duration: '达到最长答题时长',
    manual: '手动结束',
  }
  return map[reason]
}

const uploadRecordedAudio = async (blob: Blob, durationSeconds: number) => {
  if (!interviewId.value || !currentRoundId.value) {
    addLog('未找到当前轮次，跳过音频上传。')
    return false
  }

  if (!blob || blob.size <= 0) {
    addLog('音频上传失败: 录音数据为空（0KB）。')
    return false
  }

  const token = localStorage.getItem('access_token')
  if (!token) {
    addLog('登录状态已失效，音频上传失败。')
    handleUnauthorized()
    return false
  }

  const extension = blob.type.includes('mpeg') ? 'mp3' : 'webm'
  const formData = new FormData()
  formData.append('audio_file', blob, `round_${currentRoundId.value}.${extension}`)
  formData.append('duration_seconds', String(durationSeconds))

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/interviews/${interviewId.value}/rounds/${currentRoundId.value}/audio/`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      },
    )

    if (response.status === 401) {
      handleUnauthorized()
      addLog('未授权，音频上传失败。')
      return false
    }

    const data = await response.json().catch(() => ({}))
    if (!response.ok || ![200, 201].includes(data.code)) {
      const detail = data?.errors ? JSON.stringify(data.errors) : ''
      addLog(`音频上传失败: ${data.message || '未知错误'}${detail ? ` | ${detail}` : ''}`)
      return false
    }

    addLog(`音频上传成功(${(blob.size / 1024).toFixed(1)}KB)，转写状态: ${data.data?.asr_status || 'pending'}`)
    return true
  } catch (err) {
    addLog(`音频上传异常: ${errorMessage(err)}`)
    return false
  }
}

async function submitPlaceholderAndAdvance() {
  if (!interviewId.value || !currentRoundId.value) {
    addLog('当前无可提交轮次，无法自动推进。')
    return
  }

  if (isAdvancingRound.value) {
    return
  }

  if (isPaused.value) {
    addLog('当前为暂停状态，已跳过自动推进。')
    return
  }

  isAdvancingRound.value = true
  const roundId = currentRoundId.value

  try {
    await postJson(
      `${API_BASE_URL}/api/v1/interviews/${interviewId.value}/rounds/${roundId}/answer/`,
      { user_answer: '1' },
    )
    addLog('已自动提交语音占位回答，准备获取下一题。')
    roundProgressText.value = '回答已提交，正在生成下一题...'

    const ok = await fetchNextQuestion()
    if (ok && !isPaused.value) {
      await playQuestion()
    } else if (ok) {
      addLog('已获取下一题，但当前处于暂停状态，暂不播报。')
    }
  } catch (err) {
    roundProgressText.value = ''
    addLog(`自动推进失败: ${errorMessage(err)}`)
  } finally {
    isAdvancingRound.value = false
  }
}

const cleanupAudioGraph = () => {
  if (analysisTimer) {
    window.clearInterval(analysisTimer)
    analysisTimer = null
  }

  if (recognition) {
    recognition.onresult = null
    recognition.onerror = null
    recognition.onend = null
    try {
      recognition.stop()
    } catch {
      // ignore
    }
    recognition = null
  }

  if (sourceNode) {
    sourceNode.disconnect()
    sourceNode = null
  }

  if (analyser) {
    analyser.disconnect()
    analyser = null
  }

  if (audioContext) {
    audioContext.close().catch(() => undefined)
    audioContext = null
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }

  mediaRecorder = null
  micStatus.value = 'ready'
}

const stopRecording = (reason: AnswerEndReason) => {
  if (recordingState.value !== 'recording') return

  cancelSilenceFinalize()

  if (recordingStartedAtMs > 0) {
    const duration = Math.max(1, Math.round((Date.now() - recordingStartedAtMs) / 1000))
    lastRecordingDurationSeconds = duration
  }

  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop()
  }

  recordingState.value = 'idle'
  endDetector.reset()
  addLog(`结束录音，原因: ${reasonText(reason)}。`)
}

const setupKeywordRecognition = () => {
  const win = window as any
  const RecognitionCtor = win.SpeechRecognition || win.webkitSpeechRecognition
  if (!RecognitionCtor) {
    addLog('浏览器不支持关键词识别，已退化为静音+超时判停。')
    return
  }

  recognition = new RecognitionCtor()
  recognition.lang = 'zh-CN'
  recognition.continuous = true
  recognition.interimResults = true
  recognition.onresult = (event: any) => {
    const text = event.results?.[event.results.length - 1]?.[0]?.transcript || ''
    endDetector.pushRecognizedText(text)
  }
  recognition.onerror = () => {
    addLog('关键词识别异常，继续使用静音+超时判停。')
  }
  recognition.onend = () => {
    if (recordingState.value === 'recording') {
      try {
        recognition.start()
      } catch {
        // ignore
      }
    }
  }

  try {
    recognition.start()
  } catch {
    addLog('关键词识别启动失败，继续使用静音+超时判停。')
  }
}

const setupSilenceMonitor = () => {
  if (!analyser) return

  const data = new Float32Array(analyser.fftSize)
  analysisTimer = window.setInterval(() => {
    if (!analyser) return

    analyser.getFloatTimeDomainData(data)
    let sum = 0
    for (let i = 0; i < data.length; i += 1) {
      const sample = data[i] ?? 0
      sum += sample * sample
    }
    const rms = Math.sqrt(sum / data.length)
    endDetector.pushRms(rms)

    const inStoppableWindow =
      endDetector.inStoppableWindow.value ||
      endDetector.elapsedMs.value >= FORCED_STOPPABLE_AFTER_SECONDS * 1000

    if (!inStoppableWindow) {
      if (isSilenceEnding.value) {
        cancelSilenceFinalize()
      }
      return
    }

    if (endDetector.silenceMs.value >= SILENCE_TRIGGER_SECONDS * 1000) {
      beginSilenceFinalize()
    }

    if (isSilenceEnding.value && endDetector.recentRms.value > endDetector.volumeThreshold) {
      cancelSilenceFinalize(true)
    }
  }, 100)
}

const startRecording = async () => {
  cancelAutoStartPrompt()
  cancelSilenceFinalize()
  monitorError.value = ''
  if (recordingState.value === 'recording' || isPaused.value || isSpeaking.value) return

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const MediaRecorderCtor = (window as any).MediaRecorder
    if (!MediaRecorderCtor) {
      throw new Error('MediaRecorder unsupported')
    }

    mediaRecorder = new MediaRecorderCtor(mediaStream)
    audioChunks = []
    recordingStartedAtMs = Date.now()
    lastRecordingDurationSeconds = 0
    micStatus.value = 'recording'

    mediaRecorder.ondataavailable = (event: any) => {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
      const durationSeconds = lastRecordingDurationSeconds || Math.max(1, Math.round(endDetector.elapsedMs.value / 1000))
      addLog(`录音已结束，生成音频 ${(blob.size / 1024).toFixed(1)} KB，时长 ${durationSeconds}s。`)
      const uploaded = await uploadRecordedAudio(blob, durationSeconds)
      if (uploaded && !isPaused.value) {
        await submitPlaceholderAndAdvance()
      }
      cleanupAudioGraph()
      recordingStartedAtMs = 0
      lastRecordingDurationSeconds = 0
    }

    audioContext = new AudioContext()
    sourceNode = audioContext.createMediaStreamSource(mediaStream)
    analyser = audioContext.createAnalyser()
    analyser.fftSize = 2048
    sourceNode.connect(analyser)

    endDetector.start((reason) => {
      if (reason === 'silence') {
        beginSilenceFinalize()
        return
      }
      stopRecording(reason)
    })

    setupSilenceMonitor()
    setupKeywordRecognition()
    mediaRecorder.start(250)
    recordingState.value = 'recording'
    addLog('开始录音并启动实时判停监测。')
  } catch {
    monitorError.value = '无法启动录音，请检查麦克风权限。'
    micStatus.value = 'denied'
    addLog('录音启动失败。')
    endDetector.reset()
    cleanupAudioGraph()
  }
}

const playQuestion = async () => {
  if (isPaused.value) {
    addLog('当前为暂停状态，已取消题目播报。')
    return
  }

  cancelAutoStartPrompt()
  addLog('开始播报面试官问题。')
  const result = await speak(questionText.value)
  addLog(`播报结束，原因: ${result}`)

  if (result === 'ended' && autoStartRecording.value) {
    startAutoCountdown()
  }
}

const fetchNextQuestion = async () => {
  if (!interviewId.value) return false

  try {
    const data = await postJson(`${API_BASE_URL}/api/v1/interviews/${interviewId.value}/next-question/`, {})

    if (data.code === 201 && data.data) {
      questionText.value = data.data.question_content || ''
      currentRoundId.value = data.data.round_id || null
      currentRoundNumber.value = data.data.round_number || currentRoundNumber.value
      roundProgressText.value = ''
      addLog(`已获取第 ${currentRoundNumber.value} 轮题目。`)
      return true
    }

    if (data.code === 200 && data.data?.status === 'completed') {
      roundProgressText.value = ''
      addLog('面试已完成，无下一题。')
      interview.value = { ...interview.value, ...data.data }
      return false
    }

    throw new Error(data.message || '获取下一题失败')
  } catch (err) {
    addLog(`获取下一题失败: ${errorMessage(err)}`)
    return false
  }
}

const replayQuestion = async () => {
  const text = (questionText.value || '').trim()
  if (!text) {
    addLog('当前题目为空，无法重听。')
    return
  }

  addLog('重听当前问题。')
  const result = await speak(text)
  addLog(`重听结束，原因: ${result}`)
}

const toggleTTSSwitch = () => {
  setTTSEnabled(!ttsEnabled.value)
  addLog(ttsEnabled.value ? '已开启题目播报。' : '已关闭题目播报。')
}

const stopBroadcast = () => {
  stopSpeaking()
  addLog('手动停止播报。')
}

const manualStopAnswer = () => {
  stopRecording('manual')
}

const toggleMainTalk = async () => {
  if (recordingState.value === 'recording') {
    manualStopAnswer()
    return
  }
  await startRecording()
}

const holdStart = async () => {
  if (mainTalkMode.value !== 'hold') return
  await startRecording()
}

const holdEnd = () => {
  if (mainTalkMode.value !== 'hold') return
  manualStopAnswer()
}

const pauseInterview = async () => {
  if (!interviewId.value) return
  cancelAutoStartPrompt()
  cancelSilenceFinalize()
  if (recordingState.value === 'recording') {
    stopRecording('manual')
  }

  try {
    if (isPaused.value) {
      const data = await postJson(`${API_BASE_URL}/api/v1/interviews/${interviewId.value}/resume/`)
      isPaused.value = false
      interview.value = { ...interview.value, ...data.data, status: 'in_progress' }
      addLog('面试已恢复。')
      return
    }

    isPaused.value = true
    const data = await postJson(`${API_BASE_URL}/api/v1/interviews/${interviewId.value}/pause/`)
    interview.value = { ...interview.value, ...data.data, status: 'paused' }
    addLog('面试已暂停。')
  } catch (err) {
    if (interview.value?.status !== 'paused') {
      isPaused.value = false
    }
    addLog(`暂停/恢复失败: ${errorMessage(err)}`)
  }
}

const endInterview = async () => {
  if (!interviewId.value) return
  cancelAutoStartPrompt()
  cancelSilenceFinalize()
  if (recordingState.value === 'recording') {
    stopRecording('manual')
  }

  try {
    const data = await postJson(`${API_BASE_URL}/api/v1/interviews/${interviewId.value}/end/`)
    interview.value = { ...interview.value, ...data.data, status: 'completed' }
    addLog('面试结束，进入评估页。')
    router.push(`/interview/${interviewId.value}/evaluation`)
    return
  } catch (err) {
    addLog(`结束面试接口失败: ${errorMessage(err)}，将直接返回列表。`)
  }

  router.push('/home?menu=interview')
}

const submitFallbackText = async () => {
  const text = fallbackAnswerText.value.trim()
  if (!text || !interviewId.value || !currentRoundId.value) {
    addLog('当前无可提交轮次，请先获取题目。')
    return
  }

  try {
    await postJson(
      `${API_BASE_URL}/api/v1/interviews/${interviewId.value}/rounds/${currentRoundId.value}/answer/`,
      { user_answer: text },
    )
    addLog(`文本降级提交成功: ${text.slice(0, 30)}${text.length > 30 ? '...' : ''}`)
    fallbackAnswerText.value = ''

    const ok = await fetchNextQuestion()
    if (ok) {
      await playQuestion()
    }
  } catch (err) {
    addLog(`文本提交失败: ${errorMessage(err)}`)
  }

  fallbackAnswerText.value = ''
}

const handleBack = () => {
  cancelAutoStartPrompt()
  cancelSilenceFinalize()
  if (recordingState.value === 'recording') {
    stopRecording('manual')
  }
  router.push('/home?menu=interview')
}

const loadInterviewInfo = async () => {
  if (!interviewId.value) return

  try {
    const [detailResp, roundsResp] = await Promise.all([
      fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId.value}/`, { headers: getAuthHeaders() }),
      fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId.value}/rounds/`, { headers: getAuthHeaders() }),
    ])

    if (detailResp.status === 401 || roundsResp.status === 401) {
      handleUnauthorized()
      return
    }

    if (detailResp.ok) {
      const detailData = await detailResp.json()
      if (detailData.code === 200) {
        interview.value = detailData.data
      }
    }

    let hasUnfinishedRound = false

    if (roundsResp.ok) {
      const roundsData = await roundsResp.json()
      const rounds = roundsData?.data || []
      if (Array.isArray(rounds) && rounds.length) {
        currentRoundNumber.value = Math.max(...rounds.map((r: any) => r.round_number || 1))

        const unfinished = rounds.find((r: any) => !r.end_time)
        if (unfinished) {
          hasUnfinishedRound = true
          currentRoundId.value = unfinished.round_id || null
          currentRoundNumber.value = unfinished.round_number || currentRoundNumber.value
          questionText.value = unfinished.question_content || questionText.value
        }
      }
    }

    isPaused.value = interview.value?.status === 'paused'

    if (interview.value?.status === 'pending') {
      try {
        const startData = await postJson(`${API_BASE_URL}/api/v1/interviews/${interviewId.value}/start/`)
        interview.value = { ...interview.value, ...startData.data, status: 'in_progress' }
      } catch (err) {
        addLog(`自动开始面试失败: ${errorMessage(err)}`)
      }
    }

    const shouldFetchFirstQuestion =
      !hasUnfinishedRound &&
      !currentRoundId.value &&
      ['in_progress', 'pending'].includes(interview.value?.status || '')

    if (shouldFetchFirstQuestion) {
      roundProgressText.value = '正在获取第一题...'
      const ok = await fetchNextQuestion()
      if (ok && !isPaused.value) {
        await playQuestion()
      }
    }
  } catch {
    infoError.value = '面试信息加载失败，已使用默认展示。'
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    networkOnline.value = true
  })
  window.addEventListener('offline', () => {
    networkOnline.value = false
  })
}

loadInterviewInfo()
</script>

<template>
  <div class="voice-page">
    <aside class="voice-sidebar">
      <div class="sidebar-hero">
        <div class="sidebar-hero-top">
          <button class="back-btn" @click="handleBack">返回面试列表</button>
          <div class="scene-light" :class="sceneStatus">
            <span class="dot"></span>
            <span>{{ sceneStatusText }}</span>
          </div>
        </div>
        <div>
          <p class="eyebrow">语音面试</p>
          <h1 class="sidebar-title">{{ interviewNameText }}</h1>
          <p class="sidebar-subtitle">{{ interviewPositionText }}</p>
        </div>
      </div>

      <section class="voice-card sidebar-card">
        <div class="card-title-row">
          <h2>面试状态</h2>
          <span class="mini-badge">{{ interviewStatusText }}</span>
        </div>
        <div class="status-grid">
          <div class="status-item">
            <span class="status-label">当前轮次</span>
            <strong>{{ currentRoundLabel }}</strong>
          </div>
          <div class="status-item">
            <span class="status-label">总轮次</span>
            <strong>{{ interview?.total_rounds || 0 }} 轮</strong>
          </div>
          <div class="status-item">
            <span class="status-label">剩余答题</span>
            <strong>{{ remainingAnswerSecondsText }}</strong>
          </div>
          <div class="status-item">
            <span class="status-label">网络</span>
            <strong>{{ networkStatusText }}</strong>
          </div>
          <div class="status-item">
            <span class="status-label">麦克风</span>
            <strong>{{ micStatusText }}</strong>
          </div>
          <div class="status-item">
            <span class="status-label">题目播报</span>
            <strong>{{ ttsEnabled ? '开启' : '关闭' }}</strong>
          </div>
        </div>
      </section>

      <section class="voice-card sidebar-card">
        <div class="card-title-row">
          <h2>快捷操作</h2>
          <span class="mini-badge">{{ isPaused ? '已暂停' : '进行中' }}</span>
        </div>
        <div class="sidebar-actions">
          <button class="btn primary" @click="pauseInterview">{{ isPaused ? '继续面试' : '暂停面试' }}</button>
          <button class="btn danger" @click="endInterview">结束面试</button>
<!--           <button class="btn secondary" :disabled="!currentText" @click="replayQuestion">重听问题</button>
          <button class="btn secondary" :disabled="!supportsTTS() || isSpeaking" @click="playQuestion">播报题目</button> -->
        </div>
      </section>
    </aside>

    <main class="voice-content">
      <section class="main-stage">
        <article class="role-card interviewer">
          <div class="role-head">
            <div class="avatar interviewer-avatar">AI</div>
            <div>
              <h3>面试官</h3>
              <p>{{ interviewPositionText }}</p>
            </div>
          </div>
          <div class="wave" :class="{ active: isSpeaking }">
            <span v-for="(bar, index) in interviewerWaveBars" :key="`ai-${index}`" :style="{ height: `${bar}px` }"></span>
          </div>
          <p class="role-tip">{{ isSpeaking ? '正在语音播报问题...' : '等待播报' }}</p>
        </article>

        <article class="role-card candidate">
          <div class="role-head">
            <div class="avatar candidate-avatar">你</div>
            <div>
              <h3>候选人</h3>
              <p>{{ interviewStatusText }}</p>
            </div>
          </div>
          <div class="wave" :class="{ active: candidateWaveActive }">
            <span v-for="(bar, index) in candidateWaveBars" :key="`user-${index}`" :style="{ height: `${bar}px` }"></span>
          </div>
          <p class="role-tip">
            {{ recordingState === 'recording' ? `说话 ${speechSecondsText}s / 静音 ${silenceSecondsText}s` : '等待回答' }}
          </p>
        </article>
      </section>

      <section class="voice-card question-panel">
      <div class="question-title-row">
        <h2>当前题目</h2>
        <div class="question-tools">
          <button class="btn secondary" @click="toggleTTSSwitch">{{ ttsEnabled ? '关闭播报' : '开启播报' }}</button>
          <button class="btn secondary" :disabled="!supportsTTS()" @click="playQuestion">播报题目</button>
          <button class="btn secondary" :disabled="!currentText" @click="replayQuestion">重听问题</button>
          <button class="btn secondary" :disabled="!isSpeaking" @click="stopBroadcast">停止播报</button>
        </div>
      </div>
      <textarea v-model="questionText" rows="3" class="question-input" />
      <div class="switch-row">
        <label>
          <input v-model="autoStartRecording" type="checkbox" />
          播报结束后自动开始录音
        </label>
      </div>

      <div v-if="recordingGuideText" class="recording-guide">
        <div class="guide-main">{{ recordingGuideText }}</div>
        <div v-if="recordingGuideSubText" class="guide-sub">{{ recordingGuideSubText }}</div>
      </div>

      <div v-if="roundProgressText" class="round-progress">
        {{ roundProgressText }}
      </div>

      <div v-if="showAutoStartPrompt" class="autostart-prompt">
        <div class="autostart-main">即将开始录音（{{ autoStartCountdown }}s）</div>
        <div class="autostart-sub">请准备回答，你也可以手动覆盖此行为。</div>
        <div class="autostart-actions">
          <button class="btn primary" @click="startRecordingNow">立即开始</button>
          <button class="btn secondary" @click="cancelAutoStartPrompt('已选择稍后开始录音。')">稍后开始</button>
        </div>
      </div>
      <p v-if="infoError || lastError || monitorError" class="error">{{ infoError || lastError || monitorError }}</p>
      </section>

      <section class="bottom-controls">
        <div class="talk-mode">
          <span>主按钮模式：</span>
          <label><input v-model="mainTalkMode" type="radio" value="click" /> 点击开始/结束</label>
          <label><input v-model="mainTalkMode" type="radio" value="hold" /> 按住说话</label>
        </div>

        <div class="primary-actions">
          <button
            v-if="mainTalkMode === 'click'"
            class="btn primary talk-btn"
            :disabled="isPaused || isSpeaking"
            @click="toggleMainTalk"
          >
            {{ recordingState === 'recording' ? '结束回答' : '开始回答' }}
          </button>

          <button
            v-else
            class="btn primary talk-btn"
            :disabled="isPaused || isSpeaking"
            @mousedown="holdStart"
            @mouseup="holdEnd"
            @mouseleave="holdEnd"
            @touchstart.prevent="holdStart"
            @touchend.prevent="holdEnd"
          >
            按住说话
          </button>
        </div>

        <!-- <div class="secondary-actions">
          <button class="btn secondary" @click="replayQuestion">重听问题</button>
        </div> -->

        <!-- <div class="fallback-input">
          <label>文本降级入口（语音异常时使用）</label>
          <textarea v-model="fallbackAnswerText" rows="2" placeholder="输入文本回答..." />
          <button class="btn secondary" @click="submitFallbackText">提交文本回答</button>
        </div> -->
      </section>

      <section class="voice-card">
        <h2>流程日志</h2>
        <ul class="log-list">
          <li v-for="(item, idx) in flowLog" :key="idx">{{ item }}</li>
        </ul>
      </section>
    </main>
  </div>
</template>

<style scoped>
.voice-page {
  min-height: 100dvh;
  padding: 16px;
  background:
    radial-gradient(circle at top left, rgba(102, 126, 234, 0.14), transparent 34%),
    radial-gradient(circle at top right, rgba(15, 118, 110, 0.12), transparent 28%),
    #f5f7fb;
  color: #1f2937;
  display: grid;
  grid-template-columns: 332px minmax(0, 1fr);
  gap: 16px;
}

.voice-sidebar,
.voice-content {
  min-height: calc(100dvh - 32px);
}

.voice-sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 16px;
  align-self: start;
}

.back-btn {
  border: none;
  color: #fff;
  font-weight: 700;
  border-radius: 999px;
  padding: 10px 16px;
  cursor: pointer;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 10px 24px rgba(102, 126, 234, 0.24);
}

.sidebar-hero {
  background: linear-gradient(180deg, #ffffff 0%, #f8faff 100%);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 20px;
  padding: 18px;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
}

.sidebar-hero-top {
  border: none;
  color: #fff;
  font-weight: 600;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.eyebrow {
  margin: 0 0 6px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.sidebar-title {
  margin: 0;
  font-size: 26px;
  line-height: 1.15;
  color: #0f172a;
}

.sidebar-subtitle {
  margin: 8px 0 0;
  color: #475569;
  font-size: 14px;
}

.scene-light {
  padding: 8px 12px;
  border-radius: 999px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #eef2ff;
  color: #3730a3;
}

.scene-light .dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 0 0 currentColor;
  animation: pulse 1.6s infinite;
}

.scene-light.listening {
  background: #e8fff4;
  color: #0f766e;
}

.scene-light.speaking {
  background: #eef2ff;
  color: #4338ca;
}

.scene-light.thinking {
  background: #fff7ed;
  color: #9a3412;
}

.scene-light.paused {
  background: #f3f4f6;
  color: #374151;
}

.voice-card {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 20px;
  padding: 18px;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}

.sidebar-card {
  padding: 16px;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.card-title-row h2 {
  margin: 0;
  font-size: 18px;
  color: #0f172a;
}

.mini-badge {
  padding: 6px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.status-item {
  padding: 12px;
  border-radius: 16px;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.status-label {
  display: block;
  color: #64748b;
  font-size: 12px;
  margin-bottom: 8px;
}

.status-item strong {
  color: #0f172a;
  font-size: 14px;
}

.sidebar-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.sidebar-actions .btn.secondary:last-child {
  grid-column: span 2;
}

.voice-content {
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.main-stage {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.role-card {
  min-height: 208px;
}

.interviewer-avatar {
  background: linear-gradient(135deg, #4338ca 0%, #06b6d4 100%);
}

.candidate-avatar {
  background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%);
}

.wave {
  margin-top: 16px;
  height: 42px;
  display: flex;
  align-items: flex-end;
  gap: 6px;
}

.wave span {
  display: block;
  width: 9px;
  height: 10px;
  border-radius: 999px;
  background: #cbd5e1;
  transition: all 0.2s ease;
}

.wave.active span {
  background: linear-gradient(180deg, #60a5fa 0%, #4f46e5 100%);
  animation: bars 1s infinite ease-in-out;
}

.wave.active span:nth-child(2) {
  animation-delay: 0.08s;
}

.wave.active span:nth-child(3) {
  animation-delay: 0.16s;
}

.wave.active span:nth-child(4) {
  animation-delay: 0.24s;
}

.wave.active span:nth-child(5) {
  animation-delay: 0.32s;
}

@keyframes bars {
  0%,
  100% {
    opacity: 0.6;
    transform: scaleY(0.8);
  }
  50% {
    opacity: 1;
    transform: scaleY(1.15);
  }
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(15, 23, 42, 0.25);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(15, 23, 42, 0);
  }
}

.role-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.role-head h3 {
  margin: 0;
  font-size: 16px;
}

.role-head p {
  margin: 2px 0 0;
  color: #666;
  font-size: 13px;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 999px;
  background: #4338ca;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.role-tip {
  margin: 10px 0 0;
  color: #4b5563;
  font-size: 13px;
}

.voice-card {
  width: 100%;
}

.question-panel {
  margin-top: 0;
}

.autostart-prompt {
  margin-top: 10px;
  border: 1px solid #c7d2fe;
  background: #eef2ff;
  border-radius: 8px;
  padding: 10px;
}

.autostart-main {
  font-weight: 700;
  color: #312e81;
}

.autostart-sub {
  margin-top: 4px;
  color: #4338ca;
  font-size: 13px;
}

.autostart-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

.recording-guide {
  margin-top: 10px;
  border: 1px solid #86efac;
  background: #f0fdf4;
  border-radius: 8px;
  padding: 10px;
}

.guide-main {
  font-weight: 700;
  color: #166534;
}

.guide-sub {
  margin-top: 4px;
  color: #15803d;
  font-size: 13px;
}

.round-progress {
  margin-top: 10px;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  border-radius: 8px;
  padding: 10px;
  color: #1d4ed8;
  font-weight: 600;
}

.question-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.question-title-row h2 {
  margin: 0;
  font-size: 18px;
}

.question-tools {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.label {
  font-weight: 600;
}

.question-input {
  width: 100%;
  margin-top: 8px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
}

.switch-row {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.btn {
  border: none;
  background: #64748b;
  color: #fff;
  border-radius: 6px;
  padding: 8px 12px;
  cursor: pointer;
  font-weight: 600;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.btn.secondary {
  background: #334155;
}

.btn.danger {
  background: #e74c3c;
}

.bottom-controls {
  width: 100%;
}

.talk-mode {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  color: #4b5563;
  margin-bottom: 12px;
}

.primary-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.talk-btn {
  min-width: 190px;
  font-size: 16px;
  padding: 10px 14px;
}

.secondary-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.fallback-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fallback-input label {
  color: #4b5563;
  font-size: 13px;
}

.fallback-input textarea {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px;
  font-size: 14px;
}

.status-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.status-item {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.error {
  margin-top: 10px;
  color: #dc2626;
}

.log-list {
  margin: 12px 0 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-family: Consolas, monospace;
  font-size: 13px;
}

@media (max-width: 900px) {
  .voice-page {
    grid-template-columns: 1fr;
  }

  .voice-sidebar {
    position: static;
    min-height: auto;
  }

  .voice-content {
    min-height: auto;
  }

  .scene-light {
    margin-left: 0;
  }

  .main-stage {
    grid-template-columns: 1fr;
  }

  .question-title-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }

  .sidebar-actions {
    grid-template-columns: 1fr;
  }

  .sidebar-actions .btn.secondary:last-child {
    grid-column: auto;
  }
}
</style>
