<script setup lang="ts">
import { computed } from 'vue'

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

const props = defineProps<{
  visible: boolean
  loading: boolean
  detail: KnowledgeDetailData | null
}>()

const emit = defineEmits<{
  (event: 'close'): void
}>()

const closeModal = () => {
  emit('close')
}

const chartWidth = 760
const chartHeight = 250
const chartPadding = { top: 22, right: 24, bottom: 34, left: 34 }

const sortedDetails = computed(() => {
  if (!props.detail) {
    return [] as KnowledgeDetailItem[]
  }
  return [...props.detail.test_details].sort(
    (a, b) => new Date(a.tested_at).getTime() - new Date(b.tested_at).getTime(),
  )
})

const chartPoints = computed(() => {
  const details = sortedDetails.value
  const innerWidth = chartWidth - chartPadding.left - chartPadding.right
  const innerHeight = chartHeight - chartPadding.top - chartPadding.bottom

  if (!details.length) {
    return [] as Array<{ x: number; logicY: number; accuracyY: number; label: string; logic: number; accuracy: number }>
  }

  return details.map((item, index) => {
    const x = chartPadding.left + (details.length === 1 ? innerWidth / 2 : (index * innerWidth) / (details.length - 1))
    const logicY = chartPadding.top + ((100 - item.logic) / 100) * innerHeight
    const accuracyY = chartPadding.top + ((100 - item.accuracy) / 100) * innerHeight
    const label = new Date(item.tested_at).toLocaleDateString()
    return {
      x,
      logicY,
      accuracyY,
      label,
      logic: item.logic,
      accuracy: item.accuracy,
    }
  })
})

const logicPath = computed(() => {
  const points = chartPoints.value
  if (!points.length) return ''
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.logicY}`).join(' ')
})

const accuracyPath = computed(() => {
  const points = chartPoints.value
  if (!points.length) return ''
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.accuracyY}`).join(' ')
})

const yAxisTicks = [100, 75, 50, 25, 0]

const yPosition = (value: number) => {
  const innerHeight = chartHeight - chartPadding.top - chartPadding.bottom
  return chartPadding.top + ((100 - value) / 100) * innerHeight
}
</script>

