<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { playCloudTransition } from '@/utils/cloudTransition'
import { API_BASE_URL } from '@/utils/api'
import vineSvg from '@/assets/images/vine.svg'
import forestBg from '@/assets/images/forest-bg.svg'

const router = useRouter()

const activeTab = ref('login')
const loading = ref(false)
const error = ref('')
const success = ref('')
const isLeaving = ref(false)

const loginForm = reactive({
  login_type: 'email',
  identifier: '',
  password: ''
})

const registerForm = reactive({
  register_type: 'email',
  username: '',
  email: '',
  phone: '',
  password: '',
  confirm_password: '',
  verification_code: ''
})

const resetForm = reactive({
  reset_type: 'email',
  identifier: '',
  verification_code: '',
  new_password: '',
  confirm_password: ''
})

const switchTab = (tab: string) => {
  activeTab.value = tab
  error.value = ''
  success.value = ''
}

const handleLogin = async () => {
  if (!loginForm.identifier || !loginForm.password) {
    error.value = '请输入账号和密码'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/api/users/login/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(loginForm)
    })

    const data = await response.json()

    if (data.code === 200) {
      localStorage.setItem('access_token', data.data.access)
      localStorage.setItem('refresh_token', data.data.refresh)
      localStorage.setItem('user', JSON.stringify(data.data.user))

      success.value = '登录成功，正在进入平台'
      setTimeout(() => {
        isLeaving.value = true
        playCloudTransition(() => {
          router.push('/home')
        })
      }, 500)
    } else {
      error.value = data.message || '登录失败'
    }
  } catch {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  if (!registerForm.username) {
    error.value = '请输入用户名'
    return
  }

  if (!registerForm.password || registerForm.password !== registerForm.confirm_password) {
    error.value = '密码不一致'
    return
  }

  if (registerForm.register_type === 'email' && !registerForm.email) {
    error.value = '请输入邮箱'
    return
  }

  if (registerForm.register_type === 'phone' && !registerForm.phone) {
    error.value = '请输入手机号'
    return
  }

  if (!registerForm.verification_code) {
    error.value = '请输入验证码'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/api/users/register/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(registerForm)
    })

    const data = await response.json()

    if (data.code === 200) {
      success.value = '注册成功，请登录'
      setTimeout(() => {
        switchTab('login')
      }, 1400)
    } else {
      error.value = data.message || '注册失败'
    }
  } catch {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}

const sendCode = async (type: string, isRegister: boolean = false) => {
  let target = ''

  if (isRegister) {
    target = type === 'email' ? registerForm.email : registerForm.phone
  } else {
    target = resetForm.identifier
  }

  if (!target) {
    error.value = '请输入邮箱或手机号'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/api/users/send-code/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ target, send_type: type })
    })

    const data = await response.json()

    if (data.code === 200) {
      success.value = '验证码已发送'
      console.log('验证码:', data.data.verification_code)
    } else {
      error.value = data.message || '发送失败'
    }
  } catch {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}

