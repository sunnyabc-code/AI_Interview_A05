<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  ApartmentOutlined,
  AppstoreOutlined,
  AudioOutlined,
  BarChartOutlined,
  BookOutlined,
  CheckCircleOutlined,
  FolderOpenOutlined,
  HomeOutlined,
  InfoCircleOutlined,
  LineChartOutlined,
  LogoutOutlined,
  RiseOutlined,
  SyncOutlined,
  UnorderedListOutlined,
  UserOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons-vue'
import type { Component } from 'vue'
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

const menuIcons: Record<string, Component> = {
  home: HomeOutlined,
  interview: VideoCameraOutlined,
  evaluation: BarChartOutlined,
  profile: UserOutlined,
}

const featureItems: { icon: Component; title: string; text: string }[] = [
  {
    icon: AppstoreOutlined,
    title: '多题型',
    text: '技术、项目经历、场景题可按难度编排，支持追问链。',
  },
  {
    icon: AudioOutlined,
    title: '双模式',
    text: '文本作答与实时语音面试，满足不同练习习惯。',
  },
  {
    icon: RiseOutlined,
    title: '评估与推荐',
    text: '轮次打分、知识点反馈与表达分析，便于查漏补缺。',
  },
  {
    icon: BookOutlined,
    title: '岗位知识库',
    text: '按所选岗位匹配题库与生成策略，更贴近真实面试。',
  },
]

const completionPct = computed(() => {
  const t = interviewStats.value.total
  if (!t) return 0
  return Math.round((interviewStats.value.completed / t) * 100)
})

/** 统计刷新时触发动画 */
const statsAnimateKey = ref(0)

const statRows = computed(() => [
    {
      label: '面试记录',
      icon: UnorderedListOutlined,
      text: String(interviewStats.value.total),
      wide: false,
    },
    {
      label: '已完成',
      icon: CheckCircleOutlined,
      text: String(interviewStats.value.completed),
      wide: false,
    },
    {
      label: '进行中',
      icon: SyncOutlined,
      text: String(interviewStats.value.inProgress),
      wide: false,
    },
    {
      label: '项目经历',
      icon: FolderOpenOutlined,
      text: String(projectCount.value),
      wide: false,
    },
    {
      label: '开放岗位',
      icon: ApartmentOutlined,
      text: `${positionCount.value} 个可选方向`,
      wide: true,
    },
  ])

