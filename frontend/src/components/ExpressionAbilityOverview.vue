<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { useExpressionAbilityOverview } from '@/composables/useExpressionAbilityOverview'
import type {
  ExpressionDimensionMeta,
  ExpressionTrendPoint,
  VoiceLlmResultRecord,
} from '@/types/expressionAbility'

interface Props {
  apiEndpoint?: string
  records?: VoiceLlmResultRecord[]
  title?: string
  autoFetch?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  apiEndpoint: '/api/recommendations/expression-ability-overview/',
  records: () => [],
  title: '表达能力总览',
  autoFetch: true,
})

const dimensions: ExpressionDimensionMeta[] = [
  {
    key: 'speech_rate_and_rhythm_score',
    label: '语速与节奏',
    textField: 'speech_rate_and_rhythm',
  },
  {
    key: 'fluency_score',
    label: '流畅度',
    textField: 'fluency',
  },
  {
    key: 'confidence_and_voice_energy_score',
    label: '自信与能量',
    textField: 'confidence_and_voice_energy',
  },
  {
    key: 'emotional_stability_and_tone_score',
    label: '情绪稳定与语气',
    textField: 'emotional_stability_and_tone',
  },
]

const {
  loading,
  errorMessage,
  state,
  hasData,
  fetchByEndpoint,
  loadFromRecords,
} = useExpressionAbilityOverview()

const radarRef = ref<HTMLDivElement | null>(null)
const trendRef = ref<HTMLDivElement | null>(null)
const radarChart = ref<echarts.ECharts | null>(null)
const trendChart = ref<echarts.ECharts | null>(null)

const scoreUpperBound = computed(() => {
  const vals: number[] = []
  if (state.value.currentScore !== null) vals.push(state.value.currentScore)
  if (state.value.averageScore !== null) vals.push(state.value.averageScore)
  dimensions.forEach((dim) => {
    const v = state.value.dimensionsAverage[dim.key]
    if (v !== null) vals.push(v)
  })
  trendData.value.forEach((p) => {
    vals.push(
      p.overall,
      p.speech_rate_and_rhythm_score,
      p.fluency_score,
      p.confidence_and_voice_energy_score,
      p.emotional_stability_and_tone_score
    )
  })

  const maxVal = vals.length ? Math.max(...vals) : 0
  if (maxVal <= 5.5) return 5
  if (maxVal <= 10.5) return 10
  if (maxVal <= 20.5) return 20
  if (maxVal <= 50.5) return 50
  return 100
})

const scoreTone = computed(() => {
  const score = state.value.currentScore
  if (score === null) return 'neutral'
  const ratio = score / scoreUpperBound.value
  if (ratio >= 0.8) return 'strong'
  if (ratio >= 0.6) return 'mid'
  return 'risk'
})

const deltaText = computed(() => {
  const delta = state.value.scoreDelta
  if (delta === null) return '与上次暂无可比数据'
  if (delta > 0) return `较上次 +${delta.toFixed(1)}`
  if (delta < 0) return `较上次 ${delta.toFixed(1)}`
  return '较上次持平'
})

const currentScoreText = computed(() =>
  state.value.currentScore === null ? '--' : state.value.currentScore.toFixed(1)
)

const averageScoreText = computed(() =>
  state.value.averageScore === null ? '--' : state.value.averageScore.toFixed(1)
)

const radarValues = computed(() =>
  dimensions.map((dim) => state.value.dimensionsAverage[dim.key] ?? 0)
)

const trendData = computed<ExpressionTrendPoint[]>(() => state.value.trend)

const scoreBarStyle = (score: number | null) => {
  const safe = score ?? 0
  const ratio = Math.max(0, Math.min(1, safe / scoreUpperBound.value))
  const hue = Math.round(6 + ratio * 132)
  return {
    width: `${Math.round(ratio * 100)}%`,
    background: `linear-gradient(90deg, hsl(${hue} 74% 56%), hsl(${hue} 78% 44%))`,
  }
}

const formatScore = (score: number | null) => {
  if (score === null) return '--'
  return score.toFixed(1)
}

