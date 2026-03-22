<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import EditProfileModal from '../components/EditProfileModal.vue'

const router = useRouter()

const API_BASE_URL = 'http://localhost:8000'

const user = ref({
  id: 0,
  username: '',
  email: '',
  phone: '',
  avatar: '',
  target_positions: [] as any[],
  interview_count: 0,
  created_at: ''
})

const showEditModal = ref(false)

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  }
}

const fetchUserInfo = async () => {
  try {
    const token = localStorage.getItem('access_token')
    console.log('Token:', token)
    
    if (!token) {
      router.push('/auth')
      return
    }
    
    const response = await fetch(`${API_BASE_URL}/api/users/profile/`, {
      headers: getAuthHeaders()
    })
    
    console.log('Response status:', response.status)
    
    if (response.ok) {
      const data = await response.json()
      user.value = data.data || user.value
    } else if (response.status === 401) {
      console.error('Token expired or invalid')
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      router.push('/auth')
    } else {
      console.error('获取用户信息失败')
    }
  } catch (err) {
    console.error('获取用户信息错误:', err)
  }
}

const handleEdit = () => {
  showEditModal.value = true
}

const handleModalClose = () => {
  showEditModal.value = false
}

const handleModalSave = (updatedUser: any) => {
  user.value = updatedUser
  localStorage.setItem('user', JSON.stringify(updatedUser))
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
    return
  }
  
  fetchUserInfo()
})
</script>

<template>
  <div class="profile-container">
    <div class="profile-card">
      <div class="profile-header">
        <h2 class="page-title">个人中心</h2>
        <button class="edit-btn" @click="handleEdit">
          编辑
        </button>
      </div>

      <div class="profile-view">
        <div class="avatar-section">
          <div class="avatar-wrapper">
            <img v-if="user.avatar" :src="user.avatar" alt="头像" class="avatar" />
            <div v-else class="avatar-placeholder">
              {{ user.username?.charAt(0)?.toUpperCase() || 'U' }}
            </div>
          </div>
        </div>

        <div class="info-section">
          <div class="info-item">
            <label>用户名</label>
            <span class="info-value">{{ user.username || '未设置' }}</span>
          </div>

          <div class="info-item">
            <label>邮箱</label>
            <span class="info-value">{{ user.email || '未设置' }}</span>
          </div>

          <div class="info-item">
            <label>手机号</label>
            <span class="info-value">{{ user.phone || '未设置' }}</span>
          </div>

          <div class="info-item">
            <label>面试次数</label>
            <span class="info-value">{{ user.interview_count || 0 }}</span>
          </div>

          <div class="info-item">
            <label>注册时间</label>
            <span class="info-value">{{ user.created_at || '-' }}</span>
          </div>

          <div class="info-item">
            <label>目标岗位</label>
            <div v-if="user.target_positions && user.target_positions.length > 0" class="target-positions">
              <span v-for="(position, index) in user.target_positions" :key="position.id" class="position-tag">
                {{ position.name }}
              </span>
            </div>
            <span v-else class="info-value">未选择目标岗位</span>
          </div>
        </div>
      </div>

      <div class="logout-section">
        <button class="logout-btn" @click="handleLogout">
          退出登录
        </button>
      </div>
    </div>

    <EditProfileModal :show="showEditModal" @close="handleModalClose" @save="handleModalSave" />
  </div>
</template>

<style scoped>
.profile-container {
  min-height: calc(100vh - 60px);
  background: #f5f5f5;
  padding: 2rem;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.profile-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 2rem;
  width: 100%;
  max-width: 600px;
}

.profile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e0e0e0;
}

.page-title {
  color: #333;
  font-size: 1.8rem;
  font-weight: 600;
  margin: 0;
}

.edit-btn {
  padding: 0.5rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.edit-btn:hover {
  background: #5568d3;
}

.profile-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.avatar-section {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;
}

.avatar-wrapper {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 3rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.info-item label {
  color: #666;
  font-size: 0.9rem;
  font-weight: 500;
}

.info-value {
  color: #333;
  font-size: 1rem;
  font-weight: 400;
}

.target-positions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.3rem;
}

.position-tag {
  background: #f0f0f0;
  color: #666;
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
  font-size: 0.85rem;
  border: 1px solid #e0e0e0;
}

.position-tag:hover {
  background: #e0e0e0;
}

.logout-section {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}

.logout-btn {
  width: 100%;
  padding: 0.75rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.logout-btn:hover {
  background: #c0392b;
}

@media (max-width: 768px) {
  .profile-container {
    padding: 1rem;
  }
  
  .profile-card {
    padding: 1.5rem;
  }
  
  .avatar-wrapper {
    width: 100px;
    height: 100px;
  }
  
  .avatar-placeholder {
    font-size: 2.5rem;
  }
}
</style>
