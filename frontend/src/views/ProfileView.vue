<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
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
  created_at: ''
})

const joinedDays = computed(() => {
  if (!user.value.created_at) {
    return 0
  }
  const createdAt = new Date(user.value.created_at)
  if (Number.isNaN(createdAt.getTime())) {
    return 0
  }
  const diffMs = Date.now() - createdAt.getTime()
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  return Math.max(days + 1, 1)
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
const projectExpandedMap = ref<Record<number, boolean>>({})
const showProjectForm = ref(false)
const projectSubmitting = ref(false)
const projectError = ref('')
const editingProjectId = ref<number | null>(null)
const pendingDeleteProject = ref<UserProject | null>(null)

const projectSummary = computed(() => {
  const total = projects.value.length
  const withDescription = projects.value.filter((p) => p.project_description?.trim()).length
  const withResult = projects.value.filter((p) => p.project_result?.trim()).length
  const coveredPositions = new Set(projects.value.map((p) => p.position_name).filter(Boolean)).size
  const latestUpdatedAt = projects.value
    .map((p) => new Date(p.updated_at || p.created_at).getTime())
    .filter((t) => !Number.isNaN(t))
    .sort((a, b) => b - a)[0]

  return {
    total,
    withDescription,
    withResult,
    coveredPositions,
    latestUpdatedLabel: latestUpdatedAt
      ? new Date(latestUpdatedAt).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
      : '暂无',
  }
})

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
    const nextExpandedMap: Record<number, boolean> = {}
    projects.value.forEach((project, index) => {
      nextExpandedMap[project.project_id] = projectExpandedMap.value[project.project_id] ?? index === 0
    })
    projectExpandedMap.value = nextExpandedMap
  } catch (err) {
    console.error('获取个人项目失败:', err)
  }
}

const toggleProjectExpanded = (projectId: number) => {
  projectExpandedMap.value[projectId] = !projectExpandedMap.value[projectId]
}

const isProjectExpanded = (projectId: number) => {
  return !!projectExpandedMap.value[projectId]
}

