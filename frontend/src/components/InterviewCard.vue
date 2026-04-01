<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  interview: any
  onCardClick: (interview: any) => void
  onDelete: (interviewId: number) => void
}>()

const showDeleteConfirm = ref(false)

const handleDeleteClick = (event: Event) => {
  event.stopPropagation()
  showDeleteConfirm.value = true
}

const confirmDelete = () => {
  props.onDelete(props.interview.id)
  showDeleteConfirm.value = false
}

const cancelDelete = () => {
  showDeleteConfirm.value = false
}

const statusColorMap: Record<string, string> = {
  pending: '#999',
  in_progress: '#3498db',
  paused: '#f39c12',
  completed: '#27ae60',
  cancelled: '#e74c3c'
}

const statusTextMap: Record<string, string> = {
  pending: '待开始',
  in_progress: '进行中',
  paused: '已暂停',
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
      <div class="header-actions">
        <span 
          class="status-badge"
          :style="{ backgroundColor: statusColor(interview.status) }"
        >
          {{ statusText(interview.status) }}
        </span>
        <button 
          class="delete-btn"
          @click="handleDeleteClick"
          title="删除面试"
        >
          删除
        </button>
      </div>
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
  
  <!-- 删除确认弹窗 - 使用teleport移到body下避免层级问题 -->
  <Teleport to="body">
    <div v-if="showDeleteConfirm" class="delete-confirm-overlay" @click="cancelDelete">
      <div class="delete-confirm-modal" @click.stop>
        <h4>确认删除</h4>
        <p>确定要删除这个面试吗？删除后将无法恢复。</p>
        <div class="confirm-actions">
          <button class="cancel-btn" @click="cancelDelete">取消</button>
          <button class="confirm-btn" @click="confirmDelete">删除</button>
        </div>
      </div>
    </div>
  </Teleport>
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.delete-btn {
  background: #dc3545;
  color: white;
  border: none;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.delete-btn:hover {
  background: #c82333;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(220, 53, 69, 0.3);
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

/* 删除确认弹窗样式 */
.delete-confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.delete-confirm-modal {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-width: 400px;
  width: 90%;
}

.delete-confirm-modal h4 {
  color: #333;
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: 600;
}

.delete-confirm-modal p {
  color: #666;
  margin: 0 0 1.5rem 0;
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.cancel-btn {
  background: #6c757d;
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.cancel-btn:hover {
  background: #5a6268;
  transform: translateY(-1px);
}

.confirm-btn {
  background: #dc3545;
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.confirm-btn:hover {
  background: #c82333;
  transform: translateY(-1px);
}
</style>
