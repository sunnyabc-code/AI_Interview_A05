<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'

const API_BASE_URL = 'http://localhost:8000'
const router = useRouter()

const props = defineProps<{
  show: boolean
  interviewId: number | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'start', interview: any): void
}>()

const interview = ref<any>(null)
const loading = ref(false)
const error = ref('')

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  }
}

const fetchInterviewDetail = async () => {
  if (!props.interviewId) return
  
  loading.value = true
  error.value = ''
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${props.interviewId}/`, {
      headers: getAuthHeaders()
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.code === 200) {
        interview.value = data.data
      } else {
        error.value = data.message || '获取面试详情失败'
      }
    } else if (response.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/auth'
    } else {
      error.value = '网络错误，请稍后重试'
    }
  } catch (err) {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  emit('close')
}

const handleStart = () => {
  if (interview.value) {
    emit('start', interview.value)
  }
}

const openReport = () => {
  if (!interview.value?.id) return
  router.push(`/interview/${interview.value.id}/evaluation`)
}

const statusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '待开始',
    in_progress: '进行中',
    paused: '已暂停',
    completed: '已完成',
    cancelled: '已取消'
  }
  return statusMap[status] || status
}

const modeText = (mode: string) => {
  const modeMap: Record<string, string> = {
    text: '文本模式',
    voice: '语音模式',
    mixed: '混合模式'
  }
  return modeMap[mode] || mode
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

const interviewDifficultyText = () => {
  if (!interview.value) {
    return '未设置'
  }
  return difficultyText(interview.value.difficulty_name || interview.value.difficulty || interview.value.difficulty_level)
}

watch(() => props.show, (newShow) => {
  if (newShow && props.interviewId) {
    fetchInterviewDetail()
  }
})

onMounted(() => {
  if (props.show && props.interviewId) {
    fetchInterviewDetail()
  }
})
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="5" width="16" height="14" rx="3" stroke="currentColor" stroke-width="1.8"/>
              <path d="M8 10H16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M8 14H13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </span>
          <span>面试详情</span>
        </h2>
        <button class="modal-close" @click="handleClose" aria-label="关闭">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M7 7L17 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
              <path d="M17 7L7 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
            </svg>
          </span>
        </button>
      </div>
      
      <div v-if="loading" class="loading">
        <span class="spinner" aria-hidden="true"></span>
        加载中...
      </div>
      
      <div v-else-if="error" class="error-message">
        <span class="icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/>
            <path d="M12 8V13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            <circle cx="12" cy="16.5" r="1" fill="currentColor"/>
          </svg>
        </span>
        {{ error }}
      </div>
      
      <div v-else-if="interview" class="interview-detail">
        <div class="detail-section">
          <h3 class="section-title">
            <span class="icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="8.2" r="3" stroke="currentColor" stroke-width="1.8"/>
                <path d="M6.5 18C7.7 14.9 10 13.5 12 13.5C14 13.5 16.3 14.9 17.5 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
            </span>
            <span>基本信息</span>
          </h3>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">面试名称</span>
              <span class="value">{{ interview.name || '未命名' }}</span>
            </div>
            <div class="info-item">
              <span class="label">岗位</span>
              <span class="value">{{ interview.position_name }}</span>
            </div>
            <div class="info-item">
              <span class="label">难度</span>
              <span class="value">{{ interviewDifficultyText() }}</span>
            </div>
            <div class="info-item">
              <span class="label">状态</span>
              <span class="value status-{{ interview.status }}">{{ statusText(interview.status) }}</span>
            </div>
            <div class="info-item">
              <span class="label">模式</span>
              <span class="value">{{ modeText(interview.mode) }}</span>
            </div>
            <div class="info-item">
              <span class="label">总轮次</span>
              <span class="value">{{ interview.total_rounds }} 轮</span>
            </div>
            <div class="info-item">
              <span class="label">创建时间</span>
              <span class="value">{{ new Date(interview.created_at).toLocaleString() }}</span>
            </div>
          </div>
        </div>
        
        <div class="detail-section">
          <h3 class="section-title">
            <span class="icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 17V11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                <path d="M12 17V8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                <path d="M18 17V13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
            </span>
            <span>题型配置</span>
          </h3>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">技术知识题</span>
              <span class="value">{{ interview.enable_technical_questions ? '启用' : '禁用' }}</span>
            </div>
            <div class="info-item">
              <span class="label">项目经历题</span>
              <span class="value">{{ interview.enable_project_questions ? '启用' : '禁用' }}</span>
            </div>
            <div class="info-item">
              <span class="label">场景题</span>
              <span class="value">{{ interview.enable_scenario_questions ? '启用' : '禁用' }}</span>
            </div>
          </div>
        </div>
        
        <div class="detail-section" v-if="interview.notes">
          <h3 class="section-title">
            <span class="icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="4" y="5" width="16" height="14" rx="3" stroke="currentColor" stroke-width="1.8"/>
                <path d="M8 10H16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                <path d="M8 14H13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
            </span>
            <span>备注</span>
          </h3>
          <div class="notes">
            {{ interview.notes }}
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button
          v-if="interview && interview.status === 'completed'"
          type="button"
          class="report-btn"
          @click="openReport"
        >
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M6 17V11" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
              <path d="M12 17V8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
              <path d="M18 17V13" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
            </svg>
          </span>
          查看面试报告
        </button>
        <button 
          v-if="interview && interview.status === 'pending'" 
          class="start-btn" 
          @click="handleStart"
        >
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 7L17 12L9 17V7Z" fill="currentColor"/>
            </svg>
          </span>
          开始面试
        </button>
        <button 
          v-if="interview && (interview.status === 'in_progress' || interview.status === 'paused')" 
          class="start-btn" 
          @click="handleStart"
        >
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 7L17 12L9 17V7Z" fill="currentColor"/>
            </svg>
          </span>
          继续面试
        </button>
        <button class="close-btn" @click="handleClose">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M7 7L17 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
              <path d="M17 7L7 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
            </svg>
          </span>
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(22, 30, 27, 0.56);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(6px);
}

.modal-content {
  --surface: #ffffff;
  --surface-soft: #f8fbf9;
  --line: #dfe6e2;
  --line-soft: #e8eeeb;
  --text: #1f2926;
  --muted: #66756f;
  --accent: #2f5d56;
  --danger: #b44e46;

  background: var(--surface);
  border-radius: 18px;
  width: 90%;
  max-width: 700px;
  max-height: 86vh;
  overflow: hidden;
  border: 1px solid var(--line);
  box-shadow: 0 26px 52px rgba(31, 41, 38, 0.2);
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 1rem 1.1rem;
  border-bottom: 1px solid var(--line-soft);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(180deg, #ffffff 0%, #f9fbfa 100%);
}

.modal-title {
  color: var(--text);
  font-size: 1.08rem;
  font-weight: 600;
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.modal-close {
  background: #f3f7f5;
  border: 1px solid #dce6e1;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  cursor: pointer;
  color: #49655f;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.22s ease;
}

.modal-close:hover {
  background: #eaf2ef;
}

.error-message {
  background: #fff6f5;
  color: var(--danger);
  padding: 0.86rem 0.9rem;
  margin: 1rem 1.1rem;
  border-radius: 12px;
  border: 1px solid #f1d8d5;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.loading {
  padding: 2.4rem;
  text-align: center;
  color: var(--muted);
  font-size: 0.96rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.interview-detail {
  padding: 1rem 1.1rem;
  overflow-y: auto;
}

.detail-section {
  margin-bottom: 1.1rem;
  border: 1px solid var(--line-soft);
  border-radius: 14px;
  padding: 0.82rem;
  background: var(--surface-soft);
}

.section-title {
  color: var(--text);
  font-size: 0.96rem;
  font-weight: 600;
  margin: 0 0 0.7rem 0;
  padding-bottom: 0.55rem;
  border-bottom: 1px solid var(--line);
  display: inline-flex;
  align-items: center;
  gap: 0.42rem;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.22rem;
  padding: 0.62rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #ffffff;
}

.label {
  color: var(--muted);
  font-size: 0.74rem;
  font-weight: 500;
}

.value {
  color: var(--text);
  font-size: 0.86rem;
  font-weight: 600;
}

.value.status-pending {
  color: #7a8681;
}

.value.status-in_progress {
  color: var(--accent);
}

.value.status-paused {
  color: #8f6f3f;
}

.value.status-completed {
  color: #4d7c67;
}

.value.status-cancelled {
  color: var(--danger);
}

.notes {
  background: #ffffff;
  padding: 0.86rem;
  border-radius: 10px;
  border: 1px solid var(--line);
  color: var(--text);
  font-size: 0.88rem;
  line-height: 1.52;
}

.modal-footer {
  padding: 0.92rem 1.1rem;
  border-top: 1px solid var(--line-soft);
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 0.55rem;
  background: linear-gradient(180deg, #ffffff 0%, #f9fbfa 100%);
}

.report-btn {
  margin-right: auto;
  background: linear-gradient(135deg, rgba(47, 93, 86, 0.12) 0%, #ffffff 55%);
  border: 1px solid rgba(47, 93, 86, 0.28);
  color: #264a45;
  padding: 0.56rem 0.86rem;
  border-radius: 10px;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.36rem;
}

.report-btn:hover {
  border-color: #2f5d56;
  background: linear-gradient(135deg, rgba(47, 93, 86, 0.18) 0%, #f8fcfa 100%);
  box-shadow: 0 6px 16px rgba(47, 93, 86, 0.12);
}

.start-btn {
  background: linear-gradient(135deg, #3f655f 0%, #2f5d56 100%);
  color: white;
  border: none;
  padding: 0.56rem 0.86rem;
  border-radius: 10px;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.36rem;
}

.start-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(47, 93, 86, 0.24);
}

.close-btn {
  background: #eef3f1;
  border: 1px solid #dae5df;
  padding: 0.56rem 0.86rem;
  border-radius: 10px;
  font-size: 0.84rem;
  color: #395a53;
  cursor: pointer;
  transition: background 0.24s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.36rem;
  font-weight: 600;
}

.close-btn:hover {
  background: #e4ede9;
}

.icon {
  width: 15px;
  height: 15px;
  display: inline-flex;
  flex-shrink: 0;
}

.icon svg {
  width: 100%;
  height: 100%;
}

.spinner {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid #d8e3de;
  border-top-color: var(--accent);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    max-height: 90vh;
    border-radius: 14px;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-header,
  .interview-detail,
  .modal-footer {
    padding: 0.85rem;
  }

  .modal-footer {
    flex-wrap: wrap;
  }

  .start-btn,
  .close-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
