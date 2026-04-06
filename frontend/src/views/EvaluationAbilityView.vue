<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/utils/api'
import KnowledgePointDetailModal from '@/components/KnowledgePointDetailModal.vue'

interface KnowledgePointSummary {
  knowledge_id: number
  knowledge_name: string
  test_count: number
  avg_logic: number
  avg_accuracy: number
}

interface PositionGroup {
  position_name: string
  knowledge_points: KnowledgePointSummary[]
}

interface FeedbackListData {
  positions: PositionGroup[]
}

interface KnowledgeDetailItem {
  interview_name: string
  tested_at: string
  logic: number
  accuracy: number
}

interface KnowledgeDetailData {
  position_name: string
  knowledge_name: string
  test_count: number
  interview_count: number
  avg_logic: number
  avg_accuracy: number
  test_details: KnowledgeDetailItem[]
}

const router = useRouter()

const loading = ref(false)
const detailLoading = ref(false)
const errorMessage = ref('')
const listData = ref<FeedbackListData | null>(null)

const activePositionName = ref('')
const detailVisible = ref(false)
const selectedKnowledgeDetail = ref<KnowledgeDetailData | null>(null)

const hasData = computed(() => (listData.value?.positions?.length || 0) > 0)

const positionTabs = computed(() => listData.value?.positions || [])

const currentPosition = computed(() => {
  const positions = positionTabs.value
  if (!positions.length) {
    return null
  }
  const selected = positions.find((item) => item.position_name === activePositionName.value)
  return selected || positions[0]
})

const scoreWidth = (score: number) => `${Math.max(0, Math.min(100, score))}%`

const averageScore = (knowledge: KnowledgePointSummary) => {
  return (knowledge.avg_logic + knowledge.avg_accuracy) / 2
}

const cardToneClass = (knowledge: KnowledgePointSummary) => {
  const avg = averageScore(knowledge)
  if (avg > 80) return 'card-strong'
  if (avg > 50) return 'card-mid'
  return 'card-risk'
}

const cardLabel = (knowledge: KnowledgePointSummary) => {
  const avg = averageScore(knowledge)
  if (avg > 80) return '掌握稳定'
  if (avg > 50) return '仍可提升'
  return '重点补强'
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/home?menu=evaluation')
}

const fetchKnowledgeList = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await api.get('/api/recommendations/knowledge-feedback/')
    if (res.code !== 200) {
      throw new Error(res.message || '获取知识点列表失败')
    }
    listData.value = res.data as FeedbackListData

    const first = listData.value.positions?.[0]
    activePositionName.value = first?.position_name || ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}

const switchPosition = (name: string) => {
  activePositionName.value = name
}

const openKnowledgeDetail = async (knowledge: KnowledgePointSummary) => {
  detailVisible.value = true
  detailLoading.value = true
  selectedKnowledgeDetail.value = null

  try {
    const res = await api.get(`/api/recommendations/knowledge-feedback/${knowledge.knowledge_id}/detail/`)
    if (res.code !== 200) {
      throw new Error(res.message || '获取知识点详情失败')
    }
    selectedKnowledgeDetail.value = res.data as KnowledgeDetailData
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '获取知识点详情失败'
  } finally {
    detailLoading.value = false
  }
}

const closeDetailModal = () => {
  detailVisible.value = false
}

onMounted(() => {
  fetchKnowledgeList()
})
</script>

