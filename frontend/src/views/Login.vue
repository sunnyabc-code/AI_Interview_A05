<template>
  <div class="page">
    <h2>登录</h2>
    <van-field v-model="username" label="用户名" placeholder="用户名" />
    <van-field v-model="password" type="password" label="密码" placeholder="密码" />
    <van-button type="primary" block round :loading="loading" @click="onLogin">登录</van-button>
    <div class="links">
      <router-link class="link" to="/forgot-password">找回密码</router-link>
      <router-link class="link" to="/register">注册账号</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import { login } from '@/api';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const userStore = useUserStore();
const username = ref('');
const password = ref('');
const loading = ref(false);

const onLogin = async () => {
  if (!username.value || !password.value) {
    showToast('请填写用户名和密码');
    return;
  }
  loading.value = true;
  try {
    const res: any = await login({ username: username.value, password: password.value });
    userStore.setUser({ userId: res.userId, nickname: res.nickname, token: res.token });
    showToast('登录成功');
    router.push('/scenarios');
  } catch {
    /* toast in interceptor */
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.page {
  padding: 24px;
  max-width: 480px;
  margin: 0 auto;
}
.links {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.link {
  display: block;
  text-align: center;
  color: #1989fa;
}
</style>
