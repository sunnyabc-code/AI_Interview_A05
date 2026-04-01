<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

const API_BASE_URL = 'http://localhost:8000'

const props = defineProps<{
  show: boolean
  interviewId: number | null
}>()

const emit = defineEmits<{
  close: []
  start: [interview: any]
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
        <h2 class="modal-title">面试详情</h2>
        <button class="modal-close" @click="handleClose">&times;</button>
      </div>
      
      <div v-if="loading" class="loading">
        加载中...
      </div>
      
      <div v-else-if="error" class="error-message">
        {{ error }}
      </div>
      
      <div v-else-if="interview" class="interview-detail">
        <div class="detail-section">
          <h3 class="section-title">基本信息</h3>
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
              <span class="value">{{ interview.difficulty_name || '未设置' }}</span>
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
          <h3 class="section-title">题型配置</h3>
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
          <h3 class="section-title">备注</h3>
          <div class="notes">
            {{ interview.notes }}
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button 
          v-if="interview && interview.status === 'pending'" 
          class="start-btn" 
          @click="handleStart"
        >
          开始面试
        </button>
        <button 
          v-if="interview && (interview.status === 'in_progress' || interview.status === 'paused')" 
          class="start-btn" 
          @click="handleStart"
        >
          继续面试
        </button>
        <button class="close-btn" @click="handleClose">关闭</button>
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
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  color: #333;
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
  padding: 0;
  line-height: 1;
}

.modal-close:hover {
  color: #333;
}

.error-message {
  background: #fee;
  color: #e74c3c;
  padding: 1rem;
  margin: 1rem 1.5rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.loading {
  padding: 3rem;
  text-align: center;
  color: #666;
  font-size: 1rem;
}

.interview-detail {
  padding: 1.5rem;
}

.detail-section {
  margin-bottom: 2rem;
}

.section-title {
  color: #333;
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #eee;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.label {
  color: #666;
  font-size: 0.8rem;
  font-weight: 500;
}

.value {
  color: #333;
  font-size: 0.9rem;
  font-weight: 500;
}

.value.status-pending {
  color: #999;
}

.value.status-in_progress {
  color: #3498db;
}

.value.status-completed {
  color: #27ae60;
}

.value.status-cancelled {
  color: #e74c3c;
}

.notes {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 4px;
  color: #333;
  font-size: 0.9rem;
  line-height: 1.4;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.start-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.5rem 1.5rem;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.close-btn {
  background: #f0f0f0;
  border: none;
  padding: 0.5rem 1.5rem;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #333;
  cursor: pointer;
  transition: background 0.3s ease;
}

.close-btn:hover {
  background: #e0e0e0;
}

@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    max-height: 90vh;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-header,
  .interview-detail,
  .modal-footer {
    padding: 1rem;
  }
}
</style>