const ensureRadar = () => {
  if (!radarRef.value) return null
  if (!radarChart.value) {
    radarChart.value = echarts.init(radarRef.value)
  }
  return radarChart.value
}

const ensureTrend = () => {
  if (!trendRef.value) return null
  if (!trendChart.value) {
    trendChart.value = echarts.init(trendRef.value)
  }
  return trendChart.value
}

const renderRadar = () => {
  const chart = ensureRadar()
  if (!chart) return

  if (!hasData.value) {
    chart.clear()
    return
  }

  chart.setOption({
    radar: {
      center: ['50%', '54%'],
      radius: 95,
      splitNumber: 5,
      axisName: { color: '#66756f', fontSize: 12, fontWeight: 500 },
      splitArea: {
        areaStyle: {
          color: ['rgba(235,248,242,0.4)', 'rgba(204,227,219,0.3)'],
        },
      },
      axisLine: { lineStyle: { color: '#cce3db' } },
      splitLine: { lineStyle: { color: '#cce3db' } },
      indicator: dimensions.map((dim) => ({ name: dim.label, max: scoreUpperBound.value })),
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: radarValues.value,
            name: '平均表现',
            areaStyle: { color: 'rgba(47,93,86,0.2)' },
            lineStyle: { color: '#2f5d56', width: 2.5 },
            itemStyle: { color: '#2f5d56', borderWidth: 2 },
            symbolSize: 6,
          },
        ],
      },
    ],
  })
}

const renderTrend = () => {
  const chart = ensureTrend()
  if (!chart) return

  if (!trendData.value.length) {
    chart.clear()
    return
  }

  const x = trendData.value.map((item) => item.dateLabel)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: string | number) =>
        typeof value === 'number' ? value.toFixed(1) : '--',
    },
    legend: {
      top: 2,
      textStyle: { color: '#334155' },
    },
    grid: { left: 40, right: 18, top: 42, bottom: 26 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: x,
      axisLabel: { color: '#64748b', fontSize: 11 },
      axisLine: { lineStyle: { color: '#cbd5e1' } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: scoreUpperBound.value,
      axisLabel: { color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
    },
    series: [
      {
        name: '总分',
        type: 'line',
        smooth: true,
        data: trendData.value.map((item) => item.overall),
        lineStyle: { color: '#2563eb', width: 2.4 },
        itemStyle: { color: '#2563eb' },
      },
      {
        name: '语速节奏',
        type: 'line',
        smooth: true,
        data: trendData.value.map((item) => item.speech_rate_and_rhythm_score),
        lineStyle: { color: '#0ea5e9', width: 1.8 },
        itemStyle: { color: '#0ea5e9' },
      },
      {
        name: '流畅度',
        type: 'line',
        smooth: true,
        data: trendData.value.map((item) => item.fluency_score),
        lineStyle: { color: '#16a34a', width: 1.8 },
        itemStyle: { color: '#16a34a' },
      },
      {
        name: '自信能量',
        type: 'line',
        smooth: true,
        data: trendData.value.map((item) => item.confidence_and_voice_energy_score),
        lineStyle: { color: '#f97316', width: 1.8 },
        itemStyle: { color: '#f97316' },
      },
      {
        name: '情绪语气',
        type: 'line',
        smooth: true,
        data: trendData.value.map((item) => item.emotional_stability_and_tone_score),
        lineStyle: { color: '#a855f7', width: 1.8 },
        itemStyle: { color: '#a855f7' },
      },
    ],
  })
}

const disposeCharts = () => {
  if (radarChart.value) {
    radarChart.value.dispose()
    radarChart.value = null
  }
  if (trendChart.value) {
    trendChart.value.dispose()
    trendChart.value = null
  }
}

const refresh = async () => {
  if (props.records && props.records.length) {
    loadFromRecords(props.records)
    return
  }

  if (!props.autoFetch) {
    loadFromRecords([])
    return
  }

  await fetchByEndpoint(props.apiEndpoint)
}

onMounted(async () => {
  await refresh()
})

watch(
  () => [hasData.value, trendData.value.length, state.value.currentScore],
  async () => {
    await nextTick()
    renderRadar()
    renderTrend()
  }
)

