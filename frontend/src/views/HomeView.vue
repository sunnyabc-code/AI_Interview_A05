<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ProfileView from './ProfileView.vue'
import InterviewView from './InterviewView.vue'
import EvaluationView from './EvaluationView.vue'
import api from '@/utils/api'

const router = useRouter()
const route = useRoute()
const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))
const activeMenu = ref(localStorage.getItem('activeMenu') || 'home')

const homeLoading = ref(false)
const profileSummary = ref<{ email?: string; phone?: string; created_at?: string }>({})
const interviewStats = ref({ total: 0, completed: 0, inProgress: 0 })
const projectCount = ref(0)
const positionCount = ref(0)

const loadHomeDashboard = async () => {
  homeLoading.value = true
  try {
    const [profileRes, interviewsRes, projectsRes, positionsRes] = await Promise.all([
      api.get('/api/users/profile/'),
      api.get('/api/v1/interviews/'),
      api.get('/api/user-projects/'),
      api.get('/api/positions/'),
    ])

    if (profileRes.code === 200 && profileRes.data) {
      profileSummary.value = profileRes.data
      if (profileRes.data.username && !user.value?.username) {
        user.value = { ...user.value, ...profileRes.data }
      }
    }

    if (interviewsRes.code === 200 && Array.isArray(interviewsRes.data)) {
      const list = interviewsRes.data as { status: string }[]
      interviewStats.value = {
        total: list.length,
        completed: list.filter((i) => i.status === 'completed').length,
        inProgress: list.filter((i) => i.status === 'in_progress').length,
      }
    }

    if (projectsRes.code === 200 && Array.isArray(projectsRes.data)) {
      projectCount.value = projectsRes.data.length
    }

    if (positionsRes.code === 200 && Array.isArray(positionsRes.data)) {
      positionCount.value = positionsRes.data.length
    }
  } catch {
    /* 首页统计失败时保留默认 0，不阻断导航 */
  } finally {
    homeLoading.value = false
  }
}

const menuItems = [
  { id: 'home', label: '首页' },
  { id: 'interview', label: '面试' },
  { id: 'evaluation', label: '评估' },
  /* { id: 'history', label: '历史记录' }, */
  { id: 'profile', label: '个人中心' }
]

const validMenuIds = menuItems.map(item => item.id)

const setActiveMenu = async (menuId: string, syncRoute = false) => {
  const nextMenu = validMenuIds.includes(menuId) ? menuId : 'home'
  activeMenu.value = nextMenu
  localStorage.setItem('activeMenu', nextMenu)

  if (syncRoute) {
    const currentMenuFromQuery = typeof route.query.menu === 'string' ? route.query.menu : ''
    const nextMenuQuery = nextMenu === 'home' ? '' : nextMenu
    if (currentMenuFromQuery !== nextMenuQuery) {
      await router.replace({
        path: '/home',
        query: nextMenuQuery ? { menu: nextMenuQuery } : {},
      })
    }
  }
}

const handleMenuClick = (menuId: string) => {
  setActiveMenu(menuId, true)
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

  const menuFromQuery = typeof route.query.menu === 'string' ? route.query.menu : ''
  if (menuFromQuery) {
    setActiveMenu(menuFromQuery)
    if (menuFromQuery === 'home') {
      loadHomeDashboard()
    }
    return
  }

  const menuFromStorage = localStorage.getItem('activeMenu') || 'home'
  setActiveMenu(menuFromStorage, true)
  if (menuFromStorage === 'home') {
    loadHomeDashboard()
  }
})

watch(activeMenu, (id) => {
  if (id === 'home') {
    loadHomeDashboard()
  }
})
</script>

