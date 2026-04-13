<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { CSSProperties } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/utils/api'
import KnowledgePointDetailModal from '@/components/KnowledgePointDetailModal.vue'
import AbilityTechnicalSummary from '@/components/AbilityTechnicalSummary.vue'
import ExpressionAbilityOverview from '@/components/ExpressionAbilityOverview.vue'

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

type InsightFilter = 'all' | 'risk' | 'mid' | 'strong'

const router = useRouter()

const loading = ref(false)
const detailLoading = ref(false)
const errorMessage = ref('')
const listData = ref<FeedbackListData | null>(null)

const activePositionName = ref('')
const detailVisible = ref(false)
const selectedKnowledgeDetail = ref<KnowledgeDetailData | null>(null)
const insightFilter = ref<InsightFilter>('all')
const hoveredKnowledgeId = ref<number | null>(null)
const mapPointerX = ref(0)
const mapPointerY = ref(0)
const mapActive = ref(false)

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

const averageScore = (knowledge: KnowledgePointSummary) => {
  return (knowledge.avg_logic + knowledge.avg_accuracy) / 2
}

const cardLabel = (knowledge: KnowledgePointSummary) => {
  const avg = averageScore(knowledge)
  if (avg > 80) return '掌握稳定'
  if (avg > 50) return '仍可提升'
  return '重点补强'
}

const cardTone = (knowledge: KnowledgePointSummary): Exclude<InsightFilter, 'all'> => {
  const avg = averageScore(knowledge)
  if (avg > 80) return 'strong'
  if (avg > 50) return 'mid'
  return 'risk'
}

const masteryScore = (knowledge: KnowledgePointSummary) => {
  return Math.max(0, Math.min(100, averageScore(knowledge)))
}

const nodeSize = (knowledge: KnowledgePointSummary) => {
  const min = 34
  const max = 68
  const weakness = 1 - masteryScore(knowledge) / 100
  return Math.round(min + weakness * (max - min))
}

const allKnowledgePoints = computed(() => currentPosition.value?.knowledge_points || [])

const levelCount = computed(() => {
  const stats = { risk: 0, mid: 0, strong: 0 }
  allKnowledgePoints.value.forEach((item) => {
    const tone = cardTone(item)
    stats[tone] += 1
  })
  return stats
})

const visibleKnowledgePoints = computed(() => {
  const source = [...allKnowledgePoints.value]
  const filtered =
    insightFilter.value === 'all'
      ? source
      : source.filter((item) => cardTone(item) === insightFilter.value)

  return filtered.sort((a, b) => masteryScore(a) - masteryScore(b))
})

const hoveredKnowledge = computed(() => {
  if (!hoveredKnowledgeId.value) {
    return null
  }
  return allKnowledgePoints.value.find((item) => item.knowledge_id === hoveredKnowledgeId.value) || null
})

const knowledgeNodeStyle = (knowledge: KnowledgePointSummary, index: number): CSSProperties => {
  const mastery = masteryScore(knowledge)
  const size = nodeSize(knowledge)
  const x = Math.max(8, Math.min(92, knowledge.avg_accuracy))
  const y = Math.max(8, Math.min(92, 100 - knowledge.avg_logic))
  const hue = Math.round(8 + (mastery / 100) * 130)
  const sx = Math.sin((index + 1) * 1.73)
  const sy = Math.cos((index + 1) * 1.37)
  const intensity = mapActive.value ? 5 : 0
  const dx = mapPointerX.value * sx * intensity
  const dy = mapPointerY.value * sy * intensity
  const pulse = mastery < 55 ? 'knowledge-pulse 2.9s ease-in-out infinite' : 'none'
  return {
    left: `${x}%`,
    top: `${y}%`,
    width: `${size}px`,
    height: `${size}px`,
    transform: `translate(calc(-50% + ${dx.toFixed(2)}px), calc(-50% + ${dy.toFixed(2)}px))`,
    background: `radial-gradient(circle at 30% 25%, hsl(${hue} 95% 96%), hsl(${hue} 82% 84%))`,
    borderColor: `hsl(${hue} 66% 44%)`,
    boxShadow: `0 10px 20px hsla(${hue}, 68%, 35%, 0.23)`,
    animationDelay: `${Math.min(index * 28, 420)}ms`,
    animation: pulse,
  }
}

