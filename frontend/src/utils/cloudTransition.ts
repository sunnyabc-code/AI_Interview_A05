import { ref } from 'vue'

export const cloudTransitionPhase = ref<'idle' | 'gathering' | 'dispersing'>('idle')

export const playCloudTransition = (callback: () => void) => {
  if (cloudTransitionPhase.value !== 'idle') return

  // 1. 触发两片云从左上和右下向中心聚拢
  cloudTransitionPhase.value = 'gathering'

  // 2. 等待 2 秒（让漫天纯白云慢慢合拢覆盖屏幕）
  setTimeout(() => {
    // 切换实际路由/页面
    callback()
    
    // 3. 开始散开：页面已经切换好，让云雾往外炸开/淡出
    requestAnimationFrame(() => {
      cloudTransitionPhase.value = 'dispersing'
      
      // 4. 等待 2.5 秒散开动画完全结束后，重置整个状态机
      setTimeout(() => {
        cloudTransitionPhase.value = 'idle'
      }, 2500)
    })
  }, 2000)
}

