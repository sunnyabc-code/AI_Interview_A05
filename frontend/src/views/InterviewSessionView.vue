<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useInterviewSession } from '@/composables/useInterviewSession'

const {
  interview,
  messages,
  currentRound,
  isSubmitting,
  isWaitingForQuestion,
  isClosingInterview,
  isInterviewEnded,
  isPaused,
  countdownSeconds,
  showCountdown,
  fetchInterviewDetail,
  startInterview,
  pauseInterview,
  resumeInterview,
  endInterview,
  getNextQuestion,
  retryGenerateQuestion,
  submitAnswer,
  startPolling,
  stopPolling,
  addWelcomeMessage,
  loadHistoryMessages,
  statusText
} = useInterviewSession()

const loading = ref(false)
const error = ref('')
const userAnswer = ref('')
const isRecording = ref(false)
const isUploadingAudio = ref(false)
const recordedAudioBlob = ref<Blob | null>(null)
const recordedDurationSeconds = ref(0)
const audioError = ref('')

let mediaRecorder: any = null
let mediaStream: MediaStream | null = null
let audioChunks: BlobPart[] = []
let recordingStartedAt = 0

const VOICE_PLACEHOLDER_ANSWER = '1'

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

const getAuthToken = () => localStorage.getItem('access_token') || ''

const cleanupMediaResources = () => {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }
  mediaRecorder = null
}

const startRecording = async () => {
  audioError.value = ''
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new (window as any).MediaRecorder(mediaStream)
    mediaRecorder.ondataavailable = (event: any) => {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }
    mediaRecorder.start()
    recordingStartedAt = Date.now()
    isRecording.value = true
  } catch (err) {
    console.error('启动录音失败:', err)
    audioError.value = '无法启动录音，请检查麦克风权限'
    cleanupMediaResources()
  }
}

const stopRecording = async () => {
  if (!mediaRecorder || mediaRecorder.state !== 'recording') {
    return
  }

  await new Promise<void>((resolve) => {
    if (!mediaRecorder) {
      resolve()
      return
    }

    mediaRecorder.onstop = () => {
      const mimeType = mediaRecorder?.mimeType || 'audio/webm'
      recordedAudioBlob.value = new Blob(audioChunks, { type: mimeType })
      recordedDurationSeconds.value = Math.max(1, Math.round((Date.now() - recordingStartedAt) / 1000))
      isRecording.value = false
      cleanupMediaResources()
      resolve()
    }

    mediaRecorder.stop()
  })
}

const toggleRecording = async () => {
  if (isSubmitting.value || isWaitingForQuestion.value || isClosingInterview.value || isInterviewEnded.value || isPaused.value) {
    return
  }

  if (isRecording.value) {
    await stopRecording()
    return
  }

  await startRecording()
}

const uploadRecordedAudio = async () => {
  if (!recordedAudioBlob.value || !interview.value || !currentRound.value) {
    return false
  }

  const token = getAuthToken()
  if (!token) {
    audioError.value = '登录状态已失效，请重新登录'
    return false
  }

  isUploadingAudio.value = true
  audioError.value = ''

  try {
    const formData = new FormData()
    const extension = recordedAudioBlob.value.type.includes('mpeg') ? 'mp3' : 'webm'
    formData.append('audio_file', recordedAudioBlob.value, `round_${currentRound.value.round_id}.${extension}`)
    formData.append('duration_seconds', String(recordedDurationSeconds.value))

    const response = await fetch(
      `http://localhost:8000/api/v1/interviews/${interview.value.id}/rounds/${currentRound.value.round_id}/audio/`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      }
    )

    const data = await response.json().catch(() => ({}))
    if (!response.ok || ![200, 201].includes(data.code)) {
      audioError.value = data.message || '音频上传失败'
      return false
    }

    return true
  } catch (err) {
    console.error('上传音频失败:', err)
    audioError.value = '音频上传失败，请稍后重试'
    return false
  } finally {
    isUploadingAudio.value = false
  }
}

