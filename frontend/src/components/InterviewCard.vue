<script setup lang="ts">
import { ref } from 'vue'
import type { Interview } from '../types'

const props = defineProps<{
  interview: Interview
  onCardClick: (interview: Interview) => void
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

const statusClass = (status: string) => {
  const statusClassMap: Record<string, string> = {
    pending: 'status-pending',
    in_progress: 'status-in-progress',
    paused: 'status-paused',
    completed: 'status-completed',
    cancelled: 'status-cancelled'
  }
  return statusClassMap[status] || 'status-pending'
}

const difficultyText = (rawDifficulty: unknown) => {
  const map: Record<number, string> = {
    1: '简单',
    2: '中等',
    3: '困难'
  }

  const num = Number(rawDifficulty)
  if (Number.isFinite(num) && map[num]) {
    return map[num]
  }

  if (typeof rawDifficulty === 'string' && rawDifficulty.trim()) {
    return rawDifficulty
  }

  return '未设置'
}

const interviewDifficultyText = (item: Interview) => {
  const source = item as any
  return difficultyText(source.difficulty_name || source.difficulty || source.difficulty_level)
}

const cardThemeClass = (positionName: string) => {
  const normalized = (positionName || '').toLowerCase()
  if (normalized.includes('java')) {
    return 'theme-java'
  }
  if (normalized.includes('大模型') || normalized.includes('llm') || normalized.includes('ai')) {
    return 'theme-llm'
  }
  return 'theme-default'
}

</script>

<template>
  <div class="interview-card-shell">
    <div class="interview-card" :class="cardThemeClass(interview.position_name)" @click="onCardClick(interview)">
      <div class="card-header">
        <h3 class="interview-name">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="5" width="16" height="14" rx="3" stroke="currentColor" stroke-width="1.8"/>
              <path d="M8 10H16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M8 14H13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </span>
          <span>{{ interview.name || '未命名面试' }}</span>
        </h3>
        <div class="header-actions">
          <span class="status-badge" :class="statusClass(interview.status)">
            {{ statusText(interview.status) }}
          </span>
          <button class="delete-btn" @click="handleDeleteClick" title="删除面试">
            <span class="icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9.5 9V16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                <path d="M14.5 9V16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                <path d="M6.5 7H17.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                <path d="M8.5 7L9.2 5.8C9.4 5.4 9.8 5.2 10.2 5.2H13.8C14.2 5.2 14.6 5.4 14.8 5.8L15.5 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                <path d="M8 7.2L8.4 17.1C8.45 18 9.17 18.7 10.06 18.7H13.94C14.83 18.7 15.55 18 15.6 17.1L16 7.2" stroke="currentColor" stroke-width="1.8"/>
              </svg>
            </span>
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
          <span class="value">{{ interviewDifficultyText(interview) }}</span>
        </div>
        <div class="info-item">
          <span class="label">模式：</span>
          <span class="value">{{ interview.mode === 'text' ? '文本模式' : interview.mode === 'voice' ? '语音模式' : '混合模式'
            }}</span>
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
          <h4>
            <span class="icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/>
                <path d="M12 8V13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                <circle cx="12" cy="16.5" r="1" fill="currentColor"/>
              </svg>
            </span>
            <span>确认删除</span>
          </h4>
          <p>确定要删除这个面试吗？删除后将无法恢复。</p>
          <div class="confirm-actions">
            <button class="cancel-btn" @click="cancelDelete">
              <span class="icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M7 7L17 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
                  <path d="M17 7L7 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
                </svg>
              </span>
              取消
            </button>
            <button class="confirm-btn" @click="confirmDelete">
              <span class="icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M9.5 9V16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                  <path d="M14.5 9V16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                  <path d="M6.5 7H17.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                  <path d="M8.5 7L9.2 5.8C9.4 5.4 9.8 5.2 10.2 5.2H13.8C14.2 5.2 14.6 5.4 14.8 5.8L15.5 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                  <path d="M8 7.2L8.4 17.1C8.45 18 9.17 18.7 10.06 18.7H13.94C14.83 18.7 15.55 18 15.6 17.1L16 7.2" stroke="currentColor" stroke-width="1.8"/>
                </svg>
              </span>
              删除
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.interview-card {
  --surface: #ffffff;
  --surface-soft: #f8fbf9;
  --line: #dfe7e2;
  --line-soft: #e7eeea;
  --text: #202a26;
  --muted: #6a7a74;
  --accent: #2f5d56;
  --danger: #9f3a34;

  background: var(--surface);
  border-radius: var(--list-card-radius, 16px);
  box-shadow: 0 12px 28px rgba(26, 38, 34, 0.08);
  padding: 1rem 1.05rem;
  margin-bottom: 0.86rem;
  cursor: pointer;
  transition: all 0.24s ease;
  border: 1px solid var(--line);
  position: relative;
  overflow: hidden;
}

.interview-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 5px;
  background: #d6e1dc;
}

.interview-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 120px;
  height: 90px;
  pointer-events: none;
  opacity: 0.75;
  background: radial-gradient(circle at 0 0, rgba(88, 150, 124, 0.2) 0%, rgba(88, 150, 124, 0) 70%);
}

.interview-card.theme-default {
  background: #ffffff;
}

