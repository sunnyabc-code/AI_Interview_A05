<template>
  <div class="page">
    <h2>注册</h2>
    <van-field v-model="username" label="用户名" placeholder="用户名（登录用）" />
    <van-field v-model="email" label="邮箱" placeholder="可选" />
    <van-field v-model="password" type="password" label="密码" placeholder="至少6位" />
    <van-button type="primary" block round :loading="loading" @click="onReg">注册</van-button>
    <router-link class="link" to="/login">已有账号</router-link>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import { register } from '@/api';

const router = useRouter();
const username = ref('');
const email = ref('');
const password = ref('');
const loading = ref(false);

const onReg = async () => {
  if (!username.value || password.value.length < 6) {
    showToast('用户名与密码（≥6位）必填');
    return;
  }
  loading.value = true;
  try {
    await register({ username: username.value, password: password.value, email: email.value });
    showToast('注册成功，请登录');
    router.push('/login');
  } catch {
    /* handled */
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
.link {
  display: block;
  margin-top: 16px;
  text-align: center;
  color: #1989fa;
}
</style>
