<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const API_BASE_URL = 'http://localhost:8000'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

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
const success = ref('')

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
    
    if (response.ok) {
      const data = await response.json()
      positions.value = data.data || []
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

const handleSubmit = async () => {
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
  success.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/interviews/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(form.value)
    })

    const data = await response.json()

    if (data.code === 201 || data.code === 200) {
      success.value = '创建成功'
      setTimeout(() => {
        emit('close')
        resetForm()
      }, 1500)
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
  emit('close')
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
  success.value = ''
}

watch([
  () => form.value.difficulty_config,
  () => form.value.enable_technical_questions,
  () => form.value.enable_project_questions,
  () => form.value.enable_scenario_questions
], () => {
  calculateTotalRounds()
}, { deep: true })

watch(() => props.show, (newVal) => {
  if (newVal) {
    fetchPositions()
    fetchDifficultyConfigs()
  }
})
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="handleCancel">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">创建新面试</h2>
        <button class="modal-close" @click="handleCancel">&times;</button>
      </div>
      
      <div v-if="success" class="success-message">
        {{ success }}
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

.error-message {
  background: #fee;
  color: #e74c3c;
  padding: 0.75rem;
  border-radius: 4px;
  margin: 0 1.5rem 1rem;
  text-align: center;
  font-size: 0.9rem;
}

.success-message {
  background: #d4edda;
  color: #155724;
  padding: 0.75rem;
  border-radius: 4px;
  margin: 0 1.5rem 1rem;
  text-align: center;
  font-size: 0.9rem;
}

.interview-form {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

.form-hint {
  color: #999;
  font-size: 0.8rem;
  margin-top: 0.25rem;
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
  .modal-content {
    max-height: 95vh;
  }
  
  .interview-form {
    padding: 1rem;
  }
}
</style>
