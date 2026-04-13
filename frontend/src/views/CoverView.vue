<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import forestBg from '@/assets/images/forest-bg.svg'
import vineSvg from '@/assets/images/vine.svg'

const router = useRouter()

const mainText = "欢迎来到AI面试模拟系统"
const textChars = mainText.split('')
const showLoading = ref(false)
const isLeaving = ref(false)

// 为每个文字生成随机的发散坐标和浮动延迟，模拟粒子汇聚
const particleStyles = textChars.map((_, i) => ({
  '--rx': `${(Math.random() - 0.5) * 300}px`,
  '--ry': `${(Math.random() - 0.5) * 300}px`,
  '--delay': `${Math.random() * 0.6}s`,
  '--i': i
}))

onMounted(() => {
  // 1. 等待粒子文字汇聚 (约需2.2秒)
  setTimeout(() => {
    showLoading.value = true
  }, 2200)

  // 2. 触发退场动画（上划）
  setTimeout(() => {
    isLeaving.value = true
  }, 4500)

  // 3. 跳转登录页面 (等退场上划动画0.6s执行完毕后)
  setTimeout(() => {
    router.push('/auth')
  }, 5100)
})
</script>

<template>
  <!-- 动态添加 is-leaving 类控制上划退出 -->
  <div class="cover-container" :class="{ 'is-leaving': isLeaving }" :style="{ backgroundImage: `url(${forestBg})` }">
    
    <!-- 浅绿色质感光晕遮罩，保证文字清晰度 -->
    <div class="light-overlay"></div>

    <!-- 顶部摇摆的藤蔓装饰 -->
    <img :src="vineSvg" class="vine vine-left" alt="装饰藤蔓" />
    <img :src="vineSvg" class="vine vine-right" alt="装饰藤蔓" />
    <img :src="vineSvg" class="vine vine-far-right" alt="装饰藤蔓" />

    <!-- 主容器，完全居中，无背景色块 -->
    <div class="cover-content">
      <!-- 粒子汇聚文字效果 -->
      <h1 class="particle-title">
        <span 
          v-for="(char, i) in textChars" 
          :key="i"
          class="particle-char"
          :style="particleStyles[i]"
        >
          {{ char }}
        </span>
      </h1>

      <!-- 初始化与优雅的高级加载层 -->
      <div class="ai-loading-wrapper" :class="{ 'is-visible': showLoading }">
        <p class="loading-sub">智能面试系统正在初始化...</p>
        
        <!-- 更好看的带光晕和拖尾的进度条 -->
        <div class="progress-bar-glass">
          <div class="progress-track">
            <div class="progress-fill">
              <div class="progress-glow"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cover-container {
  width: 100vw;
  height: 100vh;
  position: relative;
  overflow: hidden;
  font-family: 'Inter', system-ui, sans-serif;
  background-color: #f3f8f5;
  background-size: cover;
  background-position: center bottom;
  background-repeat: no-repeat;
  transition: transform 0.6s cubic-bezier(0.65, 0, 0.35, 1), opacity 0.6s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 离场上滑动画 */
.cover-container.is-leaving {
  transform: translateY(-100vh);
  opacity: 0.8;
}

/* 柔和的环境光晕遮罩 */
.light-overlay {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.7) 0%, rgba(220, 234, 226, 0.5) 60%, rgba(47, 93, 86, 0.2) 100%);
  z-index: 2;
  pointer-events: none;
}

/* --- 藤蔓动效 --- */
.vine {
  position: absolute;
  top: -20px;
  width: 100px;
  height: auto;
  z-index: 3;
  transform-origin: top center;
  filter: drop-shadow(0 15px 15px rgba(31, 41, 38, 0.3));
}

.vine-left {
  left: 8%;
  transform: scale(1.2);
  animation: sway 7s ease-in-out infinite;
}

.vine-right {
  right: 15%;
  transform: scale(0.9) rotate(-10deg);
  animation: sway 9s ease-in-out infinite alternate;
}

.vine-far-right {
  right: -2%;
  top: -10px;
  transform: scale(1.4) rotate(5deg);
  animation: sway 6s ease-in-out infinite alternate-reverse;
  filter: blur(3px); /* 景深效果 */
}

@keyframes sway {
  0% { transform: rotate(-5deg) scale(var(--scale, 1.2)); }
  50% { transform: rotate(5deg) scale(var(--scale, 1.2)); }
  100% { transform: rotate(-5deg) scale(var(--scale, 1.2)); }
}

/* 主内容区，完全居中，无背景色块 */
.cover-content {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  width: 100%;
}

/* --- 文字粒子动画核心 --- */
.particle-title {
  margin: 0 0 2rem 0;
  font-weight: 800;
  font-size: 2.8rem;
  color: #1f3d38; /* 更深的墨绿色，保证可读性 */
  letter-spacing: 0.05em;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 2px;
  text-shadow: 0 8px 20px rgba(31, 41, 38, 0.1);
}

.particle-char {
  display: inline-block;
  opacity: 0;
  transform: translate(var(--rx), var(--ry)) scale(3) rotate(15deg);
  filter: blur(15px);
  animation: particleAssemble 1.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
  animation-delay: var(--delay);
}

@keyframes particleAssemble {
  0% {
    opacity: 0;
    transform: translate(var(--rx), var(--ry)) scale(2.5) rotate(15deg);
    filter: blur(15px);
  }
  60% {
    opacity: 0.9;
    transform: translate(0, -10px) scale(1.05) rotate(0);
    filter: blur(2px);
  }
  100% {
    opacity: 1;
    transform: translate(0, 0) scale(1) rotate(0);
    filter: blur(0);
  }
}

/* --- 高级版加载与进度条 --- */
.ai-loading-wrapper {
  opacity: 0;
  transform: translateY(30px) scale(0.95);
  transition: all 1s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 1rem;
}

.ai-loading-wrapper.is-visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.loading-sub {
  font-size: 0.95rem;
  color: #3f655f;
  font-weight: 600;
  letter-spacing: 0.3em;
  margin-bottom: 1.2rem;
  text-transform: uppercase;
}

/* 玻璃质感条基座 */
.progress-bar-glass {
  width: 300px;
  height: 8px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 8px;
  padding: 2px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1), 0 4px 10px rgba(47, 93, 86, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

/* 内轨道 */
.progress-track {
  width: 100%;
  height: 100%;
  background: rgba(47, 93, 86, 0.1);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

/* 流畅的填充色 */
.progress-fill {
  height: 100%;
  width: 0%;
  border-radius: 6px;
  background: linear-gradient(90deg, #2f5d56 0%, #4f857a 50%, #6bc1af 100%);
  position: relative;
  /* 此处时间匹配剩余等待时间（约 2.3s） */
  animation: loadProgress 2.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

/* 头部发光球，增强视觉焦点 */
.progress-glow {
  position: absolute;
  right: -4px;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 0 10px #6bc1af, 0 0 20px #4f857a;
}

@keyframes loadProgress {
  0% { width: 0%; }
  30% { width: 45%; }
  70% { width: 80%; }
  100% { width: 100%; }
}
</style>
