<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ProfileView from './ProfileView.vue'
import InterviewView from './InterviewView.vue'

const router = useRouter()
const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))
const activeMenu = ref(localStorage.getItem('activeMenu') || 'home')

const menuItems = [
  { id: 'home', label: '首页' },
  { id: 'interview', label: '面试' },
  { id: 'history', label: '历史记录' },
  { id: 'profile', label: '个人中心' }
]

const handleMenuClick = (menuId: string) => {
  activeMenu.value = menuId
  localStorage.setItem('activeMenu', menuId)
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
  }
})
</script>

<template>
  <div class="home-container">
    <header class="home-header">
      <div class="header-left">
        <h1 class="platform-name">AI面试平台</h1>
      </div>
      
      <nav class="header-menu">
        <button 
          v-for="item in menuItems"
          :key="item.id"
          :class="['menu-item', { active: activeMenu === item.id }]"
          @click="handleMenuClick(item.id)"
        >
          {{ item.label }}
        </button>
      </nav>
      
      <div class="header-right">
        <button class="profile-btn" @click="handleMenuClick('profile')">
          {{ user.username }}
        </button>
        <button class="logout-btn" @click="handleLogout">退出</button>
      </div>
    </header>
    
    <main class="main-content">
      <div v-if="activeMenu === 'home'" class="content-area">
        <h2>欢迎来到AI面试平台</h2>
        <p>请选择上方菜单开始您的面试之旅</p>
      </div>
      
      <div v-if="activeMenu === 'interview'" class="content-area">
        <InterviewView :active="true" />
      </div>
      
      <div v-if="activeMenu === 'history'" class="content-area">
        <h2>历史记录</h2>
        <p>历史记录功能正在开发中...</p>
      </div>
      
      <div v-if="activeMenu === 'profile'" class="content-area">
        <ProfileView />
      </div>
    </main>
  </div>
</template>

<style scoped>
.home-container {
  min-height: 100vh;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
}

.home-header {
  background: white;
  padding: 0 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  flex-shrink: 0;
}

.platform-name {
  color: #667eea;
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  white-space: nowrap;
}

.header-menu {
  display: flex;
  gap: 0.5rem;
  flex: 1;
  justify-content: center;
  max-width: 600px;
  margin: 0 2rem;
}

.menu-item {
  padding: 0.5rem 1.5rem;
  background: transparent;
  color: #666;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.menu-item:hover {
  background: #f0f0f0;
  color: #667eea;
}

.menu-item.active {
  background: #667eea;
  color: white;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-shrink: 0;
}

.profile-btn {
  padding: 0.5rem 1rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.profile-btn:hover {
  background: #5568d3;
}

.logout-btn {
  padding: 0.5rem 1rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.logout-btn:hover {
  background: #c0392b;
}

.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 100%;
  box-sizing: border-box;
}

.content-area {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 400px;
}

.content-area h2 {
  color: #333;
  margin-bottom: 1rem;
  font-size: 1.8rem;
}

.content-area p {
  color: #666;
  font-size: 1rem;
}

.create-interview-btn {
  margin-top: 2rem;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

@media (max-width: 768px) {
  .home-header {
    flex-direction: column;
    height: auto;
    padding: 1rem;
    gap: 1rem;
  }
  
  .header-menu {
    order: 3;
    max-width: 100%;
    margin: 0;
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .menu-item {
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
  }
  
  .header-right {
    order: 2;
  }
  
  .main-content {
    padding: 1rem;
  }
  
  .content-area {
    padding: 1.5rem;
  }
}
</style>
