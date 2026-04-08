<script setup lang="ts">
import { computed, ref } from 'vue'
import type { PathwayTask } from '../types'

const props = defineProps<{
  tasks: PathwayTask[]
  updating?: boolean
}>()

const emit = defineEmits<{
  complete: [task: PathwayTask, status: 'done' | 'skipped']
}>()

const hoveredKey = ref<string | null>(null)
let hideTimer: ReturnType<typeof setTimeout> | null = null

const clearHideTimer = () => {
  if (!hideTimer) return
  clearTimeout(hideTimer)
  hideTimer = null
}

const openHover = (key: string) => {
  clearHideTimer()
  hoveredKey.value = key
}

const closeHover = (key: string) => {
  clearHideTimer()
  hideTimer = setTimeout(() => {
    if (hoveredKey.value === key) {
      hoveredKey.value = null
    }
  }, 180)
}

const statusLabel = (status?: PathwayTask['status']) => {
  if (status === 'done') return '已完成'
  if (status === 'skipped') return '已跳过'
  return '待完成'
}

const typeLabel = (type: PathwayTask['taskType']) => {
  if (type === 'resource') return '学习'
  if (type === 'question') return '题练'
  if (type === 'practice') return '实战'
  return '复盘'
}

const focusAreaLabel = (focusArea?: string) => {
  if (focusArea === 'technical') return '技术提升'
  if (focusArea === 'scenario') return '场景应答'
  if (focusArea === 'project') return '项目表达'
  if (focusArea === 'expression') return '表达沟通'
  return '通用资料'
}

const resourceTypeLabel = (resourceType?: string) => {
  if (resourceType === 'official') return '官方文档'
  if (resourceType === 'blog') return '深度博客'
  if (resourceType === 'video') return '视频课程'
  if (resourceType === 'mock') return '模拟面试'
  if (resourceType === 'behavioral') return '行为面试'
  if (resourceType === 'communication') return '沟通表达'
  return '精选资料'
}

const linkDomain = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return 'resource'
  }
}

