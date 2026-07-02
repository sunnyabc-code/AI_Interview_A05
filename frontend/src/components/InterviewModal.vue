<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { API_BASE_URL } from '@/utils/api'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'close', createdInterview?: any): void
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
const userProjects = ref<{ position: number }[]>([])
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
    const response = await fetch(`${API_BASE_URL}/positions/`, {
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
    const response = await fetch(`${API_BASE_URL}/evaluations/difficulty-configs/`, {
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

const fetchUserProjects = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/user-projects/`, {
      headers: getAuthHeaders()
    })
    if (response.ok) {
      const data = await response.json()
      userProjects.value = data.data || []
    }
  } catch (err) {
    console.error('获取项目经历错误:', err)
  }
}

const hasProjectForSelectedPosition = computed(() => {
  if (form.value.position === null || form.value.position === undefined) return false
  return userProjects.value.some((p) => p.position === form.value.position)
})

const projectPrerequisiteHint = computed(() => {
  if (!form.value.enable_project_questions) return ''
  if (form.value.position === null || form.value.position === undefined) {
    return '已勾选项目经历题：请选择岗位，并确保已在「个人中心」为该岗位填写项目经历。'
  }
  if (!hasProjectForSelectedPosition.value) {
    return '已勾选项目经历题：请先在「个人中心 → 项目经历」为该岗位添加至少一条记录，否则无法创建面试。'
  }
  return ''
})

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

  if (form.value.enable_project_questions && !hasProjectForSelectedPosition.value) {
    error.value =
      '已勾选项目经历题，请先在个人中心为所选岗位填写至少一条项目经历。'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/v1/interviews/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(form.value)
    })

    const data = await response.json()

    if (data.code === 201 || data.code === 200) {
      success.value = '创建成功'
      setTimeout(() => {
        emit('close', data.data || null)
        resetForm()
      }, 1500)
    } else {
      const errs = data.errors as Record<string, string[] | string> | undefined
      if (errs && typeof errs === 'object') {
        const firstKey = Object.keys(errs)[0]
        const v = firstKey ? errs[firstKey] : null
        error.value = Array.isArray(v) ? v[0] : typeof v === 'string' ? v : data.message || '创建失败'
      } else {
        error.value = data.message || '创建失败'
      }
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
    fetchUserProjects()
  }
})
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="handleCancel">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="5" width="16" height="14" rx="3" stroke="currentColor" stroke-width="1.8"/>
              <path d="M12 9V15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M9 12H15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </span>
          <span>创建新面试</span>
        </h2>
        <button class="modal-close" @click="handleCancel" aria-label="关闭">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M7 7L17 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
              <path d="M17 7L7 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
            </svg>
          </span>
        </button>
      </div>
      
      <div v-if="success" class="success-message">
        <span class="icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/>
            <path d="M8 12.5L10.7 15.2L16 9.9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        {{ success }}
      </div>

      <div v-if="error" class="error-message">
        <span class="icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/>
            <path d="M12 8V13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            <circle cx="12" cy="16.5" r="1" fill="currentColor"/>
          </svg>
        </span>
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
              <span class="check-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6.5 12.5L10 16L17.5 8.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span>技术知识题</span>
            </label>
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="form.enable_project_questions"
              />
              <span class="check-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6.5 12.5L10 16L17.5 8.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span>项目经历题</span>
            </label>
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="form.enable_scenario_questions"
              />
              <span class="check-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6.5 12.5L10 16L17.5 8.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span>场景题</span>
            </label>
          </div>
          <p v-if="projectPrerequisiteHint" class="form-inline-warn">{{ projectPrerequisiteHint }}</p>
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
            <!-- <option value="mixed">混合模式</option> -->
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
            <span class="icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M7 7L17 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
                <path d="M17 7L7 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
              </svg>
            </span>
            取消
          </button>
          <button
            type="submit"
            class="btn btn-submit"
            :disabled="loading"
          >
            <span class="icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 6V18" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
                <path d="M6 12H18" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
              </svg>
            </span>
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
  background: rgba(20, 29, 26, 0.56);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  z-index: 1000;
  padding: clamp(1rem, 4vh, 2rem) 0.95rem;
  overflow-y: auto;
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
  --accent-2: #3f6b63;
  --danger: #ad4b43;

  background: var(--surface);
  border-radius: 18px;
  box-shadow: 0 24px 48px rgba(24, 35, 31, 0.22);
  border: 1px solid var(--line);
  max-width: 640px;
  width: min(640px, calc(100vw - 1.9rem));
  max-height: calc(100vh - 2rem);
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.1rem;
  border-bottom: 1px solid var(--line-soft);
  background: linear-gradient(180deg, #ffffff 0%, #f9fbfa 100%);
}

.modal-title {
  color: var(--text);
  font-size: 1.06rem;
  font-weight: 600;
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.42rem;
}

.modal-close {
  background: #f3f7f5;
  border: 1px solid #dce6e1;
  color: #48635d;
  cursor: pointer;
  padding: 0;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  transition: all 0.24s ease;
}

.modal-close:hover {
  background: #eaf2ef;
}

.error-message {
  background: #fff6f5;
  color: var(--danger);
  padding: 0.78rem 0.88rem;
  border-radius: 12px;
  border: 1px solid #f1d8d4;
  margin: 0.85rem 1.1rem 0.75rem;
  font-size: 0.88rem;
  display: flex;
  align-items: center;
  gap: 0.42rem;
}

.success-message {
  background: #edf6f2;
  color: #2d5f54;
  padding: 0.78rem 0.88rem;
  border-radius: 12px;
  border: 1px solid #d2e5dc;
  margin: 0.85rem 1.1rem 0.75rem;
  font-size: 0.88rem;
  display: flex;
  align-items: center;
  gap: 0.42rem;
}

.interview-form {
  padding: 0.95rem 1.1rem 1.05rem;
  display: flex;
  flex-direction: column;
  gap: 0.74rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.36rem;
  background: var(--surface-soft);
  border: 1px solid var(--line-soft);
  border-radius: 12px;
  padding: 0.7rem;
}

.form-group label {
  color: var(--text);
  font-weight: 500;
  font-size: 0.84rem;
}

.required {
  color: var(--danger);
  margin-left: 0.25rem;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select,
.form-group textarea {
  padding: 0.58rem 0.68rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 0.86rem;
  transition: all 0.24s ease;
  font-family: inherit;
  color: var(--text);
  background: #ffffff;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #7ea79c;
  box-shadow: 0 0 0 3px rgba(84, 141, 122, 0.16);
}

.form-group textarea {
  resize: vertical;
  min-height: 60px;
}

.checkbox-group {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.45rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  font-weight: normal;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.48rem 0.52rem;
  background: #ffffff;
  position: relative;
}

.checkbox-label input[type="checkbox"] {
  width: 15px;
  height: 15px;
  cursor: pointer;
}

.checkbox-label span {
  color: var(--muted);
  font-size: 0.82rem;
}

.checkbox-label input[type="checkbox"] ~ .check-icon {
  opacity: 0;
}

.checkbox-label input[type="checkbox"]:checked ~ .check-icon {
  opacity: 1;
}

.check-icon {
  width: 14px;
  height: 14px;
  color: #3f6b63;
  display: inline-flex;
  flex-shrink: 0;
  transition: opacity 0.18s ease;
}

.check-icon svg {
  width: 100%;
  height: 100%;
}

.form-inline-warn {
  margin: 0.35rem 0 0;
  padding: 0.5rem 0.55rem;
  border-radius: 10px;
  background: #fff8f2;
  border: 1px solid #f0dcc8;
  color: #8a4a1f;
  font-size: 0.78rem;
  line-height: 1.45;
}

.form-hint {
  color: var(--muted);
  font-size: 0.76rem;
  margin-top: 0.25rem;
}

.form-actions {
  display: flex;
  gap: 0.55rem;
  margin-top: 0.36rem;
}

.btn {
  flex: 1;
  min-height: 38px;
  padding: 0.5rem 0.72rem;
  border-radius: 10px;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.36rem;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background: #eef3f1;
  color: #3d5b54;
  border: 1px solid #d7e3dd;
}

.btn-cancel:hover:not(:disabled) {
  background: #e4ede9;
}

.btn-submit {
  background: linear-gradient(135deg, var(--accent-2) 0%, var(--accent) 100%);
  color: white;
  border: none;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(47, 93, 86, 0.24);
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

@media (max-width: 768px) {
  .modal-content {
    max-height: calc(100vh - 1.5rem);
    border-radius: 14px;
  }
  
  .interview-form {
    padding: 0.84rem;
    gap: 0.66rem;
  }

  .modal-header {
    padding: 0.82rem 0.84rem;
  }

  .success-message,
  .error-message {
    margin: 0.75rem 0.84rem 0.62rem;
  }

  .checkbox-group {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}
</style>
