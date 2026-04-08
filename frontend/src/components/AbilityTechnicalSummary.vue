<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import api from '@/utils/api'

type CategoryKey = 'technical' | 'scenario' | 'project'
type ScoreKey = 'technical_score' | 'communication_score' | 'logic_score' | 'adaptability_score'

interface InterviewListItem {
  id: number
  name: string
  position_name: string
  created_at: string
  start_time: string | null
}

interface RoundAnalysis {
  technical_score: number | null
  communication_score: number | null
  logic_score: number | null
  adaptability_score: number | null
}

interface InterviewRoundItem {
  interview_id: number
  followup_depth: number
  category: string | null
  category_name: string | null
  created_at: string
  analysis?: RoundAnalysis | null
}

interface ApiResp<T> {
  code: number
  message: string
  data: T
}

interface CategoryTrendItem {
  interviewId: number
  interviewName: string
  positionName: string
  testedAt: string
  questionCount: number
  scores: Record<ScoreKey, number | null>
}

interface CategorySummary {
  key: CategoryKey
  label: string
  questionCount: number
  scores: Record<ScoreKey, number | null>
  trend: CategoryTrendItem[]
}

const CATEGORY_LABELS: Record<CategoryKey, string> = {
  technical: '技术题',
  scenario: '场景题',
  project: '项目题',
}

const SCORE_LABELS: Record<ScoreKey, string> = {
  technical_score: '技术',
  communication_score: '沟通',
  logic_score: '逻辑',
  adaptability_score: '应变',
}

const CATEGORY_ORDER: CategoryKey[] = ['technical', 'scenario', 'project']
const SCORE_KEYS: ScoreKey[] = [
  'technical_score',
  'communication_score',
  'logic_score',
  'adaptability_score',
]

const loading = ref(false)
const errorMessage = ref('')
const detailVisible = ref(false)
const activeCategory = ref<CategoryKey>('technical')
const trendChartRef = ref<HTMLDivElement | null>(null)
const trendChartInstance = ref<echarts.ECharts | null>(null)
const summaries = ref<Record<CategoryKey, CategorySummary>>({
  technical: {
    key: 'technical',
    label: CATEGORY_LABELS.technical,
    questionCount: 0,
    scores: {
      technical_score: null,
      communication_score: null,
      logic_score: null,
      adaptability_score: null,
    },
    trend: [],
  },
  scenario: {
    key: 'scenario',
    label: CATEGORY_LABELS.scenario,
    questionCount: 0,
    scores: {
      technical_score: null,
      communication_score: null,
      logic_score: null,
      adaptability_score: null,
    },
    trend: [],
  },
  project: {
    key: 'project',
    label: CATEGORY_LABELS.project,
    questionCount: 0,
    scores: {
      technical_score: null,
      communication_score: null,
      logic_score: null,
      adaptability_score: null,
    },
    trend: [],
  },
})

const summaryCards = computed(() => CATEGORY_ORDER.map((key) => summaries.value[key]))
const activeSummary = computed(() => summaries.value[activeCategory.value])
const activeTrendCount = computed(() => activeSummary.value?.trend.length || 0)

const toNum = (val: unknown): number | null => {
  if (typeof val !== 'number' || Number.isNaN(val)) {
    return null
  }
  return Math.max(0, Math.min(100, Number(val)))
}

const formatScore = (score: number | null) => {
  if (score === null) return '--'
  return Number(score).toFixed(1)
}

