<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import InterviewModal from '../components/InterviewModal.vue'
import InterviewCard from '../components/InterviewCard.vue'
import InterviewDetailModal from '../components/InterviewDetailModal.vue'

const props = defineProps<{
  active: boolean
}>()

const emit = defineEmits<{
  update: []
}>()

const router = useRouter()

const showCreateModal = ref(false)
const showDetailModal = ref(false)
const selectedInterview = ref<any>(null)
const interviews = ref<any[]>([])
const loading = ref(false)
const error = ref('')

const API_BASE_URL = 'http://localhost:8000'

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  }
}

const fetchInterviews = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/interviews/`, {
      headers: getAuthHeaders()
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.code === 200) {
        interviews.value = data.data
      } else {
        error.value = data.message || '获取面试列表失败'
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

const handleCreateInterview = () => {
  showCreateModal.value = true
}

const handleModalClose = () => {
  showCreateModal.value = false
  fetchInterviews()
  emit('update')
}

const handleInterviewCardClick = (interview: any) => {
  selectedInterview.value = interview
  showDetailModal.value = true
}

const handleDetailModalClose = () => {
  showDetailModal.value = false
}

const handleStartInterview = async (interview: any) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interview.id}/`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({ status: 'in_progress' })
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.code === 200) {
        showDetailModal.value = false
        router.push(`/interview/${interview.id}`)
      } else {
        alert(data.message || '开始面试失败')
      }
    } else {
      alert('网络错误，请稍后重试')
    }
  } catch (err) {
    alert('网络错误，请稍后重试')
  }
}

watch(() => props.active, (newActive) => {
  if (newActive) {
    fetchInterviews()
  }
})

onMounted(() => {
  if (props.active) {
    fetchInterviews()
  }
})
</script>

<template>
  <div class="interview-view">
    <h2>面试功能</h2>
    <p>点击下方按钮创建新面试</p>
    <button class="create-interview-btn" @click="handleCreateInterview">
      创建新面试
    </button>
    
    <div class="interviews-list">
      <h3 class="section-title">我的面试</h3>
      
      <div v-if="loading" class="loading">
        加载中...
      </div>
      
      <div v-else-if="error" class="error">
        {{ error }}
      </div>
      
      <div v-else-if="interviews.length === 0" class="empty-state">
        暂无面试记录
      </div>
      
      <div v-else class="interview-cards">
        <InterviewCard 
          v-for="interview in interviews" 
          :key="interview.id"
          :interview="interview"
          :on-card-click="handleInterviewCardClick"
        />
      </div>
    </div>
    
    <InterviewModal :show="showCreateModal" @close="handleModalClose" />
    <InterviewDetailModal 
      :show="showDetailModal" 
      :interview-id="selectedInterview?.id || null"
      @close="handleDetailModalClose"
      @start="handleStartInterview"
    />
  </div>
</template>

<style scoped>
.interview-view {
  width: 100%;
}

.create-interview-btn {
  margin-top: 2rem;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.create-interview-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.interviews-list {
  margin-top: 3rem;
}

.section-title {
  color: #333;
  font-size: 1.3rem;
  font-weight: 600;
  margin: 0 0 1.5rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #f0f0f0;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #666;
  font-size: 1rem;
  background: #f9f9f9;
  border-radius: 4px;
}

.error {
  background: #fee;
  color: #e74c3c;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  text-align: center;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #999;
  font-size: 1rem;
  background: #f9f9f9;
  border-radius: 4px;
}

.interview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

@media (max-width: 768px) {
  .interview-cards {
    grid-template-columns: 1fr;
  }
  
  .interviews-list {
    margin-top: 2rem;
  }
  
  .section-title {
    font-size: 1.1rem;
  }
  
  .create-interview-btn {
    width: 100%;
    padding: 0.8rem;
    font-size: 1rem;
  }
}
</style>
