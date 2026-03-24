<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useInterviewSession } from '@/composables/useInterviewSession'

const {
  interview,
  messages,
  currentRound,
  isSubmitting,
  isWaitingForQuestion,
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
  if (isSubmitting.value || isWaitingForQuestion.value || isInterviewEnded.value || isPaused.value) {
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
          <h2 class="sidebar-title">面试信息</h2>
          
          <div class="info-section">
            <div class="info-item">
              <span class="info-label">面试名称</span>
              <span class="info-value">{{ interview?.name || '未命名' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">岗位</span>
              <span class="info-value">{{ interview?.position_name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">难度</span>
              <span class="info-value">{{ interview?.difficulty_name || '未设置' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">模式</span>
              <span class="info-value">文本模式</span>
            </div>
            <div class="info-item">
              <span class="info-label">状态</span>
              <span class="info-value status-{{ interview?.status }}">
                {{ statusText(interview?.status) }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">总轮次</span>
              <span class="info-value">{{ interview?.total_rounds }} 轮</span>
            </div>
            <div v-if="currentRound" class="info-item">
              <span class="info-label">当前轮次</span>
              <span class="info-value">第 {{ currentRound.round_number }} 轮</span>
            </div>
          </div>
          
          <div class="sidebar-actions">
            <!-- 面试控制按钮 -->
            <div v-if="interview?.status === 'pending'" class="action-group">
              <button class="start-btn" @click="startInterview">
                开始面试
              </button>
            </div>
            
            <div v-else-if="interview?.status === 'in_progress'" class="action-group">
              <button class="pause-btn" @click="pauseInterview">
                暂停面试
              </button>
              <button class="end-btn" @click="endInterview">
                结束面试
              </button>
            </div>
            
            <div v-else-if="interview?.status === 'paused'" class="action-group">
              <button class="resume-btn" @click="resumeInterview">
                继续面试
              </button>
              <button class="end-btn" @click="endInterview">
                结束面试
              </button>
            </div>
            
            <div v-else-if="interview?.status === 'completed'" class="action-group">
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
                  <span class="system-icon">ℹ</span>
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
              :disabled="isSubmitting || isWaitingForQuestion || isInterviewEnded || isPaused"
              rows="3"
              @keydown.enter.prevent="handleSendMessage"
            />
            <div class="input-buttons">
              <button
                class="record-btn"
                @click="toggleRecording"
                :disabled="isSubmitting || isWaitingForQuestion || isInterviewEnded || isPaused || isUploadingAudio"
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
                :disabled="isWaitingForQuestion || isInterviewEnded || isPaused || currentRound"
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
  height: 100vh;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  font-size: 1.2rem;
  color: #666;
}

.error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #fee;
  color: #e74c3c;
  font-size: 1.2rem;
  padding: 2rem;
}

.countdown-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.countdown-content {
  background: white;
  padding: 3rem 4rem;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.countdown-number {
  font-size: 6rem;
  font-weight: 700;
  color: #667eea;
  margin-bottom: 1rem;
  line-height: 1;
}

.countdown-text {
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 2rem;
  font-weight: 600;
}

.countdown-bar {
  width: 300px;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin: 0 auto;
}

.countdown-progress {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 1s linear;
}

.session-container {
  display: flex;
  flex: 1;
  height: calc(100vh - 60px);
  overflow: hidden;
}

.session-sidebar {
  width: 320px;
  background: white;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.sidebar-title {
  color: #333;
  font-size: 1.3rem;
  font-weight: 600;
  margin: 0 0 1.5rem 0;
  padding-bottom: 1rem;
  border-bottom: 2px solid #f0f0f0;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.info-label {
  color: #666;
  font-size: 0.85rem;
  font-weight: 500;
}

.info-value {
  color: #333;
  font-size: 0.95rem;
  font-weight: 600;
}

.info-value.status-pending {
  color: #999;
}

.info-value.status-in_progress {
  color: #3498db;
}

.info-value.status-completed {
  color: #27ae60;
}

.info-value.status-cancelled {
  color: #e74c3c;
}

.sidebar-actions {
  margin-top: auto;
  padding-top: 2rem;
  border-top: 1px solid #f0f0f0;
}

.action-group {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.start-btn {
  width: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 1rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.pause-btn {
  width: 100%;
  background: #f39c12;
  color: white;
  border: none;
  padding: 0.8rem;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.pause-btn:hover {
  background: #e67e22;
  transform: translateY(-2px);
}

.resume-btn {
  width: 100%;
  background: #27ae60;
  color: white;
  border: none;
  padding: 0.8rem;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.resume-btn:hover {
  background: #229954;
  transform: translateY(-2px);
}

.end-btn {
  width: 100%;
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.8rem;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.end-btn:hover {
  background: #c0392b;
  transform: translateY(-2px);
}

.exit-btn {
  width: 100%;
  background: #95a5a6;
  color: white;
  border: none;
  padding: 0.8rem;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.exit-btn:hover {
  background: #7f8c8d;
  transform: translateY(-2px);
}

.info-value.status-paused {
  color: #f39c12;
}

.session-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f9f9f9;
  height: 100%;
  overflow: hidden;
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
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  scroll-behavior: smooth;
}

.message {
  max-width: 80%;
  animation: slideIn 0.3s ease;
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
  background: #e3f2fd;
  color: #1e40af;
  padding: 1rem 1.5rem;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  font-size: 0.95rem;
  line-height: 1.5;
}

.system-icon {
  font-size: 1.5rem;
  font-weight: 700;
}

.message-ai {
  align-self: flex-start;
}

.ai-message {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.message-user {
  align-self: flex-end;
}

.user-message {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  overflow: hidden;
}

.message-header {
  padding: 0.8rem 1rem 0.5rem;
  font-size: 0.8rem;
  font-weight: 500;
}

.ai-message .message-header {
  color: #666;
  border-bottom: 1px solid #f0f0f0;
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
  font-size: 0.75rem;
  opacity: 0.8;
}

.message-text {
  padding: 0.5rem 1rem 1rem;
  font-size: 0.95rem;
  line-height: 1.6;
  color: #333;
}

.user-message .message-text {
  color: white;
}

.input-area {
  background: white;
  padding: 1rem 1.5rem;
  border-top: 1px solid #e0e0e0;
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-shrink: 0;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
}

.input-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.audio-status {
  margin-top: 0.6rem;
  color: #4b5563;
  font-size: 0.86rem;
  display: flex;
  gap: 0.8rem;
  align-items: center;
  flex-wrap: wrap;
}

.audio-error {
  color: #dc2626;
}

.message-input {
  flex: 1;
  padding: 0.8rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 0.95rem;
  font-family: inherit;
  resize: none;
  transition: border-color 0.3s ease;
  max-height: 120px;
}

.message-input:focus {
  outline: none;
  border-color: #667eea;
}

.message-input:disabled {
  background: #f9f9f9;
  cursor: not-allowed;
}

.send-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.8rem 2rem;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.record-btn {
  background: #ec4899;
  color: white;
  border: none;
  padding: 0.6rem 1.5rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.record-btn:hover:not(:disabled) {
  background: #db2777;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(219, 39, 119, 0.35);
}

.record-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.retry-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 0.6rem 1.5rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.retry-btn:hover:not(:disabled) {
  background: #2980b9;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.4);
}

.retry-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 1024px) {
  .session-container {
    flex-direction: column;
  }
  
  .session-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #e0e0e0;
    max-height: 300px;
  }
  
  .sidebar-content {
    padding: 1rem;
  }
  
  .sidebar-actions {
    display: none;
  }
  
  .message {
    max-width: 95%;
  }
}

@media (max-width: 768px) {
  .countdown-number {
    font-size: 4rem;
  }
  
  .countdown-content {
    padding: 2rem;
  }
  
  .sidebar-title {
    font-size: 1.1rem;
  }
  
  .chat-messages {
    padding: 1rem;
  }
  
  .input-area {
    padding: 1rem;
  }
  
  .message-input {
    padding: 0.6rem;
  }
  
  .send-btn {
    padding: 0.6rem 1.5rem;
    font-size: 0.9rem;
  }
  
  .retry-btn {
    padding: 0.5rem 1.2rem;
    font-size: 0.8rem;
  }
  
  .input-buttons {
    gap: 0.3rem;
  }
}
</style>