<template>
  <section class="ability-page">
    <header class="topbar">
      <button type="button" class="back-btn" @click="goBack">返回</button>
      <div class="title-block">
        <h1>知识点掌握总览</h1>
        <p>先切换岗位，再查看知识点卡片颜色和双分数，点击卡片弹窗看详细面试记录。</p>
      </div>
      <button type="button" class="refresh-btn" :disabled="loading" @click="fetchKnowledgeList">
        {{ loading ? '刷新中...' : '刷新数据' }}
      </button>
    </header>

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <section v-if="hasData" class="main-panel">
      <div class="position-tabs">
        <button
          v-for="position in positionTabs"
          :key="position.position_name"
          type="button"
          :class="['position-tab', { active: currentPosition?.position_name === position.position_name }]"
          @click="switchPosition(position.position_name)"
        >
          {{ position.position_name }}
        </button>
      </div>

      <div v-if="currentPosition" class="knowledge-grid">
        <article
          v-for="knowledge in currentPosition.knowledge_points"
          :key="knowledge.knowledge_id"
          :class="['knowledge-card', cardToneClass(knowledge)]"
          @click="openKnowledgeDetail(knowledge)"
        >
          <div class="card-head">
            <h3>{{ knowledge.knowledge_name }}</h3>
            <span class="status-pill">{{ cardLabel(knowledge) }}</span>
          </div>

          <p class="test-count">测试次数：{{ knowledge.test_count }}</p>

          <div class="score-row">
            <div class="score-meta">
              <span>逻辑平均分</span>
              <strong>{{ knowledge.avg_logic }}</strong>
            </div>
            <div class="score-track"><div class="score-fill logic-fill" :style="{ width: scoreWidth(knowledge.avg_logic) }" /></div>
          </div>

          <div class="score-row">
            <div class="score-meta">
              <span>准确平均分</span>
              <strong>{{ knowledge.avg_accuracy }}</strong>
            </div>
            <div class="score-track"><div class="score-fill accuracy-fill" :style="{ width: scoreWidth(knowledge.avg_accuracy) }" /></div>
          </div>
        </article>
      </div>
    </section>

    <section v-if="!loading && !hasData" class="empty-panel">
      <h2>暂无知识点评分</h2>
      <p>完成几次面试后，这里会自动展示岗位下的知识点掌握情况。</p>
    </section>

    <KnowledgePointDetailModal
      :visible="detailVisible"
      :loading="detailLoading"
      :detail="selectedKnowledgeDetail"
      @close="closeDetailModal"
    />
  </section>
</template>

<style scoped>
.ability-page {
  min-height: calc(100vh - 120px);
  padding: 1.1rem;
  border-radius: 16px;
  border: 1px solid #dbeafe;
  background:
    radial-gradient(circle at 15% 20%, rgba(191, 219, 254, 0.45), transparent 38%),
    radial-gradient(circle at 82% 88%, rgba(187, 247, 208, 0.36), transparent 42%),
    linear-gradient(120deg, #f8fafc 0%, #eef2ff 52%, #f0fdf4 100%);
}

.topbar {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1rem;
}

.title-block h1 {
  margin: 0;
  color: #0f172a;
  font-size: 1.5rem;
}

.title-block p {
  margin: 0.3rem 0 0;
  color: #475569;
}

.back-btn,
.refresh-btn {
  border: 1px solid #93c5fd;
  background: #ffffff;
  color: #1d4ed8;
  border-radius: 9px;
  padding: 0.52rem 0.9rem;
  cursor: pointer;
}

.refresh-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.error-banner {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #991b1b;
  border-radius: 8px;
  padding: 0.7rem 0.9rem;
  margin-bottom: 1rem;
}

.main-panel {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #dbeafe;
  border-radius: 14px;
  padding: 1rem;
}

.position-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.9rem;
}

.position-tab {
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  padding: 0.35rem 0.82rem;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
}

.position-tab.active {
  border-color: #3b82f6;
  color: #1d4ed8;
  background: #eff6ff;
}

.knowledge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 0.8rem;
}

.knowledge-card {
  border-radius: 12px;
  padding: 0.78rem;
  border: 1px solid #dbeafe;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.2s ease;
}

.knowledge-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.1);
}

.card-strong {
  background: linear-gradient(145deg, #ecfdf5, #d1fae5);
  border-color: #6ee7b7;
}

.card-mid {
  background: linear-gradient(145deg, #fff7ed, #ffedd5);
  border-color: #fdba74;
}

.card-risk {
  background: linear-gradient(145deg, #fef2f2, #fee2e2);
  border-color: #fca5a5;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 0.65rem;
}

.card-head h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
}

.status-pill {
  display: inline-block;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(148, 163, 184, 0.45);
  color: #334155;
  font-size: 0.72rem;
  padding: 0.12rem 0.48rem;
  white-space: nowrap;
}

.test-count {
  margin: 0.52rem 0 0;
  color: #334155;
  font-size: 0.84rem;
}

.score-row {
  margin-top: 0.58rem;
}

.score-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.25rem;
  color: #1f2937;
  font-size: 0.82rem;
}

.score-meta strong {
  color: #0f172a;
}

.score-track {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: rgba(226, 232, 240, 0.86);
  overflow: hidden;
}

.score-fill {
  height: 100%;
}

.logic-fill {
  background: linear-gradient(90deg, #22c55e, #16a34a);
}

.accuracy-fill {
  background: linear-gradient(90deg, #3b82f6, #1d4ed8);
}

.empty-panel {
  text-align: center;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem;
}

.empty-panel h2 {
  margin: 0;
  color: #334155;
}

.empty-panel p {
  margin: 0.45rem 0 0;
  color: #64748b;
}

@media (max-width: 900px) {
  .topbar {
    grid-template-columns: 1fr;
    align-items: start;
  }
}
</style>