const loadHomeDashboard = async () => {
  homeLoading.value = true
  try {
    const [profileRes, interviewsRes, projectsRes, positionsRes] = await Promise.all([
      api.get('/users/profile/'),
      api.get('/v1/interviews/'),
      api.get('/user-projects/'),
      api.get('/positions/'),
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
    statsAnimateKey.value += 1
  }
}

const menuItems = [
  { id: 'home', label: '首页' },
  { id: 'interview', label: '面试' },
  { id: 'evaluation', label: '评估' },
  /* { id: 'history', label: '历史记录' }, */
  { id: 'profile', label: '个人中心' },
]

const validMenuIds = menuItems.map((item) => item.id)

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
          <span class="platform-mark" aria-hidden="true">
            <LineChartOutlined class="ada-icon ada-icon--logo" />
          </span>
          <span>AI面试平台</span>
        </h1>
      </div>

      <nav class="header-menu" aria-label="主导航">
        <button
          v-for="item in menuItems"
          :key="item.id"
          type="button"
          :class="['menu-item', { active: activeMenu === item.id }]"
          @click="handleMenuClick(item.id)"
        >
          <component :is="menuIcons[item.id]" class="ada-icon" />
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="header-right">
        <button type="button" class="profile-btn" @click="handleMenuClick('profile')">
          <UserOutlined class="ada-icon" />
          <span>{{ user.username }}</span>
        </button>
        <button type="button" class="logout-btn" @click="handleLogout">
          <LogoutOutlined class="ada-icon" />
          <span>退出</span>
        </button>
      </div>
    </header>

    <main class="main-content">
      <Transition name="panel-fade" mode="out-in">
        <div v-if="activeMenu === 'home'" key="home" class="content-area home-dashboard">
          <div class="home-dashboard-inner">
            <section class="hero-banner" aria-labelledby="home-welcome-title">
              <div class="hero-banner__glow" aria-hidden="true" />
              <div class="hero-banner__mesh hero-banner__mesh--twinkle" aria-hidden="true">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 800 200" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="home-mesh-a" x1="0" y1="0" x2="800" y2="0">
                      <stop stop-color="#2f5d56" stop-opacity="0" />
                      <stop offset="0.35" stop-color="#2f5d56" stop-opacity="0.07" />
                      <stop offset="0.65" stop-color="#3f655f" stop-opacity="0.05" />
                      <stop offset="1" stop-color="#2f5d56" stop-opacity="0" />
                    </linearGradient>
                  </defs>
                  <path stroke="url(#home-mesh-a)" stroke-width="0.6" d="M0 40h800M0 80h800M0 120h800M0 160h800M80 0v200M240 0v200M400 0v200M560 0v200M720 0v200" />
                  <circle cx="680" cy="36" r="48" stroke="#2f5d56" stroke-opacity="0.06" />
                  <circle cx="120" cy="150" r="64" stroke="#3f655f" stroke-opacity="0.05" />
                </svg>
              </div>
              <div class="hero-banner__sparkles" aria-hidden="true">
                <span class="hero-spark hero-spark--a" />
                <span class="hero-spark hero-spark--b" />
                <span class="hero-spark hero-spark--c" />
                <span class="hero-spark hero-spark--d" />
              </div>

              <div class="home-hero">
                <p class="home-eyebrow">Dashboard</p>
                <h1 id="home-welcome-title" class="home-title">
                  欢迎回来，{{ user.username || '候选人' }}
                </h1>
                <p class="home-subtitle">
                  工作台 · 模拟面试与评估一站完成
                </p>
                <p class="home-lead">
                  AI 面试平台支持多岗位模拟面试、语音与文本答题、轮次分析与学习推荐。<br>从下方入口开始练习，或在个人中心维护简历与项目经历。
                </p>
              </div>
            </section>

            <div class="home-strip" role="status">
              <InfoCircleOutlined class="ada-icon ada-icon--strip" />
              <p class="home-strip__text">
                系统已就绪。选择<strong>去面试</strong>开始一轮模拟；含<strong>项目经历题</strong>时请先完善对应岗位的项目资料。
              </p>
            </div>

            <div class="section-rule-wrap" role="presentation">
              <div class="section-rule" />
              <svg class="section-rule__dots" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 12" fill="none" aria-hidden="true">
                <defs>
                  <linearGradient id="rule-dash" x1="0" y1="0" x2="120" y2="0">
                    <stop stop-color="#c5d9d0" stop-opacity="0" />
                    <stop offset="0.5" stop-color="#2f5d56" stop-opacity="0.2" />
                    <stop offset="1" stop-color="#c5d9d0" stop-opacity="0" />
                  </linearGradient>
                </defs>
                <line x1="0" y1="6" x2="120" y2="6" stroke="url(#rule-dash)" stroke-width="1" stroke-dasharray="3 7" stroke-opacity="0.35" />
                <circle class="section-dot section-dot--1" cx="8" cy="6" r="2" fill="#2f5d56" fill-opacity="0.22" />
                <circle class="section-dot section-dot--2" cx="28" cy="6" r="1.5" fill="#3f655f" fill-opacity="0.28" />
                <circle class="section-dot section-dot--3" cx="48" cy="6" r="2" fill="#2f5d56" fill-opacity="0.18" />
                <circle class="section-dot section-dot--4" cx="68" cy="6" r="1.5" fill="#3f655f" fill-opacity="0.2" />
                <circle class="section-dot section-dot--5" cx="88" cy="6" r="2" fill="#2f5d56" fill-opacity="0.16" />
              </svg>
            </div>

            <div class="home-grid">
              <section class="home-card home-card--accent home-card--lift" aria-labelledby="home-platform-title">
                <div class="home-card-head">
                  <h3 id="home-platform-title" class="home-card-title">平台能力</h3>
                  <p class="home-card-sub">练习、反馈与岗位匹配</p>
                </div>
                <div class="home-card-divider" />
                <ul class="home-feature-list">
                  <li v-for="(f, idx) in featureItems" :key="idx" class="home-feature-item">
                    <span class="home-feature-icon" aria-hidden="true">
                      <component :is="f.icon" class="ada-icon ada-icon--feature" />
                    </span>
                    <div class="home-feature-body">
                      <strong>{{ f.title }}</strong>
                      <span class="home-feature-text">{{ f.text }}</span>
                    </div>
                  </li>
                </ul>
                <p class="home-card-footnote">
                  以上能力在面试全流程中贯通：选题 → 作答 → 评估 → 复盘。
                </p>
              </section>

              <section class="home-card home-card--surface home-card--lift" aria-labelledby="home-personal-title">
                <div class="home-card-head home-card-head--row">
                  <div>
                    <h3 id="home-personal-title" class="home-card-title">我的概览</h3>
                    <p class="home-card-sub">关键数据一览</p>
                  </div>
                  <div
                    v-if="!homeLoading && interviewStats.total > 0"
                    class="home-completion"
                  >
                    <div
                      class="home-completion-ring"
                      role="img"
                      :aria-label="`面试完成率 ${completionPct}%`"
                      :style="{ '--pct': String(completionPct) }"
                    >
                      <div class="home-completion-ring__hole">
                        <span
                          :key="`pct-${completionPct}-${statsAnimateKey}`"
                          class="home-completion-ring__num"
                        >{{ completionPct }}%</span>
                      </div>
                    </div>
                    <span class="home-completion-caption">完成率</span>
                  </div>
                </div>
                <div class="home-card-divider" />

                <div v-if="homeLoading" class="skeleton-block" aria-busy="true" aria-label="加载统计数据">
                  <div class="skeleton skeleton--line" />
                  <div class="skeleton-stats">
                    <div v-for="n in 4" :key="n" class="skeleton skeleton--stat" />
                    <div class="skeleton skeleton--stat skeleton--stat-wide" />
                  </div>
                </div>

                <template v-else>
                  <dl class="home-stat-grid">
                    <div
                      v-for="row in statRows"
                      :key="`${statsAnimateKey}-${row.label}`"
                      class="home-stat home-stat--interactive"
                      :class="{ 'home-stat--wide': row.wide }"
                    >
                      <dt class="home-stat-dt">
                        <span class="home-stat__dot" aria-hidden="true" />
                        <component :is="row.icon" class="ada-icon ada-icon--stat" />
                        <span class="home-stat__label">{{ row.label }}</span>
                      </dt>
                      <dd class="home-stat-dd">
                        {{ row.text }}
                      </dd>
                    </div>
                  </dl>
                  <div v-if="profileSummary.email || profileSummary.phone" class="home-meta">
                    <div class="home-meta-divider" />
                    <p v-if="profileSummary.email">
                      <span class="home-meta-label">邮箱</span>{{ profileSummary.email }}
                    </p>
                    <p v-if="profileSummary.phone">
                      <span class="home-meta-label">手机</span>{{ profileSummary.phone }}
                    </p>
                  </div>
                </template>
              </section>

              <section
                class="home-card home-card--actions home-card--lift"
                aria-labelledby="home-actions-title"
              >
                <div class="home-card-head home-card-head--center">
                  <h3 id="home-actions-title" class="home-card-title">快捷入口</h3>
                  <p class="home-card-sub home-card-sub--center">常用操作一键直达</p>
                </div>
                <div class="home-card-divider home-card-divider--center" />
                <div class="home-action-row home-action-row--center">
                  <button
                    type="button"
                    class="home-action-btn home-action-btn--primary home-action-btn--pulse"
                    @click="handleMenuClick('interview')"
                  >
                    <span class="home-action-btn__halo" aria-hidden="true" />
                    <VideoCameraOutlined class="ada-icon ada-icon--btn-primary" />
                    <span>去面试</span>
                  </button>
                  <button type="button" class="home-action-btn" @click="handleMenuClick('evaluation')">
                    查看评估
                  </button>
                  <button type="button" class="home-action-btn" @click="handleMenuClick('profile')">
                    个人中心
                  </button>
                </div>
                <div class="home-tip-callout home-tip-callout--center" role="note">
                  <InfoCircleOutlined class="ada-icon ada-icon--tip" />
                  <p class="home-tip-callout__text">
                    创建面试时若勾选<strong>项目经历题</strong>，须先在个人中心为<strong>所选岗位</strong>填写至少一条项目经历，否则无法创建。
                  </p>
                </div>
              </section>
            </div>
          </div>
        </div>

        <div v-else-if="activeMenu === 'interview'" key="interview" class="content-area content-area--panel">
          <InterviewView :active="true" />
        </div>

        <div v-else-if="activeMenu === 'evaluation'" key="evaluation" class="content-area content-area--panel">
          <EvaluationView />
        </div>

        <div v-else-if="activeMenu === 'profile'" key="profile" class="content-area content-area--panel">
          <ProfileView />
        </div>
      </Transition>
    </main>
  </div>
</template>

<style scoped>
.home-container {
  --bg: #f3f8f5;
  --surface: rgba(255, 255, 255, 0.78);
  --surface-soft: rgba(248, 251, 249, 0.92);
  --surface-muted: rgba(240, 247, 243, 0.95);
  --line: rgba(221, 229, 225, 0.85);
  --line-soft: #e3ebe6;
  --line-strong: #c5d9d0;
  --text: #161d1a;
  --muted: #5c6b65;
  --muted-soft: #8a9a93;
  --accent: #2f5d56;
  --accent-2: #3f655f;
  --accent-glow: rgba(47, 93, 86, 0.18);
  --accent-shadow: rgba(47, 93, 86, 0.12);
  --danger: #a7564f;
  --shadow-sm: 0 2px 12px rgba(31, 41, 38, 0.045);
  --shadow-md: 0 10px 36px rgba(31, 41, 38, 0.065);
  --shadow-lg: 0 20px 56px rgba(31, 41, 38, 0.075);
  --shadow-card-hover: 0 18px 48px rgba(31, 41, 38, 0.1), 0 0 0 1px rgba(47, 93, 86, 0.06);
  --shadow-nav: 0 10px 40px rgba(31, 41, 38, 0.08), 0 1px 0 rgba(255, 255, 255, 0.65) inset;
  --ease-smooth: cubic-bezier(0.22, 1, 0.36, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-soft: cubic-bezier(0.33, 1, 0.68, 1);
  --radius-lg: 18px;
  --radius-md: 14px;
  --radius-sm: 12px;
  --space-unit: 8px;

  min-height: 100vh;
  background: linear-gradient(180deg, #e8f2ec 0%, #f3f8f5 42%, #f3f8f5 100%);
  display: flex;
  flex-direction: column;
  font-family:
    'Inter',
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    system-ui,
    sans-serif;
}

.ada-icon {
  font-size: 15px;
  display: inline-flex;
  line-height: 1;
  flex-shrink: 0;
}

.ada-icon--logo {
  font-size: 18px;
  color: var(--accent);
}

.ada-icon--feature {
  font-size: 17px;
  color: var(--accent);
  transition:
    color 0.34s var(--ease-smooth),
    opacity 0.34s var(--ease-smooth),
    transform 0.34s var(--ease-spring);
}

.ada-icon--strip,
.ada-icon--tip {
  font-size: 16px;
  color: var(--accent);
  opacity: 0.85;
}

.ada-icon--stat {
  font-size: 14px;
  color: var(--accent);
  opacity: 0.72;
  transition:
    color 0.32s var(--ease-smooth),
    opacity 0.32s var(--ease-smooth),
    transform 0.32s var(--ease-smooth);
}

.ada-icon--btn-primary {
  font-size: 17px;
  position: relative;
  z-index: 1;
}

.home-header {
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.88);
  border-radius: var(--radius-lg);
  margin: calc(var(--space-unit) * 1.5) calc(var(--space-unit) * 1.5) 0;
  padding: 0 calc(var(--space-unit) * 2);
  box-shadow: var(--shadow-nav);
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 64px;
  height: auto;
  position: sticky;
  top: calc(var(--space-unit) * 1.5);
  z-index: 200;
  backdrop-filter: blur(16px) saturate(1.15);
  -webkit-backdrop-filter: blur(16px) saturate(1.15);
  transition:
    box-shadow 0.42s var(--ease-smooth),
    border-color 0.42s var(--ease-smooth),
    transform 0.42s var(--ease-smooth);
}

.home-header:hover {
  box-shadow:
    0 14px 48px rgba(31, 41, 38, 0.1),
    0 0 0 1px rgba(47, 93, 86, 0.05),
    0 1px 0 rgba(255, 255, 255, 0.7) inset;
}

.header-left {
  flex-shrink: 0;
}

.platform-name {
  color: var(--text);
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  letter-spacing: -0.02em;
}

.platform-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: linear-gradient(145deg, rgba(238, 246, 242, 0.95), rgba(255, 255, 255, 0.9));
  border: 1px solid var(--line-soft);
  box-shadow: var(--shadow-sm);
}

.header-menu {
  display: flex;
  gap: 0.35rem;
  flex: 1;
  justify-content: center;
  max-width: 720px;
  margin: 0 calc(var(--space-unit) * 2);
  flex-wrap: wrap;
}

.menu-item {
  padding: 0.5rem 1rem;
  background: transparent;
  color: var(--muted);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  cursor: pointer;
  transition:
    background 0.34s var(--ease-smooth) 0.015s,
    color 0.34s var(--ease-smooth) 0.015s,
    border-color 0.34s var(--ease-smooth) 0.015s,
    transform 0.36s var(--ease-spring) 0.02s,
    box-shadow 0.36s var(--ease-smooth);
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
}

.menu-item:hover {
  background: rgba(240, 247, 243, 0.92);
  color: var(--accent);
  border-color: rgba(197, 217, 208, 0.72);
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 6px 20px rgba(47, 93, 86, 0.08);
}

.menu-item.active {
  background: linear-gradient(135deg, var(--accent-2) 0%, var(--accent) 100%);
  color: white;
  box-shadow:
    0 12px 28px var(--accent-glow),
    0 0 0 1px rgba(255, 255, 255, 0.12) inset;
  border-color: transparent;
  transform: translateY(-1px) scale(1.01);
}

.menu-item:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.profile-btn {
  padding: 0.5rem 0.9rem;
  background: rgba(238, 244, 241, 0.95);
  color: #375951;
  border: 1px solid #d5e2dc;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  cursor: pointer;
  transition:
    background 0.22s ease,
    transform 0.18s ease,
    box-shadow 0.22s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
}

.profile-btn:hover {
  background: #e6efeb;
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.profile-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.logout-btn {
  padding: 0.5rem 0.9rem;
  background: rgba(255, 250, 249, 0.95);
  border: 1px solid #efd4d1;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  cursor: pointer;
  transition:
    background 0.22s ease,
    transform 0.18s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: #9d4a43;
  font-weight: 600;
}

.logout-btn:hover {
  background: #fcede9;
  transform: translateY(-1px);
}

.logout-btn:focus-visible {
  outline: 2px solid #c75c54;
  outline-offset: 2px;
}

.main-content {
  flex: 1;
  padding: calc(var(--space-unit) * 2);
  max-width: 100%;
  box-sizing: border-box;
}

.content-area {
  background: var(--surface);
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  padding: calc(var(--space-unit) * 3);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.65);
  box-shadow: var(--shadow-md);
  min-height: 400px;
  transition: box-shadow 0.35s ease;
}

.content-area--panel {
  animation: content-in 0.48s var(--ease-smooth) both;
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
  padding: calc(var(--space-unit) * 3.5);
}

.home-dashboard-inner {
  max-width: 1120px;
  margin: 0 auto;
  width: 100%;
  position: relative;
  padding-bottom: calc(var(--space-unit) * 3);
}

.home-dashboard-inner::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  width: min(100%, 920px);
  height: 120px;
  pointer-events: none;
  background: radial-gradient(ellipse 80% 100% at 50% 100%, rgba(47, 93, 86, 0.06), transparent 70%);
  opacity: 0.9;
}

.hero-banner {
  position: relative;
  border-radius: var(--radius-lg);
  padding: calc(var(--space-unit) * 4) calc(var(--space-unit) * 3);
  margin-bottom: calc(var(--space-unit) * 3);
  overflow: hidden;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.72) 0%, rgba(244, 250, 247, 0.88) 50%, rgba(238, 246, 242, 0.75) 100%);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: var(--shadow-sm);
}

