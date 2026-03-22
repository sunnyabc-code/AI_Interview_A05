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
          <label for="avatar">头像URL</label>
          <input
            type="text"
            id="avatar"
            v-model="editForm.avatar"
            placeholder="请输入头像URL"
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

.success-message {
  background: #d4edda;
  color: #155724;
  padding: 0.75rem;
  border-radius: 4px;
  margin: 0 1.5rem 1rem;
  text-align: center;
  font-size: 0.9rem;
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
  color: #333;
  font-weight: 500;
  font-size: 0.9rem;
}

.form-group input[type="text"],
.form-group input[type="email"] {
  padding: 0.6rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 0.95rem;
  transition: all 0.3s ease;
  font-family: inherit;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
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

.btn-save {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-save:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
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
