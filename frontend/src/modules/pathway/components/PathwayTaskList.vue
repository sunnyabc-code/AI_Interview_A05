<script setup lang="ts">
import type { PathwayTask } from '../types'

defineProps<{
  tasks: PathwayTask[]
}>()

const emit = defineEmits<{
  complete: [task: PathwayTask, status: 'done' | 'skipped']
}>()

const canOperate = (task: PathwayTask) => task.status !== 'done' && task.status !== 'skipped'

const statusLabel = (status?: PathwayTask['status']) => {
  if (status === 'done') return '已完成'
  if (status === 'skipped') return '已跳过'
  return '待完成'
}
</script>

<template>
  <section class="task-list">
    <article v-for="task in tasks" :key="`${task.dayIndex}-${task.title}`" class="task-item">
      <div class="left">
        <span class="day">第 {{ task.dayIndex }} 天</span>
        <h4>{{ task.title }}</h4>
        <p>{{ task.reason }}</p>
      </div>
      <div class="right">
        <span class="status" :class="task.status">{{ statusLabel(task.status) }}</span>
        <span class="duration">{{ task.estimatedMinutes }} 分钟</span>
        <div class="ops" v-if="canOperate(task)">
          <button type="button" class="done" @click="emit('complete', task, 'done')">完成</button>
          <button type="button" class="skip" @click="emit('complete', task, 'skipped')">跳过</button>
        </div>
      </div>
    </article>
  </section>
</template>

<style scoped>
.task-list {
  display: grid;
  gap: 0.6rem;
}

.task-item {
  border: 1px solid #cce3db;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.95);
  padding: 0.65rem;
  display: flex;
  justify-content: space-between;
  gap: 0.7rem;
}

.day {
  display: inline-block;
  border-radius: 999px;
  border: 1px solid #cce3db;
  color: #2f5d56;
  background: rgba(235, 248, 242, 0.6);
  font-size: 0.75rem;
  padding: 0.08rem 0.45rem;
}

h4 {
  margin: 0.35rem 0 0;
  color: #1f2926;
  font-size: 0.95rem;
}

p {
  margin: 0.22rem 0 0;
  color: #66756f;
  font-size: 0.82rem;
}

.duration {
  color: #66756f;
  font-size: 0.82rem;
  white-space: nowrap;
}

.right {
  display: grid;
  justify-items: end;
  gap: 0.35rem;
}

.status {
  border-radius: 999px;
  padding: 0.08rem 0.45rem;
  font-size: 0.72rem;
  border: 1px solid #cce3db;
  color: #66756f;
  background: #f8fafc;
}

.status.done {
  border-color: #2f5d56;
  color: #2f5d56;
  background: #e6f2eb;
}

.status.skipped {
  border-color: #cce3db;
  color: #66756f;
  background: #f8fafc;
}

.ops {
  display: flex;
  gap: 0.32rem;
}

.ops button {
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #fff;
  color: #1e3a8a;
  font-size: 0.75rem;
  padding: 0.18rem 0.48rem;
  cursor: pointer;
}

.ops .done {
  border-color: #86efac;
  color: #166534;
}

.ops .skip {
  border-color: #fdba74;
  color: #9a3412;
}
</style>