const handleSendMessage = async () => {
  const textAnswer = userAnswer.value.trim()
  const hasAudioToSend = isRecording.value || !!recordedAudioBlob.value
  if (!textAnswer && !hasAudioToSend) return

  if (isRecording.value) {
    await stopRecording()
  }

  let uploadedAudio = false
  if (recordedAudioBlob.value) {
    uploadedAudio = await uploadRecordedAudio()
    if (!uploadedAudio) return
  }

  const answerToSubmit = textAnswer || (uploadedAudio ? VOICE_PLACEHOLDER_ANSWER : '')
  if (!answerToSubmit) return

  await submitAnswer(answerToSubmit)
  userAnswer.value = ''
  recordedAudioBlob.value = null
  recordedDurationSeconds.value = 0
}

const handleExit = () => {
  stopPolling()
  window.location.href = '/home?menu=interview'
}

const canSubmit = computed(() => {
  const hasText = !!userAnswer.value.trim()
  const hasAudio = isRecording.value || !!recordedAudioBlob.value
  return !isSubmitting.value && 
         !isUploadingAudio.value &&
         (hasText || hasAudio) && 
         currentRound.value && 
         !isWaitingForQuestion.value &&
         !isClosingInterview.value &&
         !isInterviewEnded.value &&
         !isPaused.value
})

