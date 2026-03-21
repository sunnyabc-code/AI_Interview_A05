<template>
  <div class="loading-page">
    <div class="inner">
      <van-loading type="spinner" size="48px" color="#1989fa" vertical>
        {{ message }}
      </van-loading>
      <p class="sub">{{ sub }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const message = computed(() => (route.query.msg as string) || '加载中');
const sub = computed(() => (route.query.sub as string) || '请稍候');
</script>

<style scoped>
.loading-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #f0f4ff 0%, #f7f8fa 45%, #ffffff 100%);
}
.inner {
  text-align: center;
  padding: 32px;
}
.sub {
  margin-top: 16px;
  font-size: 14px;
  color: #969799;
}
</style>