const onKnowledgeMapMove = (event: MouseEvent) => {
  const el = event.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  if (!rect.width || !rect.height) {
    return
  }
  const nx = ((event.clientX - rect.left) / rect.width) * 2 - 1
  const ny = ((event.clientY - rect.top) / rect.height) * 2 - 1
  mapPointerX.value = Math.max(-1, Math.min(1, nx))
  mapPointerY.value = Math.max(-1, Math.min(1, ny))
  mapActive.value = true
}

const onKnowledgeMapLeave = () => {
  mapActive.value = false
  mapPointerX.value = 0
  mapPointerY.value = 0
  hoveredKnowledgeId.value = null
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
  insightFilter.value = 'all'
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
        <h1>个人能力总览</h1>
        <p>先切换岗位，再查看知识点掌握分布，点击节点弹窗查看详细面试记录。</p>
      </div>
      <button type="button" class="refresh-btn" :disabled="loading" @click="fetchKnowledgeList">
        {{ loading ? '刷新中...' : '刷新数据' }}
      </button>
    </header>

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <section class="main-panel">
      <AbilityTechnicalSummary />

      <div v-if="hasData" class="position-tabs">
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

      <div v-if="currentPosition" class="knowledge-grid" @mousemove="onKnowledgeMapMove" @mouseleave="onKnowledgeMapLeave">
        <div class="section-title-block">
          <h2>第二部分 · 知识点掌握情况</h2>
          <p>颜色越红越需要补强，越绿越稳定；节点越大表示当前掌握越薄弱。</p>
        </div>

        <div class="knowledge-toolbar">
          <div class="filter-group">
            <button
              type="button"
              :class="['filter-chip', { active: insightFilter === 'all' }]"
              @click="insightFilter = 'all'"
            >
              全部 {{ allKnowledgePoints.length }}
            </button>
            <button
              type="button"
              :class="['filter-chip', 'risk-chip', { active: insightFilter === 'risk' }]"
              @click="insightFilter = 'risk'"
            >
              重点补强 {{ levelCount.risk }}
            </button>
            <button
              type="button"
              :class="['filter-chip', 'mid-chip', { active: insightFilter === 'mid' }]"
              @click="insightFilter = 'mid'"
            >
              仍可提升 {{ levelCount.mid }}
            </button>
            <button
              type="button"
              :class="['filter-chip', 'strong-chip', { active: insightFilter === 'strong' }]"
              @click="insightFilter = 'strong'"
            >
              掌握稳定 {{ levelCount.strong }}
            </button>
          </div>

        </div>

        <div class="knowledge-map" @mousemove="onKnowledgeMapMove" @mouseleave="onKnowledgeMapLeave">
          <div class="map-grid" />
          <div class="map-axis map-axis-x">准确性 →</div>
          <div class="map-axis map-axis-y">逻辑性 ↑</div>
          <button
            v-for="(knowledge, index) in visibleKnowledgePoints"
            :key="knowledge.knowledge_id"
            type="button"
            class="knowledge-node"
            :style="knowledgeNodeStyle(knowledge, index)"
            :title="knowledge.knowledge_name"
            @mouseenter="hoveredKnowledgeId = knowledge.knowledge_id"
            @mouseleave="hoveredKnowledgeId = null"
            @focus="hoveredKnowledgeId = knowledge.knowledge_id"
            @blur="hoveredKnowledgeId = null"
            @click="openKnowledgeDetail(knowledge)"
          >
            <span class="node-score">{{ masteryScore(knowledge).toFixed(0) }}</span>
          </button>
        </div>

        <div class="hover-panel" v-if="hoveredKnowledge">
          <div class="hover-head">
            <h3>{{ hoveredKnowledge.knowledge_name }}</h3>
            <span class="hover-tag">{{ cardLabel(hoveredKnowledge) }}</span>
          </div>
          <div class="hover-metrics">
            <span>逻辑 {{ hoveredKnowledge.avg_logic }}</span>
            <span>准确 {{ hoveredKnowledge.avg_accuracy }}</span>
            <span>测试 {{ hoveredKnowledge.test_count }} 次</span>
          </div>
          <p>点击该节点查看该知识点的完整面试详情。</p>
        </div>
        <div class="hover-panel empty-hover" v-else>
          <h3>知识点掌握地图</h3>
          <p>横轴是准确性，纵轴是逻辑性。颜色越绿越稳定，越红越需要补强。节点越大表示掌握越薄弱。</p>
          <p class="helper-tip">先切换筛选分组，再将鼠标移到节点上查看细节。</p>
        </div>
      </div>

      <section v-if="!loading && !hasData" class="empty-panel">
        <h2>第二部分 · 暂无知识点评分</h2>
        <p>完成几次面试后，这里会自动展示岗位下的知识点掌握情况。</p>
      </section>
    </section>

    <section class="expression-panel">
      <ExpressionAbilityOverview title="第三部分 · 表达能力总览" />
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
  border: 1px solid #cce3db;
  background:
    radial-gradient(circle at 15% 20%, rgba(47, 93, 86, 0.08), transparent 38%),
    radial-gradient(circle at 82% 88%, rgba(204, 227, 219, 0.4), transparent 42%),
    linear-gradient(120deg, #f0f7f4 0%, #e6f2eb 52%, #ffffff 100%);
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
  color: #1f2926;
  font-size: 1.5rem;
}

.title-block p {
  margin: 0.3rem 0 0;
  color: #66756f;
}

.back-btn,
.refresh-btn {
  border: 1px solid #cce3db;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  color: #2f5d56;
  border-radius: 9px;
  padding: 0.52rem 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn:hover,
.refresh-btn:not(:disabled):hover {
  background: #2f5d56;
  color: white;
}

.refresh-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.error-banner {
  border: 1px solid #ffcdd2;
  background: #fff5f5;
  color: #d32f2f;
  border-radius: 8px;
  padding: 0.7rem 0.9rem;
  margin-bottom: 1rem;
}

.main-panel {
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(12px);
  border: 1px solid #cce3db;
  border-radius: 14px;
  padding: 1rem;
  box-shadow: 0 4px 15px rgba(47, 93, 86, 0.05);
}

.expression-panel {
  margin-top: 0.9rem;
}

.position-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.9rem;
}

.position-tab {
  border: 1px solid #cce3db;
  border-radius: 999px;
  padding: 0.35rem 0.82rem;
  background: rgba(255, 255, 255, 0.8);
  color: #66756f;
  cursor: pointer;
  transition: all 0.2s ease;
}

.position-tab:hover {
  background: #f0f7f4;
}

.position-tab.active {
  border-color: #2f5d56;
  color: #2f5d56;
  background: #e6f2eb;
}

.knowledge-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.8rem;
}