.hero-banner__glow {
  position: absolute;
  inset: -40% -20% auto -20%;
  height: 85%;
  background: radial-gradient(ellipse 70% 60% at 70% 20%, rgba(47, 93, 86, 0.09), transparent 55%),
    radial-gradient(ellipse 50% 45% at 15% 80%, rgba(63, 101, 95, 0.06), transparent 50%);
  pointer-events: none;
}

.hero-banner__mesh {
  position: absolute;
  inset: 0;
  opacity: 0.85;
  pointer-events: none;
}

.hero-banner__mesh--twinkle {
  animation: mesh-breathe 5.5s var(--ease-soft) infinite alternate;
}

.hero-banner__mesh svg {
  width: 100%;
  height: 100%;
  display: block;
}

.hero-banner__sparkles {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.hero-spark {
  position: absolute;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(47, 93, 86, 0.45), transparent 70%);
  animation: spark-twinkle 3.2s var(--ease-soft) infinite;
}

.hero-spark--a {
  top: 18%;
  left: 72%;
  animation-delay: 0s;
}

.hero-spark--b {
  top: 42%;
  left: 14%;
  animation-delay: 0.6s;
}

.hero-spark--c {
  top: 68%;
  left: 58%;
  animation-delay: 1.1s;
}

.hero-spark--d {
  top: 28%;
  left: 38%;
  animation-delay: 1.8s;
}