const formatDate = (raw: string) => {
  if (!raw) return '--'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const ensureTrendChart = () => {
  if (!trendChartRef.value) {
    return null
  }
  if (!trendChartInstance.value) {
    trendChartInstance.value = echarts.init(trendChartRef.value)
  }
  return trendChartInstance.value
}

const disposeTrendChart = () => {
  if (trendChartInstance.value) {
    trendChartInstance.value.dispose()
    trendChartInstance.value = null
  }
}

const renderTrendChart = () => {
  const chart = ensureTrendChart()
  const trend = activeSummary.value?.trend || []
  if (!chart) {
    return
  }

  if (!trend.length) {
    chart.clear()
    return
  }

  const xAxis = trend.map((item) => formatDate(item.testedAt))
  const colorMap: Record<ScoreKey, string> = {
    technical_score: '#2563eb',
    communication_score: '#0ea5e9',
    logic_score: '#16a34a',
    adaptability_score: '#f97316',
  }

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: string | number) => {
        if (typeof value !== 'number' || Number.isNaN(value)) {
          return '--'
        }
        return Number(value).toFixed(1)
      },
    },
    legend: {
      top: 4,
      textStyle: {
        color: '#334155',
      },
    },
    grid: {
      left: 44,
      right: 18,
      top: 42,
      bottom: 30,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxis,
      axisLabel: {
        color: '#64748b',
        fontSize: 11,
      },
      axisLine: {
        lineStyle: {
          color: '#cbd5e1',
        },
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: {
        color: '#64748b',
        fontSize: 11,
      },
      splitLine: {
        lineStyle: {
          color: '#e2e8f0',
        },
      },
    },
    series: SCORE_KEYS.map((scoreKey) => ({
      name: SCORE_LABELS[scoreKey],
      type: 'line',
      smooth: true,
      connectNulls: true,
      data: trend.map((row) => row.scores[scoreKey]),
      symbol: 'circle',
      symbolSize: 7,
      lineStyle: {
        width: 2,
        color: colorMap[scoreKey],
      },
      itemStyle: {
        color: colorMap[scoreKey],
      },
      areaStyle: {
        opacity: 0.08,
        color: colorMap[scoreKey],
      },
      emphasis: {
        focus: 'series',
      },
    })),
  })
}

const normalizeCategory = (round: InterviewRoundItem): CategoryKey | null => {
  const code = (round.category || '').toLowerCase().trim()
  if (code === 'technical' || code === '1') return 'technical'
  if (code === 'scenario' || code === '2') return 'scenario'
  if (code === 'project' || code === '3') return 'project'

  const cname = (round.category_name || '').trim()
  if (cname.includes('技术')) return 'technical'
  if (cname.includes('场景')) return 'scenario'
  if (cname.includes('项目')) return 'project'
  return null
}

const scoreStyle = (score: number | null) => {
  const safe = score ?? 0
  const hue = Math.round(6 + (safe / 100) * 132)
  return {
    width: `${safe}%`,
    background: `linear-gradient(90deg, hsl(${hue} 74% 54%), hsl(${hue} 78% 42%))`,
  }
}

const openDetail = (key: CategoryKey) => {
  activeCategory.value = key
  detailVisible.value = true
}

const closeDetail = () => {
  detailVisible.value = false
}

const buildSummary = (interviews: InterviewListItem[], roundsByInterview: Record<number, InterviewRoundItem[]>) => {
  const initAccumulator = () => ({
    count: 0,
    sums: {
      technical_score: 0,
      communication_score: 0,
      logic_score: 0,
      adaptability_score: 0,
    } as Record<ScoreKey, number>,
    counts: {
      technical_score: 0,
      communication_score: 0,
      logic_score: 0,
      adaptability_score: 0,
    } as Record<ScoreKey, number>,
  })

  const categoryAcc: Record<CategoryKey, ReturnType<typeof initAccumulator>> = {
    technical: initAccumulator(),
    scenario: initAccumulator(),
    project: initAccumulator(),
  }

  const trendAcc: Record<CategoryKey, Map<number, ReturnType<typeof initAccumulator> & {
    interviewName: string
    positionName: string
    testedAt: string
  }>> = {
    technical: new Map(),
    scenario: new Map(),
    project: new Map(),
  }

  const interviewMeta = new Map<number, InterviewListItem>()
  interviews.forEach((item) => interviewMeta.set(item.id, item))

  interviews.forEach((interview) => {
    const rounds = roundsByInterview[interview.id] || []
    rounds
      .filter((round) => Number(round.followup_depth) === 0)
      .forEach((round) => {
        const category = normalizeCategory(round)
        if (!category) return

        categoryAcc[category].count += 1

        let trendItem = trendAcc[category].get(interview.id)
        if (!trendItem) {
          trendItem = {
            ...initAccumulator(),
            interviewName: interview.name || `${interview.position_name}面试`,
            positionName: interview.position_name,
            testedAt: interview.start_time || interview.created_at,
          }
          trendAcc[category].set(interview.id, trendItem)
        }
        trendItem.count += 1

        const analysis = round.analysis || null
        if (!analysis) {
          return
        }

        SCORE_KEYS.forEach((key) => {
          const value = toNum(analysis[key])
          if (value === null) return
          categoryAcc[category].sums[key] += value
          categoryAcc[category].counts[key] += 1
          trendItem!.sums[key] += value
          trendItem!.counts[key] += 1
        })
      })
  })

  const nextSummaries = { ...summaries.value }

  CATEGORY_ORDER.forEach((key) => {
    const acc = categoryAcc[key]
    const scores = SCORE_KEYS.reduce((obj, scoreKey) => {
      const c = acc.counts[scoreKey]
      obj[scoreKey] = c > 0 ? Number((acc.sums[scoreKey] / c).toFixed(2)) : null
      return obj
    }, {} as Record<ScoreKey, number | null>)

    const trend = Array.from(trendAcc[key].entries())
      .map(([interviewId, item]) => {
        const scoreByInterview = SCORE_KEYS.reduce((obj, scoreKey) => {
          const c = item.counts[scoreKey]
          obj[scoreKey] = c > 0 ? Number((item.sums[scoreKey] / c).toFixed(2)) : null
          return obj
        }, {} as Record<ScoreKey, number | null>)

        const meta = interviewMeta.get(interviewId)
        return {
          interviewId,
          interviewName: item.interviewName,
          positionName: item.positionName,
          testedAt: meta?.start_time || meta?.created_at || item.testedAt,
          questionCount: item.count,
          scores: scoreByInterview,
        }
      })
      .sort((a, b) => new Date(a.testedAt).getTime() - new Date(b.testedAt).getTime())

    nextSummaries[key] = {
      key,
      label: CATEGORY_LABELS[key],
      questionCount: acc.count,
      scores,
      trend,
    }
  })

  summaries.value = nextSummaries
}