watch(
  () => props.records,
  (newRecords) => {
    if (newRecords && newRecords.length) {
      loadFromRecords(newRecords)
    }
  },
  { deep: true }
)

onBeforeUnmount(() => {
  disposeCharts()
})
</script>

<template>
  <section class="expression-overview">
    <header class="head">
      <div>
        <h2>{{ title }}</h2>
        <p>基于语音 LLM 评估结果，聚合表达能力趋势与关键改进方向。</p>
      </div>
      <button type="button" class="refresh-btn" :disabled="loading" @click="refresh">
        {{ loading ? '加载中...' : '刷新' }}
      </button>
    </header>

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <div v-if="hasData" class="score-strip">
      <article :class="['score-card', scoreTone]">
        <h3>当前表达总分</h3>
        <strong>{{ currentScoreText }}</strong>
        <p>{{ deltaText }}</p>
      </article>
      <article class="score-card neutral">
        <h3>历史平均分</h3>
        <strong>{{ averageScoreText }}</strong>
        <p>有效样本 {{ state.sampleCount }} 场</p>
      </article>
    </div>

    <div v-if="hasData" class="main-grid">
      <article class="panel dimension-panel">
        <h3>四维能力画像</h3>
        <p class="range-hint">当前量程: 0 - {{ scoreUpperBound }}</p>
        <div ref="radarRef" class="radar" />
        <div class="dimension-bars">
          <div v-for="dim in dimensions" :key="dim.key" class="bar-row">
            <div class="bar-head">
              <span>{{ dim.label }}</span>
              <strong>{{ formatScore(state.dimensionsAverage[dim.key]) }}</strong>
            </div>
            <div class="bar-track">
              <div class="bar-fill" :style="scoreBarStyle(state.dimensionsAverage[dim.key])" />
            </div>
          </div>
        </div>
      </article>

      <article class="panel trend-panel">
        <h3>变化趋势</h3>
        <p class="range-hint">当前量程: 0 - {{ scoreUpperBound }}</p>
        <div ref="trendRef" class="trend" />
      </article>
    </div>

    <div v-if="hasData" class="insight-grid">
      <article class="panel insight-panel">
        <h3>高频优势</h3>
        <ul>
          <li v-for="item in state.strengthsTop" :key="item.text">
            <span>{{ item.text }}</span>
            <em>×{{ item.count }}</em>
          </li>
          <li v-if="!state.strengthsTop.length" class="muted">暂无优势摘要</li>
        </ul>
      </article>

      <article class="panel insight-panel">
        <h3>优先改进</h3>
        <ul>
          <li v-for="item in state.improvementsTop" :key="item.text">
            <span>{{ item.text }}</span>
            <em>×{{ item.count }}</em>
          </li>
          <li v-if="!state.improvementsTop.length" class="muted">暂无改进摘要</li>
        </ul>
      </article>

      <article class="panel insight-panel">
        <h3>岗位沟通建议</h3>
        <ul>
          <li v-for="item in state.positionTipsTop" :key="item.text">
            <span>{{ item.text }}</span>
            <em>×{{ item.count }}</em>
          </li>
          <li v-if="!state.positionTipsTop.length" class="muted">暂无岗位建议</li>
        </ul>
      </article>
    </div>

    <article v-if="hasData && state.encouragement" class="panel encouragement">
      <h3>鼓励反馈</h3>
      <p>{{ state.encouragement }}</p>
    </article>

    <section v-if="!loading && !hasData" class="empty">
      <h3>暂无表达能力数据</h3>
      <p>当语音 LLM 结果写入后，该模块会自动展示表达能力总览。</p>
    </section>
  </section>
</template>

<style scoped>
.expression-overview {
  border: 1px solid #1a332f;
  border-radius: 16px;
  padding: 1rem;
  background:
    radial-gradient(circle at 12% 8%, rgba(255, 255, 255, 0.08), transparent 38%),
    radial-gradient(circle at 88% 88%, rgba(204, 227, 219, 0.12), transparent 42%),
    linear-gradient(135deg, #2f5d56, #234741);
  box-shadow: 0 6px 20px rgba(47, 93, 86, 0.2);
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 0.8rem;
}

.head h2 {
  margin: 0;
  color: #ffffff;
  font-size: 1.12rem;
}

.head p {
  margin: 0.22rem 0 0;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.86rem;
}

.refresh-btn {
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  color: #ffffff;
  border-radius: 9px;
  padding: 0.42rem 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.25);
  color: white;
}