.section-title-block h2 {
  margin: 0;
  color: #1f2926;
  font-size: 1.1rem;
}

.section-title-block p {
  margin: 0.2rem 0 0;
  color: #66756f;
  font-size: 0.86rem;
}

.knowledge-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.8rem;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.filter-chip {
  border: 1px solid #cce3db;
  background: rgba(255, 255, 255, 0.8);
  color: #66756f;
  border-radius: 999px;
  padding: 0.28rem 0.68rem;
  cursor: pointer;
  font-size: 0.78rem;
  transition: all 0.2s ease;
}

.filter-chip:hover {
  background: #f0f7f4;
}

.filter-chip.active {
  border-color: #2f5d56;
  color: #2f5d56;
  background: #e6f2eb;
}

.risk-chip.active {
  border-color: #dc2626;
  color: #991b1b;
  background: #fef2f2;
}

.mid-chip.active {
  border-color: #d97706;
  color: #92400e;
  background: #fffbeb;
}

.strong-chip.active {
  border-color: #16a34a;
  color: #166534;
  background: #f0fdf4;
}


.knowledge-map {
  position: relative;
  height: 430px;
  border-radius: 16px;
  border: 1px solid #cce3db;
  overflow: hidden;
  background:
    radial-gradient(circle at 14% 15%, rgba(220, 38, 38, 0.08), transparent 42%),
    radial-gradient(circle at 86% 18%, rgba(47, 93, 86, 0.12), transparent 46%),
    linear-gradient(145deg, rgba(235, 248, 242, 0.4), rgba(220, 240, 230, 0.3) 55%, rgba(255, 255, 255, 0.6));
}

