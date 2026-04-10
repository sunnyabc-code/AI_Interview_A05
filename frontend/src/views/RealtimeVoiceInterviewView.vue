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
  silenceThresholdSeconds: 10,
  autoStopOnSilence: false,
  maxAnswerSeconds: 300,
  volumeThreshold: 0.02,
})

const interview = ref<any>(null)
const currentRoundNumber = ref(1)
const currentRoundId = ref<number | null>(null)
const currentQuestionCategory = ref('')
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
const showInterviewEndedNotice = ref(false)
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
  autoStartCountdown.value = 5
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

const difficultyText = (rawDifficulty: unknown) => {
  const map: Record<number, string> = {
    1: '简单',
    2: '中等',
    3: '困难'
  }

  const num = Number(rawDifficulty)
  if (Number.isFinite(num) && map[num]) {
    return map[num]
  }

  if (typeof rawDifficulty === 'string' && rawDifficulty.trim()) {
    return rawDifficulty
  }

  return '未设置'
}

const interviewNameText = computed(() => interview.value?.name || '未命名面试')
const interviewPositionText = computed(() => interview.value?.position_name || '未设置岗位')
const interviewDifficultyText = computed(() =>
  difficultyText(interview.value?.difficulty_name ?? interview.value?.difficulty ?? interview.value?.difficulty_level)
)
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
const questionCategoryTextMap: Record<string, string> = {
  technical: '知识点题',
  project: '项目题',
  scenario: '场景题',
}
const currentRoundLabel = computed(() => {
  return currentRoundNumber.value ? `第 ${currentRoundNumber.value} 轮` : '等待生成'
})
const currentQuestionTypeText = computed(() => {
  const raw = (currentQuestionCategory.value || '').trim()
  if (!raw) return '待生成'
  return questionCategoryTextMap[raw] || raw
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
const remainingAnswerSeconds = computed(() => {
  return Math.max(endDetector.maxAnswerSeconds - Math.floor(endDetector.elapsedMs.value / 1000), 0)
})
const remainingAnswerSecondsText = computed(() => {
  return `${remainingAnswerSeconds.value}s`
})
const isAnswerTimeRunningOut = computed(() => {
  if (recordingState.value !== 'recording') return false
  return remainingAnswerSeconds.value > 0 && remainingAnswerSeconds.value <= 10
})
const answerTimeWarningText = computed(() => {
  if (!isAnswerTimeRunningOut.value) return ''
  return `答题时间快没有了，请尽快收尾（剩余 ${remainingAnswerSeconds.value} 秒）`
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

const speechRecognitionErrorText = (event: any) => {
  const error = String(event?.error || 'unknown')
  const message = String(event?.message || '')

  const errorMap: Record<string, string> = {
    'no-speech': '没有检测到语音输入',
    aborted: '识别被中止',
    'audio-capture': '无法捕获麦克风音频',
    network: '识别服务网络异常',
    'not-allowed': '麦克风权限被拒绝或未授权',
    'service-not-allowed': '当前环境不允许使用语音识别服务',
    'bad-grammar': '语法配置异常',
    'language-not-supported': '当前语言不被支持',
  }

  const baseText = errorMap[error] || '未知语音识别错误'
  return `${baseText}（error=${error}${message ? `, message=${message}` : ''}）`
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
  recognition.onerror = (event: any) => {
    const detail = speechRecognitionErrorText(event)
    addLog(`关键词识别异常：${detail}，继续使用静音+超时判停。`)

    if (event?.error === 'not-allowed' || event?.error === 'service-not-allowed' || event?.error === 'audio-capture') {
      micStatus.value = 'denied'
    }
  }
  recognition.onend = () => {
    if (recordingState.value === 'recording') {
      try {
        recognition.start()
      } catch {
        addLog('关键词识别重启失败，继续使用静音+超时判停。')
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
      currentQuestionCategory.value = data.data.category_name || data.data.category || ''
      roundProgressText.value = ''
      addLog(`已获取第 ${currentRoundNumber.value} 轮题目。`)
      return true
    }

    if (data.code === 200 && data.data?.status === 'completed') {
      roundProgressText.value = ''
      currentQuestionCategory.value = ''
      showInterviewEndedNotice.value = true
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
    showInterviewEndedNotice.value = true
    addLog('面试结束，结果报告生成中。')
    return
  } catch (err) {
    addLog(`结束面试接口失败: ${errorMessage(err)}，将直接返回列表。`)
  }

  router.push('/home?menu=interview')
}

const backToInterviewList = () => {
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
          currentQuestionCategory.value = unfinished.category_name || unfinished.category || ''
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
  <div v-if="showInterviewEndedNotice" class="ended-screen">
    <div class="ended-card">
      <h1>当前面试已结束</h1>
      <p>结果报告正在生成中，请稍后在评估报告中查看。</p>
      <button class="btn primary" @click="backToInterviewList">返回面试列表</button>
    </div>
  </div>

  <div v-else class="voice-page">
    <div class="voice-sidebar-shell">
    <aside class="voice-sidebar">
      <div class="sidebar-hero">
        <div class="sidebar-hero-top">
          <button class="back-btn" @click="handleBack">
            <span class="btn-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M15 6L9 12L15 18" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            <span>返回面试列表</span>
          </button>
          <span class="mini-badge">{{ interviewStatusText }}</span>
        </div>
        <div>
          <p class="eyebrow">语音面试</p>
          <h1 class="sidebar-title">{{ interviewNameText }}</h1>
          <p class="sidebar-subtitle">{{ interviewPositionText }}</p>
          <p class="sidebar-meta">难度：{{ interviewDifficultyText }}</p>
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
            <span class="status-label">题目类型</span>
            <strong>{{ currentQuestionTypeText }}</strong>
          </div>
          <div class="status-item">
            <span class="status-label">总轮次</span>
            <strong>{{ (interview && interview.total_rounds) || 0 }} 轮</strong>
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
          <div class="action-group">
            <button class="btn primary" @click="pauseInterview">
              <span class="btn-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path v-if="!isPaused" d="M10 7H8V17H10V7ZM16 7H14V17H16V7Z" fill="currentColor"/>
                  <path v-else d="M9 7L17 12L9 17V7Z" fill="currentColor"/>
                </svg>
              </span>
              <span>{{ isPaused ? '继续面试' : '暂停面试' }}</span>
            </button>
            <button class="btn danger" @click="endInterview">
              <span class="btn-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor"/>
                </svg>
              </span>
              <span>结束面试</span>
            </button>
          </div>
<!--           <button class="btn secondary" :disabled="!currentText" @click="replayQuestion">重听问题</button>
          <button class="btn secondary" :disabled="!supportsTTS() || isSpeaking" @click="playQuestion">播报题目</button> -->
        </div>
      </section>
    </aside>
    </div>

    <div class="voice-content-shell">
    <main class="voice-content">
      <section class="main-stage">
        <article class="role-card interviewer">
          <div class="role-head">
            <div class="avatar interviewer-avatar" aria-hidden="true">
              <svg class="avatar-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="5" y="8" width="14" height="10" rx="4" stroke="currentColor" stroke-width="1.7"/>
                <circle cx="9" cy="13" r="1.1" fill="currentColor"/>
                <circle cx="15" cy="13" r="1.1" fill="currentColor"/>
                <path d="M12 4V7" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
              </svg>
            </div>
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
            <div class="avatar candidate-avatar" aria-hidden="true">
              <svg class="avatar-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="8.5" r="3.2" stroke="currentColor" stroke-width="1.7"/>
                <path d="M6.5 18C7.8 14.8 10.2 13.5 12 13.5C13.8 13.5 16.2 14.8 17.5 18" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
              </svg>
            </div>
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
          <button class="btn secondary" @click="toggleTTSSwitch">
            <span class="btn-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5 14V10H8L12 7V17L8 14H5Z" fill="currentColor"/>
              </svg>
            </span>
            <span>{{ ttsEnabled ? '关闭播报' : '开启播报' }}</span>
          </button>
          <button class="btn secondary" :disabled="!supportsTTS()" @click="playQuestion">
            <span class="btn-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 7L17 12L9 17V7Z" fill="currentColor"/>
              </svg>
            </span>
            <span>播报题目</span>
          </button>
          <button class="btn secondary" :disabled="!currentText" @click="replayQuestion">
            <span class="btn-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 7V13H12" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M6.3 13C7.2 16 10 18 13.1 18C17 18 20 15 20 11.2C20 7.4 17 4.4 13.1 4.4C10.9 4.4 8.9 5.4 7.6 7.1" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
              </svg>
            </span>
            <span>重听问题</span>
          </button>
          <button class="btn secondary" :disabled="!isSpeaking" @click="stopBroadcast">
            <span class="btn-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor"/>
              </svg>
            </span>
            <span>停止播报</span>
          </button>
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

      <div v-if="isAnswerTimeRunningOut" class="time-warning">
        {{ answerTimeWarningText }}
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

      <!-- <section class="voice-card">
        <h2>流程日志</h2>
        <ul class="log-list">
          <li v-for="(item, idx) in flowLog" :key="idx">{{ item }}</li>
        </ul>
      </section> -->
    </main>
    </div>
  </div>
</template>

<style scoped>
.voice-page {
  --bg: #f2f5f3;
  --surface: #fbfcfb;
  --surface-solid: #ffffff;
  --line: #dde5e1;
  --line-soft: #e7edea;
  --text: #1f2926;
  --muted: #66746f;
  --accent: #2f5d56;
  --accent-soft: #eaf1ee;
  --danger: #a7564f;
  --danger-soft: #f9efee;
  --warning: #8f7748;
  --warning-soft: #f8f4ea;

  min-height: 100dvh;
  padding: 14px;
  background:
    radial-gradient(circle at top left, rgba(47, 93, 86, 0.08), transparent 36%),
    radial-gradient(circle at top right, rgba(31, 41, 38, 0.05), transparent 34%),
    var(--bg);
  color: var(--text);
  display: grid;
  grid-template-columns: 338px minmax(0, 1fr);
  gap: 12px;
}

.voice-sidebar-shell {
  padding: 6px;
  border-radius: 20px;
  border: 1px solid #d8e2dd;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.66) 0%, rgba(242, 246, 244, 0.7) 100%);
  box-shadow: 0 14px 30px rgba(31, 41, 38, 0.08);
  min-width: 0;
  min-height: calc(100dvh - 28px);
}

.voice-content-shell {
  padding: 6px;
  border-radius: 20px;
  border: 1px solid #d8e2dd;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.66) 0%, rgba(242, 246, 244, 0.7) 100%);
  box-shadow: 0 14px 30px rgba(31, 41, 38, 0.08);
  min-width: 0;
  min-height: calc(100dvh - 28px);
  position: relative;
  overflow: hidden;
  isolation: isolate;
}

.voice-content-shell::before {
  content: '';
  position: absolute;
  right: 18px;
  bottom: 16px;
  width: 250px;
  height: 320px;
  pointer-events: none;
  z-index: 0;
  background:
    linear-gradient(150deg, rgba(74, 132, 112, 0.2) 0%, rgba(74, 132, 112, 0.08) 48%, rgba(74, 132, 112, 0.02) 100%),
    radial-gradient(70% 72% at 34% 28%, rgba(255, 255, 255, 0.24) 0%, rgba(255, 255, 255, 0) 100%);
  border-radius: 62% 38% 56% 44% / 40% 62% 38% 60%;
  transform: rotate(-17deg);
  opacity: 0.72;
  box-shadow: inset 0 0 0 1px rgba(82, 134, 116, 0.14);
}

.voice-content-shell::after {
  content: '';
  position: absolute;
  right: 180px;
  top: 50%;
  width: 180px;
  height: 220px;
  pointer-events: none;
  z-index: 0;
  opacity: 0.45;
  background:
    radial-gradient(84% 76% at 34% 32%, rgba(73, 128, 110, 0.18) 0%, rgba(73, 128, 110, 0.04) 70%, rgba(73, 128, 110, 0) 100%),
    radial-gradient(56% 62% at 62% 62%, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0) 100%);
  border-radius: 58% 42% 60% 40% / 46% 60% 40% 54%;
  transform: translateY(-50%) rotate(18deg);
  filter: blur(0.2px);
}

.voice-content-shell > .voice-content {
  position: relative;
  z-index: 1;
}

.ended-screen {
  min-height: 100dvh;
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at top left, rgba(47, 93, 86, 0.1), transparent 36%),
    radial-gradient(circle at top right, rgba(31, 41, 38, 0.06), transparent 32%),
    var(--bg);
}

.ended-card {
  width: min(520px, 100%);
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: 0 20px 40px rgba(31, 41, 38, 0.14);
  padding: 24px;
  text-align: center;
}

.ended-card h1 {
  margin: 0;
  color: var(--text);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.ended-card p {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 15px;
}

.ended-card .btn {
  margin-top: 18px;
}

.voice-sidebar,
.voice-content {
  min-height: 100%;
}

.voice-sidebar {
  display: grid;
  grid-template-rows: minmax(0, 0.82fr) minmax(0, 1.62fr) minmax(0, 0.56fr);
  gap: 10px;
  position: sticky;
  top: 0;
  align-self: start;
  height: 100%;
}

.voice-sidebar > * {
  min-height: 0;
  height: 100%;
}

.back-btn {
  border: 1px solid transparent;
  color: #fff;
  font-weight: 600;
  border-radius: 999px;
  padding: 8px 13px;
  cursor: pointer;
  background: linear-gradient(135deg, #3f655f 0%, #2f5d56 100%);
  box-shadow: 0 8px 18px rgba(47, 93, 86, 0.24);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.back-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(47, 93, 86, 0.26);
}

.sidebar-hero {
  background: linear-gradient(180deg, #ffffff 0%, #f9fbfa 100%);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 14px 28px rgba(31, 41, 38, 0.08);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 14px;
}

.sidebar-hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 0;
}

.sidebar-hero > div:last-child {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: flex-start;
  text-align: left;
}

.eyebrow {
  margin: 0 0 5px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
}

.sidebar-title {
  margin: 0;
  font-size: 27px;
  line-height: 1.18;
  color: var(--text);
  letter-spacing: -0.02em;
  font-weight: 600;
}

.sidebar-subtitle {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 16px;
}

.sidebar-meta {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 14px;
}

.voice-card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 14px 28px rgba(31, 41, 38, 0.08);
  backdrop-filter: blur(6px);
}

.sidebar-card {
  padding: 14px;
  display: flex;
  flex-direction: column;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.card-title-row h2 {
  margin: 0;
  font-size: 16px;
  color: var(--text);
  font-weight: 600;
}

.mini-badge {
  padding: 5px 9px;
  border-radius: 999px;
  background: #edf2ef;
  color: #4f5f5a;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid #dde7e3;
}

.status-grid {
  margin-top: 2px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  flex: 1;
  align-content: start;
}

.status-item {
  padding: 10px;
  border-radius: 12px;
  background: linear-gradient(180deg, #fbfdfc 0%, #ffffff 100%);
  border: 1px solid var(--line-soft);
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.status-label {
  display: block;
  color: var(--muted);
  font-size: 11px;
}

.status-item strong {
  color: var(--text);
  font-size: 15px;
  font-weight: 600;
}

.voice-sidebar .sidebar-card:first-of-type .card-title-row h2 {
  font-size: 18px;
}

.voice-sidebar .sidebar-card:first-of-type .mini-badge {
  font-size: 12px;
  padding: 6px 10px;
}

.voice-sidebar .sidebar-card:first-of-type .status-item {
  padding: 12px;
  gap: 6px;
}

.voice-sidebar .sidebar-card:first-of-type .status-label {
  font-size: 12px;
}

.voice-sidebar .sidebar-card:last-of-type {
  padding: 11px;
}

.voice-sidebar .sidebar-card:last-of-type .card-title-row {
  margin-bottom: 8px;
}

.voice-sidebar .sidebar-card:last-of-type .card-title-row h2 {
  font-size: 17px;
}

.voice-sidebar .sidebar-card:last-of-type .mini-badge {
  font-size: 12px;
  padding: 5px 9px;
}

.voice-sidebar .sidebar-card:last-of-type .sidebar-actions {
  gap: 6px;
}

.voice-sidebar .sidebar-card:last-of-type .btn {
  padding: 7px 11px;
  font-size: 13px;
}

.sidebar-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.voice-content {
  display: grid;
  grid-template-rows: repeat(3, minmax(0, 1fr));
  align-items: stretch;
  gap: 10px;
  min-width: 0;
  height: 100%;
}

.main-stage {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  align-items: stretch;
}

.role-card {
  min-height: 194px;
  height: 100%;
}

.interviewer-avatar {
  background: #edf3f1;
  color: #335751;
  border: 1px solid #d8e4df;
}

.candidate-avatar {
  background: #eef2f0;
  color: #456660;
  border: 1px solid #dce6e2;
}

.wave {
  margin-top: 14px;
  height: 40px;
  display: flex;
  align-items: flex-end;
  gap: 5px;
}

.wave span {
  display: block;
  width: 8px;
  height: 10px;
  border-radius: 999px;
  background: #ced8d4;
  transition: all 0.2s ease;
}

.wave.active span {
  background: linear-gradient(180deg, #6a8c84 0%, #2f5d56 100%);
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
    box-shadow: 0 0 0 0 rgba(47, 93, 86, 0.2);
  }
  70% {
    box-shadow: 0 0 0 9px rgba(47, 93, 86, 0);
  }
}

.role-head {
  display: flex;
  align-items: center;
  gap: 9px;
}

.role-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.role-head p {
  margin: 2px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.avatar {
  width: 60px;
  height: 60px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-icon {
  width: 40px;
  height: 40px;
}

.role-tip {
  margin: 9px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.voice-card {
  width: 100%;
}

.question-panel {
  margin-top: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.autostart-prompt {
  margin-top: 8px;
  border: 1px solid #d4e2dd;
  background: #edf4f1;
  border-radius: 10px;
  padding: 9px 10px;
}

.autostart-main {
  font-weight: 600;
  color: #2f5d56;
  font-size: 15px;
}

.autostart-sub {
  margin-top: 3px;
  color: #50726b;
  font-size: 14px;
}

.autostart-actions {
  margin-top: 7px;
  display: flex;
  gap: 7px;
}

.recording-guide {
  margin-top: 8px;
  border: 1px solid #d3e2dc;
  background: #eff6f3;
  border-radius: 10px;
  padding: 9px 10px;
}

.guide-main {
  font-weight: 600;
  color: #325d56;
  font-size: 15px;
}

.guide-sub {
  margin-top: 3px;
  color: #55756e;
  font-size: 14px;
}

.round-progress {
  margin-top: 8px;
  border: 1px solid #d8e5e0;
  background: #f0f5f3;
  border-radius: 10px;
  padding: 9px 10px;
  color: #446a62;
  font-weight: 600;
  font-size: 15px;
}

.time-warning {
  margin-top: 8px;
  border: 1px solid #e7dcc7;
  background: var(--warning-soft);
  border-radius: 10px;
  padding: 9px 10px;
  color: var(--warning);
  font-weight: 600;
  font-size: 15px;
}

.question-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.question-title-row h2 {
  margin: 0;
  font-size: 19px;
  font-weight: 600;
}

.question-tools {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.question-input {
  width: 100%;
  margin-top: 7px;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 9px 10px;
  font-size: 16px;
  color: var(--text);
  background: var(--surface-solid);
  min-height: 86px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.question-input:focus {
  outline: none;
  border-color: #7e9b94;
  box-shadow: 0 0 0 3px rgba(47, 93, 86, 0.11);
}

.switch-row {
  margin-top: 10px;
  display: flex;
  gap: 7px;
  align-items: center;
  flex-wrap: wrap;
  color: var(--muted);
  font-size: 15px;
}

.question-panel .btn {
  font-size: 14px;
}

.btn {
  border: 1px solid transparent;
  background: #5e706b;
  color: #fff;
  border-radius: 10px;
  padding: 7px 11px;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.52;
  cursor: not-allowed;
}

.btn.primary {
  background: linear-gradient(135deg, #3e6560 0%, #2f5d56 100%);
  box-shadow: 0 8px 16px rgba(47, 93, 86, 0.22);
}

.btn.secondary {
  background: #6a7d77;
}

.btn.danger {
  background: var(--danger);
}

.btn-icon {
  width: 14px;
  height: 14px;
  display: inline-flex;
}

.btn-icon svg {
  width: 100%;
  height: 100%;
}

.bottom-controls {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.talk-mode {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
  color: var(--muted);
  margin-bottom: 12px;
  font-size: 16px;
  line-height: 1.25;
  font-weight: 600;
  text-align: center;
}

.talk-mode label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #445650;
}

.talk-mode input[type='radio'] {
  width: 16px;
  height: 16px;
}

.primary-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  justify-content: center;
  align-items: center;
}

.talk-btn {
  min-width: 280px;
  min-height: 56px;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.01em;
  padding: 12px 22px;
  border-radius: 14px;
}

.primary-actions .talk-btn.btn.primary {
  background: linear-gradient(135deg, #3f8f7e 0%, #2f7f6f 48%, #2b675d 100%);
  box-shadow:
    0 16px 30px rgba(47, 127, 111, 0.34),
    0 0 0 1px rgba(255, 255, 255, 0.34) inset;
}

.primary-actions .talk-btn.btn.primary:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.01);
  box-shadow:
    0 20px 36px rgba(47, 127, 111, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.4) inset;
}

.primary-actions .talk-btn.btn.primary:active:not(:disabled) {
  transform: translateY(0);
}

.error {
  margin-top: 8px;
  color: var(--danger);
  font-size: 14px;
}

.log-list {
  margin: 10px 0 0;
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-family: Consolas, monospace;
  font-size: 12px;
  color: #33403c;
}

@media (max-width: 900px) {
  .voice-page {
    grid-template-columns: 1fr;
    padding: 10px;
    gap: 10px;
  }

  .voice-sidebar-shell,
  .voice-content-shell {
    min-height: auto;
    padding: 4px;
  }

  .voice-content-shell::before,
  .voice-content-shell::after {
    opacity: 0.24;
  }

  .voice-sidebar {
    position: static;
    min-height: auto;
    height: auto;
    display: flex;
    flex-direction: column;
  }

  .voice-sidebar > * {
    height: auto;
  }

  .voice-content {
    min-height: auto;
    height: auto;
    display: flex;
    flex-direction: column;
  }

  .main-stage {
    grid-template-columns: 1fr;
  }

  .question-title-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 7px;
  }

  .status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .sidebar-actions {
    width: 100%;
  }

  .autostart-actions,
  .primary-actions {
    flex-direction: column;
  }

  .talk-mode {
    font-size: 15px;
    gap: 10px;
  }

  .talk-mode label {
    font-size: 14px;
  }

  .talk-btn,
  .primary-actions .btn,
  .autostart-actions .btn {
    width: 100%;
    min-width: 0;
  }
}

@media (max-width: 640px) {
  .sidebar-title {
    font-size: 21px;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }

  .question-tools {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .question-tools .btn {
    width: 100%;
  }

  .voice-card,
  .sidebar-card,
  .sidebar-hero {
    border-radius: 14px;
    padding: 12px;
  }

  .voice-content-shell::before,
  .voice-content-shell::after {
    opacity: 0.14;
  }

  .voice-content-shell::before {
    width: 150px;
    height: 190px;
    right: 10px;
    bottom: 10px;
  }

  .voice-content-shell::after {
    width: 110px;
    height: 140px;
    right: 96px;
  }

  .sidebar-hero {
    gap: 10px;
  }

  .question-input {
    min-height: 78px;
  }
}
</style>
