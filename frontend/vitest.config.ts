import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    // jsdom 模拟浏览器环境
    environment: 'jsdom',
    // 全局变量（无需每个文件 import describe/it/expect）
    globals: true,
    // 测试文件匹配模式
    include: ['src/**/*.{test,spec}.{ts,js}'],
    // 覆盖率配置
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,vue}'],
      exclude: [
        'src/main.ts',
        'src/**/*.d.ts',
        'node_modules/',
      ],
    },
  },
})