const formatProjectDate = (dateText: string) => {
  const date = new Date(dateText)
  if (Number.isNaN(date.getTime())) {
    return '未知时间'
  }
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
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

const openDeleteProjectDialog = (project: UserProject) => {
  pendingDeleteProject.value = project
}

const closeDeleteProjectDialog = () => {
  pendingDeleteProject.value = null
}

const confirmDeleteProject = async () => {
  if (!pendingDeleteProject.value) {
    return
  }

  const project = pendingDeleteProject.value

  try {
    const response = await fetch(`${API_BASE_URL}/api/user-projects/${project.project_id}/`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      return
    }
    await fetchProjects()
    closeDeleteProjectDialog()
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
        <div class="identity-section">
          <div class="identity-badge">
            <div class="initial-letter">{{ user.username?.charAt(0)?.toUpperCase() || 'U' }}</div>
          </div>
          <div class="identity-block">
            <h3>{{ user.username || '未设置用户名' }}</h3>
            <p>{{ user.email || '未设置邮箱' }}</p>
          </div>
        </div>

        <div class="quick-metrics">
          <article class="metric-card">
            <p>已加入天数</p>
            <strong>{{ joinedDays }}</strong>
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
            <label>已加入天数</label>
            <span class="info-value">{{ joinedDays }} 天</span>
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

          <div class="project-overview">
            <div class="project-overview-stats">
              <article class="overview-stat-card">
                <p>项目总数</p>
                <strong>{{ projectSummary.total }}</strong>
              </article>
              <article class="overview-stat-card">
                <p>岗位覆盖</p>
                <strong>{{ projectSummary.coveredPositions }}</strong>
              </article>
              <article class="overview-stat-card">
                <p>最近更新</p>
                <strong>{{ projectSummary.latestUpdatedLabel }}</strong>
              </article>
            </div>
          </div>

          <div v-if="projects.length > 0" class="project-list">
            <article v-for="project in projects" :key="project.project_id" class="project-card">
              <div class="project-card-header">
                <div>
                  <h4>{{ project.project_name }}</h4>
                  <div class="project-meta-row">
                    <span class="project-chip">{{ project.position_name || '未关联岗位' }}</span>
                    <span class="project-chip">{{ project.project_role || '未填写角色' }}</span>
                    <span class="project-chip project-chip--date">更新于 {{ formatProjectDate(project.updated_at || project.created_at) }}</span>
                  </div>
                </div>
                <div class="project-actions">
                  <button class="project-action-btn" @click="toggleProjectExpanded(project.project_id)">
                    {{ isProjectExpanded(project.project_id) ? '收起详情' : '展开详情' }}
                  </button>
                  <button class="project-action-btn" @click="openEditProjectForm(project)">编辑</button>
                  <button class="project-action-btn danger" @click="openDeleteProjectDialog(project)">删除</button>
                </div>
              </div>

              <Transition name="panel-slide">
                <div v-if="isProjectExpanded(project.project_id)" class="project-detail-grid">
                  <div class="project-block">
                    <label>项目描述</label>
                    <p>{{ project.project_description || '未填写' }}</p>
                  </div>
                  <div class="project-block">
                    <label>项目成果</label>
                    <p>{{ project.project_result || '未填写' }}</p>
                  </div>
                </div>
              </Transition>

              <p v-if="!isProjectExpanded(project.project_id)" class="project-preview">
                {{ project.project_description || project.project_result || '暂无详细描述，点击“展开详情”补充和查看完整信息。' }}
              </p>
              <div class="project-updated-at">创建于 {{ formatProjectDate(project.created_at) }}</div>
            </article>
          </div>
          <div v-else class="project-empty">
            <p>暂无项目，点击“新增项目”开始维护。</p>
            <button class="project-add-btn project-add-btn--empty" @click="openCreateProjectForm">立即新增第一个项目</button>
              </div>
        </section>
      </div>

      <div class="logout-section">
        <button class="logout-btn" @click="handleLogout">
          退出登录
        </button>
      </div>
    </div>

    <EditProfileModal :show="showEditModal" @close="handleModalClose" @save="handleModalSave" />

    <div v-if="pendingDeleteProject" class="delete-modal-mask" @click.self="closeDeleteProjectDialog">
      <div class="delete-modal" role="dialog" aria-modal="true" aria-labelledby="delete-project-title">
        <h3 id="delete-project-title">确认删除项目</h3>
        <p>
          删除后将无法恢复：<strong>{{ pendingDeleteProject.project_name }}</strong>
        </p>
        <div class="delete-modal-actions">
          <button class="secondary-btn" @click="closeDeleteProjectDialog">取消</button>
          <button class="danger-btn" @click="confirmDeleteProject">确认删除</button>
        </div>
      </div>
    </div>

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
  /* 移除原本的渐变蓝粉色，让页面继承全局系统的浅绿色背景 */
  background: transparent;
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
  color: #2f5d56;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.page-title {
  color: #1f2926;
  font-size: 1.9rem;
  font-weight: 700;
  margin: 0;
}

.edit-btn {
  padding: 0.55rem 1rem;
  background: #2f5d56;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.edit-btn:hover {
  transform: translateY(-1px);
  background: #3f655f;
  box-shadow: 0 10px 20px rgba(47, 93, 86, 0.28);
}

.profile-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.identity-section {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  gap: 0.8rem;
  margin-top: 1rem;
  margin-bottom: 1rem;
}

.identity-badge {
  width: 90px;
  height: 90px;
  border-radius: 20px;
  background: linear-gradient(135deg, #e8f2ec 0%, #d1e6db 100%);
  border: 2px solid #ffffff;
  box-shadow: 0 8px 24px rgba(47, 93, 86, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2f5d56;
  font-size: 2.5rem;
  font-weight: 700;
  transform: rotate(-3deg);
}

.initial-letter {
  transform: rotate(3deg);
}

.identity-block {
  text-align: center;
}

.identity-block h3 {
  margin: 0;
  color: #1f2926;
  font-size: 1.3rem;
  font-weight: 600;
}

.identity-block p {
  margin: 0.35rem 0 0;
  color: #66756f;
  font-size: 0.9rem;
}

.quick-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
}

.metric-card {
  border: 1px solid #dde5e1;
  border-radius: 12px;
  padding: 0.8rem 0.75rem;
  background: linear-gradient(135deg, #f9fbfaf8, #ffffff);
  text-align: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(31, 41, 38, 0.05);
}

.metric-card p {
  margin: 0;
  color: #66756f;
  font-size: 0.8rem;
}

.metric-card strong {
  margin-top: 0.4rem;
  display: inline-block;
  font-size: 1.4rem;
  color: #2f5d56;
  font-weight: 700;
}

.info-section {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
  margin-top: 0.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  border: 1px solid #dde5e1;
  border-radius: 12px;
  padding: 0.9rem 1rem;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
}

.info-item label {
  color: #66756f;
  font-size: 0.82rem;
  font-weight: 500;
}

.info-value {
  color: #1f2926;
  font-size: 1.05rem;
  font-weight: 600;
}

.logout-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px dashed #dde5e1;
  display: flex;
  justify-content: center;
}

.project-section {
  margin-top: 1rem;
  border: 1px solid #cce3db;
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(235, 248, 242, 0.88), rgba(218, 236, 227, 0.78));
  backdrop-filter: blur(10px);
  overflow: hidden;
  box-shadow: 0 6px 18px rgba(47, 93, 86, 0.07);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px dashed #b5d1c5;
  background: rgba(255, 255, 255, 0.3);
}

.project-header h3 {
  margin: 0;
  color: #1f2926;
  font-size: 1.2rem;
  font-weight: 600;
}

.project-header p {
  margin: 0.35rem 0 0;
  color: #66756f;
  font-size: 0.85rem;
}

.project-overview {
  padding: 1rem 1.5rem 0;
}

.project-overview-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.7rem;
}

.overview-stat-card {
  border: 1px solid #d6e7df;
  border-radius: 12px;
  padding: 0.85rem 0.95rem;
  background: rgba(255, 255, 255, 0.78);
}

.overview-stat-card p {
  margin: 0;
  font-size: 0.78rem;
  color: #66756f;
}

.overview-stat-card strong {
  display: inline-block;
  margin-top: 0.35rem;
  color: #1f2926;
  font-size: 1.06rem;
  font-weight: 700;
}

.project-add-btn {
  padding: 0.45rem 1rem;
  border: 1px solid #2f5d56;
  background: white;
  color: #2f5d56;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.project-add-btn:hover {
  background: #2f5d56;
  color: white;
}

.project-list {
  padding: 1rem 1.5rem 1.4rem;
  display: flex;
  flex-direction: column;
  gap: 0.92rem;
}

.project-card {
  border: 1px solid #d1e4dc;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  padding: 1rem 1.05rem;
  box-shadow: 0 2px 10px rgba(47, 93, 86, 0.04);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(47, 93, 86, 0.08);
}

.project-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.7rem;
}

