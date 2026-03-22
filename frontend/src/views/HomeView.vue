<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))
const activeMenu = ref('home')
const showCreateModal = ref(false)

const API_BASE_URL = 'http://localhost:8000'

const menuItems = [
  { id: 'home', label: '首页' },
  { id: 'interview', label: '面试' },
  { id: 'history', label: '历史记录' },
  { id: 'profile', label: '个人中心' }
]

const form = ref({
  name: '',
  position: null as number | null,
  enable_technical_questions: true,
  enable_project_questions: true,
  enable_scenario_questions: true,
  difficulty_config: null as number | null,
  mode: 'text',
  total_rounds: 0,
  notes: ''
})

const positions = ref<any[]>([])
const difficultyConfigs = ref<any[]>([])
const loading = ref(false)
const error = ref('')

const handleMenuClick = (menuId: string) => {
  activeMenu.value = menuId
}

const calculateTotalRounds = () => {
  const selectedConfig = difficultyConfigs.value.find(c => c.id === form.value.difficulty_config)
  
  if (!selectedConfig) {
    form.value.total_rounds = 0
    return
  }
  
  let total = 0
  
  if (form.value.enable_technical_questions) {
    total += (selectedConfig.technical_chain_count || 0) * (selectedConfig.technical_max_followup_depth || 1)
  }
  
  if (form.value.enable_project_questions) {
    total += (selectedConfig.project_chain_count || 0) * (selectedConfig.project_max_followup_depth || 1)
  }
  
  if (form.value.enable_scenario_questions) {
    total += (selectedConfig.scenario_chain_count || 0) * (selectedConfig.scenario_max_followup_depth || 1)
  }
  
  form.value.total_rounds = total
}

const handleCreateInterview = () => {
  showCreateModal.value = true
  fetchPositions()
  fetchDifficultyConfigs()
}

const handleCloseModal = () => {
  showCreateModal.value = false
  resetForm()
}

const resetForm = () => {
  form.value = {
    name: '',
    position: null,
    enable_technical_questions: true,
    enable_project_questions: true,
    enable_scenario_questions: true,
    difficulty_config: null,
    mode: 'text',
    total_rounds: 0,
    notes: ''
  }
  error.value = ''
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
      headers: getAuthHeaders()
    })
    
    console.log('Positions response status:', response.status)
    
    if (response.ok) {
      const data = await response.json()
      console.log('Positions data:', data)
      positions.value = data.data || []
      console.log('Positions value after assignment:', positions.value)
      console.log('First position details:', positions.value[0])
      console.log('First position id:', positions.value[0]?.id)
      console.log('First position name:', positions.value[0]?.name)
    } else {
      const errorData = await response.json()
      console.error('获取岗位列表失败:', errorData)
    }
  } catch (err) {
    console.error('获取岗位列表错误:', err)
  }
}

