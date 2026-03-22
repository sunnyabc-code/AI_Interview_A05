<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{
  interview: any
  onCardClick: (interview: any) => void
}>()

const statusColorMap: Record<string, string> = {
  pending: '#999',
  in_progress: '#3498db',
  completed: '#27ae60',
  cancelled: '#e74c3c'
}

const statusTextMap: Record<string, string> = {
  pending: '待开始',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消'
}

const statusText = (status: string) => {
  return statusTextMap[status] || status
}

const statusColor = (status: string) => {
  return statusColorMap[status] || '#999'
}
</script>

<template>
  <div class="interview-card" @click="onCardClick(interview)">
    <div class="card-header">
      <h3 class="interview-name">{{ interview.name || '未命名面试' }}</h3>
      <span 
        class="status-badge"
        :style="{ backgroundColor: statusColor(interview.status) }"
      >
        {{ statusText(interview.status) }}
      </span>
    </div>
    <div class="card-body">
        <div class="info-item">
          <span class="label">岗位：</span>
          <span class="value">{{ interview.position_name }}</span>
        </div>
        <div class="info-item">
          <span class="label">难度：</span>
          <span class="value">{{ interview.difficulty_name || '未设置' }}</span>
        </div>
        <div class="info-item">
          <span class="label">模式：</span>
          <span class="value">{{ interview.mode === 'text' ? '文本模式' : interview.mode === 'voice' ? '语音模式' : '混合模式' }}</span>
        </div>
      <div class="info-item">
        <span class="label">总轮次：</span>
        <span class="value">{{ interview.total_rounds }} 轮</span>
      </div>
      <div class="info-item">
        <span class="label">创建时间：</span>
        <span class="value">{{ new Date(interview.created_at).toLocaleString() }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.interview-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  margin-bottom: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  border-left: 4px solid #667eea;
}

.interview-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.interview-name {
  color: #333;
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
  flex: 1;
}

.status-badge {
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
  font-size: 0.8rem;
  color: white;
  font-weight: 500;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.label {
  color: #666;
  font-size: 0.9rem;
  font-weight: 500;
  min-width: 80px;
}

.value {
  color: #333;
  font-size: 0.9rem;
  flex: 1;
}

@media (max-width: 768px) {
  .interview-card {
    padding: 1rem;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .status-badge {
    align-self: flex-start;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.2rem;
  }
  
  .label {
    min-width: auto;
  }
}
</style>