.interview-card.theme-llm {
  background: linear-gradient(180deg, #f3fbf8 0%, #e5f4ed 100%);
  border-color: #bdd8cc;
}

.interview-card.theme-llm::before {
  background: linear-gradient(90deg, #2f745f 0%, #4f977a 100%);
}

.interview-card.theme-llm::after {
  background: radial-gradient(circle at 0 0, rgba(63, 139, 111, 0.24) 0%, rgba(63, 139, 111, 0) 72%);
}

.interview-card.theme-java {
  background: linear-gradient(180deg, #fbfefd 0%, #eef7f4 100%);
  border-color: #d1e3db;
}

.interview-card.theme-java::before {
  background: linear-gradient(90deg, #5c9b84 0%, #84b8a4 100%);
}

.interview-card.theme-java::after {
  background: radial-gradient(circle at 0 0, rgba(112, 173, 148, 0.2) 0%, rgba(112, 173, 148, 0) 72%);
}

.interview-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(26, 38, 34, 0.12);
  border-color: #cad8d2;
}

.interview-card.theme-llm:hover {
  box-shadow: 0 16px 30px rgba(33, 101, 74, 0.2);
  border-color: #abd0c0;
}

.interview-card.theme-java:hover {
  box-shadow: 0 16px 30px rgba(68, 128, 103, 0.17);
  border-color: #bfd8cd;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.8rem;
  margin-bottom: 0.86rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--list-card-action-gap, 0.5rem);
}

.delete-btn {
  background: #a24842;
  color: #ffffff;
  border: 1px solid #973e39;
  font-size: var(--list-card-button-font-size, 0.8rem);
  font-weight: 600;
  cursor: pointer;
  padding: 0 0.7rem;
  height: var(--list-card-button-height, 34px);
  border-radius: 9px;
  transition: all 0.24s ease;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 0.28rem;
}

.delete-btn:hover {
  background: #8e3833;
  transform: translateY(-1px);
  border-color: #7e312c;
  box-shadow: 0 8px 18px rgba(146, 56, 50, 0.24);
}

.interview-name {
  color: var(--text);
  font-size: var(--list-card-title-size, 1rem);
  font-weight: 600;
  margin: 0;
  flex: 1;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.status-badge {
  padding: 0 0.68rem;
  min-height: var(--list-card-status-height, 28px);
  border-radius: 999px;
  font-size: var(--list-card-status-font-size, 0.75rem);
  color: var(--text);
  font-weight: 600;
  border: 1px solid transparent;
  background: var(--surface-soft);
  display: inline-flex;
  align-items: center;
}

.status-pending {
  color: #566963;
  background: #edf3f0;
  border-color: #d5e1db;
}

.status-in-progress {
  color: #1d4f9b;
  background: #e5efff;
  border-color: #c5d8f8;
}

.status-paused {
  color: #785f34;
  background: #f8efdd;
  border-color: #e7d4ae;
}

.status-completed {
  color: #206744;
  background: #e1f4e8;
  border-color: #bddfc9;
}

.status-cancelled {
  color: #8f3833;
  background: #f9ebe9;
  border-color: #eacdc8;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: var(--list-card-body-gap, 0.42rem);
  padding: 0.78rem;
  border: 1px solid var(--line-soft);
  border-radius: 12px;
  background: var(--surface-soft);
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 1.65rem;
}

.label {
  color: var(--muted);
  font-size: var(--list-card-label-size, 0.81rem);
  font-weight: 500;
  min-width: 74px;
}

.value {
  color: var(--text);
  font-size: var(--list-card-text-size, 0.83rem);
  font-weight: 550;
  flex: 1;
}

@media (max-width: 768px) {
  .interview-card {
    padding: 0.82rem;
    border-radius: 14px;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.55rem;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .status-badge {
    align-self: flex-start;
  }

  .info-item {
    flex-direction: row;
    align-items: flex-start;
    gap: 0.35rem;
    min-height: 1.5rem;
  }

  .label {
    min-width: 66px;
  }
}

/* 删除确认弹窗样式 */
.delete-confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(22, 30, 27, 0.56);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1300;
  backdrop-filter: blur(5px);
}

.delete-confirm-modal {
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid #dce6e1;
  padding: 1rem;
  box-shadow: 0 20px 40px rgba(25, 37, 34, 0.2);
  max-width: 400px;
  width: 90%;
}

.delete-confirm-modal h4 {
  color: #1f2926;
  margin: 0 0 0.7rem 0;
  font-size: 1rem;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.delete-confirm-modal p {
  color: #63756f;
  margin: 0 0 0.92rem 0;
  line-height: 1.45;
  font-size: 0.86rem;
}

.confirm-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.cancel-btn {
  background: #f0f5f3;
  color: #3d5d56;
  border: 1px solid #dae5df;
  padding: 0.5rem 0.8rem;
  border-radius: 9px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.cancel-btn:hover {
  background: #e5eeea;
  transform: translateY(-1px);
}

.confirm-btn {
  background: linear-gradient(135deg, #be5f57 0%, #b24d45 100%);
  color: white;
  border: none;
  padding: 0.5rem 0.8rem;
  border-radius: 9px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.24s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.confirm-btn:hover {
  background: linear-gradient(135deg, #b7554d 0%, #a7443d 100%);
  transform: translateY(-1px);
}

.icon {
  width: 14px;
  height: 14px;
  display: inline-flex;
  flex-shrink: 0;
}

.icon svg {
  width: 100%;
  height: 100%;
}

@media (max-width: 640px) {
  .delete-confirm-modal {
    padding: 0.86rem;
  }

  .confirm-actions {
    width: 100%;
  }

  .cancel-btn,
  .confirm-btn {
    flex: 1;
    justify-content: center;
  }
}
</style>