const fetchDifficultyConfigs = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/evaluations/difficulty-configs/`, {
      headers: getAuthHeaders()
    })
    
    if (response.ok) {
      const data = await response.json()
      difficultyConfigs.value = data.data || []
    }
  } catch (err) {
    console.error('获取难度配置错误:', err)
  }
}

const handleSubmit = async () => {
  console.log('Form value:', form.value)
  console.log('Position value:', form.value.position)
  console.log('Positions list:', positions.value)
  
  if (!form.value.name) {
    error.value = '请输入面试名称'
    return
  }
  
  if (form.value.position === null || form.value.position === undefined) {
    error.value = '请选择岗位'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/interviews/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(form.value)
    })

    const data = await response.json()

    if (data.code === 201 || data.code === 200) {
      handleCloseModal()
    } else {
      error.value = data.message || '创建失败'
    }
  } catch (err) {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  router.push('/auth')
}

onMounted(() => {
  const token = localStorage.getItem('access_token')
  if (!token) {
    router.push('/auth')
  }
})

watch([
  () => form.value.difficulty_config,
  () => form.value.enable_technical_questions,
  () => form.value.enable_project_questions,
  () => form.value.enable_scenario_questions
], () => {
  calculateTotalRounds()
}, { deep: true })
</script>

<template>
  <div class="home-container">
    <header class="home-header">
      <div class="header-left">
        <h1 class="platform-name">AI面试平台</h1>
      </div>
      
      <nav class="header-menu">
        <button 
          v-for="item in menuItems"
          :key="item.id"
          :class="['menu-item', { active: activeMenu === item.id }]"
          @click="handleMenuClick(item.id)"
        >
          {{ item.label }}
        </button>
      </nav>
      
      <div class="header-right">
        <span class="username">{{ user.username }}</span>
        <button class="logout-btn" @click="handleLogout">退出</button>
      </div>
    </header>
    
    <main class="main-content">
      <div v-if="activeMenu === 'home'" class="content-area">
        <h2>欢迎来到AI面试平台</h2>
        <p>请选择上方菜单开始您的面试之旅</p>
        <button class="create-interview-btn" @click="handleCreateInterview">
          创建新面试
        </button>
      </div>
      
      <div v-if="activeMenu === 'interview'" class="content-area">
        <h2>面试功能</h2>
        <p>面试功能正在开发中...</p>
      </div>
      
      <div v-if="activeMenu === 'history'" class="content-area">
        <h2>历史记录</h2>
        <p>历史记录功能正在开发中...</p>
      </div>
      
      <div v-if="activeMenu === 'profile'" class="content-area">
        <h2>个人中心</h2>
        <p>个人中心功能正在开发中...</p>
      </div>
    </main>
    
    <div v-if="showCreateModal" class="modal-overlay" @click.self="handleCloseModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2 class="modal-title">创建新面试</h2>
          <button class="modal-close" @click="handleCloseModal">&times;</button>
        </div>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <form @submit.prevent="handleSubmit" class="interview-form">
          <div class="form-group">
            <label for="name">面试名称 <span class="required">*</span></label>
            <input
              type="text"
              id="name"
              v-model="form.name"
              placeholder="请输入面试名称，如：腾讯前端工程师面试"
              maxlength="200"
            />
          </div>

          <div class="form-group">
            <label for="position">选择岗位 <span class="required">*</span></label>
            <select id="position" v-model="form.position" required>
              <option value="">请选择岗位</option>
              <option
                v-for="position in positions"
                :key="position.id"
                :value="position.id"
              >
                {{ position.name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>题目类型</label>
            <div class="checkbox-group">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="form.enable_technical_questions"
                />
                <span>技术知识题</span>
              </label>
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="form.enable_project_questions"
                />
                <span>项目经历题</span>
              </label>
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="form.enable_scenario_questions"
                />
                <span>场景题</span>
              </label>
            </div>
          </div>

          <div class="form-group">
            <label for="difficulty">难度配置</label>
            <select id="difficulty" v-model="form.difficulty_config">
              <option value="">请选择难度</option>
              <option
                v-for="config in difficultyConfigs"
                :key="config.id"
                :value="config.id"
              >
                {{ config.difficulty_name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label for="mode">交互模式</label>
            <select id="mode" v-model="form.mode">
              <option value="text">文本模式</option>
              <option value="voice">语音模式</option>
              <option value="mixed">混合模式</option>
            </select>
          </div>

          <div class="form-group">
            <label for="total_rounds">总轮次</label>
            <input
              type="number"
              id="total_rounds"
              v-model.number="form.total_rounds"
              min="0"
              placeholder="自动计算"
              readonly
            />
            <small class="form-hint">根据选择的题型和难度自动计算</small>
          </div>

          <div class="form-group">
            <label for="notes">备注</label>
            <textarea
              id="notes"
              v-model="form.notes"
              placeholder="请输入备注信息（可选）"
              rows="3"
            ></textarea>
          </div>

          <div class="form-actions">
            <button
              type="button"
              class="btn btn-cancel"
              @click="handleCloseModal"
              :disabled="loading"
            >
              取消
            </button>
            <button
              type="submit"
              class="btn btn-submit"
              :disabled="loading"
            >
              {{ loading ? '创建中...' : '创建面试' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  min-height: 100vh;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
}

.home-header {
  background: white;
  padding: 0 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  flex-shrink: 0;
}

.platform-name {
  color: #667eea;
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  white-space: nowrap;
}

.header-menu {
  display: flex;
  gap: 0.5rem;
  flex: 1;
  justify-content: center;
  max-width: 600px;
  margin: 0 2rem;
}

.menu-item {
  padding: 0.5rem 1.5rem;
  background: transparent;
  color: #666;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.menu-item:hover {
  background: #f0f0f0;
  color: #667eea;
}

.menu-item.active {
  background: #667eea;
  color: white;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-shrink: 0;
}

.username {
  font-size: 0.9rem;
  color: #666;
  white-space: nowrap;
}

.logout-btn {
  padding: 0.5rem 1rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.logout-btn:hover {
  background: #c0392b;
}

.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 100%;
  box-sizing: border-box;
}

.content-area {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 400px;
}

.content-area h2 {
  color: #333;
  margin-bottom: 1rem;
  font-size: 1.8rem;
}

.content-area p {
  color: #666;
  font-size: 1rem;
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
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-title {
  color: #333;
  font-size: 1.4rem;
  font-weight: 600;
  margin: 0;
}

.modal-close {
  background: transparent;
  border: none;
  font-size: 2rem;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: color 0.3s ease;
}

.modal-close:hover {
  color: #333;
}

.interview-form {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.error-message {
  background: #fee;
  color: #e74c3c;
  padding: 0.75rem;
  border-radius: 4px;
  margin: 0 1.5rem 1rem;
  text-align: center;
  font-size: 0.9rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-group label {
  color: #333;
  font-weight: 500;
  font-size: 0.9rem;
}

.required {
  color: #e74c3c;
  margin-left: 0.25rem;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select,
.form-group textarea {
  padding: 0.6rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 0.95rem;
  transition: all 0.3s ease;
  font-family: inherit;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.form-group textarea {
  resize: vertical;
  min-height: 60px;
}

.form-hint {
  color: #999;
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: normal;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.checkbox-label span {
  color: #666;
  font-size: 0.9rem;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.btn {
  flex: 1;
  padding: 0.6rem;
  border: none;
  border-radius: 4px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background: #f5f5f5;
  color: #666;
}

.btn-cancel:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-submit {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
}

@media (max-width: 768px) {
  .home-header {
    flex-direction: column;
    height: auto;
    padding: 1rem;
    gap: 1rem;
  }
  
  .header-menu {
    order: 3;
    max-width: 100%;
    margin: 0;
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .menu-item {
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
  }
  
  .header-right {
    order: 2;
  }
  
  .main-content {
    padding: 1rem;
  }
  
  .content-area {
    padding: 1.5rem;
  }
  
  .modal-content {
    max-height: 95vh;
  }
  
  .interview-form {
    padding: 1rem;
  }
}
</style>