onMounted(async () => {
  loading.value = true
  try {
    await fetchInterviewDetail()
    if (interview.value) {
      // 加载历史消息
      await loadHistoryMessages()
      
      // 根据面试状态执行不同操作
      if (interview.value.status === 'pending') {
        // 待开始状态，显示开始按钮
      } else if (interview.value.status === 'in_progress') {
        // 进行中状态，获取下一个问题
        getNextQuestion()
      } else if (interview.value.status === 'paused') {
        // 已暂停状态，显示恢复按钮
      }
    }
  } catch (err) {
    const e = err as any
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  cleanupMediaResources()
  stopPolling()
})
</script>

<template>
  <div class="interview-session">
    <Teleport to="body">
      <div
        v-if="isClosingInterview"
        class="session-exit-overlay"
        aria-live="polite"
      >
        <div class="session-exit-inner">
          <div class="session-spinner" />
          <p class="session-exit-text">正在结束面试，请稍候…</p>
        </div>
      </div>
    </Teleport>

    <div v-if="loading" class="loading">
      加载中...
    </div>
    
    <div v-else-if="error" class="error">
      {{ error }}
    </div>
    
    <div v-else-if="showCountdown" class="countdown-overlay">
      <div class="countdown-content">
        <div class="countdown-number">{{ countdownSeconds }}</div>
        <div class="countdown-text">面试即将开始</div>
        <div class="countdown-bar">
          <div class="countdown-progress" :style="{ width: ((5 - countdownSeconds) / 5 * 100) + '%' }"></div>
        </div>
      </div>
    </div>
    
    <div v-else class="session-container">
      <aside class="session-sidebar">
        <div class="sidebar-content">
          <section class="sidebar-panel sidebar-hero-panel">
            <div class="hero-top">
              <button class="back-btn" @click="handleExit">
                <span class="btn-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M15 6L9 12L15 18" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </span>
                <span>返回面试列表</span>
              </button>
              <span class="mini-badge">{{ statusText(interview && interview.status) }}</span>
            </div>
            <p class="hero-eyebrow">文本面试</p>
            <h2 class="hero-title">{{ (interview && interview.name) || '未命名面试' }}</h2>
            <p class="hero-subtitle">{{ (interview && interview.position_name) || '未设置岗位' }}</p>
            <p class="hero-meta">难度：{{ difficultyText(interview && (interview.difficulty_name || interview.difficulty || interview.difficulty_level)) }}</p>
          </section>

          <section class="sidebar-panel sidebar-status-panel">
            <div class="panel-title-row">
              <h3>面试状态</h3>
              <span class="mini-badge">文本模式</span>
            </div>
            <div class="status-grid">
              <div class="status-item">
                <span class="status-label">当前状态</span>
                <strong>{{ statusText(interview && interview.status) }}</strong>
              </div>
              <div class="status-item">
                <span class="status-label">总轮次</span>
                <strong>{{ (interview && interview.total_rounds) || 0 }} 轮</strong>
              </div>
              <div class="status-item">
                <span class="status-label">当前轮次</span>
                <strong>{{ currentRound ? `第 ${currentRound.round_number} 轮` : '等待开始' }}</strong>
              </div>
              <div class="status-item">
                <span class="status-label">回答提交</span>
                <strong>{{ isSubmitting ? '提交中' : '就绪' }}</strong>
              </div>
              <div class="status-item">
                <span class="status-label">录音状态</span>
                <strong>{{ isRecording ? '录音中' : '未录音' }}</strong>
              </div>
              <div class="status-item">
                <span class="status-label">问题状态</span>
                <strong>{{ isWaitingForQuestion ? '生成中' : '已就绪' }}</strong>
              </div>
            </div>
          </section>

          <section class="sidebar-panel sidebar-actions-panel">
            <div class="panel-title-row">
              <h3>快捷操作</h3>
              <span class="mini-badge">{{ isPaused ? '已暂停' : '进行中' }}</span>
            </div>
            <div class="sidebar-actions">
              <div v-if="interview && interview.status === 'pending'" class="action-group">
                <button class="start-btn" @click="startInterview">
                  开始面试
                </button>
              </div>

              <div v-else-if="interview && interview.status === 'in_progress'" class="action-group">
                <button class="pause-btn" @click="pauseInterview">
                  暂停面试
                </button>
                <button class="end-btn" @click="endInterview">
                  结束面试
                </button>
              </div>

              <div v-else-if="interview && interview.status === 'paused'" class="action-group">
                <button class="resume-btn" @click="resumeInterview">
                  继续面试
                </button>
                <button class="end-btn" @click="endInterview">
                  结束面试
                </button>
              </div>

              <div v-else-if="interview && interview.status === 'completed'" class="action-group">
                <button class="exit-btn" @click="handleExit">
                  退出面试
                </button>
              </div>

              <div v-else class="action-group">
                <button class="exit-btn" @click="handleExit">
                  退出面试
                </button>
              </div>
            </div>
          </section>
        </div>
      </aside>
      
      <main class="session-main">
        <div class="chat-container">
          <div class="chat-messages">
            <div 
              v-for="(message, index) in messages" 
              :key="index"
              :class="['message', 'message-' + message.type]"
            >
              <div class="message-content">
                <div v-if="message.type === 'system'" class="system-message">
                  <span class="system-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8" />
                      <path d="M12 10V16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                      <circle cx="12" cy="7.2" r="1" fill="currentColor" />
                    </svg>
                  </span>
                  {{ message.content }}
                </div>
                <div v-else-if="message.type === 'ai'" class="ai-message">
                  <div class="message-header">
                    <span class="message-role">面试官</span>
                    <span class="message-time">{{ message.time }}</span>
                  </div>
                  <div class="message-text" style="white-space: pre-wrap;">{{ message.content }}</div>
                </div>
                <div v-else-if="message.type === 'user'" class="user-message">
                  <div class="message-header">
                    <span class="message-role">您</span>
                    <span class="message-time">{{ message.time }}</span>
                  </div>
                  <div class="message-text">{{ message.content }}</div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="input-area">
            <textarea
              v-model="userAnswer"
              class="message-input"
              placeholder="请输入您的回答..."
              :disabled="isSubmitting || isWaitingForQuestion || isClosingInterview || isInterviewEnded || isPaused"
              rows="3"
              @keydown.enter.prevent="handleSendMessage"
            />
            <div class="input-buttons">
              <button
                class="record-btn"
                @click="toggleRecording"
                :disabled="isSubmitting || isWaitingForQuestion || isClosingInterview || isInterviewEnded || isPaused || isUploadingAudio"
              >
                {{ isRecording ? '停止录音' : '开始录音' }}
              </button>
              <button 
                class="send-btn" 
                @click="handleSendMessage"
                :disabled="!canSubmit"
              >
                {{ isSubmitting || isUploadingAudio ? '提交中...' : '提交回答' }}
              </button>
              <button 
                class="retry-btn" 
                @click="retryGenerateQuestion"
                :disabled="isWaitingForQuestion || isClosingInterview || isInterviewEnded || isPaused || currentRound"
              >
                重试生成问题
              </button>
            </div>
          </div>
          <div v-if="isRecording || recordedAudioBlob || audioError" class="audio-status">
            <span v-if="isRecording">录音中，请点击“提交回答”发送</span>
            <span v-else-if="recordedAudioBlob">已录制 {{ recordedDurationSeconds }} 秒，点击“提交回答”发送</span>
            <span v-if="audioError" class="audio-error">{{ audioError }}</span>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.interview-session {
  --bg: #f3f5f4;
  --surface: #fbfcfb;
  --surface-strong: #ffffff;
  --line: #dfe6e2;
  --line-soft: #e9eeeb;
  --text: #1f2926;
  --muted: #66756f;
  --accent: #2f5d56;
  --accent-press: #264c46;
  --danger: #b44e46;
  --warning: #9b7a43;

  height: 100vh;
  background:
    radial-gradient(circle at top right, rgba(47, 93, 86, 0.08), transparent 38%),
    radial-gradient(circle at top left, rgba(31, 41, 38, 0.04), transparent 42%),
    var(--bg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: var(--text);
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  font-size: 1.06rem;
  color: var(--muted);
}

.error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #fff7f6;
  color: var(--danger);
  font-size: 1.06rem;
  padding: 1.6rem;
}

.countdown-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(22, 30, 27, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(6px);
}

.countdown-content {
  background: var(--surface-strong);
  padding: 2.2rem 2.4rem;
  border-radius: 20px;
  border: 1px solid var(--line);
  text-align: center;
  box-shadow: 0 24px 46px rgba(31, 41, 38, 0.16);
}

.countdown-number {
  font-size: 4.6rem;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--accent);
  margin-bottom: 0.6rem;
  line-height: 1;
}

