<script setup lang="ts">
import { cloudTransitionPhase } from '@/utils/cloudTransition'
import cloudSvg from '@/assets/images/cloud.svg'
</script>

<template>
  <div 
    class="cloud-overlay" 
    :class="cloudTransitionPhase"
  >
    <!-- 使用真实的 SVG 云朵，从屏幕对角线移动 -->
    <img :src="cloudSvg" class="cloud-img top-left-cloud" alt="Cloud" />
    <img :src="cloudSvg" class="cloud-img bottom-right-cloud" alt="Cloud" />
    <div class="cloud-flash"></div>
  </div>
</template>

<style scoped>
.cloud-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: none; /* 让所有的点击穿透 */
  overflow: hidden;
  /* 平常不要干扰页面层叠，用 visibility 和 opacity 双轨控制 */
  visibility: hidden;
}

/* 激活时显示并强制层级 */
.cloud-overlay.gathering,
.cloud-overlay.dispersing {
  visibility: visible;
}

.cloud-img {
  position: absolute;
  width: 140vw;
  min-width: 1200px;
  height: auto;
  opacity: 0.95;
  /* 阴影改为极淡的灰色以配合纯白的云，显得更清透 */
  filter: drop-shadow(0 20px 50px rgba(0, 0, 0, 0.08));
  /* 动画放慢为 2 秒，显得更大气 */
  transition: transform 2s cubic-bezier(0.3, 0, 0.2, 1), opacity 1.5s ease;
}

/* 初始状态：停留在屏幕对角外侧 */
.top-left-cloud {
  top: -80vh;
  left: -80vw;
  transform: translate(0, 0) scale(0.9);
}

.bottom-right-cloud {
  bottom: -80vh;
  right: -80vw;
  /* 翻转 180 度，使两片云不对称有相嵌的感觉 */
  transform: translate(0, 0) rotate(180deg) scale(0.9);
}

/* 防止云片拼接有缝隙时的纯白遮罩，在云靠近中心时浮现 */
.cloud-flash {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 1);
  backdrop-filter: blur(20px);
  opacity: 0;
  /* 遮罩白屏浮现也放慢 */
  transition: opacity 0.8s ease 1s;
}

/* --- Gathering 聚集阶段 --- */
/* 左上角往右下角走，右下角往左上角走，聚拢铺满 */
.gathering .top-left-cloud {
  transform: translate(60vw, 60vh) scale(1.2);
}
.gathering .bottom-right-cloud {
  transform: translate(-60vw, -60vh) rotate(180deg) scale(1.2);
}
.gathering .cloud-flash {
  opacity: 1; /* 云聚完完全白屏 */
}

/* --- Dispersing 散开阶段 --- */
/* 继续往前突破散开或者原路退后（这里做成慢速退场效果） */
.dispersing .top-left-cloud {
  transform: translate(-50vw, -50vh) scale(1.9);
  opacity: 0;
  transition: transform 2.5s cubic-bezier(0.1, 0.9, 0.2, 1), opacity 2s ease-out;
}
.dispersing .bottom-right-cloud {
  transform: translate(50vw, 50vh) rotate(180deg) scale(1.9);
  opacity: 0;
  transition: transform 2.5s cubic-bezier(0.1, 0.9, 0.2, 1), opacity 2s ease-out;
}
.dispersing .cloud-flash {
  opacity: 0;
  transition: opacity 1.5s ease 0s;
}
</style>