.home-hero {
  position: relative;
  max-width: 52rem;
  z-index: 1;
  animation: fade-up 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.home-eyebrow {
  margin: 0 0 calc(var(--space-unit) * 1.25);
  font-size: 0.6875rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--muted-soft);
  font-weight: 700;
}

.home-title {
  margin: 0;
  font-size: clamp(1.85rem, 4vw, 2.5rem);
  font-weight: 800;
  letter-spacing: -0.035em;
  line-height: 1.18;
  color: var(--text);
}

.home-subtitle {
  margin: calc(var(--space-unit) * 1.75) 0 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.04em;
  display: inline-block;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid rgba(47, 93, 86, 0.22);
  opacity: 0.96;
}

.home-lead {
  margin: calc(var(--space-unit) * 2.5) 0 0;
  max-width: 38rem;
  line-height: 1.78;
  font-size: 1.0625rem;
  color: var(--muted);
}

.home-strip {
  display: flex;
  align-items: flex-start;
  gap: calc(var(--space-unit) * 1.5);
  padding: calc(var(--space-unit) * 2) calc(var(--space-unit) * 2.5);
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, rgba(238, 246, 242, 0.95), rgba(255, 255, 255, 0.65));
  border: 1px solid var(--line-soft);
  box-shadow: var(--shadow-sm);
  margin-bottom: calc(var(--space-unit) * 3);
  animation: fade-up 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.08s both;
}