.countdown-text {
  font-size: 1.04rem;
  color: var(--muted);
  margin-bottom: 1.25rem;
  font-weight: 500;
}

.countdown-bar {
  width: min(320px, 72vw);
  height: 6px;
  background: #edf1ef;
  border-radius: 999px;
  overflow: hidden;
  margin: 0 auto;
}

.countdown-progress {
  height: 100%;
  background: linear-gradient(90deg, #76968f 0%, #2f5d56 100%);
  border-radius: 999px;
  transition: width 1s linear;
}

.session-container {
  display: flex;
  flex: 1;
  height: 100vh;
  overflow: hidden;
  padding: 14px;
  gap: 12px;
}

.session-sidebar {
  width: 320px;
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  box-shadow: 0 14px 30px rgba(31, 41, 38, 0.08);
}

.sidebar-content {
  flex: 1;
  overflow: hidden;
  padding: 0.95rem;
  display: grid;
  grid-template-rows: minmax(0, 0.9fr) minmax(0, 1.35fr) minmax(0, 0.75fr);
  gap: 0.75rem;
}

.sidebar-panel {
  background: linear-gradient(180deg, #ffffff 0%, #f9fbfa 100%);
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 8px 18px rgba(31, 41, 38, 0.06);
  padding: 0.85rem;
  min-height: 0;
}

.sidebar-hero-panel {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 0.45rem;
}

.hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.45rem;
}

.back-btn {
  border: 1px solid transparent;
  color: #fff;
  font-weight: 600;
  border-radius: 999px;
  padding: 7px 12px;
  cursor: pointer;
  background: linear-gradient(135deg, #3f655f 0%, #2f5d56 100%);
  box-shadow: 0 8px 18px rgba(47, 93, 86, 0.24);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
  font-size: 12px;
}

.back-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(47, 93, 86, 0.26);
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

.hero-eyebrow {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}

.hero-title {
  margin: 0;
  font-size: 27px;
  line-height: 1.18;
  letter-spacing: -0.02em;
  color: var(--text);
  font-weight: 600;
}

.hero-subtitle {
  margin: 0;
  color: #435752;
  font-size: 16px;
}

.hero-meta {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
}

.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  margin-bottom: 0.65rem;
}

.panel-title-row h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
}

.mini-badge {
  padding: 0.22rem 0.48rem;
  border-radius: 999px;
  background: #edf2ef;
  color: #4f5f5a;
  font-size: 0.68rem;
  font-weight: 600;
  border: 1px solid #dde7e3;
}

.sidebar-status-panel {
  display: flex;
  flex-direction: column;
}

.sidebar-status-panel .panel-title-row h3 {
  font-size: 18px;
}

.sidebar-status-panel .mini-badge {
  font-size: 12px;
  padding: 6px 10px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  align-content: start;
  overflow: auto;
}

.status-item {
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  padding: 0.72rem;
  display: flex;
  flex-direction: column;
  gap: 0.38rem;
  background: #fcfdfc;
}