const fetchSummary = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const listRes = (await api.get('/api/v1/interviews/')) as ApiResp<InterviewListItem[]>
    if (listRes.code !== 200) {
      throw new Error(listRes.message || '获取面试记录失败')
    }

    const interviews = Array.isArray(listRes.data) ? listRes.data : []
    if (!interviews.length) {
      buildSummary([], {})
      return
    }

    const roundResults = await Promise.allSettled(
      interviews.map((interview) => api.get(`/api/v1/interviews/${interview.id}/rounds/`))
    )

    const roundsByInterview: Record<number, InterviewRoundItem[]> = {}
    roundResults.forEach((result, idx) => {
      const interviewId = interviews[idx].id
      if (result.status !== 'fulfilled') {
        roundsByInterview[interviewId] = []
        return
      }
      const payload = result.value as ApiResp<InterviewRoundItem[]>
      roundsByInterview[interviewId] = payload.code === 200 && Array.isArray(payload.data) ? payload.data : []
    })

    buildSummary(interviews, roundsByInterview)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载个人技术能力总览失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSummary()
})

watch(
  () => [detailVisible.value, activeCategory.value, activeTrendCount.value],
  async ([visible]) => {
    if (!visible) {
      disposeTrendChart()
      return
    }
    await nextTick()
    renderTrendChart()
  }
)

onBeforeUnmount(() => {
  disposeTrendChart()
})
</script>