<template>
  <div class="home-container">
    <header class="home-header">
      <div class="header-left">
        <h1 class="platform-name">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="5" width="16" height="14" rx="3" stroke="currentColor" stroke-width="1.8"/>
              <path d="M8 10H16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M8 14H13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </span>
          <span>AI面试平台</span>
        </h1>
      </div>

      <nav class="header-menu">
        <button v-for="item in menuItems" :key="item.id" :class="['menu-item', { active: activeMenu === item.id }]"
          @click="handleMenuClick(item.id)">
          <span class="icon" aria-hidden="true">
            <svg v-if="item.id === 'home'" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M4 11.2L12 5L20 11.2V19H14V14H10V19H4V11.2Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="item.id === 'interview'" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="5" width="16" height="14" rx="3" stroke="currentColor" stroke-width="1.8"/>
              <path d="M8 10H16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M8 14H13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
            <svg v-else-if="item.id === 'evaluation'" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M6 17V11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M12 17V8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M18 17V13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
            <svg v-else-if="item.id === 'history'" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M6 7V12H11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M6.4 12C7.2 15.4 10.2 18 13.8 18C18 18 21 15 21 10.8C21 6.6 18 3.6 13.8 3.6C11.5 3.6 9.4 4.5 8 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="8.2" r="3" stroke="currentColor" stroke-width="1.8"/>
              <path d="M6.5 18C7.7 14.9 10 13.5 12 13.5C14 13.5 16.3 14.9 17.5 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </span>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="header-right">
        <button class="profile-btn" @click="handleMenuClick('profile')">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="8.2" r="3" stroke="currentColor" stroke-width="1.8"/>
              <path d="M6.5 18C7.7 14.9 10 13.5 12 13.5C14 13.5 16.3 14.9 17.5 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </span>
          <span>{{ user.username }}</span>
        </button>
        <button class="logout-btn" @click="handleLogout">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M15 8L19 12L15 16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M10 12H19" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M13 5H7C5.9 5 5 5.9 5 7V17C5 18.1 5.9 19 7 19H13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </span>
          <span>退出</span>
        </button>
      </div>
    </header>

    <main class="main-content">
      <div v-if="activeMenu === 'home'" class="content-area home-dashboard">
        <div class="home-hero">
          <p class="home-eyebrow">Dashboard</p>
          <h1>欢迎回来，{{ user.username || '候选人' }}</h1>
          <p class="home-lead">
            AI 面试平台支持多岗位模拟面试、语音与文本答题、轮次分析与学习推荐。从下方入口开始练习，或在个人中心维护简历与项目经历。
          </p>
        </div>

        <p v-if="homeLoading" class="home-loading">正在加载概览…</p>

        <div class="home-grid">
          <section class="home-card home-card--accent" aria-labelledby="home-platform-title">
            <h3 id="home-platform-title" class="home-card-title">平台能力</h3>
            <ul class="home-feature-list">
              <li><strong>多题型</strong>：技术、项目经历、场景题可按难度编排，支持追问链。</li>
              <li><strong>双模式</strong>：文本作答与实时语音面试，满足不同练习习惯。</li>
              <li><strong>评估与推荐</strong>：轮次打分、知识点反馈与表达分析，便于查漏补缺。</li>
              <li><strong>岗位知识库</strong>：按所选岗位匹配题库与生成策略，更贴近真实面试。</li>
            </ul>
          </section>

          <section class="home-card" aria-labelledby="home-personal-title">
            <h3 id="home-personal-title" class="home-card-title">我的概览</h3>
            <dl class="home-stat-grid">
              <div class="home-stat">
                <dt>面试记录</dt>
                <dd>{{ interviewStats.total }}</dd>
              </div>
              <div class="home-stat">
                <dt>已完成</dt>
                <dd>{{ interviewStats.completed }}</dd>
              </div>
              <div class="home-stat">
                <dt>进行中</dt>
                <dd>{{ interviewStats.inProgress }}</dd>
              </div>
              <div class="home-stat">
                <dt>项目经历</dt>
                <dd>{{ projectCount }}</dd>
              </div>
              <div class="home-stat home-stat--wide">
                <dt>开放岗位</dt>
                <dd>{{ positionCount }} 个可选方向</dd>
              </div>
            </dl>
            <div class="home-meta" v-if="profileSummary.email || profileSummary.phone">
              <p v-if="profileSummary.email"><span class="home-meta-label">邮箱</span>{{ profileSummary.email }}</p>
              <p v-if="profileSummary.phone"><span class="home-meta-label">手机</span>{{ profileSummary.phone }}</p>
            </div>
          </section>

          <section class="home-card home-card--actions" aria-labelledby="home-actions-title">
            <h3 id="home-actions-title" class="home-card-title">快捷入口</h3>
            <div class="home-action-row">
              <button type="button" class="home-action-btn primary" @click="handleMenuClick('interview')">
                去面试
              </button>
              <button type="button" class="home-action-btn" @click="handleMenuClick('evaluation')">
                查看评估
              </button>
              <button type="button" class="home-action-btn" @click="handleMenuClick('profile')">
                个人中心
              </button>
            </div>
            <p class="home-tip">
              创建面试时若勾选<strong>项目经历题</strong>，须先在个人中心为<strong>所选岗位</strong>填写至少一条项目经历，否则无法创建。
            </p>
          </section>
        </div>
      </div>

      <div v-if="activeMenu === 'interview'" class="content-area">
        <InterviewView :active="true" />
      </div>

      <div v-if="activeMenu === 'evaluation'" class="content-area">
        <EvaluationView />
      </div>

      <!-- <div v-if="activeMenu === 'history'" class="content-area">
        <h2>历史记录</h2>
        <p>历史记录功能正在开发中...</p>
      </div> -->

      <div v-if="activeMenu === 'profile'" class="content-area">
        <ProfileView />
      </div>
    </main>
  </div>