.status-label {
  font-size: 12px;
  color: var(--muted);
}

.status-item strong {
  font-size: 15px;
  color: var(--text);
  font-weight: 600;
}

.sidebar-actions-panel {
  display: flex;
  flex-direction: column;
}

.sidebar-actions {
  min-height: 0;
}

.action-group {
  display: flex;
  flex-direction: column;
  gap: 0.58rem;
}

.start-btn {
  width: 100%;
  background: linear-gradient(135deg, #395f59 0%, #2f5d56 100%);
  color: white;
  border: none;
  padding: 0.78rem 0.9rem;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
}

.start-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(47, 93, 86, 0.26);
}

.pause-btn {
  width: 100%;
  background: #8d7b54;
  color: white;
  border: none;
  padding: 0.72rem 0.86rem;
  border-radius: 10px;
  font-size: 0.86rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
}

.pause-btn:hover {
  background: #796847;
  transform: translateY(-1px);
}

.resume-btn {
  width: 100%;
  background: var(--accent);
  color: white;
  border: none;
  padding: 0.72rem 0.86rem;
  border-radius: 10px;
  font-size: 0.86rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
}

.resume-btn:hover {
  background: var(--accent-press);
  transform: translateY(-1px);
}

.end-btn {
  width: 100%;
  background: #a65951;
  color: white;
  border: none;
  padding: 0.72rem 0.86rem;
  border-radius: 10px;
  font-size: 0.86rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
}

.end-btn:hover {
  background: #8e4b44;
  transform: translateY(-1px);
}

.exit-btn {
  width: 100%;
  background: #70837e;
  color: white;
  border: none;
  padding: 0.72rem 0.86rem;
  border-radius: 10px;
  font-size: 0.86rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
}

.exit-btn:hover {
  background: #5f706b;
  transform: translateY(-1px);
}

.info-value.status-paused {
  color: var(--warning);
}

.session-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 18px;
  height: 100%;
  overflow: hidden;
  box-shadow: 0 14px 30px rgba(31, 41, 38, 0.08);
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.1rem 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.78rem;
  scroll-behavior: smooth;
}