const handleResetPassword = async () => {
  if (!resetForm.identifier || !resetForm.verification_code || !resetForm.new_password) {
    error.value = '请填写完整信息'
    return
  }

  if (resetForm.new_password !== resetForm.confirm_password) {
    error.value = '密码不一致'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/api/users/reset-password/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(resetForm)
    })

    const data = await response.json()

    if (data.code === 200) {
      success.value = '密码重置成功，请登录'
      setTimeout(() => {
        switchTab('login')
      }, 1400)
    } else {
      error.value = data.message || '重置失败'
    }
  } catch {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="auth-shell" :class="{ 'is-leaving': isLeaving }">
    <div class="ambient-layer" aria-hidden="true">
      <div class="mesh mesh-a" />
      <div class="mesh mesh-b" />
      <img :src="forestBg" class="forest-ground" alt="" />
      <img :src="vineSvg" class="vine vine-left" alt="" />
      <img :src="vineSvg" class="vine vine-right" alt="" />
    </div>

    <div class="auth-layout">
      <aside class="story-panel">
        <p class="story-kicker">AI Interview Studio</p>
        <h1>在进入面试之前，先进入状态。</h1>
        <p>
          这不是一个普通登录页。它是你与平台能力体系建立连接的第一步，
          也是从被动刷题转向主动训练的开始。
        </p>

        <div class="story-tags">
          <span>技术维度诊断</span>
          <span>表达能力评估</span>
          <span>7日路径生成</span>
        </div>
      </aside>

      <main class="panel-card">
        <header class="panel-head">
          <p>欢迎回来</p>
          <h2>账户中心</h2>
        </header>

        <nav class="mode-tabs" aria-label="认证模式切换">
          <button
            type="button"
            :class="['mode-tab', { active: activeTab === 'login' }]"
            @click="switchTab('login')"
          >
            登录
          </button>
          <button
            type="button"
            :class="['mode-tab', { active: activeTab === 'register' }]"
            @click="switchTab('register')"
          >
            注册
          </button>
          <button
            type="button"
            :class="['mode-tab', { active: activeTab === 'reset' }]"
            @click="switchTab('reset')"
          >
            找回密码
          </button>
        </nav>

        <p v-if="error" class="notice notice-error">{{ error }}</p>
        <p v-if="success" class="notice notice-success">{{ success }}</p>

        <form v-if="activeTab === 'login'" class="auth-form" @submit.prevent="handleLogin">
          <div class="switch-row">
            <button
              type="button"
              :class="['switch-chip', { active: loginForm.login_type === 'email' }]"
              @click="loginForm.login_type = 'email'"
            >
              邮箱登录
            </button>
            <button
              type="button"
              :class="['switch-chip', { active: loginForm.login_type === 'phone' }]"
              @click="loginForm.login_type = 'phone'"
            >
              手机号登录
            </button>
          </div>

          <label class="field">
            <span>{{ loginForm.login_type === 'email' ? '邮箱地址' : '手机号' }}</span>
            <input
              :type="loginForm.login_type === 'email' ? 'email' : 'tel'"
              v-model="loginForm.identifier"
              :placeholder="loginForm.login_type === 'email' ? 'name@example.com' : '请输入手机号'"
            />
          </label>

          <label class="field">
            <span>密码</span>
            <input type="password" v-model="loginForm.password" placeholder="请输入密码" />
          </label>

          <div class="inline-link-row">
            <button type="button" class="link-btn" @click="switchTab('reset')">忘记密码？</button>
          </div>

          <button type="submit" class="primary-btn" :disabled="loading">
            {{ loading ? '登录中...' : '进入平台' }}
          </button>

          <p class="hint-row">
            还没有账号？
            <button type="button" class="link-btn" @click="switchTab('register')">立即创建</button>
          </p>
        </form>

        <form v-if="activeTab === 'register'" class="auth-form" @submit.prevent="handleRegister">
          <div class="switch-row">
            <button
              type="button"
              :class="['switch-chip', { active: registerForm.register_type === 'email' }]"
              @click="registerForm.register_type = 'email'"
            >
              邮箱注册
            </button>
            <button
              type="button"
              :class="['switch-chip', { active: registerForm.register_type === 'phone' }]"
              @click="registerForm.register_type = 'phone'"
            >
              手机号注册
            </button>
          </div>

          <label class="field">
            <span>用户名</span>
            <input type="text" v-model="registerForm.username" placeholder="请输入用户名" />
          </label>

          <label class="field" v-if="registerForm.register_type === 'email'">
            <span>邮箱地址</span>
            <input type="email" v-model="registerForm.email" placeholder="name@example.com" />
          </label>

          <label class="field" v-else>
            <span>手机号</span>
            <input type="tel" v-model="registerForm.phone" placeholder="请输入手机号" />
          </label>

          <label class="field">
            <span>登录密码</span>
            <input type="password" v-model="registerForm.password" placeholder="请输入密码" />
          </label>

          <label class="field">
            <span>确认密码</span>
            <input type="password" v-model="registerForm.confirm_password" placeholder="请再次输入密码" />
          </label>

          <div class="field-inline">
            <label class="field">
              <span>验证码</span>
              <input type="text" v-model="registerForm.verification_code" placeholder="请输入验证码" />
            </label>
            <button
              type="button"
              class="ghost-btn"
              @click="sendCode(registerForm.register_type, true)"
              :disabled="loading"
            >
              发送验证码
            </button>
          </div>

          <button type="submit" class="primary-btn" :disabled="loading">
            {{ loading ? '注册中...' : '创建账号' }}
          </button>

          <p class="hint-row">
            已有账号？
            <button type="button" class="link-btn" @click="switchTab('login')">返回登录</button>
          </p>
        </form>

        <form v-if="activeTab === 'reset'" class="auth-form" @submit.prevent="handleResetPassword">
          <div class="switch-row">
            <button
              type="button"
              :class="['switch-chip', { active: resetForm.reset_type === 'email' }]"
              @click="resetForm.reset_type = 'email'"
            >
              邮箱找回
            </button>
            <button
              type="button"
              :class="['switch-chip', { active: resetForm.reset_type === 'phone' }]"
              @click="resetForm.reset_type = 'phone'"
            >
              手机号找回
            </button>
          </div>

          <label class="field">
            <span>{{ resetForm.reset_type === 'email' ? '邮箱地址' : '手机号' }}</span>
            <input
              :type="resetForm.reset_type === 'email' ? 'email' : 'tel'"
              v-model="resetForm.identifier"
              :placeholder="resetForm.reset_type === 'email' ? 'name@example.com' : '请输入手机号'"
            />
          </label>

          <div class="field-inline">
            <label class="field">
              <span>验证码</span>
              <input type="text" v-model="resetForm.verification_code" placeholder="请输入验证码" />
            </label>
            <button
              type="button"
              class="ghost-btn"
              @click="sendCode(resetForm.reset_type, false)"
              :disabled="loading"
            >
              发送验证码
            </button>
          </div>

          <label class="field">
            <span>新密码</span>
            <input type="password" v-model="resetForm.new_password" placeholder="请输入新密码" />
          </label>

          <label class="field">
            <span>确认新密码</span>
            <input type="password" v-model="resetForm.confirm_password" placeholder="请确认新密码" />
          </label>

          <button type="submit" class="primary-btn" :disabled="loading">
            {{ loading ? '重置中...' : '重置密码' }}
          </button>

          <p class="hint-row">
            记起密码了？
            <button type="button" class="link-btn" @click="switchTab('login')">返回登录</button>
          </p>
        </form>
      </main>
    </div>
  </section>
</template>

<style scoped>
.auth-shell {
  --brand-900: #1c3530;
  --brand-800: #234741;
  --brand-700: #2f5d56;
  --brand-600: #3d746b;
  --ink-900: #1f2926;
  --ink-700: #4e5e58;
  --ink-600: #62726c;
  --line: #c9ddd6;
  --mist: #eef5f1;
  --paper: rgba(255, 255, 255, 0.92);
  --warn: #bf4f4a;
  --ok: #2b7e64;

  min-height: 100vh;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  overflow: hidden;
  color: var(--ink-900);
  font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Source Han Sans SC', sans-serif;
  opacity: 0;
  animation: panel-enter 0.9s cubic-bezier(0.19, 1, 0.22, 1) forwards;
}

@keyframes panel-enter {
  0% {
    opacity: 0;
    transform: translateY(40px) scale(0.98);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.auth-shell.is-leaving {
  animation: panel-leave 0.7s cubic-bezier(0.32, 0, 0.67, 0) forwards;
  pointer-events: none;
}

@keyframes panel-leave {
  0% {
    opacity: 1;
    transform: translateY(0) scale(1);
    filter: blur(0);
  }
  100% {
    opacity: 0;
    transform: translateY(-12vh) scale(0.97);
    filter: blur(10px);
  }
}

.ambient-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.mesh {
  position: absolute;
  border-radius: 50%;
  filter: blur(6px);
}

.mesh-a {
  width: 58vw;
  height: 58vw;
  top: -28vw;
  left: -12vw;
  background: radial-gradient(circle, rgba(61, 116, 107, 0.23), rgba(61, 116, 107, 0));
}

.mesh-b {
  width: 52vw;
  height: 52vw;
  right: -16vw;
  bottom: -24vw;
  background: radial-gradient(circle, rgba(47, 93, 86, 0.18), rgba(47, 93, 86, 0));
}

.forest-ground {
  position: absolute;
  left: 0;
  bottom: -1px;
  width: 100%;
  opacity: 0.64;
  filter: saturate(1.1);
}

.vine {
  position: absolute;
  width: min(28vw, 390px);
  opacity: 0.5;
  top: -1.2rem;
}

.vine-left {
  left: -3rem;
  transform-origin: top left;
  animation: sway-left 6.6s ease-in-out infinite alternate;
}

.vine-right {
  right: -3rem;
  transform-origin: top right;
  transform: scaleX(-1);
  animation: sway-right 7.2s ease-in-out infinite alternate;
}

@keyframes sway-left {
  from { transform: rotate(-3deg); }
  to { transform: rotate(3deg); }
}

@keyframes sway-right {
  from { transform: scaleX(-1) rotate(-2deg); }
  to { transform: scaleX(-1) rotate(4deg); }
}

.auth-layout {
  position: relative;
  z-index: 2;
  width: min(1080px, 100%);
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: linear-gradient(145deg, rgba(249, 253, 251, 0.82), rgba(237, 245, 241, 0.78));
  backdrop-filter: blur(16px);
  border-radius: 26px;
  box-shadow:
    0 26px 60px rgba(31, 41, 38, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.85);
  overflow: hidden;
}

.story-panel {
  padding: clamp(2rem, 3vw, 3rem);
  background:
    linear-gradient(175deg, rgba(28, 53, 48, 0.97), rgba(47, 93, 86, 0.96)),
    repeating-linear-gradient(
      -35deg,
      rgba(255, 255, 255, 0.03) 0,
      rgba(255, 255, 255, 0.03) 14px,
      rgba(255, 255, 255, 0) 14px,
      rgba(255, 255, 255, 0) 28px
    );
  color: #f1faf6;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 1.2rem;
}

.story-kicker {
  margin: 0;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 0.78rem;
  opacity: 0.84;
}

.story-panel h1 {
  margin: 0;
  font-family: 'STSong', 'Songti SC', 'Noto Serif SC', serif;
  font-size: clamp(1.75rem, 2.7vw, 2.35rem);
  line-height: 1.22;
  letter-spacing: 0.02em;
}

.story-panel > p {
  margin: 0;
  color: rgba(241, 250, 246, 0.88);
  line-height: 1.75;
  font-size: 0.98rem;
}

.story-tags {
  margin-top: 0.6rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.story-tags span {
  display: inline-flex;
  padding: 0.42rem 0.8rem;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.26);
  background: rgba(255, 255, 255, 0.1);
  font-size: 0.78rem;
  letter-spacing: 0.04em;
}

.panel-card {
  padding: clamp(1.4rem, 2vw, 2rem);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-head p {
  margin: 0;
  color: var(--ink-600);
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.panel-head h2 {
  margin: 0.25rem 0 0;
  color: var(--brand-900);
  font-family: 'STSong', 'Songti SC', 'Noto Serif SC', serif;
  font-size: 1.7rem;
  letter-spacing: 0.03em;
}

.mode-tabs {
  position: relative;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.45rem;
  padding: 0.45rem;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: linear-gradient(180deg, #f7fbf9, #edf5f1);
}

.mode-tab {
  border: 0;
  background: transparent;
  border-radius: 10px;
  padding: 0.58rem 0.3rem;
  color: var(--ink-700);
  font-size: 0.86rem;
  font-weight: 700;
  transition: all 0.25s ease;
}

.mode-tab:hover {
  color: var(--brand-700);
}

.mode-tab.active {
  background: linear-gradient(145deg, var(--brand-700), var(--brand-600));
  color: #fff;
  box-shadow: 0 10px 18px rgba(47, 93, 86, 0.25);
}

.notice {
  margin: 0;
  border-radius: 12px;
  padding: 0.62rem 0.78rem;
  font-size: 0.88rem;
  border: 1px solid;
}

.notice-error {
  color: #8f3430;
  border-color: #f0c6c4;
  background: #fff3f2;
}

.notice-success {
  color: #1e6f55;
  border-color: #b9dfcf;
  background: #ecfaf3;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.switch-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.55rem;
}

.switch-chip {
  border: 1px solid var(--line);
  background: #f8fbf9;
  color: var(--ink-700);
  border-radius: 10px;
  padding: 0.55rem 0.68rem;
  font-size: 0.82rem;
  font-weight: 700;
  transition: all 0.2s ease;
}

.switch-chip:hover {
  border-color: #a9c9bf;
}

.switch-chip.active {
  border-color: var(--brand-700);
  color: var(--brand-700);
  background: #edf6f2;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.42rem;
}

.field > span {
  font-size: 0.84rem;
  color: var(--ink-700);
}

.field input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.7rem 0.82rem;
  font-size: 0.94rem;
  color: var(--ink-900);
  background: rgba(255, 255, 255, 0.9);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.field input:focus {
  outline: 0;
  border-color: var(--brand-600);
  box-shadow: 0 0 0 4px rgba(61, 116, 107, 0.15);
}

.field-inline {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.55rem;
  align-items: end;
}

.primary-btn,
.ghost-btn {
  border-radius: 12px;
  font-weight: 700;
  font-size: 0.9rem;
  transition: transform 0.22s ease, box-shadow 0.22s ease, opacity 0.22s ease;
}

.primary-btn {
  border: 0;
  padding: 0.78rem 1rem;
  color: #fff;
  background: linear-gradient(145deg, var(--brand-700), var(--brand-600));
  box-shadow: 0 12px 24px rgba(47, 93, 86, 0.26);
}

.primary-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.ghost-btn {
  border: 1px solid #9ebeb4;
  background: #f4fbf8;
  color: var(--brand-800);
  padding: 0.72rem 0.92rem;
  white-space: nowrap;
}

.ghost-btn:hover:not(:disabled) {
  border-color: var(--brand-700);
}

.primary-btn:disabled,
.ghost-btn:disabled {
  opacity: 0.56;
  cursor: not-allowed;
}

.inline-link-row,
.hint-row {
  margin: 0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.28rem;
  color: var(--ink-600);
  font-size: 0.83rem;
}

.hint-row {
  justify-content: center;
}

.link-btn {
  border: 0;
  background: transparent;
  color: var(--brand-700);
  font-weight: 700;
  padding: 0;
}

.link-btn:hover {
  text-decoration: underline;
}

@media (max-width: 980px) {
  .auth-layout {
    grid-template-columns: 1fr;
    max-width: 620px;
  }

  .story-panel {
    border-bottom: 1px solid rgba(255, 255, 255, 0.18);
    padding-bottom: 1.5rem;
  }
}

@media (max-width: 640px) {
  .auth-shell {
    padding: 0.9rem;
  }

  .panel-card {
    padding: 1rem;
  }

  .mode-tab {
    font-size: 0.78rem;
    padding: 0.55rem 0.2rem;
  }

  .field-inline {
    grid-template-columns: 1fr;
  }

  .vine {
    opacity: 0.3;
  }
}
</style>
