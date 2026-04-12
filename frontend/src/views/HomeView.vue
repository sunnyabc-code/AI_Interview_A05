<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ProfileView from './ProfileView.vue'
import InterviewView from './InterviewView.vue'
import EvaluationView from './EvaluationView.vue'

const router = useRouter()
const route = useRoute()
const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))
const activeMenu = ref(localStorage.getItem('activeMenu') || 'home')

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
    return
  }

  const menuFromStorage = localStorage.getItem('activeMenu') || 'home'
  setActiveMenu(menuFromStorage, true)
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
      <div v-if="activeMenu === 'home'" class="content-area">
        <div class="home-hero">
          <p class="home-eyebrow">Welcome</p>
          <h2>欢迎来到AI面试平台</h2>
          <p>请选择上方菜单开始您的面试之旅，系统会为你统一管理面试流程、评估结果与历史记录。</p>
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
  --bg: #f3f5f4;
  --surface: #ffffff;
  --surface-soft: #f8fbf9;
  --line: #dde5e1;
  --line-soft: #e8eeeb;
  --text: #1f2926;
  --muted: #66756f;
  --accent: #2f5d56;
  --accent-2: #3f655f;
  --danger: #a7564f;

  min-height: 100vh;
  background:
    radial-gradient(circle at top right, rgba(47, 93, 86, 0.08), transparent 38%),
    radial-gradient(circle at top left, rgba(31, 41, 38, 0.05), transparent 40%),
    var(--bg);
  display: flex;
  flex-direction: column;
}

.home-header {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid var(--line);
  border-radius: 16px;
  margin: 0.75rem 0.75rem 0;
  padding: 0 1rem;
  box-shadow: 0 12px 24px rgba(31, 41, 38, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  position: sticky;
  top: 0.75rem;
  z-index: 100;
  backdrop-filter: blur(8px);
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
  padding: 1rem;
  border-radius: 16px;
  border: 1px solid var(--line);
  box-shadow: 0 14px 28px rgba(31, 41, 38, 0.08);
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

.home-hero {
  max-width: 760px;
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
