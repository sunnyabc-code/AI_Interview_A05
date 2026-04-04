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

interface PositionOption {
  id: number
  name: string
}

interface UserProject {
  project_id: number
  position: number
  position_name: string
  project_name: string
  project_role: string
  project_description: string
  project_result: string
  created_at: string
  updated_at: string
}

const positions = ref<PositionOption[]>([])
const projects = ref<UserProject[]>([])
const showProjectForm = ref(false)
const projectSubmitting = ref(false)
const projectError = ref('')
const editingProjectId = ref<number | null>(null)

const projectForm = ref({
  position: 0,
  project_name: '',
  project_role: '',
  project_description: '',
  project_result: '',
})

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

const fetchPositions = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/positions/`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      return
    }
    const payload = await response.json()
    positions.value = payload.data || []
  } catch (err) {
    console.error('获取岗位列表失败:', err)
  }
}

const fetchProjects = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/user-projects/`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      return
    }
    const payload = await response.json()
    projects.value = payload.data || []
  } catch (err) {
    console.error('获取个人项目失败:', err)
  }
}

const resetProjectForm = () => {
  projectForm.value = {
    position: positions.value[0]?.id || 0,
    project_name: '',
    project_role: '',
    project_description: '',
    project_result: '',
  }
  editingProjectId.value = null
  projectError.value = ''
}

const openCreateProjectForm = () => {
  resetProjectForm()
  showProjectForm.value = true
}

const openEditProjectForm = (project: UserProject) => {
  projectForm.value = {
    position: project.position,
    project_name: project.project_name,
    project_role: project.project_role,
    project_description: project.project_description,
    project_result: project.project_result,
  }
  editingProjectId.value = project.project_id
  projectError.value = ''
  showProjectForm.value = true
}

const closeProjectForm = () => {
  showProjectForm.value = false
  resetProjectForm()
}

const submitProject = async () => {
  if (!projectForm.value.position || !projectForm.value.project_name.trim() || !projectForm.value.project_role.trim()) {
    projectError.value = '请至少填写岗位、项目名称、项目角色'
    return
  }

  projectSubmitting.value = true
  projectError.value = ''

  try {
    const isEdit = editingProjectId.value !== null
    const endpoint = isEdit
      ? `${API_BASE_URL}/api/user-projects/${editingProjectId.value}/`
      : `${API_BASE_URL}/api/user-projects/`

    const response = await fetch(endpoint, {
      method: isEdit ? 'PATCH' : 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(projectForm.value),
    })

    const payload = await response.json()
    if (!response.ok || payload.code >= 400) {
      projectError.value = payload?.message || '保存项目失败'
      return
    }

    await fetchProjects()
    closeProjectForm()
  } catch (err) {
    console.error('保存项目失败:', err)
    projectError.value = '保存项目失败，请稍后重试'
  } finally {
    projectSubmitting.value = false
  }
}

