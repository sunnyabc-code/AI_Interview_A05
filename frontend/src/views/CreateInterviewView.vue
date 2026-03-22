<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const API_BASE_URL = 'http://localhost:8000'

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

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  }
}

const fetchPositions = async () => {
  try {
    const token = localStorage.getItem('access_token')
    console.log('Token:', token ? 'exists' : 'not found')
    
    const response = await fetch(`${API_BASE_URL}/api/positions/`, {
      headers: getAuthHeaders()
    })
    
    console.log('Response status:', response.status)
    
    if (response.ok) {
      const data = await response.json()
      positions.value = data.data || []
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
    } else {
      console.error('获取难度配置失败')
    }
  } catch (err) {
    console.error('获取难度配置错误:', err)
  }
}

const handleSubmit = async () => {
  if (!form.value.name) {
    error.value = '请输入面试名称'
    return
  }
  
  if (!form.value.position) {
    error.value = '请选择岗位'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/api/interviews/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(form.value)
    })

    const data = await response.json()

    if (data.code === 201 || data.code === 200) {
      router.push('/home')
    } else {
      error.value = data.message || '创建失败'
    }
  } catch (err) {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  router.push('/home')
}

onMounted(() => {
  const token = localStorage.getItem('access_token')
  if (!token) {
    router.push('/auth')
    return
  }
  fetchPositions()
  fetchDifficultyConfigs()
})
</script>

<template>
  <div class="create-interview-container">
    <div class="create-interview-card">
      <h2 class="page-title">创建新面试</h2>
      
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
            placeholder="0表示自动计算"
          />
        </div>

        <div class="form-group">
          <label for="notes">备注</label>
          <textarea
            id="notes"
            v-model="form.notes"
            placeholder="请输入备注信息（可选）"
            rows="4"
          ></textarea>
        </div>

        <div class="form-actions">
          <button
            type="button"
            class="btn btn-cancel"
            @click="handleCancel"
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
</template>

<style scoped>
.create-interview-container {
  min-height: calc(100vh - 60px);
  background: #f5f5f5;
  padding: 2rem;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.create-interview-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 2rem;
  width: 100%;
  max-width: 600px;
}

.page-title {
  color: #333;
  font-size: 1.8rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  text-align: center;
}

.error-message {
  background: #fee;
  color: #e74c3c;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  text-align: center;
  font-size: 0.9rem;
}

.interview-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  color: #333;
  font-weight: 500;
  font-size: 0.95rem;
}

.required {
  color: #e74c3c;
  margin-left: 0.25rem;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select,
.form-group textarea {
  padding: 0.75rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;
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
  min-height: 80px;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: normal;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-label span {
  color: #666;
  font-size: 0.95rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.btn {
  flex: 1;
  padding: 0.75rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
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
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

@media (max-width: 768px) {
  .create-interview-container {
    padding: 1rem;
  }
  
  .create-interview-card {
    padding: 1.5rem;
  }
  
  .form-actions {
    flex-direction: column;
  }
}
</style>