<template>
  <div v-if="visible" class="modal-mask" @click.self="closeModal">
    <div class="modal-panel">
      <header class="modal-header">
        <div>
          <h2>知识点详细情况</h2>
          <p v-if="detail">{{ detail.position_name }} · {{ detail.knowledge_name }}</p>
        </div>
        <button type="button" class="close-btn" @click="closeModal">关闭</button>
      </header>

      <div v-if="loading" class="loading-block">详情加载中...</div>

      <div v-else-if="detail" class="modal-content">
        <div class="metrics-grid">
          <article>
            <h3>测试次数</h3>
            <strong>{{ detail.test_count }}</strong>
          </article>
          <article>
            <h3>涉及面试</h3>
            <strong>{{ detail.interview_count }}</strong>
          </article>
          <article>
            <h3>逻辑平均分</h3>
            <strong>{{ detail.avg_logic }}</strong>
          </article>
          <article>
            <h3>准确平均分</h3>
            <strong>{{ detail.avg_accuracy }}</strong>
          </article>
        </div>

        <section class="trend-panel">
          <div class="trend-head">
            <h3>分数趋势曲线</h3>
            <div class="legend-row">
              <span class="legend-item"><i class="dot logic-dot" />逻辑分</span>
              <span class="legend-item"><i class="dot accuracy-dot" />准确分</span>
            </div>
          </div>
          <div class="chart-wrap" v-if="chartPoints.length">
            <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="trend-chart" aria-label="logic和accuracy趋势图">
              <defs>
                <linearGradient id="logicGradient" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stop-color="#22c55e" stop-opacity="0.28" />
                  <stop offset="100%" stop-color="#22c55e" stop-opacity="0" />
                </linearGradient>
                <linearGradient id="accuracyGradient" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.24" />
                  <stop offset="100%" stop-color="#3b82f6" stop-opacity="0" />
                </linearGradient>
              </defs>

              <g>
                <line
                  v-for="tick in yAxisTicks"
                  :key="`grid-${tick}`"
                  :x1="chartPadding.left"
                  :x2="chartWidth - chartPadding.right"
                  :y1="yPosition(tick)"
                  :y2="yPosition(tick)"
                  class="grid-line"
                />
                <text
                  v-for="tick in yAxisTicks"
                  :key="`label-${tick}`"
                  :x="chartPadding.left - 10"
                  :y="yPosition(tick) + 4"
                  text-anchor="end"
                  class="axis-label"
                >
                  {{ tick }}
                </text>
              </g>

              <path
                :d="`${logicPath} L ${chartPoints[chartPoints.length - 1].x} ${chartHeight - chartPadding.bottom} L ${chartPoints[0].x} ${chartHeight - chartPadding.bottom} Z`"
                fill="url(#logicGradient)"
              />
              <path
                :d="`${accuracyPath} L ${chartPoints[chartPoints.length - 1].x} ${chartHeight - chartPadding.bottom} L ${chartPoints[0].x} ${chartHeight - chartPadding.bottom} Z`"
                fill="url(#accuracyGradient)"
              />

              <path :d="logicPath" class="line logic-line" />
              <path :d="accuracyPath" class="line accuracy-line" />

              <g v-for="(point, idx) in chartPoints" :key="`point-${idx}`">
                <circle :cx="point.x" :cy="point.logicY" r="4.3" class="point logic-point" />
                <circle :cx="point.x" :cy="point.accuracyY" r="4.3" class="point accuracy-point" />
                <text :x="point.x" :y="chartHeight - 10" text-anchor="middle" class="axis-label x-label">{{ point.label }}</text>
              </g>
            </svg>
          </div>
          <p v-else class="loading-block">暂无趋势数据</p>
        </section>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>面试名称</th>
                <th>测试时间</th>
                <th>逻辑分</th>
                <th>准确分</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in detail.test_details" :key="`${row.interview_name}-${index}`">
                <td>{{ row.interview_name }}</td>
                <td>{{ new Date(row.tested_at).toLocaleString() }}</td>
                <td>{{ row.logic }}</td>
                <td>{{ row.accuracy }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else class="loading-block">暂无详细数据</div>
    </div>
  </div>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(2px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.modal-panel {
  width: min(960px, 96vw);
  max-height: 86vh;
  overflow: auto;
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid #dbeafe;
  box-shadow: 0 24px 48px rgba(2, 6, 23, 0.24);
}

.modal-header {
  position: sticky;
  top: 0;
  z-index: 5;
  background: linear-gradient(120deg, #eff6ff, #ecfdf5);
  border-bottom: 1px solid #dbeafe;
  padding: 0.95rem 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.8rem;
}

.modal-header h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.18rem;
}

.modal-header p {
  margin: 0.3rem 0 0;
  color: #475569;
  font-size: 0.9rem;
}

.close-btn {
  border: 1px solid #93c5fd;
  background: #ffffff;
  color: #1d4ed8;
  border-radius: 8px;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
}

.loading-block {
  padding: 1.2rem;
  color: #64748b;
}

.modal-content {
  padding: 1rem;
}

.trend-panel {
  border: 1px solid #dbeafe;
  border-radius: 12px;
  padding: 0.72rem 0.75rem;
  background: linear-gradient(140deg, #f8fafc, #eff6ff);
  margin-bottom: 0.9rem;
}

.trend-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  margin-bottom: 0.5rem;
}

.trend-head h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
}

.legend-row {
  display: flex;
  gap: 0.7rem;
}

.legend-item {
  font-size: 0.8rem;
  color: #334155;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.logic-dot {
  background: #16a34a;
}

.accuracy-dot {
  background: #1d4ed8;
}

.chart-wrap {
  width: 100%;
  overflow-x: auto;
}

.trend-chart {
  width: 100%;
  min-width: 680px;
  height: 250px;
}

.grid-line {
  stroke: #dbeafe;
  stroke-width: 1;
}

.axis-label {
  fill: #64748b;
  font-size: 11px;
}

.x-label {
  font-size: 10px;
}

.line {
  fill: none;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.logic-line {
  stroke: #16a34a;
}

.accuracy-line {
  stroke: #1d4ed8;
}

.point {
  stroke: #ffffff;
  stroke-width: 1.4;
}

.logic-point {
  fill: #16a34a;
}

.accuracy-point {
  fill: #1d4ed8;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.55rem;
  margin-bottom: 0.9rem;
}

.metrics-grid article {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.6rem 0.7rem;
  background: #f8fafc;
}

.metrics-grid h3 {
  margin: 0;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 500;
}

.metrics-grid strong {
  margin-top: 0.2rem;
  display: inline-block;
  color: #0f172a;
  font-size: 1.18rem;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 620px;
}

th,
td {
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  padding: 0.5rem 0.35rem;
  color: #334155;
  font-size: 0.88rem;
}

th {
  background: #f8fafc;
  color: #0f172a;
}
</style>