.home-strip__text {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.65;
  color: var(--muted);
}

.home-strip__text strong {
  color: var(--text);
  font-weight: 600;
}

.section-rule-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: calc(var(--space-unit) * 1.25);
  margin-bottom: calc(var(--space-unit) * 3);
}

.section-rule {
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(47, 93, 86, 0.18), var(--line-strong), rgba(47, 93, 86, 0.18), transparent);
  opacity: 0.55;
}

.section-rule__dots {
  width: 120px;
  height: 12px;
  overflow: visible;
}

.section-dot {
  transform-origin: center;
}

.section-dot--1 {
  animation: dot-pulse 2.8s var(--ease-soft) infinite;
}

.section-dot--2 {
  animation: dot-pulse 2.8s var(--ease-soft) infinite 0.35s;
}

.section-dot--3 {
  animation: dot-pulse 2.8s var(--ease-soft) infinite 0.7s;
}

.section-dot--4 {
  animation: dot-pulse 2.8s var(--ease-soft) infinite 1.05s;
}

.section-dot--5 {
  animation: dot-pulse 2.8s var(--ease-soft) infinite 1.4s;
}

.home-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: calc(var(--space-unit) * 2.875);
  margin-top: 0;
}

.home-card {
  text-align: left;
  border-radius: var(--radius-md);
  padding: calc(var(--space-unit) * 3.25) calc(var(--space-unit) * 3.25);
  transition:
    transform 0.4s var(--ease-smooth) 0.018s,
    box-shadow 0.42s var(--ease-smooth),
    border-color 0.42s var(--ease-smooth);
  animation: card-enter 0.58s var(--ease-smooth) 0.12s backwards;
}

