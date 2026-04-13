<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [user: any]
}>()

const API_BASE_URL = 'http://localhost:8000'

const isEditing = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref('')

const editForm = ref({
  username: '',
  email: '',
  phone: '',
  avatar: '',
  target_positions: [] as number[]
})

const positions = ref<any[]>([])

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

const initForm = (userInfo: any) => {
  const targetPositionIds = userInfo.target_positions ? 
    userInfo.target_positions.map((p: any) => p.id) : []
  
  editForm.value = {
    username: userInfo.username || '',
    email: userInfo.email || '',
    phone: userInfo.phone || '',
    avatar: userInfo.avatar || '',
    target_positions: targetPositionIds
  }
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    fetchPositions()
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    initForm(user)
  }
})

const handleSave = async () => {
  loading.value = true
  error.value = ''
  success.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/api/users/profile/update/`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(editForm.value)
    })

    const data = await response.json()

    if (data.code === 200) {
      success.value = '更新成功'
      setTimeout(() => {
        emit('save', data.data)
        emit('close')
      }, 1500)
    } else {
      error.value = data.message || '更新失败'
    }
  } catch (err) {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  emit('close')
}
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="handleCancel">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">编辑个人信息</h2>
        <button class="modal-close" @click="handleCancel">&times;</button>
      </div>

      <div v-if="success" class="success-message">
        {{ success }}
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <form @submit.prevent="handleSave" class="edit-form">
        <div class="form-group">
          <label for="username">用户名</label>
          <input
            type="text"
            id="username"
            v-model="editForm.username"
            maxlength="150"
          />
        </div>

        <div class="form-group">
          <label for="email">邮箱</label>
          <input
            type="email"
            id="email"
            v-model="editForm.email"
            placeholder="请输入邮箱"
          />
        </div>

        <div class="form-group">
          <label for="phone">手机号</label>
          <input
            type="text"
            id="phone"
            v-model="editForm.phone"
            maxlength="20"
            placeholder="请输入手机号"
          />
        </div>

        <div class="form-group">
          <label>目标岗位</label>
          <div class="checkbox-group">
            <label
              v-for="position in positions"
              :key="position.id"
              class="checkbox-label"
            >
              <input
                type="checkbox"
                :value="position.id"
                v-model="editForm.target_positions"
              />
              <span>{{ position.name }}</span>
            </label>
          </div>
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
            class="btn btn-save"
            :disabled="loading"
          >
            {{ loading ? '保存中...' : '保存' }}
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
  background: rgba(31, 41, 38, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(31, 41, 38, 0.15);
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
  border-bottom: 1px dashed #dde5e1;
}

.modal-title {
  color: #1f2926;
  font-size: 1.3rem;
  font-weight: 600;
  margin: 0;
}

.modal-close {
  background: transparent;
  border: none;
  font-size: 2rem;
  color: #66756f;
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
  color: #2f5d56;
}

.success-message {
  background: #f0fdf4;
  color: #166534;
  padding: 0.75rem;
  border-radius: 8px;
  margin: 0 1.5rem 1rem;
  text-align: center;
  font-size: 0.9rem;
}

.error-message {
  background: #fef2f2;
  color: #b91c1c;
  padding: 0.75rem;
  border-radius: 8px;
  margin: 0 1.5rem 1rem;
  text-align: center;
  font-size: 0.9rem;
}

.edit-form {
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
  color: #66756f;
  font-weight: 600;
  font-size: 0.85rem;
}

.form-group input[type="text"],
.form-group input[type="email"] {
  padding: 0.75rem 1rem;
  border: 1px solid #dde5e1;
  border-radius: 8px;
  font-size: 0.95rem;
  color: #1f2926;
  background: #f9fbfaf8;
  transition: all 0.2s ease;
  font-family: inherit;
}

.form-group input:focus {
  outline: none;
  border-color: #2f5d56;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(47, 93, 86, 0.1);
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #dde5e1;
  border-radius: 8px;
  padding: 0.75rem;
  background: #f9fbfaf8;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  padding: 0.4rem;
  border-radius: 4px;
  transition: background 0.2s ease;
}

.checkbox-label:hover {
  background: #ffffff;
}

.checkbox-label input[type="checkbox"] {
  width: 1.1rem;
  height: 1.1rem;
  border: 1px solid #dde5e1;
  border-radius: 3px;
  accent-color: #2f5d56;
}

.checkbox-label span {
  font-size: 0.95rem;
  color: #1f2926;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1.5rem;
  border-top: 1px dashed #dde5e1;
}

.btn {
  padding: 0.7rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-cancel {
  background: transparent;
  color: #66756f;
  border: 1px solid #dde5e1;
}

.btn-cancel:hover:not(:disabled) {
  background: #f9fbfaf8;
  color: #1f2926;
  border-color: #66756f;
}

.btn-save {
  background: #2f5d56;
  color: white;
}

.btn-save:hover:not(:disabled) {
  background: #3f655f;
  box-shadow: 0 4px 12px rgba(47, 93, 86, 0.2);
}

@media (max-width: 768px) {
  .modal-content {
    max-height: 95vh;
  }
  
  .edit-form {
    padding: 1rem;
  }
}
</style>