.refresh-btn:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.error-banner {
  margin-top: 0.65rem;
  border: 1px solid #ffcdd2;
  background: #fff5f5;
  color: #d32f2f;
  border-radius: 8px;
  padding: 0.64rem 0.82rem;
}

.score-strip {
  margin-top: 0.75rem;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.62rem;
}

.score-card {
  border-radius: 12px;
  padding: 0.66rem 0.72rem;
  border: 1px solid #cce3db;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 15px rgba(47, 93, 86, 0.03);
}

.score-card h3 {
  margin: 0;
  color: #66756f;
  font-size: 0.84rem;
}

.score-card strong {
  display: block;
  margin-top: 0.35rem;
  font-size: 1.34rem;
  color: #1f2926;
}

.score-card p {
  margin: 0.15rem 0 0;
  color: #66756f;
  font-size: 0.78rem;
}

.score-card.strong {
  border-color: rgba(47, 93, 86, 0.3);
  background: linear-gradient(145deg, #e6f2eb, #cce3db);
}

.score-card.mid {
  border-color: rgba(217, 119, 6, 0.3);
  background: linear-gradient(145deg, #fffbeb, #fef3c7);
}

.score-card.risk {
  border-color: rgba(220, 38, 38, 0.3);
  background: linear-gradient(145deg, #fef2f2, #fee2e2);
}

.main-grid {
  margin-top: 0.72rem;
  display: grid;
  grid-template-columns: minmax(320px, 0.95fr) minmax(360px, 1.05fr);
  gap: 0.65rem;
}

.panel {
  border: 1px solid #cce3db;
  border-radius: 12px;
  padding: 0.7rem;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 15px rgba(47, 93, 86, 0.02);
}

.panel h3 {
  margin: 0;
  color: #1f2926;
  font-size: 0.95rem;
}

.range-hint {
  margin: 0.26rem 0 0;
  color: #64748b;
  font-size: 0.76rem;
}

.radar {
  width: 100%;
  height: 255px;
}

.dimension-bars {
  display: grid;
  gap: 0.35rem;
}

.bar-row {
  display: grid;
  gap: 0.18rem;
}

.bar-head {
  display: flex;
  justify-content: space-between;
  color: #334155;
  font-size: 0.8rem;
}

.bar-head strong {
  color: #0f172a;
}

.bar-track {
  width: 100%;
  height: 7px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: inherit;
}

.trend {
  width: 100%;
  height: 360px;
}

.insight-grid {
  margin-top: 0.7rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.6rem;
}

.insight-panel ul {
  margin: 0.55rem 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.38rem;
}

.insight-panel li {
  display: flex;
  justify-content: space-between;
  gap: 0.6rem;
  font-size: 0.82rem;
  color: #334155;
  border-radius: 8px;
  padding: 0.34rem 0.46rem;
  background: rgba(241, 245, 249, 0.65);
}

.insight-panel li em {
  font-style: normal;
  color: #64748b;
  white-space: nowrap;
}

.insight-panel .muted {
  color: #94a3b8;
}

.encouragement {
  margin-top: 0.68rem;
}

.encouragement p {
  margin: 0.45rem 0 0;
  color: #334155;
  line-height: 1.6;
}

.empty {
  margin-top: 0.8rem;
  text-align: center;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.7);
}

.empty h3 {
  margin: 0;
  color: #334155;
}

.empty p {
  margin: 0.42rem 0 0;
  color: #64748b;
}

@media (max-width: 1060px) {
  .score-strip,
  .insight-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .main-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .head {
    flex-direction: column;
  }

  .score-strip,
  .insight-grid {
    grid-template-columns: 1fr;
  }

  .trend {
    height: 300px;
  }
}
</style>