</template>

<style scoped>
.home-container {
  --bg: #f3f8f5;
  --surface: rgba(255, 255, 255, 0.7);
  --surface-soft: rgba(248, 251, 249, 0.8);
  --line: rgba(221, 229, 225, 0.8);
  --line-soft: #e8eeeb;
  --text: #1f2926;
  --muted: #66756f;
  --accent: #2f5d56;
  --accent-2: #3f655f;
  --danger: #a7564f;

  min-height: 100vh;
  background: linear-gradient(180deg, #e8f2ec 0%, #f3f8f5 100%);
  display: flex;
  flex-direction: column;
}

.home-header {
  background: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 16px;
  margin: 0.75rem 0.75rem 0;
  padding: 0 1rem;
  box-shadow: 0 4px 16px rgba(31, 41, 38, 0.04);
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  position: sticky;
  top: 0.75rem;
  z-index: 100;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.header-left {
  flex-shrink: 0;
}

.platform-name {
  color: var(--text);
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 0.48rem;
}

.header-menu {
  display: flex;
  gap: 0.38rem;
  flex: 1;
  justify-content: center;
  max-width: 720px;
  margin: 0 1rem;
}

.menu-item {
  padding: 0.5rem 0.86rem;
  background: transparent;
  color: var(--muted);
  border: 1px solid transparent;
  border-radius: 10px;
  font-size: 0.88rem;
  cursor: pointer;
  transition: all 0.24s ease;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-weight: 600;
}

.menu-item:hover {
  background: #f0f5f2;
  color: var(--accent);
  border-color: #d9e5df;
}

.menu-item.active {
  background: linear-gradient(135deg, var(--accent-2) 0%, var(--accent) 100%);
  color: white;
  box-shadow: 0 8px 18px rgba(47, 93, 86, 0.24);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-shrink: 0;
}

.profile-btn {
  padding: 0.48rem 0.78rem;
  background: #eef4f1;
  color: #375951;
  border: 1px solid #d5e2dc;
  border-radius: 10px;
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.24s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.profile-btn:hover {
  background: #e6efeb;
}

.logout-btn {
  padding: 0.48rem 0.78rem;
  background: #fff7f6;
  color: white;
  border: 1px solid #efd4d1;
  border-radius: 10px;
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.24s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: #9d4a43;
  font-weight: 600;
}

.logout-btn:hover {
  background: #fcede9;
}

.main-content {
  flex: 1;
  padding: 0.75rem;
  max-width: 100%;
  box-sizing: border-box;
}

.content-area {
  background: var(--surface);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  padding: 1rem;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 24px rgba(31, 41, 38, 0.04);
  min-height: 400px;
}

.content-area h2 {
  color: var(--text);
  margin-bottom: 1rem;
  font-size: 1.5rem;
  letter-spacing: -0.02em;
}

.content-area p {
  color: var(--muted);
  font-size: 0.96rem;
}

.content-area.home-dashboard {
  min-height: 480px;
}

.home-lead {
  max-width: 100%;
  line-height: 1.65;
  margin-top: 0.5rem;
}

.home-loading {
  font-size: 0.88rem;
  color: var(--muted);
  margin: 0.25rem 0 0.75rem;
}

.home-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 1.25rem;
}

.home-card {
  background: var(--surface-soft);
  border: 1px solid var(--line-soft);
  border-radius: 14px;
  padding: 1rem 1.1rem;
  text-align: left;
}

.home-card--accent {
  background: linear-gradient(145deg, #f4faf7 0%, #eef6f2 100%);
  border-color: #d5e8df;
}

.home-card--actions {
  grid-column: 1 / -1;
}

.home-card-title {
  margin: 0 0 0.75rem;
  font-size: 1.02rem;
  color: var(--text);
  letter-spacing: -0.02em;
}

.home-feature-list {
  margin: 0;
  padding-left: 1.15rem;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.65;
}

.home-feature-list li {
  margin-bottom: 0.45rem;
}

.home-feature-list strong {
  color: var(--text);
  font-weight: 600;
}

.home-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 0;
}

.home-stat {
  margin: 0;
  padding: 0.65rem 0.75rem;
  background: #fff;
  border: 1px solid var(--line-soft);
  border-radius: 12px;
}

.home-stat--wide {
  grid-column: 1 / -1;
}

.home-stat dt {
  margin: 0;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  font-weight: 600;
}

.home-stat dd {
  margin: 0.2rem 0 0;
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: -0.02em;
}

.home-meta {
  margin-top: 0.85rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--line-soft);
  font-size: 0.86rem;
  color: var(--muted);
}

.home-meta p {
  margin: 0.25rem 0;
}

.home-meta-label {
  display: inline-block;
  min-width: 2.5rem;
  color: var(--text);
  font-weight: 600;
  margin-right: 0.35rem;
}

.home-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.home-action-btn {
  padding: 0.55rem 1rem;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--text);
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
}

