<template>
  <div class="page">
    <van-nav-bar title="找回密码" left-arrow fixed placeholder @click-left="router.push('/login')" />
    <div class="body">
      <p class="tip">请使用账号已绑定的邮箱或手机号；若注册时未填写，请先在资料中补全或联系管理员。</p>
      <van-radio-group v-model="resetType" direction="horizontal" class="radio">
        <van-radio name="email">邮箱</van-radio>
        <van-radio name="phone">手机号</van-radio>
      </van-radio-group>
      <van-field
        v-model="identifier"
        :label="resetType === 'email' ? '邮箱' : '手机号'"
        :placeholder="resetType === 'email' ? '请输入注册邮箱' : '请输入注册手机号'"
      />
      <div class="code-row">
        <van-field v-model="code" label="验证码" placeholder="6位数字" maxlength="6" />
        <van-button
          size="small"
          type="primary"
          plain
          :disabled="countdown > 0 || sending"
          :loading="sending"
          @click="onSendCode"
        >
          {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
        </van-button>
      </div>
      <van-field v-model="newPassword" type="password" label="新密码" placeholder="至少6位" />
      <van-field v-model="confirmPassword" type="password" label="确认密码" placeholder="再次输入" />
      <van-button type="primary" block round :loading="loading" @click="onSubmit">重置密码</van-button>
      <router-link class="link" to="/login">返回登录</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import { sendVerificationCode, resetPassword } from '@/api';

const router = useRouter();
const resetType = ref<'email' | 'phone'>('email');
const identifier = ref('');
const code = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const loading = ref(false);
const sending = ref(false);
const countdown = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;

onUnmounted(() => {
  if (timer) clearInterval(timer);
});

const onSendCode = async () => {
  let id = identifier.value.trim().replace(/＠/g, '@');
  if (!id) {
    showToast('请先填写邮箱或手机号');
    return;
  }
  if (resetType.value === 'email') {
    if (!id.includes('@')) {
      showToast('请填写完整邮箱（需含 @）；若仅绑定手机请切换到「手机号」');
      return;
    }
  } else {
    const digits = id.replace(/\D/g, '');
    if (digits.length < 11) {
      showToast('请输入11位手机号');
      return;
    }
    id = digits;
  }
  sending.value = true;
  try {
    const res: any = await sendVerificationCode({
      target: id,
      send_type: resetType.value,
      purpose: 'reset',
    });
    const demo = res?.verificationCode;
    if (demo) {
      showToast(`验证码已发送（演示）：${demo}`);
    } else {
      showToast('验证码已发送');
    }
    countdown.value = 60;
    if (timer) clearInterval(timer);
    timer = setInterval(() => {
      countdown.value -= 1;
      if (countdown.value <= 0 && timer) {
        clearInterval(timer);
        timer = null;
      }
    }, 1000);
  } catch {
    /* interceptor */
  } finally {
    sending.value = false;
  }
};

const onSubmit = async () => {
  let id = identifier.value.trim().replace(/＠/g, '@');
  if (!id || !code.value.trim() || !newPassword.value || !confirmPassword.value) {
    showToast('请填写完整信息');
    return;
  }
  if (resetType.value === 'email' && !id.includes('@')) {
    showToast('请填写完整邮箱（需含 @）或切换到「手机号」');
    return;
  }
  if (resetType.value === 'phone') {
    id = id.replace(/\D/g, '');
  }
  if (newPassword.value !== confirmPassword.value) {
    showToast('两次密码不一致');
    return;
  }
  if (newPassword.value.length < 6) {
    showToast('密码至少6位');
    return;
  }
  loading.value = true;
  try {
    await resetPassword({
      identifier: id,
      verification_code: code.value.trim(),
      new_password: newPassword.value,
      confirm_password: confirmPassword.value,
      reset_type: resetType.value,
    });
    showToast('密码重置成功，请登录');
    router.replace('/login');
  } catch {
    /* interceptor */
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f7f8fa;
}
.body {
  padding: 16px 24px 24px;
  max-width: 480px;
  margin: 0 auto;
}
.tip {
  font-size: 13px;
  color: #969799;
  line-height: 1.5;
  margin-bottom: 16px;
}
.radio {
  margin-bottom: 12px;
}
.code-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.code-row :deep(.van-field) {
  flex: 1;
}
.link {
  display: block;
  margin-top: 16px;
  text-align: center;
  color: #1989fa;
}
</style>