.home-card--lift:hover {
  transform: translateY(-5px) scale(1.006);
  box-shadow: var(--shadow-card-hover);
}

.home-card--accent {
  background: linear-gradient(155deg, #f7fbf9 0%, #eef6f2 48%, #e8f2ec 100%);
  border: 1px solid rgba(197, 217, 208, 0.55);
  box-shadow: var(--shadow-sm);
  min-height: 320px;
  display: flex;
  flex-direction: column;
}

.home-card--accent.home-card--lift:hover {
  box-shadow: var(--shadow-card-hover), 0 0 0 1px rgba(47, 93, 86, 0.04);
}

.home-card--surface {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--line-soft);
  box-shadow: var(--shadow-sm);
}

.home-card--surface.home-card--lift:hover {
  box-shadow: var(--shadow-card-hover);
}

.home-card--actions {
  grid-column: 1 / -1;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.97) 0%, rgba(248, 251, 249, 0.93) 100%);
  border: 1px solid var(--line-soft);
  box-shadow: var(--shadow-md);
  text-align: center;
}

.home-card--actions.home-card--lift:hover {
  box-shadow:
    var(--shadow-lg),
    0 0 60px rgba(47, 93, 86, 0.05);
}

.home-card-head {
  margin-bottom: calc(var(--space-unit) * 1.25);
}

.home-card-head--row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: calc(var(--space-unit) * 2);
}

.home-card-head--center {
  text-align: center;
  margin-left: auto;
  margin-right: auto;
  max-width: 36rem;
}

.home-card-title {
  margin: 0;
  font-size: 1.1875rem;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.025em;
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
}

.home-card-title::before {
  content: '';
  width: 6px;
  height: 1.05em;
  min-height: 17px;
  border-radius: 6px;
  background: linear-gradient(180deg, var(--accent) 0%, var(--accent-2) 88%);
  box-shadow: 0 2px 10px var(--accent-glow);
  flex-shrink: 0;
}

.home-card-head--center .home-card-title {
  justify-content: center;
}

.home-card-sub {
  margin: calc(var(--space-unit) * 0.85) 0 0;
  font-size: 0.8125rem;
  color: var(--muted-soft);
  line-height: 1.55;
  font-weight: 500;
}

.home-card-sub--center {
  margin-left: auto;
  margin-right: auto;
  max-width: 22rem;
  opacity: 0.88;
}

.home-card-divider {
  height: 1px;
  background: linear-gradient(90deg, var(--line-strong), transparent);
  opacity: 0.35;
  margin-bottom: calc(var(--space-unit) * 2.75);
}

.home-card-divider--center {
  max-width: 200px;
  margin-left: auto;
  margin-right: auto;
  margin-bottom: calc(var(--space-unit) * 3);
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.2;
}

.home-feature-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: calc(var(--space-unit) * 2.25);
  flex: 1;
}

.home-feature-item {
  display: flex;
  gap: calc(var(--space-unit) * 1.75);
  align-items: flex-start;
  padding: calc(var(--space-unit) * 1.25);
  margin: calc(var(--space-unit) * -0.5);
  border-radius: var(--radius-sm);
  transition: background 0.35s var(--ease-smooth);
}

.home-feature-item:hover {
  background: rgba(255, 255, 255, 0.35);
}

.home-feature-icon {
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(197, 217, 208, 0.45);
  box-shadow: var(--shadow-sm);
  transition:
    box-shadow 0.34s var(--ease-smooth),
    transform 0.34s var(--ease-spring) 0.02s,
    background 0.34s var(--ease-smooth);
}