.home-action-btn:hover {
  background: #f4faf7;
  border-color: #c5d9d0;
}

.home-action-btn.primary {
  background: linear-gradient(135deg, var(--accent-2) 0%, var(--accent) 100%);
  color: #fff;
  border: none;
  box-shadow: 0 8px 18px rgba(47, 93, 86, 0.22);
}

.home-action-btn.primary:hover {
  transform: translateY(-1px);
}

.home-tip {
  margin: 0.85rem 0 0;
  font-size: 0.82rem;
  line-height: 1.55;
  color: var(--muted);
}

.home-hero {
  max-width: 920px;
}

.home-eyebrow {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
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
  .home-header {
    flex-direction: column;
    height: auto;
    padding: 0.75rem;
    gap: 0.7rem;
    margin: 0.6rem 0.6rem 0;
    top: 0.6rem;
  }

  .header-menu {
    order: 3;
    max-width: 100%;
    margin: 0;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.3rem;
  }

  .menu-item {
    padding: 0.45rem 0.72rem;
    font-size: 0.82rem;
  }

  .header-right {
    order: 2;
    width: 100%;
    justify-content: center;
  }

  .main-content {
    padding: 0.6rem;
  }

  .content-area {
    padding: 0.8rem;
    min-height: 320px;
  }

  .home-grid {
    grid-template-columns: 1fr;
  }

  .home-stat-grid {
    grid-template-columns: 1fr;
  }

  .home-stat--wide {
    grid-column: auto;
  }

  .hero-copy h2 {
    font-size: 1.15rem;
  }

  .hero-copy p {
    font-size: 0.88rem;
  }

  .hero-panel {
    flex-direction: column;
    align-items: stretch;
    gap: 0.7rem;
  }
}
</style>
