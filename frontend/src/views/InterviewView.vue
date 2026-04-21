<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { API_BASE_URL } from '@/utils/api'
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

const POSITION_FILTER_KEY = 'interview_position_filter'

const showCreateModal = ref(false)
const showDetailModal = ref(false)
const selectedInterview = ref<any>(null)
const interviews = ref<any[]>([])
const positions = ref<{ id: number; name: string; code: string }[]>([])
const selectedPositionId = ref<number | null>(null)
const loading = ref(false)
const error = ref('')
const toastMessage = ref('')
const toastType = ref<'success' | 'error'>('success')
const showToast = ref(false)

const positionFilterLabel = computed(() => {
  if (selectedPositionId.value == null) return '全部岗位'
  const p = positions.value.find((x) => x.id === selectedPositionId.value)
  return p?.name || '岗位'
})

const getInterviewRoute = (interview: any) => {
  if (interview?.mode === 'voice') {
    return `/interview/voice/${interview.id}`
  }

  return `/interview/${interview.id}`
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  }
}

const fetchPositions = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/positions/`, {
      headers: getAuthHeaders(),
    })
    if (response.ok) {
      const data = await response.json()
      if (data.code === 200 && Array.isArray(data.data)) {
        positions.value = data.data
      }
    }
  } catch {
    /* ignore */
  }
}

const setPositionFilter = (id: number | null) => {
  selectedPositionId.value = id
  if (id == null) {
    localStorage.removeItem(POSITION_FILTER_KEY)
  } else {
    localStorage.setItem(POSITION_FILTER_KEY, String(id))
  }
  fetchInterviews()
}

const fetchInterviews = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const q =
      selectedPositionId.value != null
        ? `?position_id=${selectedPositionId.value}`
        : ''
    const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${q}`, {
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

const handleModalClose = (createdInterview?: any) => {
  showCreateModal.value = false
  fetchInterviews()
  emit('update')

  if (createdInterview?.id) {
    router.push(getInterviewRoute(createdInterview))
  }
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
    // 已在进行中的面试直接进入页面。
    if (interview.status === 'in_progress') {
      showDetailModal.value = false
      router.push(getInterviewRoute(interview))
      return
    }

    let endpoint = `${API_BASE_URL}/api/v1/interviews/${interview.id}/start/`
    if (interview.status === 'paused') {
      endpoint = `${API_BASE_URL}/api/v1/interviews/${interview.id}/resume/`
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({})
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.code === 200) {
        showDetailModal.value = false
        const routeInterview = {
          ...interview,
          ...(data.data || {}),
          status: 'in_progress',
        }
        router.push(getInterviewRoute(routeInterview))
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

const showToastMessage = (message: string, type: 'success' | 'error' = 'success') => {
  toastMessage.value = message
  toastType.value = type
  showToast.value = true
  setTimeout(() => {
    showToast.value = false
  }, 3000)
}

const handleDeleteInterview = async (interviewId: number) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId}/`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.code === 200) {
        fetchInterviews()
        emit('update')
        showToastMessage('删除面试成功', 'success')
      } else {
        showToastMessage(data.message || '删除面试失败', 'error')
      }
    } else if (response.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/auth'
    } else {
      const errorData = await response.json().catch(() => ({ message: '删除面试失败' }))
      showToastMessage(errorData.message || '删除面试失败', 'error')
    }
  } catch (err) {
    showToastMessage('网络错误，请稍后重试', 'error')
  }
}

watch(() => props.active, (newActive) => {
  if (newActive) {
    fetchInterviews()
  }
})

onMounted(() => {
  const saved = localStorage.getItem(POSITION_FILTER_KEY)
  if (saved) {
    const n = parseInt(saved, 10)
    if (Number.isFinite(n)) {
      selectedPositionId.value = n
    }
  }
  fetchPositions()
  if (props.active) {
    fetchInterviews()
  }
})
</script>

<template>
  <div class="interview-view">
    <section class="hero-panel">
      <div class="hero-copy">
        <p class="hero-eyebrow">Interview Workspace</p>
        <h2>面试管理中心</h2>
        <p>按岗位筛选面试记录；结束后可随时打开评估报告（数据保存在服务端）。</p>
      </div>
      <button class="create-interview-btn" @click="handleCreateInterview">
        <span class="icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 6V18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            <path d="M6 12H18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </span>
        <span>创建新面试</span>
      </button>
    </section>

    <div class="position-filter" role="group" aria-label="按岗位筛选">
      <span class="filter-label">
        <span class="icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 6H20" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
            <path d="M7 12H17" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
            <path d="M10 18H14" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
          </svg>
        </span>
        岗位
      </span>
      <div class="filter-chips">
        <button
          type="button"
          class="chip"
          :class="{ active: selectedPositionId === null }"
          @click="setPositionFilter(null)"
        >
          全部
        </button>
        <button
          v-for="p in positions"
          :key="p.id"
          type="button"
          class="chip"
          :class="{ active: selectedPositionId === p.id }"
          @click="setPositionFilter(p.id)"
        >
          {{ p.name }}
        </button>
      </div>
    </div>
    
    <div class="interviews-list">
      <div class="section-head">
        <div class="section-head-inner">
          <h3 class="section-title">
            <span class="icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="4" y="5" width="16" height="14" rx="3" stroke="currentColor" stroke-width="1.7"/>
                <path d="M8 10H16" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
                <path d="M8 14H13" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
              </svg>
            </span>
            <span>我的面试</span>
          </h3>
          <p class="section-hint">{{ positionFilterLabel }}</p>
        </div>
      </div>
      
      <div v-if="loading" class="loading">
        <span class="spinner" aria-hidden="true"></span>
        加载中...
      </div>
      
      <div v-else-if="error" class="error">
        <span class="icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/>
            <path d="M12 8V13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            <circle cx="12" cy="16.5" r="1" fill="currentColor"/>
          </svg>
        </span>
        {{ error }}
      </div>
      
      <div v-else-if="interviews.length === 0" class="empty-state">
        <span class="icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="5" width="16" height="14" rx="3" stroke="currentColor" stroke-width="1.7"/>
            <path d="M8 10H16" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
          </svg>
        </span>
        暂无面试记录
      </div>
      
      <div v-else class="interview-cards">
        <InterviewCard 
          v-for="interview in interviews" 
          :key="interview.id"
          :interview="interview"
          :on-card-click="handleInterviewCardClick"
          :on-delete="handleDeleteInterview"
        />
      </div>
    </div>
    
    <InterviewModal :show="showCreateModal" @close="handleModalClose" />
    <InterviewDetailModal 
      :show="showDetailModal" 
      :interview-id="selectedInterview ? selectedInterview.id : null"
      @close="handleDetailModalClose"
      @start="handleStartInterview"
    />
    
    <!-- Toast 提示 -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="showToast" class="toast-container" :class="toastType">
          <span class="icon" aria-hidden="true">
            <svg v-if="toastType === 'success'" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/>
              <path d="M8 12.5L10.7 15.2L16 9.9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/>
              <path d="M12 8V13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <circle cx="12" cy="16.5" r="1" fill="currentColor"/>
            </svg>
          </span>
          <span class="toast-message">{{ toastMessage }}</span>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.interview-view {
  --bg: #f3f5f4;
  --surface: #ffffff;
  --surface-soft: #f8fbf9;
  --line: #dfe6e2;
  --line-soft: #e8eeeb;
  --text: #1f2926;
  --muted: #66756f;
  --accent: #2f5d56;
  --accent-2: #406a63;
  --danger: #b44e46;

  width: 100%;
  color: var(--text);
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 240px);
}

.hero-panel {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbf9 100%);
  box-shadow: 0 14px 28px rgba(31, 41, 38, 0.08);
  padding: 1rem 1.1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.hero-copy h2 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.hero-copy p {
  margin: 0.4rem 0 0;
  color: var(--muted);
  font-size: 0.95rem;
}

.hero-eyebrow {
  margin: 0 0 0.35rem !important;
  font-size: 0.72rem !important;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--muted);
  font-weight: 600;
}

.create-interview-btn {
  padding: 0.72rem 1.12rem;
  background: linear-gradient(135deg, var(--accent-2) 0%, var(--accent) 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.42rem;
  white-space: nowrap;
}

.create-interview-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(47, 93, 86, 0.26);
}

.interviews-list {
  margin-top: 1rem;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface);
  box-shadow: 0 14px 28px rgba(31, 41, 38, 0.08);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  min-height: clamp(360px, 54vh, 760px);
}

.position-filter {
  margin-top: 1rem;
  padding: 0.85rem 1rem;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--surface);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem 1rem;
}

.filter-label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.chip {
  padding: 0.45rem 0.85rem;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--surface-soft);
  color: var(--text);
  font-size: 0.86rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.chip:hover {
  border-color: #c5d4cd;
  background: #fff;
}

.chip.active {
  border-color: var(--accent);
  background: rgba(47, 93, 86, 0.1);
  color: var(--accent);
}

.section-head {
  width: 100%;
}

.section-head-inner {
  width: 100%;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid var(--line-soft);
  margin-bottom: 0.85rem;
}

.section-hint {
  margin: 0.35rem 0 0;
  font-size: 0.82rem;
  color: var(--muted);
}

.section-title {
  color: var(--text);
  font-size: 1.08rem;
  font-weight: 600;
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.42rem;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.52rem;
  text-align: center;
  padding: 2.4rem;
  color: var(--muted);
  font-size: 0.95rem;
  background: var(--surface-soft);
  border-radius: 12px;
  border: 1px solid var(--line-soft);
}

.error {
  background: #fff6f5;
  color: var(--danger);
  padding: 0.9rem 1rem;
  border-radius: 12px;
  border: 1px solid #f2d7d4;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
}

.empty-state {
  text-align: center;
  padding: 2.4rem 1rem;
  color: var(--muted);
  font-size: 0.95rem;
  background: var(--surface-soft);
  border-radius: 12px;
  border: 1px solid var(--line-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  flex: 1;
  min-height: 240px;
}

.interview-cards {
  --list-card-radius: 16px;
  --list-card-title-size: 1rem;
  --list-card-text-size: 0.83rem;
  --list-card-label-size: 0.81rem;
  --list-card-button-height: 34px;
  --list-card-button-font-size: 0.8rem;
  --list-card-status-height: 28px;
  --list-card-status-font-size: 0.75rem;
  --list-card-action-gap: 0.5rem;
  --list-card-body-gap: 0.42rem;

  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 0.95rem;
}

.icon {
  width: 16px;
  height: 16px;
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
  border: 2px solid #d7e2dd;
  border-top-color: var(--accent);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .interview-view {
    min-height: calc(100vh - 200px);
  }

  .hero-panel {
    flex-direction: column;
    align-items: stretch;
    gap: 0.8rem;
  }

  .create-interview-btn {
    width: 100%;
  }

  .interview-cards {
    grid-template-columns: 1fr;
  }
  
  .interviews-list {
    margin-top: 0.8rem;
    padding: 0.8rem;
    min-height: calc(100vh - 280px);
  }
  
  .section-title {
    font-size: 1rem;
  }
}

/* Toast 提示样式 */
.toast-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.78rem 1rem;
  border-radius: 12px;
  box-shadow: 0 10px 24px rgba(31, 41, 38, 0.18);
  z-index: 9999;
  font-weight: 500;
  font-size: 0.9rem;
  display: inline-flex;
  align-items: center;
  gap: 0.42rem;
}

.toast-container.success {
  background: #edf5f2;
  color: #2f5d56;
  border: 1px solid #d6e6df;
}

.toast-container.error {
  background: #fff4f3;
  color: #9d4a43;
  border: 1px solid #f0d5d1;
}

.toast-message {
  display: block;
}

/* Toast 动画 */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

.toast-enter-to,
.toast-leave-from {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
</style>