const deleteProject = async (project: UserProject) => {
  const ok = window.confirm(`确认删除项目「${project.project_name}」吗？`)
  if (!ok) {
    return
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/user-projects/${project.project_id}/`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      return
    }
    await fetchProjects()
  } catch (err) {
    console.error('删除项目失败:', err)
  }
}

onMounted(() => {
  const token = localStorage.getItem('access_token')
  if (!token) {
    router.push('/auth')
    return
  }
  
  fetchUserInfo()
  fetchPositions()
  fetchProjects()
})
</script>

<template>
  <div class="profile-container">
    <div class="profile-card">
      <div class="profile-header">
        <div>
          <p class="eyebrow">Profile</p>
          <h2 class="page-title">个人中心</h2>
        </div>
        <button class="edit-btn" @click="handleEdit">编辑资料</button>
      </div>

      <div class="profile-view">
        <div class="avatar-section">
          <div class="avatar-wrapper">
            <img v-if="user.avatar" :src="user.avatar" alt="头像" class="avatar" />
            <div v-else class="avatar-placeholder">
              {{ user.username?.charAt(0)?.toUpperCase() || 'U' }}
            </div>
          </div>
          <div class="identity-block">
            <h3>{{ user.username || '未设置用户名' }}</h3>
            <p>{{ user.email || '未设置邮箱' }}</p>
          </div>
        </div>

        <div class="quick-metrics">
          <article class="metric-card">
            <p>面试次数</p>
            <strong>{{ user.interview_count || 0 }}</strong>
          </article>
          <article class="metric-card">
            <p>目标岗位数量</p>
            <strong>{{ (user.target_positions && user.target_positions.length) || 0 }}</strong>
          </article>
          <article class="metric-card">
            <p>账号状态</p>
            <strong>已激活</strong>
          </article>
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

        <section class="project-section">
          <div class="project-header">
            <div>
              <h3>个人项目</h3>
              <p>你可以维护与目标岗位相关的项目经历，用于后续面试和评估参考。</p>
            </div>
            <button class="project-add-btn" @click="openCreateProjectForm">新增项目</button>
          </div>

          <div v-if="projects.length > 0" class="project-list">
            <article v-for="project in projects" :key="project.project_id" class="project-card">
              <div class="project-card-header">
                <div>
                  <h4>{{ project.project_name }}</h4>
                  <p>{{ project.position_name }} · {{ project.project_role }}</p>
                </div>
                <div class="project-actions">
                  <button class="project-action-btn" @click="openEditProjectForm(project)">编辑</button>
                  <button class="project-action-btn danger" @click="deleteProject(project)">删除</button>
                </div>
              </div>
              <div class="project-block">
                <label>项目描述</label>
                <p>{{ project.project_description || '未填写' }}</p>
              </div>
              <div class="project-block">
                <label>项目成果</label>
                <p>{{ project.project_result || '未填写' }}</p>
              </div>
            </article>
          </div>
          <div v-else class="project-empty">暂无项目，点击“新增项目”开始维护。</div>
        </section>
      </div>

      <div class="logout-section">
        <button class="logout-btn" @click="handleLogout">
          退出登录
        </button>
      </div>
    </div>

    <EditProfileModal :show="showEditModal" @close="handleModalClose" @save="handleModalSave" />

    <div v-if="showProjectForm" class="project-modal-mask" @click.self="closeProjectForm">
      <div class="project-modal">
        <div class="project-modal-header">
          <h3>{{ editingProjectId ? '编辑项目' : '新增项目' }}</h3>
          <button class="project-close-btn" @click="closeProjectForm">关闭</button>
        </div>

        <div class="project-form-grid">
          <div class="field">
            <label>关联岗位</label>
            <select v-model.number="projectForm.position">
              <option :value="0" disabled>请选择岗位</option>
              <option v-for="position in positions" :key="position.id" :value="position.id">
                {{ position.name }}
              </option>
            </select>
          </div>

          <div class="field">
            <label>项目名称</label>
            <input v-model="projectForm.project_name" type="text" placeholder="请输入项目名称" />
          </div>

          <div class="field">
            <label>项目角色</label>
            <input v-model="projectForm.project_role" type="text" placeholder="例如：后端开发 / 项目负责人" />
          </div>

          <div class="field field-full">
            <label>项目描述</label>
            <textarea v-model="projectForm.project_description" rows="4" placeholder="请描述项目背景、技术栈和你的核心工作" />
          </div>

          <div class="field field-full">
            <label>项目成果</label>
            <textarea v-model="projectForm.project_result" rows="4" placeholder="请描述可量化成果、性能提升或业务收益" />
          </div>
        </div>

        <p v-if="projectError" class="project-error">{{ projectError }}</p>

        <div class="project-modal-actions">
          <button class="secondary-btn" @click="closeProjectForm">取消</button>
          <button class="primary-btn" :disabled="projectSubmitting" @click="submitProject">
            {{ projectSubmitting ? '保存中...' : '保存项目' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-container {
  min-height: calc(100vh - 60px);
  background:
    radial-gradient(circle at 15% 12%, rgba(191, 219, 254, 0.45), transparent 35%),
    radial-gradient(circle at 84% 86%, rgba(252, 165, 165, 0.24), transparent 42%),
    linear-gradient(135deg, #f8fafc 0%, #eef2ff 45%, #fff7ed 100%);
  padding: 2rem;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.profile-card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #dbeafe;
  border-radius: 16px;
  box-shadow: 0 24px 40px rgba(15, 23, 42, 0.12);
  padding: 2rem;
  width: 100%;
  max-width: 740px;
}

.profile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.eyebrow {
  margin: 0;
  color: #64748b;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.page-title {
  color: #0f172a;
  font-size: 1.9rem;
  font-weight: 700;
  margin: 0;
}

.edit-btn {
  padding: 0.55rem 1rem;
  background: linear-gradient(120deg, #3b82f6, #1d4ed8);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.edit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(29, 78, 216, 0.28);
}

.profile-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.avatar-section {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  gap: 0.7rem;
}

.avatar-wrapper {
  width: 126px;
  height: 126px;
  border-radius: 50%;
  overflow: hidden;
  border: 3px solid #ffffff;
  box-shadow: 0 10px 24px rgba(59, 130, 246, 0.25);
}

.avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #3b82f6 0%, #0ea5e9 100%);
  color: white;
  font-size: 3rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.identity-block {
  text-align: center;
}

.identity-block h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1.2rem;
}

.identity-block p {
  margin: 0.25rem 0 0;
  color: #64748b;
}

.quick-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
}

.metric-card {
  border: 1px solid #dbeafe;
  border-radius: 12px;
  padding: 0.7rem 0.75rem;
  background: linear-gradient(135deg, #eff6ff, #ffffff);
}

.metric-card p {
  margin: 0;
  color: #64748b;
  font-size: 0.8rem;
}

.metric-card strong {
  margin-top: 0.3rem;
  display: inline-block;
  font-size: 1.25rem;
  color: #0f172a;
}

.info-section {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.7rem 0.8rem;
  background: #ffffff;
}

.info-item label {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 600;
}

.info-value {
  color: #1e293b;
  font-size: 1rem;
  font-weight: 500;
}

.target-positions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.position-tag {
  background: #eef2ff;
  color: #3730a3;
  padding: 0.25rem 0.7rem;
  border-radius: 999px;
  font-size: 0.85rem;
  border: 1px solid #c7d2fe;
}

.position-tag:hover {
  background: #e0e7ff;
}

.logout-section {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.project-section {
  margin-top: 0.4rem;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  background: linear-gradient(145deg, #ffffff, #f8fafc);
  padding: 0.95rem;
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.8rem;
  margin-bottom: 0.8rem;
}

.project-header h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1.1rem;
}

.project-header p {
  margin: 0.3rem 0 0;
  color: #64748b;
  font-size: 0.88rem;
}

.project-add-btn {
  border: none;
  border-radius: 10px;
  padding: 0.45rem 0.8rem;
  background: linear-gradient(120deg, #16a34a, #22c55e);
  color: #ffffff;
  cursor: pointer;
}

.project-list {
  display: grid;
  gap: 0.65rem;
}

.project-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 0.75rem;
}

.project-card-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 0.7rem;
}

.project-card-header h4 {
  margin: 0;
  color: #0f172a;
}

.project-card-header p {
  margin: 0.26rem 0 0;
  color: #64748b;
  font-size: 0.85rem;
}

.project-actions {
  display: flex;
  gap: 0.4rem;
}

.project-action-btn {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 8px;
  padding: 0.26rem 0.55rem;
  cursor: pointer;
}

.project-action-btn.danger {
  border-color: #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.project-block {
  margin-top: 0.6rem;
}

.project-block label {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 600;
}

.project-block p {
  margin: 0.26rem 0 0;
  color: #1e293b;
  white-space: pre-wrap;
}

.project-empty {
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  padding: 0.72rem;
  color: #64748b;
  text-align: center;
}

.project-modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  z-index: 1300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.project-modal {
  width: min(760px, 96vw);
  max-height: 88vh;
  overflow: auto;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #dbeafe;
  box-shadow: 0 24px 40px rgba(15, 23, 42, 0.24);
  padding: 1rem;
}

.project-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.8rem;
}

.project-modal-header h3 {
  margin: 0;
  color: #0f172a;
}

.project-close-btn {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  padding: 0.32rem 0.58rem;
  cursor: pointer;
}

.project-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.7rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.32rem;
}

.field-full {
  grid-column: 1 / -1;
}

.field label {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 600;
}

.field input,
.field select,
.field textarea {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.52rem 0.6rem;
  font: inherit;
  color: #1e293b;
  background: #ffffff;
}

.field textarea {
  resize: vertical;
}

.project-error {
  color: #b91c1c;
  margin: 0.7rem 0 0;
}

.project-modal-actions {
  margin-top: 0.9rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.55rem;
}

.secondary-btn,
.primary-btn {
  border: none;
  border-radius: 9px;
  padding: 0.45rem 0.8rem;
  cursor: pointer;
}

.secondary-btn {
  background: #e2e8f0;
  color: #334155;
}

.primary-btn {
  background: linear-gradient(120deg, #3b82f6, #1d4ed8);
  color: #ffffff;
}

.primary-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.logout-btn {
  width: 100%;
  padding: 0.78rem;
  background: linear-gradient(120deg, #ef4444, #dc2626);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.logout-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(220, 38, 38, 0.28);
}

@media (max-width: 768px) {
  .profile-container {
    padding: 1rem;
  }
  
  .profile-card {
    padding: 1.5rem;
  }

  .quick-metrics {
    grid-template-columns: 1fr;
  }

  .info-section {
    grid-template-columns: 1fr;
  }

  .project-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .project-form-grid {
    grid-template-columns: 1fr;
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