.map-grid {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(to right, rgba(47, 93, 86, 0.08) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(47, 93, 86, 0.08) 1px, transparent 1px);
  background-size: 20% 20%;
  pointer-events: none;
}

.map-axis {
  position: absolute;
  font-size: 0.76rem;
  color: #66756f;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
  border: 1px solid #cce3db;
  border-radius: 999px;
  padding: 0.15rem 0.5rem;
  pointer-events: none;
}

.map-axis-x {
  right: 0.6rem;
  bottom: 0.6rem;
}

.map-axis-y {
  left: 0.6rem;
  top: 0.6rem;
}

.knowledge-node {
  position: absolute;
  border-radius: 999px;
  border: 2px solid transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #0f172a;
  font-weight: 800;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  animation: node-enter 0.45s ease-out both;
}

.knowledge-node:hover {
  transform: translate(-50%, -50%) scale(1.16) !important;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.24) !important;
  z-index: 8;
}

.node-score {
  font-size: 0.82rem;
}

.hover-panel {
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 14px;
  padding: 0.86rem 0.96rem;
  background: linear-gradient(140deg, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.86));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65), 0 8px 20px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(4px);
}

.hover-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.7rem;
}

.hover-head h3,
.empty-hover h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
}

.hover-tag {
  font-size: 0.72rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.5);
  padding: 0.14rem 0.52rem;
  color: #334155;
  background: rgba(255, 255, 255, 0.72);
  white-space: nowrap;
}

.hover-metrics {
  display: flex;
  gap: 0.85rem;
  flex-wrap: wrap;
  margin-top: 0.42rem;
  color: #1f2937;
  font-size: 0.84rem;
}

.hover-panel p {
  margin: 0.42rem 0 0;
  color: #475569;
  font-size: 0.85rem;
  line-height: 1.45;
}

.empty-hover {
  border-style: dashed;
}

.helper-tip {
  color: #1d4ed8 !important;
  font-weight: 600;
}

@keyframes node-enter {
  from {
    opacity: 0;
    transform: translate(-50%, calc(-50% + 8px)) scale(0.8);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

@keyframes knowledge-pulse {
  0%,
  100% {
    box-shadow: 0 10px 20px rgba(239, 68, 68, 0.18);
  }
  50% {
    box-shadow: 0 14px 30px rgba(239, 68, 68, 0.32);
  }
}

.empty-panel {
  text-align: center;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
  border: 1px solid #cce3db;
  border-radius: 12px;
  padding: 1rem;
}

.empty-panel h2 {
  margin: 0;
  color: #1f2926;
}

.empty-panel p {
  margin: 0.45rem 0 0;
  color: #66756f;
}

@media (max-width: 900px) {
  .topbar {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .knowledge-map {
    height: 380px;
  }

  .hover-head {
    flex-direction: column;
    align-items: flex-start;
  }

}
</style>
