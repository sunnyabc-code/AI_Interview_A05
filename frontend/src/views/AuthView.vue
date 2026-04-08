<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const activeTab = ref('login')
const loading = ref(false)
const error = ref('')
const success = ref('')

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

const API_BASE_URL = 'http://localhost:8000'

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
      
      success.value = '登录成功'
      setTimeout(() => {
        router.push('/home')
      }, 1000)
    } else {
      error.value = data.message || '登录失败'
    }
  } catch (err) {
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
      }, 1500)
    } else {
      error.value = data.message || '注册失败'
    }
  } catch (err) {
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
    target = type === 'email' ? resetForm.identifier : resetForm.identifier
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
  } catch (err) {
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
      }, 1500)
    } else {
      error.value = data.message || '重置失败'
    }
  } catch (err) {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-tabs">
        <button 
          :class="['auth-tab', { active: activeTab === 'login' }]"
          @click="switchTab('login')"
        >
          登录
        </button>
        <button 
          :class="['auth-tab', { active: activeTab === 'register' }]"
          @click="switchTab('register')"
        >
          注册
        </button>
        <button 
          :class="['auth-tab', { active: activeTab === 'reset' }]"
          @click="switchTab('reset')"
        >
          找回密码
        </button>
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      <div v-if="success" class="success-message">
        {{ success }}
      </div>

      <form v-if="activeTab === 'login'" class="auth-form" @submit.prevent="handleLogin">
        <h2>登录</h2>
        
        <div class="login-type-selector">
          <button 
            :class="['type-btn', { active: loginForm.login_type === 'email' }]"
            @click="loginForm.login_type = 'email'"
          >
            邮箱登录
          </button>
          <button 
            :class="['type-btn', { active: loginForm.login_type === 'phone' }]"
            @click="loginForm.login_type = 'phone'"
          >
            手机号登录
          </button>
        </div>

        <div class="form-group">
          <label :for="loginForm.login_type === 'email' ? 'email' : 'phone'">
            {{ loginForm.login_type === 'email' ? '邮箱' : '手机号' }}
          </label>
          <input 
            :type="loginForm.login_type === 'email' ? 'email' : 'tel'"
            :id="loginForm.login_type === 'email' ? 'email' : 'phone'"
            v-model="loginForm.identifier"
            :placeholder="loginForm.login_type === 'email' ? '请输入邮箱' : '请输入手机号'"
          />
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input 
            type="password" 
            id="password" 
            v-model="loginForm.password"
            placeholder="请输入密码"
          />
        </div>

        <button 
          type="submit"
          class="auth-btn" 
          :disabled="loading"
        >
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <div v-if="activeTab === 'register'" class="auth-form">
        <h2>注册</h2>
        
        <div class="login-type-selector">
          <button 
            :class="['type-btn', { active: registerForm.register_type === 'email' }]"
            @click="registerForm.register_type = 'email'"
          >
            邮箱注册
          </button>
          <button 
            :class="['type-btn', { active: registerForm.register_type === 'phone' }]"
            @click="registerForm.register_type = 'phone'"
          >
            手机号注册
          </button>
        </div>

        <div class="form-group">
          <label for="username">用户名</label>
          <input 
            type="text" 
            id="username" 
            v-model="registerForm.username"
            placeholder="请输入用户名"
          />
        </div>

        <div class="form-group" v-if="registerForm.register_type === 'email'">
          <label for="reg-email">邮箱</label>
          <input 
            type="email" 
            id="reg-email" 
            v-model="registerForm.email"
            placeholder="请输入邮箱"
          />
        </div>

        <div class="form-group" v-if="registerForm.register_type === 'phone'">
          <label for="reg-phone">手机号</label>
          <input 
            type="tel" 
            id="reg-phone" 
            v-model="registerForm.phone"
            placeholder="请输入手机号"
          />
        </div>

        <div class="form-group">
          <label for="reg-password">密码</label>
          <input 
            type="password" 
            id="reg-password" 
            v-model="registerForm.password"
            placeholder="请输入密码"
          />
        </div>

        <div class="form-group">
          <label for="confirm-password">确认密码</label>
          <input 
            type="password" 
            id="confirm-password" 
            v-model="registerForm.confirm_password"
            placeholder="请确认密码"
          />
        </div>

        <div class="form-group">
          <label for="reg-verification-code">验证码</label>
          <div class="code-input-group">
            <input 
              type="text" 
              id="reg-verification-code" 
              v-model="registerForm.verification_code"
              placeholder="请输入验证码"
            />
            <button 
              class="send-code-btn"
              @click="sendCode(registerForm.register_type, true)"
              :disabled="loading"
            >
              发送验证码
            </button>
          </div>
        </div>

        <button 
          class="auth-btn" 
          @click="handleRegister"
          :disabled="loading"
        >
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </div>

      <div v-if="activeTab === 'reset'" class="auth-form">
        <h2>找回密码</h2>
        
        <div class="login-type-selector">
          <button 
            :class="['type-btn', { active: resetForm.reset_type === 'email' }]"
            @click="resetForm.reset_type = 'email'"
          >
            邮箱找回
          </button>
          <button 
            :class="['type-btn', { active: resetForm.reset_type === 'phone' }]"
            @click="resetForm.reset_type = 'phone'"
          >
            手机号找回
          </button>
        </div>

        <div class="form-group">
          <label :for="resetForm.reset_type === 'email' ? 'reset-email' : 'reset-phone'">
            {{ resetForm.reset_type === 'email' ? '邮箱' : '手机号' }}
          </label>
          <input 
            :type="resetForm.reset_type === 'email' ? 'email' : 'tel'"
            :id="resetForm.reset_type === 'email' ? 'reset-email' : 'reset-phone'"
            v-model="resetForm.identifier"
            :placeholder="resetForm.reset_type === 'email' ? '请输入邮箱' : '请输入手机号'"
          />
        </div>

        <div class="form-group">
          <label for="verification-code">验证码</label>
          <div class="code-input-group">
            <input 
              type="text" 
              id="verification-code" 
              v-model="resetForm.verification_code"
              placeholder="请输入验证码"
            />
            <button 
              class="send-code-btn"
              @click="sendCode(resetForm.reset_type, false)"
              :disabled="loading"
            >
              发送验证码
            </button>
          </div>
        </div>

        <div class="form-group">
          <label for="new-password">新密码</label>
          <input 
            type="password" 
            id="new-password" 
            v-model="resetForm.new_password"
            placeholder="请输入新密码"
          />
        </div>

        <div class="form-group">
          <label for="reset-confirm-password">确认新密码</label>
          <input 
            type="password" 
            id="reset-confirm-password" 
            v-model="resetForm.confirm_password"
            placeholder="请确认新密码"
          />
        </div>

        <button 
          class="auth-btn" 
          @click="handleResetPassword"
          :disabled="loading"
        >
          {{ loading ? '重置中...' : '重置密码' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-container {
  width: 100vw;
  height: 100vh;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
}

.auth-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 450px;
  overflow: hidden;
}

.auth-tabs {
  display: flex;
  border-bottom: 1px solid #e0e0e0;
}

.auth-tab {
  flex: 1;
  padding: 1rem;
  background: none;
  border: none;
  font-size: 1rem;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  transition: all 0.3s ease;
}

.auth-tab:hover {
  color: #667eea;
}

.auth-tab.active {
  color: #667eea;
  border-bottom: 2px solid #667eea;
}

.auth-form {
  padding: 2rem;
}

.auth-form h2 {
  text-align: center;
  color: #333;
  margin-bottom: 2rem;
  font-size: 1.5rem;
  font-weight: 600;
}

.login-type-selector {
  display: flex;
  margin-bottom: 1.5rem;
  gap: 1rem;
}

.type-btn {
  flex: 1;
  padding: 0.75rem;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #666;
  cursor: pointer;
  transition: all 0.3s ease;
}

.type-btn:hover {
  background: #e8e8e8;
}

.type-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #666;
  font-weight: 500;
  font-size: 0.9rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.code-input-group {
  display: flex;
  gap: 0.75rem;
}

.code-input-group input {
  flex: 1;
}

.send-code-btn {
  padding: 0 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.send-code-btn:hover {
  background: #764ba2;
}

.send-code-btn:disabled {
  background: #a0a0a0;
  cursor: not-allowed;
}

.auth-btn {
  width: 100%;
  padding: 0.75rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 1rem;
}

.auth-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.auth-btn:disabled {
  background: #a0a0a0;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.error-message {
  background: #fee;
  color: #e74c3c;
  padding: 0.75rem;
  border-radius: 4px;
  margin: 1rem 2rem;
  text-align: center;
  font-size: 0.9rem;
}

.success-message {
  background: #efe;
  color: #27ae60;
  padding: 0.75rem;
  border-radius: 4px;
  margin: 1rem 2rem;
  text-align: center;
  font-size: 0.9rem;
}

@media (max-width: 480px) {
  .auth-card {
    margin: 1rem;
  }
  
  .auth-form {
    padding: 1.5rem;
  }
  
  .login-type-selector {
    flex-direction: column;
  }
  
  .code-input-group {
    flex-direction: column;
  }
  
  .send-code-btn {
    padding: 0.75rem;
  }
}
</style>