.message {
  max-width: 86%;
  animation: slideIn 0.24s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-system {
  align-self: center;
}

.system-message {
  background: #f0f4f2;
  color: #365651;
  padding: 0.76rem 0.9rem;
  border-radius: 11px;
  border: 1px solid #d6e4df;
  display: flex;
  align-items: center;
  gap: 0.58rem;
  font-size: 0.88rem;
  line-height: 1.55;
}

.system-icon {
  width: 16px;
  height: 16px;
  display: inline-flex;
  color: #365651;
  flex-shrink: 0;
}

.system-icon svg {
  width: 100%;
  height: 100%;
}

.message-ai {
  align-self: flex-start;
}

.ai-message {
  background: var(--surface-strong);
  border-radius: 12px;
  border: 1px solid var(--line-soft);
  box-shadow: 0 6px 16px rgba(31, 41, 38, 0.06);
  overflow: hidden;
}

.message-user {
  align-self: flex-end;
}

.user-message {
  background: linear-gradient(135deg, #40635d 0%, #2f5d56 100%);
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(47, 93, 86, 0.24);
  overflow: hidden;
}

.message-header {
  padding: 0.66rem 0.86rem 0.45rem;
  font-size: 0.75rem;
  font-weight: 500;
  display: flex;
  align-items: center;
}

.ai-message .message-header {
  color: var(--muted);
  border-bottom: 1px solid var(--line-soft);
}

.user-message .message-header {
  color: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.message-role {
  font-weight: 600;
}

.message-time {
  margin-left: auto;
  font-size: 0.7rem;
  opacity: 0.8;
}

.message-text {
  padding: 0.46rem 0.86rem 0.86rem;
  font-size: 0.9rem;
  line-height: 1.62;
  color: var(--text);
}

.user-message .message-text {
  color: white;
}

.input-area {
  --input-btn-height: 36px;
  --input-btn-gap: 7px;
  --input-stack-height: calc(var(--input-btn-height) * 3 + var(--input-btn-gap) * 2);

  background: var(--surface-strong);
  padding: 0.88rem 1.05rem;
  border-top: 1px solid var(--line);
  display: flex;
  gap: 0.8rem;
  align-items: stretch;
  flex-shrink: 0;
  box-shadow: 0 -4px 14px rgba(31, 41, 38, 0.04);
}

.input-buttons {
  display: flex;
  flex-direction: column;
  gap: var(--input-btn-gap);
  min-width: 152px;
  width: 152px;
  height: var(--input-stack-height);
}

.input-buttons button {
  flex: 1;
  min-height: 0;
}

.audio-status {
  margin-top: 0.5rem;
  color: var(--muted);
  font-size: 0.82rem;
  display: flex;
  gap: 0.6rem;
  align-items: center;
  flex-wrap: wrap;
  padding: 0 1rem 0.88rem;
}

.audio-error {
  color: var(--danger);
}

.message-input {
  flex: 1;
  padding: 0.72rem 0.78rem;
  border: 1px solid var(--line);
  border-radius: 11px;
  font-size: 0.9rem;
  font-family: inherit;
  resize: none;
  transition: border-color 0.24s ease, box-shadow 0.24s ease;
  height: var(--input-stack-height);
  min-height: var(--input-stack-height);
  max-height: var(--input-stack-height);
  background: #ffffff;
  color: var(--text);
}

.message-input:focus {
  outline: none;
  border-color: #7b9991;
  box-shadow: 0 0 0 3px rgba(47, 93, 86, 0.12);
}

.message-input:disabled {
  background: #f4f6f5;
  cursor: not-allowed;
}

.send-btn {
  background: linear-gradient(135deg, #3e6560 0%, #2f5d56 100%);
  color: white;
  border: none;
  padding: 0 1.2rem;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
  white-space: nowrap;
}

.record-btn {
  background: #55776f;
  color: white;
  border: none;
  padding: 0 1.06rem;
  border-radius: 10px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
  white-space: nowrap;
}

.record-btn:hover:not(:disabled) {
  background: #46645e;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(47, 93, 86, 0.24);
}

.record-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(47, 93, 86, 0.24);
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.retry-btn {
  background: #6f837d;
  color: white;
  border: none;
  padding: 0 1.06rem;
  border-radius: 10px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
  white-space: nowrap;
}

.retry-btn:hover:not(:disabled) {
  background: #61766f;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(31, 41, 38, 0.18);
}

.retry-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.session-exit-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(251, 252, 251, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.session-exit-inner {
  text-align: center;
  padding: 1.6rem;
}

.session-spinner {
  width: 42px;
  height: 42px;
  margin: 0 auto 0.8rem;
  border: 3px solid #dde7e3;
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: session-spin 0.85s linear infinite;
}

.session-exit-text {
  margin: 0;
  font-size: 0.95rem;
  color: #42514c;
}

@keyframes session-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1024px) {
  .session-container {
    flex-direction: column;
    padding: 10px;
    gap: 10px;
  }
  
  .session-sidebar {
    width: 100%;
    border-bottom: 1px solid var(--line);
    max-height: none;
  }
  
  .sidebar-content {
    padding: 0.85rem;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    overflow-y: auto;
  }
  
  .message {
    max-width: 94%;
  }

  .input-area {
    flex-direction: column;
    align-items: stretch;
  }

  .input-buttons {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.45rem;
    height: auto;
    min-width: 0;
  }

  .message-input {
    height: auto;
    min-height: 94px;
    max-height: 120px;
  }

  .input-buttons button {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .countdown-number {
    font-size: 3.2rem;
  }
  
  .countdown-content {
    padding: 1.5rem 1.2rem;
  }
  
  .hero-title {
    font-size: 1.35rem;
  }

  .sidebar-status-panel .panel-title-row h3 {
    font-size: 1rem;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .chat-messages {
    padding: 0.8rem;
  }
  
  .input-area {
    padding: 0.72rem;
  }
  
  .message-input {
    padding: 0.65rem;
    min-height: 88px;
  }
  
  .send-btn,
  .record-btn,
  .retry-btn {
    font-size: 0.8rem;
    padding: 0.58rem 0.6rem;
  }
  
  .input-buttons {
    grid-template-columns: 1fr;
    gap: 0.38rem;
  }

  .audio-status {
    padding: 0 0.72rem 0.72rem;
  }
}
</style>