.project-card-header h4 {
  margin: 0;
  color: #1f2926;
  font-size: 1.1rem;
  font-weight: 600;
}

.project-meta-row {
  margin-top: 0.45rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.project-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid #d8e7e0;
  background: #f8fcfa;
  color: #49605a;
  font-size: 0.74rem;
  padding: 0.16rem 0.54rem;
}

.project-chip--date {
  color: #607770;
}

.project-actions {
  display: flex;
  gap: 0.38rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.project-action-btn {
  border: 1px solid #dde5e1;
  background: white;
  color: #2f5d56;
  border-radius: 6px;
  padding: 0.26rem 0.6rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.project-action-btn:hover {
  background: #f3f8f5;
  border-color: #2f5d56;
}

.project-action-btn.danger {
  border-color: #fca5a5;
  background: #fef2f2;
  color: #dc2626;
}

.project-action-btn.danger:hover {
  background: #fee2e2;
  border-color: #ef4444;
}

.project-block {
  margin-top: 0;
  padding: 0.8rem 0.85rem;
  border: 1px solid #e1ece7;
  border-radius: 10px;
  background: #fbfdfc;
}

.project-block label {
  color: #66756f;
  font-size: 0.8rem;
  font-weight: 600;
}

.project-block p {
  margin: 0.35rem 0 0;
  color: #1f2926;
  font-size: 0.95rem;
  white-space: pre-wrap;
  line-height: 1.5;
}

.project-detail-grid {
  margin-top: 0.8rem;
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.65rem;
}

.project-preview {
  margin: 0.75rem 0 0;
  color: #4a6059;
  font-size: 0.88rem;
  line-height: 1.58;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.project-updated-at {
  margin-top: 0.52rem;
  color: #6b8079;
  font-size: 0.74rem;
}

.project-empty {
  padding: 2rem 1.4rem 2.4rem;
  color: #6d837c;
  text-align: center;
}

.project-empty p {
  margin: 0;
}

.project-add-btn--empty {
  margin-top: 0.95rem;
}

.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all 0.24s ease;
  overflow: hidden;
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
  max-height: 0;
}

.panel-slide-enter-to,
.panel-slide-leave-from {
  opacity: 1;
  transform: translateY(0);
  max-height: 280px;
}

.project-modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(31, 41, 38, 0.5);
  backdrop-filter: blur(4px);
  z-index: 1300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.delete-modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(31, 41, 38, 0.42);
  backdrop-filter: blur(3px);
  z-index: 1350;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.delete-modal {
  width: min(440px, 94vw);
  border-radius: 14px;
  border: 1px solid #d4e5dd;
  background: linear-gradient(170deg, #ffffff, #f6fbf8);
  box-shadow: 0 22px 42px rgba(31, 41, 38, 0.18);
  padding: 1.2rem 1.25rem;
}

.delete-modal h3 {
  margin: 0;
  color: #1f2926;
  font-size: 1.08rem;
}

.delete-modal p {
  margin: 0.68rem 0 0;
  color: #4f655e;
  font-size: 0.92rem;
  line-height: 1.6;
}

.delete-modal p strong {
  color: #2f5d56;
}

.delete-modal-actions {
  margin-top: 1rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.52rem;
}

.danger-btn {
  border: none;
  border-radius: 8px;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #d46a61, #c2554c);
  color: #ffffff;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}

.danger-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(194, 85, 76, 0.28);
  filter: saturate(1.06);
}

.project-modal {
  width: min(760px, 96vw);
  max-height: 88vh;
  overflow: auto;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #dde5e1;
  box-shadow: 0 24px 40px rgba(31, 41, 38, 0.15);
  padding: 2rem;
}

.project-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #f3f8f5;
  padding-bottom: 1rem;
}

.project-modal-header h3 {
  margin: 0;
  color: #1f2926;
  font-size: 1.3rem;
}

.project-close-btn {
  border: none;
  background: transparent;
  color: #66756f;
  font-size: 1.5rem;
  cursor: pointer;
  line-height: 1;
}

.project-close-btn:hover {
  color: #2f5d56;
}

.project-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-full {
  grid-column: 1 / -1;
}

.field label {
  color: #66756f;
  font-size: 0.85rem;
  font-weight: 600;
}

.field input,
.field select,
.field textarea {
  border: 1px solid #dde5e1;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  font: inherit;
  color: #1f2926;
  background: #f9fbfaf8;
  transition: all 0.2s ease;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  outline: none;
  border-color: #2f5d56;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(47, 93, 86, 0.1);
}

.field textarea {
  resize: vertical;
}

.project-error {
  color: #dc2626;
  margin: 1rem 0 0;
}

.logout-btn {
  padding: 0.75rem 2.5rem;
  background: #fff7f6;
  color: #9d4a43;
  border: 1px solid #efd4d1;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
}

.logout-btn:hover {
  background: #fcede9;
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
  border-radius: 8px;
  padding: 0.5rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.secondary-btn {
  background: white;
  border: 1px solid #cce3db;
  color: #66756f;
}

.secondary-btn:hover {
  background: #f0f7f4;
  color: #2f5d56;
}

.primary-btn {
  background: #2f5d56;
  color: #ffffff;
}

.primary-btn:hover {
  background: #234741;
}

.primary-btn:disabled {
  background: #b5d1c5;
  cursor: not-allowed;
}

.logout-btn {
  width: 100%;
  padding: 0.75rem;
  background: #fff7f6;
  color: #9d4a43;
  border: 1px solid #efd4d1;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.logout-btn:hover {
  background: #fcede9;
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

  .project-overview {
    padding: 0.9rem 1rem 0;
  }

  .project-overview-stats,
  .project-detail-grid {
    grid-template-columns: 1fr;
  }

  .project-list {
    padding: 0.9rem 1rem 1.1rem;
  }

  .project-card-header {
    flex-direction: column;
  }

  .project-actions {
    width: 100%;
    justify-content: flex-start;
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