.home-feature-item:hover .home-feature-icon {
  transform: scale(1.08);
  background: linear-gradient(135deg, #f3f8f5 70%, #ddece8 100%);
  box-shadow: 0 7px 20px var(--accent-glow);
}

.home-feature-item:hover .ada-icon--feature {
  color: var(--accent);
  opacity: 1;
  transform: scale(1.06);
}

.home-feature-body {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
}

.home-feature-body strong {
  color: var(--text);
  font-weight: 700;
  font-size: 0.9375rem;
}

.home-feature-text {
  font-size: 0.875rem;
  line-height: 1.68;
  color: var(--muted);
}

.home-card-footnote {
  margin: calc(var(--space-unit) * 2.75) 0 0;
  padding-top: calc(var(--space-unit) * 2);
  border-top: 1px dashed rgba(197, 217, 208, 0.65);
  font-size: 0.8125rem;
  line-height: 1.6;
  color: var(--muted-soft);
  font-weight: 500;
}

.home-completion {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}

.home-completion-ring {
  --pct: 0;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: conic-gradient(var(--accent) calc(var(--pct) * 1%), #dfe8e3 0);
  display: grid;
  place-items: center;
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.6);
  animation: ring-pop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) 0.2s both;
}

.home-completion-ring__hole {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #fff;
  display: grid;
  place-items: center;
  box-shadow: 0 1px 4px rgba(31, 41, 38, 0.06);
}

.home-completion-ring__num {
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--accent);
  letter-spacing: -0.02em;
  display: inline-block;
  animation: number-pop 0.42s cubic-bezier(0.7, -0.3, 0.92, 1.45) both;
}

.home-completion-caption {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted-soft);
}

.home-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: calc(var(--space-unit) * 1.75);
  margin: 0;
}

.home-stat {
  margin: 0;
  padding: calc(var(--space-unit) * 1.85) calc(var(--space-unit) * 2.15);
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-sm);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.8) inset;
  transition:
    border-color 0.34s var(--ease-smooth) 0.015s,
    box-shadow 0.36s var(--ease-smooth),
    transform 0.36s var(--ease-spring) 0.02s;
}

.home-stat--interactive:hover {
  border-color: rgba(47, 93, 86, 0.3);
  box-shadow: var(--shadow-sm), 0 0 0 1px rgba(47, 93, 86, 0.04);
  transform: translateY(-3px) scale(1.01);
}

.home-stat--interactive:hover .ada-icon--stat {
  opacity: 1;
  color: var(--accent);
  transform: scale(1.08);
}

.home-stat--wide {
  grid-column: 1 / -1;
}

.home-stat-dt {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted-soft);
  font-weight: 700;
}

.home-stat__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  opacity: 0.55;
  flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(47, 93, 86, 0.08);
}

.home-stat__label {
  flex: 1;
  min-width: 0;
}

.home-stat-dd {
  margin: 0.45rem 0 0;
  padding-left: calc(6px + 0.4rem + 14px + 0.4rem);
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--accent);
  letter-spacing: -0.03em;
  line-height: 1.1;
  animation: stat-value-in 0.48s var(--ease-spring) both;
}

.home-meta {
  margin-top: calc(var(--space-unit) * 2.5);
  font-size: 0.875rem;
  color: var(--muted);
  line-height: 1.6;
}

.home-meta-divider {
  height: 1px;
  background: var(--line-soft);
  margin-bottom: calc(var(--space-unit) * 1.75);
}

.home-meta p {
  margin: 0.35rem 0;
}

.home-meta-label {
  display: inline-block;
  min-width: 2.6rem;
  color: var(--text);
  font-weight: 600;
  margin-right: 0.4rem;
}

.home-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: calc(var(--space-unit) * 1.75);
}

.home-action-row--center {
  justify-content: center;
  align-items: center;
}

.home-action-btn {
  padding: 0.72rem 1.45rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: #fff;
  color: var(--text);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.34s var(--ease-smooth) 0.015s,
    border-color 0.34s var(--ease-smooth) 0.015s,
    transform 0.36s var(--ease-spring) 0.02s,
    box-shadow 0.36s var(--ease-smooth);
}

.home-action-btn:hover {
  background: #f4faf7;
  border-color: #b8d0c4;
  transform: translateY(-2px) scale(1.02);
  box-shadow: var(--shadow-sm);
}

.home-action-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.home-action-btn--primary {
  position: relative;
  overflow: visible;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  padding: 0.85rem 1.85rem;
  font-size: 1rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--accent-2) 0%, var(--accent) 100%);
  color: #fff;
  border: none;
  box-shadow: 0 12px 32px var(--accent-glow), 0 0 0 1px rgba(255, 255, 255, 0.12) inset;
}

.home-action-btn__halo {
  position: absolute;
  inset: -8px;
  border-radius: inherit;
  background: radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.35), transparent 55%);
  opacity: 0;
  pointer-events: none;
  animation: btn-halo-pulse 2.8s var(--ease-soft) infinite;
}

