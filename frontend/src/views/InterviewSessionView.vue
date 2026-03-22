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
  fetchInterviewDetail,
  getNextQuestion,
  submitAnswer,
  startPolling,
  stopPolling,
  addWelcomeMessage,
  loadHistoryMessages,
  statusText
} = useInterviewSession()

const loading = ref(false)
const error = ref('')
const showCountdown = ref(true)
const countdownSeconds = ref(5)
const countdownInterval = ref<number | null>(null)
const userAnswer = ref('')

const startCountdown = () => {
  showCountdown.value = true
  countdownSeconds.value = 5
  
  countdownInterval.value = window.setInterval(() => {
    countdownSeconds.value--
    if (countdownSeconds.value <= 0) {
      stopCountdown()
      addWelcomeMessage()
      getNextQuestion()
    }
  }, 1000)
}

const stopCountdown = () => {
  if (countdownInterval.value) {
    clearInterval(countdownInterval.value)
    countdownInterval.value = null
  }
  showCountdown.value = false
}

const handleSendMessage = () => {
  if (!userAnswer.value.trim()) return
  submitAnswer(userAnswer.value.trim())
  userAnswer.value = ''
}

const handleExit = () => {
  stopCountdown()
  stopPolling()
  window.location.href = '/home?menu=interview'
}

const canSubmit = computed(() => {
  return !isSubmitting.value && 
         userAnswer.value.trim() && 
         currentRound.value && 
         !isWaitingForQuestion.value &&
         !isInterviewEnded.value
})

onMounted(async () => {
  loading.value = true
  try {
    await fetchInterviewDetail()
    if (interview.value) {
      // 加载历史消息
      await loadHistoryMessages()
      startCountdown()
    }
  } catch (err: any) {
    error.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  stopCountdown()
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
            <button class="exit-btn" @click="handleExit">
              退出面试
            </button>
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
              :disabled="isSubmitting || isWaitingForQuestion || isInterviewEnded"
              rows="3"
              @keydown.enter.prevent="handleSendMessage"
            />
            <button 
              class="send-btn" 
              @click="handleSendMessage"
              :disabled="!canSubmit"
            >
              {{ isSubmitting ? '提交中...' : '提交回答' }}
            </button>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.interview-session {
  min-height: 100vh;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
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

.exit-btn {
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

.exit-btn:hover {
  background: #c0392b;
  transform: translateY(-2px);
}

.session-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f9f9f9;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.send-btn:disabled {
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
}
</style>
