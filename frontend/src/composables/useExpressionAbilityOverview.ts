import { computed, ref } from 'vue'
import api from '@/utils/api'
import type {
  ExpressionDimensionKey,
  ExpressionInsight,
  ExpressionOverviewApiResponse,
  ExpressionOverviewState,
  ExpressionTrendPoint,
  VoiceLlmResultRecord,
} from '@/types/expressionAbility'

const DIMENSION_KEYS: ExpressionDimensionKey[] = [
  'speech_rate_and_rhythm_score',
  'fluency_score',
  'confidence_and_voice_energy_score',
  'emotional_stability_and_tone_score',
]

const SAFE_RANGE_MIN = 0
const SAFE_RANGE_MAX = 100

const toSafeScore = (val: unknown): number | null => {
  if (typeof val !== 'number' || Number.isNaN(val)) {
    return null
  }
  return Math.max(SAFE_RANGE_MIN, Math.min(SAFE_RANGE_MAX, val))
}

const toTimestamp = (record: VoiceLlmResultRecord): number => {
  const source = record.generated_at || record.created_at || record.updated_at
  const ms = new Date(source).getTime()
  return Number.isNaN(ms) ? 0 : ms
}

const toDateLabel = (timestamp: number): string => {
  if (!timestamp) return '--'
  const d = new Date(timestamp)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const splitInsightText = (input: string): string[] => {
  if (!input) return []
  const segments = input
    .split(/\n|；|;|。|\.|\d+[、\.]/g)
    .map((item) => item.trim())
    .filter((item) => item.length > 1)
  return segments
}

const aggregateTopInsights = (inputs: string[], topN = 3): ExpressionInsight[] => {
  const counter = new Map<string, number>()
  inputs.forEach((chunk) => {
    splitInsightText(chunk).forEach((item) => {
      counter.set(item, (counter.get(item) || 0) + 1)
    })
  })

  return Array.from(counter.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([text, count]) => ({ text, count }))
}

const average = (nums: number[]): number | null => {
  if (!nums.length) return null
  const sum = nums.reduce((acc, val) => acc + val, 0)
  return Number((sum / nums.length).toFixed(1))
}

const defaultState = (): ExpressionOverviewState => ({
  currentScore: null,
  previousScore: null,
  scoreDelta: null,
  averageScore: null,
  sampleCount: 0,
  dimensionsAverage: {
    speech_rate_and_rhythm_score: null,
    fluency_score: null,
    confidence_and_voice_energy_score: null,
    emotional_stability_and_tone_score: null,
  },
  trend: [],
  strengthsTop: [],
  improvementsTop: [],
  positionTipsTop: [],
  encouragement: '',
  modelInfo: null,
})

export const useExpressionAbilityOverview = () => {
  const loading = ref(false)
  const errorMessage = ref('')
  const state = ref<ExpressionOverviewState>(defaultState())

  const hasData = computed(() => state.value.sampleCount > 0)

  const buildOverview = (records: VoiceLlmResultRecord[]) => {
    const successRecords = records
      .filter((item) => item.status === 'success')
      .map((item) => ({ ...item, safeOverall: toSafeScore(item.overall_audio_score) }))
      .filter((item) => item.safeOverall !== null)
      .sort((a, b) => toTimestamp(a) - toTimestamp(b))

    if (!successRecords.length) {
      state.value = defaultState()
      return
    }

    const trend: ExpressionTrendPoint[] = successRecords.map((item) => {
      const timestamp = toTimestamp(item)
      return {
        id: item.id,
        dateLabel: toDateLabel(timestamp),
        timestamp,
        overall: item.safeOverall as number,
        speech_rate_and_rhythm_score: toSafeScore(item.speech_rate_and_rhythm_score) ?? 0,
        fluency_score: toSafeScore(item.fluency_score) ?? 0,
        confidence_and_voice_energy_score:
          toSafeScore(item.confidence_and_voice_energy_score) ?? 0,
        emotional_stability_and_tone_score:
          toSafeScore(item.emotional_stability_and_tone_score) ?? 0,
      }
    })

    const latest = successRecords[successRecords.length - 1]
    if (!latest) {
      state.value = defaultState()
      return
    }
    const previous = successRecords.length > 1 ? successRecords[successRecords.length - 2] : null

    const dimensionAverage = DIMENSION_KEYS.reduce((obj, key) => {
      const values = successRecords
        .map((item) => toSafeScore(item[key]))
        .filter((v): v is number => v !== null)
      obj[key] = average(values)
      return obj
    }, {} as Record<ExpressionDimensionKey, number | null>)

    const allOveralls = successRecords
      .map((item) => item.safeOverall)
      .filter((v): v is number => v !== null)

    const currentScore = toSafeScore(latest.overall_audio_score)
    const previousScore = previous ? toSafeScore(previous.overall_audio_score) : null
    const scoreDelta =
      currentScore !== null && previousScore !== null
        ? Number((currentScore - previousScore).toFixed(1))
        : null

    state.value = {
      currentScore,
      previousScore,
      scoreDelta,
      averageScore: average(allOveralls),
      sampleCount: successRecords.length,
      dimensionsAverage: dimensionAverage,
      trend,
      strengthsTop: aggregateTopInsights(successRecords.map((item) => item.strengths)),
      improvementsTop: aggregateTopInsights(successRecords.map((item) => item.improvements)),
      positionTipsTop: aggregateTopInsights(
        successRecords.map((item) => item.position_communication_tips)
      ),
      encouragement: latest.encouragement || '',
      modelInfo: {
        llmModel: latest.llm_model || '--',
        promptVersion: latest.prompt_version || '--',
      },
    }
  }

  const fetchByEndpoint = async (endpoint: string) => {
    loading.value = true
    errorMessage.value = ''
    try {
      const resp = (await api.get(endpoint)) as ExpressionOverviewApiResponse
      if (resp.code !== 200) {
        throw new Error(resp.message || '获取表达能力数据失败')
      }
      const records = Array.isArray(resp.data?.records) ? resp.data!.records : []
      buildOverview(records)
    } catch (error) {
      state.value = defaultState()
      errorMessage.value = error instanceof Error ? error.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  const loadFromRecords = (records: VoiceLlmResultRecord[]) => {
    errorMessage.value = ''
    buildOverview(records)
  }

  return {
    loading,
    errorMessage,
    state,
    hasData,
    fetchByEndpoint,
    loadFromRecords,
  }
}