.home-action-btn--primary:hover {
  background: linear-gradient(135deg, #48756d 0%, #285349 100%);
  transform: translateY(-3px) scale(1.03);
  box-shadow: 0 16px 40px rgba(47, 93, 86, 0.32), 0 0 0 1px rgba(255, 255, 255, 0.14) inset;
}

.home-action-btn--primary:hover .home-action-btn__halo {
  opacity: 0.9;
}

.home-action-btn--pulse .home-action-btn__halo {
  opacity: 0.45;
}

.skeleton-block {
  min-height: 200px;
}

.skeleton {
  border-radius: var(--radius-sm);
  background: linear-gradient(
    90deg,
    #e8eeeb 0%,
    #f4faf7 45%,
    #e8eeeb 90%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.15s ease-in-out infinite;
}

.skeleton--line {
  height: 14px;
  width: 40%;
  margin-bottom: calc(var(--space-unit) * 2);
}

.skeleton-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: calc(var(--space-unit) * 1.75);
}

.skeleton--stat {
  height: 76px;
}

.skeleton--stat-wide {
  grid-column: 1 / -1;
  height: 72px;
}

.home-tip-callout {
  margin-top: calc(var(--space-unit) * 3.25);
  display: flex;
  gap: calc(var(--space-unit) * 1.75);
  align-items: flex-start;
  padding: calc(var(--space-unit) * 2.25) calc(var(--space-unit) * 2.75);
  border-radius: var(--radius-md);
  background: rgba(255, 252, 245, 0.92);
  border: 1px solid rgba(229, 214, 176, 0.55);
  box-shadow: var(--shadow-sm);
  text-align: left;
}

.home-tip-callout--center {
  max-width: 40rem;
  margin-left: auto;
  margin-right: auto;
}

.home-tip-callout__text {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.72;
  color: var(--muted);
}

.home-tip-callout__text strong {
  color: var(--text);
  font-weight: 600;
}

.panel-fade-enter-active,
.panel-fade-leave-active {
  transition:
    opacity 0.42s var(--ease-smooth),
    transform 0.45s var(--ease-smooth);
}

.panel-fade-enter-from,
.panel-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes mesh-breathe {
  from {
    opacity: 0.78;
  }
  to {
    opacity: 0.95;
  }
}

@keyframes spark-twinkle {
  0%,
  100% {
    opacity: 0.2;
    transform: scale(0.85);
  }
  50% {
    opacity: 0.95;
    transform: scale(1.15);
  }
}

@keyframes dot-pulse {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.35);
  }
}

@keyframes number-pop {
  0% {
    transform: scale(0.85);
  }
  90% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}

@keyframes stat-value-in {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.92);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes btn-halo-pulse {
  0%,
  100% {
    transform: scale(0.92);
    opacity: 0.25;
  }
  50% {
    transform: scale(1.08);
    opacity: 0.55;
  }
}

@keyframes content-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

@keyframes ring-pop {
  from {
    opacity: 0;
    transform: scale(0.85);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@media (max-width: 768px) {
  .home-header {
    flex-direction: column;
    padding: calc(var(--space-unit) * 1.75);
    gap: calc(var(--space-unit) * 1.5);
    margin: calc(var(--space-unit) * 1.25) calc(var(--space-unit) * 1.25) 0;
    top: calc(var(--space-unit) * 1.25);
  }

  .header-menu {
    order: 3;
    max-width: 100%;
    margin: 0;
    justify-content: center;
  }

  .menu-item {
    padding: 0.45rem 0.75rem;
    font-size: 0.8125rem;
  }

  .header-right {
    order: 2;
    width: 100%;
    justify-content: center;
  }

  .main-content {
    padding: calc(var(--space-unit) * 1.5);
  }

  .content-area {
    padding: calc(var(--space-unit) * 2);
    min-height: 320px;
  }

  .content-area.home-dashboard {
    padding: calc(var(--space-unit) * 2);
  }

  .hero-banner {
    padding: calc(var(--space-unit) * 3) calc(var(--space-unit) * 2);
  }

  .home-grid {
    grid-template-columns: 1fr;
    gap: calc(var(--space-unit) * 2);
  }

  .home-stat-grid {
    grid-template-columns: 1fr;
  }

  .home-stat--wide {
    grid-column: auto;
  }

  .home-card-head--row {
    flex-direction: column;
    align-items: stretch;
  }

  .home-completion {
    flex-direction: row;
    justify-content: flex-start;
    align-items: center;
    gap: calc(var(--space-unit) * 1.5);
  }

  .home-feature-list {
    grid-template-columns: 1fr;
    gap: calc(var(--space-unit) * 2);
  }

  .home-card {
    border-radius: 20px;
    padding: calc(var(--space-unit) * 3.5) calc(var(--space-unit) * 2.75);
  }

  .home-card-title {
    font-size: 1.25rem;
  }

  .home-feature-body strong {
    font-size: 1rem;
  }

  .home-feature-text {
    font-size: 0.9375rem;
  }

  .home-stat-dd {
    font-size: 1.625rem;
    padding-left: 0;
  }

  .home-stat-dt {
    font-size: 0.72rem;
  }

  .home-action-row--center {
    flex-direction: column;
    align-items: stretch;
    gap: calc(var(--space-unit) * 1.5);
  }

  .home-action-btn--primary {
    width: 100%;
    max-width: 320px;
    margin-left: auto;
    margin-right: auto;
  }
}
</style>