const linkFavicon = (url: string) => {
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(linkDomain(url))}&sz=64`
}

const taskKey = (task: PathwayTask, index: number) => `${task.id ?? 'x'}-${task.dayIndex}-${index}`

const canOperate = (task: PathwayTask) => task.status !== 'done' && task.status !== 'skipped'

const dayBuckets = computed(() => {
  const map = new Map<number, PathwayTask[]>()
  for (const task of props.tasks) {
    const existing = map.get(task.dayIndex) || []
    existing.push(task)
    map.set(task.dayIndex, existing)
  }

  const maxDay = Math.max(7, ...Array.from(map.keys()), 0)
  const list: Array<{ day: number; tasks: PathwayTask[] }> = []
  for (let day = 1; day <= maxDay; day += 1) {
    const tasks = (map.get(day) || []).slice().sort((a, b) => (a.priority || 9) - (b.priority || 9))
    list.push({ day, tasks })
  }
  return list
})
</script>

<template>
  <section class="route-wrap">
    <div class="spark spark-a" />
    <div class="spark spark-b" />
    <div class="spark spark-c" />
    <div class="route-line" />
    <article
      v-for="(node, index) in dayBuckets"
      :key="node.day"
      :class="['day-node', index % 2 === 0 ? 'left' : 'right']"
      :style="{ animationDelay: `${index * 90}ms` }"
    >
      <div class="station">
        <span class="day-badge">第 {{ node.day }} 天</span>
        <span class="station-type" v-if="node.tasks[0]">{{ typeLabel(node.tasks[0].taskType) }}</span>
      </div>

      <div class="task-cloud" v-if="node.tasks.length">
        <div
          v-for="(task, taskIndex) in node.tasks"
          :key="taskKey(task, taskIndex)"
          :class="['task-pill', task.status || 'pending']"
          @mouseenter="openHover(taskKey(task, taskIndex))"
          @mouseleave="closeHover(taskKey(task, taskIndex))"
        >
          <span class="pill-title">{{ task.title }}</span>
          <span class="pill-meta">{{ typeLabel(task.taskType) }} · {{ task.estimatedMinutes }} 分钟 · {{ statusLabel(task.status) }}</span>

          <div v-if="task.recommendedLinks && task.recommendedLinks.length" class="resource-board">
            <p class="resource-board-title">推荐资料</p>
            <a
              v-for="link in task.recommendedLinks"
              :key="link.id"
              :href="link.url"
              class="resource-card"
              target="_blank"
              rel="noopener noreferrer"
            >
              <div :class="['resource-cover', `focus-${link.focusArea || 'general'}`]">
                <img :src="linkFavicon(link.url)" alt="站点图标" class="resource-favicon" />
                <span class="resource-focus">{{ focusAreaLabel(link.focusArea) }}</span>
              </div>
              <div class="resource-content">
                <strong>{{ link.title }}</strong>
                <span>{{ resourceTypeLabel(link.resourceType) }} · {{ linkDomain(link.url) }}</span>
              </div>
            </a>
          </div>

          <div
            v-if="hoveredKey === taskKey(task, taskIndex)"
            class="hover-panel"
            @mouseenter="openHover(taskKey(task, taskIndex))"
            @mouseleave="closeHover(taskKey(task, taskIndex))"
          >
            <p class="hover-reason">{{ task.reason }}</p>
            <div class="hover-actions" v-if="canOperate(task)">
              <button type="button" :disabled="updating" @click="emit('complete', task, 'done')">标记完成</button>
              <button type="button" :disabled="updating" class="ghost" @click="emit('complete', task, 'skipped')">标记跳过</button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty-day">今日未安排任务</div>
    </article>
  </section>
</template>

<style scoped>
.route-wrap {
  position: relative;
  display: grid;
  gap: 0.85rem;
  padding: 0.9rem 0.55rem;
  border-radius: 18px;
  border: 1px solid #f5d0a9;
  background:
    radial-gradient(circle at 10% 15%, rgba(254, 243, 199, 0.8) 0, transparent 18%),
    radial-gradient(circle at 88% 8%, rgba(253, 230, 138, 0.8) 0, transparent 22%),
    linear-gradient(180deg, #fffdf6 0%, #fff7e6 100%);
  overflow: visible;
}

.route-line {
  position: absolute;
  left: 50%;
  top: 0.5rem;
  bottom: 0.5rem;
  width: 10px;
  transform: translateX(-50%);
  border-radius: 999px;
  background: repeating-linear-gradient(
    180deg,
    #f59e0b 0,
    #f59e0b 10px,
    #fbbf24 10px,
    #fbbf24 20px
  );
  opacity: 0.45;
}

.day-node {
  position: relative;
  z-index: 1;
  width: calc(50% - 22px);
  padding: 0.64rem;
  border-radius: 18px;
  border: 1px solid #eab308;
  background: linear-gradient(145deg, #fffef8 0%, #fff5dc 100%);
  box-shadow: 0 10px 22px rgba(180, 83, 9, 0.14);
  animation: floatIn 0.45s ease both;
}

.day-node:hover {
  z-index: 40;
}

.day-node.left {
  margin-right: auto;
}

.day-node.right {
  margin-left: auto;
}

.station {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.day-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid #fdba74;
  background: #ffedd5;
  color: #9a3412;
  font-size: 0.78rem;
  padding: 0.14rem 0.56rem;
}

.station-type {
  border-radius: 999px;
  border: 1px solid #f59e0b;
  background: #fef3c7;
  color: #92400e;
  font-size: 0.72rem;
  padding: 0.12rem 0.45rem;
}

.task-cloud {
  display: grid;
  gap: 0.4rem;
}

.task-pill {
  position: relative;
  z-index: 1;
  border-radius: 12px;
  border: 1px solid #fcd34d;
  background: #fffdf7;
  padding: 0.48rem 0.55rem;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.task-pill:hover {
  z-index: 60;
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(146, 64, 14, 0.18);
}

.task-pill.done {
  border-color: #86efac;
  background: #f0fdf4;
}

.task-pill.skipped {
  border-color: #fdba74;
  background: #fff7ed;
}

.pill-title {
  display: block;
  color: #7c2d12;
  font-size: 0.86rem;
  font-weight: 600;
}

.pill-meta {
  display: block;
  margin-top: 0.16rem;
  color: #9a3412;
  font-size: 0.75rem;
}

.resource-board {
  margin-top: 0.5rem;
  display: grid;
  gap: 0.42rem;
}

.resource-board-title {
  margin: 0;
  color: #b45309;
  font-size: 0.74rem;
  font-weight: 700;
}

.resource-card {
  display: grid;
  grid-template-columns: 96px 1fr;
  text-decoration: none;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.resource-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 16px rgba(194, 65, 12, 0.18);
}

.resource-cover {
  position: relative;
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, #fed7aa, #fdba74);
}

.resource-cover.focus-technical {
  background: linear-gradient(145deg, #bfdbfe, #60a5fa);
}

.resource-cover.focus-scenario {
  background: linear-gradient(145deg, #fde68a, #f59e0b);
}

.resource-cover.focus-project {
  background: linear-gradient(145deg, #fecdd3, #f472b6);
}

.resource-cover.focus-expression {
  background: linear-gradient(145deg, #c4b5fd, #8b5cf6);
}

.resource-favicon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  padding: 2px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.2);
}

.resource-focus {
  position: absolute;
  left: 6px;
  right: 6px;
  bottom: 6px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.32);
  color: #fff;
  text-align: center;
  font-size: 0.66rem;
  padding: 0.1rem 0.25rem;
}

.resource-content {
  padding: 0.4rem 0.5rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.18rem;
}

.resource-content strong {
  color: #7c2d12;
  font-size: 0.78rem;
  line-height: 1.35;
}

.resource-content span {
  color: #9a3412;
  font-size: 0.72rem;
}

.hover-panel {
  position: absolute;
  z-index: 1000;
  top: 0;
  left: calc(100% + 10px);
  width: min(320px, 86vw);
  border-radius: 12px;
  border: 1px solid #fdba74;
  background: #fff8e1;
  box-shadow: 0 16px 32px rgba(124, 45, 18, 0.24);
  padding: 0.56rem;
}

.day-node.right .hover-panel {
  left: auto;
  right: calc(100% + 10px);
}

.hover-reason {
  margin: 0;
  color: #7c2d12;
  font-size: 0.79rem;
  line-height: 1.5;
}

.hover-actions {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.45rem;
}

.hover-actions button {
  border: none;
  border-radius: 8px;
  background: #ea580c;
  color: #fff;
  font-size: 0.75rem;
  padding: 0.24rem 0.54rem;
  cursor: pointer;
}

.hover-actions button.ghost {
  background: #fde68a;
  color: #92400e;
}

.empty-day {
  color: #a16207;
  font-size: 0.8rem;
}

.spark {
  position: absolute;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: radial-gradient(circle, #fde68a 0%, rgba(253, 230, 138, 0) 70%);
  opacity: 0.7;
  animation: twinkle 2.8s ease-in-out infinite;
}

.spark-a {
  top: 10px;
  left: 24px;
}

.spark-b {
  top: 52px;
  right: 28px;
  animation-delay: 0.9s;
}

.spark-c {
  bottom: 28px;
  left: 44%;
  animation-delay: 1.6s;
}

@keyframes floatIn {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes twinkle {
  0%,
  100% {
    transform: scale(0.9);
    opacity: 0.4;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.85;
  }
}

@media (max-width: 900px) {
  .route-line {
    left: 12px;
    transform: none;
  }

  .day-node,
  .day-node.left,
  .day-node.right {
    width: calc(100% - 20px);
    margin-left: 20px;
    margin-right: 0;
  }

  .hover-panel,
  .day-node.right .hover-panel {
    left: 0;
    right: auto;
    top: calc(100% + 8px);
  }
}
</style>
