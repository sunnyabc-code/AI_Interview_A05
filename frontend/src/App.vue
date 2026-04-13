<script setup lang="ts">
import { RouterView } from 'vue-router'
import CloudTransition from '@/components/CloudTransition.vue'
</script>

<template>
  <RouterView />
  <!-- 全局的云雾过渡动画挂载点 -->
  <CloudTransition />
</template>

<style>
:root {
  --color-primary: #2f5d56;
  --color-secondary: #3f655f;
  --color-text: #1f2926;
  --color-muted: #66756f;
  --color-light: #f3f5f4;
  --color-white: #ffffff;
  --color-line: #dde5e1;
  --shadow-sm: 0 8px 20px rgba(31, 41, 38, 0.06);
  --shadow-md: 0 12px 28px rgba(31, 41, 38, 0.1);
  --border-radius: 12px;
  --transition: color 0.2s ease, background 0.2s ease, border-color 0.2s ease;
}

html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow-x: hidden;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  /* 统一设为浅绿色渐变大圆底或者继承 Auth 的清新底色 */
  background: linear-gradient(180deg, #e8f2ec 0%, #f3f8f5 100%);
  background-attachment: fixed;
  color: var(--color-text);
  min-height: 100vh;
}

a {
  color: var(--color-primary);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
  opacity: 0.92;
}

button {
  cursor: pointer;
  border: none;
  outline: none;
}
</style>