<template>
  <section class="tech-overview">
    <div class="section-head">
      <div>
        <h2>第一部分 · 个人技术能力总览</h2>
        <p>统计口径：仅统计 followup_depth=0 的主问题，按技术题/场景题/项目题汇总展示。</p>
      </div>
      <button type="button" class="refresh-btn" :disabled="loading" @click="fetchSummary">
        {{ loading ? '统计中...' : '刷新统计' }}
      </button>
    </div>

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <div class="summary-grid">
      <article v-for="item in summaryCards" :key="item.key" class="summary-card">
        <div class="card-top">
          <h3>{{ item.label }}</h3>
          <span class="count-pill">{{ item.questionCount }} 题</span>
        </div>

        <div class="metric-list">
          <div v-for="(label, key) in SCORE_LABELS" :key="key" class="metric-row">
            <div class="metric-head">
              <span>{{ label }}</span>
              <strong>{{ formatScore(item.scores[key]) }}</strong>
            </div>
            <div class="metric-track">
              <div class="metric-fill" :style="scoreStyle(item.scores[key])" />
            </div>
          </div>
        </div>

        <button type="button" class="detail-btn" @click="openDetail(item.key)">查看变化过程</button>
      </article>
    </div>

    <teleport to="body">
      <div v-if="detailVisible" class="detail-mask" @click.self="closeDetail">
        <div class="detail-panel">
          <div class="detail-top">
            <div>
              <h3>{{ activeSummary?.label }}变化过程</h3>
              <p>按每场面试聚合（仅主问题）。</p>
            </div>
            <button type="button" class="close-btn" @click="closeDetail">关闭</button>
          </div>

          <div v-if="!activeSummary?.trend?.length" class="detail-empty">暂无变化数据</div>

          <div v-else class="trend-chart-wrap">
            <div class="chart-meta">
              <span>共 {{ activeSummary.trend.length }} 场面试参与统计</span>
              <span>横轴：面试日期 · 纵轴：分数（0-100）</span>
            </div>
            <div ref="trendChartRef" class="trend-chart" />
          </div>
        </div>
      </div>
    </teleport>
  </section>
</template>

<style scoped>
.tech-overview {
  margin-bottom: 0.95rem;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  padding: 0.95rem;
  background:
    radial-gradient(circle at 6% 12%, rgba(56, 189, 248, 0.18), transparent 42%),
    radial-gradient(circle at 94% 18%, rgba(16, 185, 129, 0.14), transparent 38%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.94), rgba(240, 249, 255, 0.9));
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  align-items: start;
}

.section-head h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.06rem;
}

.section-head p {
  margin: 0.22rem 0 0;
  color: #475569;
  font-size: 0.84rem;
}

.refresh-btn {
  border: 1px solid #93c5fd;
  background: #ffffff;
  color: #1d4ed8;
  border-radius: 9px;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
}

.refresh-btn:disabled {
  cursor: not-allowed;
  opacity: 0.64;
}

.error-banner {
  margin-top: 0.65rem;
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #991b1b;
  border-radius: 8px;
  padding: 0.62rem 0.78rem;
}

.summary-grid {
  margin-top: 0.75rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.7rem;
}

.summary-card {
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 12px;
  padding: 0.72rem;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.6rem;
}

.card-top h3 {
  margin: 0;
  color: #0f172a;
  font-size: 0.98rem;
}

.count-pill {
  border-radius: 999px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  padding: 0.12rem 0.52rem;
  font-size: 0.74rem;
}

.metric-list {
  margin-top: 0.6rem;
  display: grid;
  gap: 0.42rem;
}

.metric-row {
  display: grid;
  gap: 0.2rem;
}

.metric-head {
  display: flex;
  justify-content: space-between;
  font-size: 0.79rem;
  color: #334155;
}

.metric-head strong {
  color: #0f172a;
}

.metric-track {
  height: 7px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.metric-fill {
  height: 100%;
  border-radius: inherit;
  transition: width 0.4s ease;
}

.detail-btn {
  margin-top: 0.62rem;
  width: 100%;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 8px;
  padding: 0.36rem;
  cursor: pointer;
}

.detail-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  padding: 1rem;
}

.detail-panel {
  width: min(860px, 100%);
  max-height: calc(100vh - 2rem);
  overflow: auto;
  border-radius: 14px;
  border: 1px solid #dbeafe;
  background: #ffffff;
  padding: 0.92rem;
}

.detail-top {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  align-items: start;
}

.detail-top h3 {
  margin: 0;
  color: #0f172a;
}

.detail-top p {
  margin: 0.22rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
}

.close-btn {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  border-radius: 8px;
  padding: 0.38rem 0.72rem;
  cursor: pointer;
}

.detail-empty {
  margin-top: 0.8rem;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  text-align: center;
  color: #64748b;
  padding: 1rem;
}

.trend-chart-wrap {
  margin-top: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.65rem;
  background: #fcfdff;
}

.chart-meta {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  color: #475569;
  font-size: 0.8rem;
  margin-bottom: 0.42rem;
}

.trend-chart {
  width: 100%;
  height: 360px;
}

@media (max-width: 980px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .section-head {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .trend-chart {
    height: 300px;
  }

  .chart-meta {
    flex-direction: column;
    gap: 0.2rem;
  }
}
</style>
