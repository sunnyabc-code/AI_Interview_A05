<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'

interface RoundInfo {
    id: string
    roundNumber: number
    label: string
    interviewerQuestion: string
    yourAnswer: string
    audioFileUrl: string | null
    overall_score: number | null
    overall_comment: string | null
    technical_score: number | null
    communication_score: number | null
    logic_score: number | null
    adaptability_score: number | null
    summary: string
    highlights: string[]
    weaknesses: string[]
    suggestions: string[]
    audioAnalysis?: RoundAudioAnalysis | null
}

interface VoiceAnalysis {
    duration_seconds: number | null
    speech_rate: number | null
    speech_rate_level: string | null
    audio_clarity_score: number | null
    confidence_score: number | null
    emotion: string | null
    filler_word_total: number | null
    filler_word_counts: Record<string, number> | null
    silence_ratio: number | null
    silence_ratio_level: string | null
    imentiv_emotion_analysis?: {
        overall?: {
            audio?: Record<string, number> | null
        } | null
    } | null
    audio?: Record<string, number> | null
}

interface RoundAudioAnalysis {
    round_id: number
    audio_data?: {
        voice_analysis?: VoiceAnalysis | null
    } | null
}

interface RoundAudioAnalysisApiResponse {
    code: number
    message: string
    data?: RoundAudioAnalysis
}

interface InterviewHistoryItem {
    id: string
    title: string
    date: string
    position: string
    mode: string
    status: string
    duration_seconds: number | null
    rounds: RoundInfo[]
}

interface InterviewListApiItem {
    id: number
    name: string
    position_name: string
    mode?: string | null
    status: string
    start_time: string | null
    created_at: string
    duration_seconds?: number | null
}

interface InterviewRoundApiItem {
    round_id: number
    interview_id: number
    round_number: number
    chain_index: number
    followup_depth: number
    category: string
    category_name: string | null
    question_id: number | null
    question_content: string | null
    user_answer: string | null
    audio_file_url?: string | null
    start_time: string | null
    end_time: string | null
    created_at: string
    analysis?: {
        overall_score: number | null
        overall_comment: string | null
        technical_score: number | null
        communication_score: number | null
        logic_score: number | null
        adaptability_score: number | null
        highlights: string[]
        weaknesses: string[]
        suggestions: string[]
    } | null
}

interface RoundNavItem {
    id: string
    label: string
}

interface VoiceLLMResultData {
    id: number
    status: string
    overall_audio_score: number | string | null
    speech_rate_and_rhythm_score: number | string | null
    speech_rate_and_rhythm: string | null
    fluency_score: number | string | null
    fluency: string | null
    confidence_and_voice_energy_score: number | string | null
    confidence_and_voice_energy: string | null
    emotional_stability_and_tone_score: number | string | null
    emotional_stability_and_tone: string | null
    strengths: string | null
    improvements: string | null
    position_communication_tips: string | null
    encouragement: string | null
}

interface VoiceLLMResultApiResponse {
    code: number
    message: string
    data?: {
        interview_id: number
        voice_llm_result: VoiceLLMResultData | null
    }
}

type LevelTone = 'excellent' | 'good' | 'warning' | 'danger' | 'neutral'

interface LevelDisplay {
    label: string
    tone: LevelTone
    hint: string
}

const router = useRouter()

const API_BASE_URL = 'http://localhost:8000'

const interviewHistory = ref<InterviewHistoryItem[]>([])
const historySearchKeyword = ref('')
const historyDateStart = ref('')
const historyDateEnd = ref('')
const historyDateStartInputType = ref<'text' | 'date'>('text')
const historyDateEndInputType = ref<'text' | 'date'>('text')
const loadingInterviews = ref(false)
const interviewError = ref('')
const loadingRounds = ref(false)
const roundError = ref('')
const loadedRoundInterviewIds = ref<Set<string>>(new Set())
const loadingAudioRoundIds = ref<Set<string>>(new Set())
const audioAnalysisErrors = ref<Record<string, string>>({})
const voiceLlmResultMap = ref<Record<string, VoiceLLMResultData | null>>({})
const loadingVoiceLlmInterviewIds = ref<Set<string>>(new Set())
const voiceLlmErrors = ref<Record<string, string>>({})
const voiceLlmWaitingMap = ref<Record<string, boolean>>({})
const voiceLlmPollTimerMap = new Map<string, number>()
const OVERVIEW_ROUND_ID = 'overview-summary'
const radarChartRef = ref<HTMLDivElement | null>(null)
const radarChartInstance = ref<echarts.ECharts | null>(null)
const scoreLineChartRef = ref<HTMLDivElement | null>(null)
const scoreLineChartInstance = ref<echarts.ECharts | null>(null)
const emotionChartRef = ref<HTMLDivElement | null>(null)
const emotionChartInstance = ref<echarts.ECharts | null>(null)
const voiceScoreGaugeChartRef = ref<HTMLDivElement | null>(null)
const voiceScoreGaugeChartInstance = ref<echarts.ECharts | null>(null)

const selectedInterviewId = ref(interviewHistory.value[0]?.id ?? '')
const selectedRoundId = ref(OVERVIEW_ROUND_ID)

const selectedInterview = computed(() =>
    interviewHistory.value.find(item => item.id === selectedInterviewId.value)
)

const isVoiceEnabledInterviewMode = (mode: string | null | undefined) => mode === 'voice' || mode === 'mixed'

const selectedInterviewSupportsVoice = computed(() =>
    isVoiceEnabledInterviewMode(selectedInterview.value?.mode)
)

const parseDateToDayStart = (dateText: string): Date | null => {
    const date = new Date(dateText)
    if (Number.isNaN(date.getTime())) {
        return null
    }

    date.setHours(0, 0, 0, 0)
    return date
}

const filteredInterviewHistory = computed(() => {
    const keyword = historySearchKeyword.value.trim().toLowerCase()
    const startDate = historyDateStart.value ? parseDateToDayStart(`${historyDateStart.value}T00:00:00`) : null
    const endDate = historyDateEnd.value ? parseDateToDayStart(`${historyDateEnd.value}T00:00:00`) : null

    return interviewHistory.value.filter(item => {
        const keywordMatched =
            !keyword ||
            item.title.toLowerCase().includes(keyword) ||
            item.position.toLowerCase().includes(keyword)

        if (!keywordMatched) {
            return false
        }

        if (!startDate && !endDate) {
            return true
        }

        const itemDate = parseDateToDayStart(item.date)
        if (!itemDate) {
            return false
        }

        if (startDate && itemDate < startDate) {
            return false
        }

        if (endDate && itemDate > endDate) {
            return false
        }

        return true
    })
})

const hasActiveHistoryFilters = computed(
    () => !!historySearchKeyword.value.trim() || !!historyDateStart.value || !!historyDateEnd.value
)

const selectedRound = computed(() =>
    selectedInterview.value?.rounds.find(round => round.id === selectedRoundId.value)
)

function nonEmptyStringList(items: string[] | null | undefined): string[] {
    return (items ?? []).map((s) => String(s ?? '').trim()).filter((s) => s.length > 0)
}

const selectedRoundHighlightLines = computed(() => nonEmptyStringList(selectedRound.value?.highlights))

const selectedRoundAudioSrc = computed(() => {
    const audioFileUrl = selectedRound.value?.audioFileUrl
    if (!audioFileUrl) {
        return ''
    }

    const trimmedUrl = audioFileUrl.trim()
    if (!trimmedUrl) {
        return ''
    }

    if (/^https?:\/\//i.test(trimmedUrl)) {
        return trimmedUrl
    }

    return `${API_BASE_URL}${trimmedUrl.startsWith('/') ? '' : '/'}${trimmedUrl}`
})

const isOverviewSelected = computed(() => selectedRoundId.value === OVERVIEW_ROUND_ID)

const selectedVoiceAnalysis = computed<VoiceAnalysis | null>(
    () => selectedRound.value?.audioAnalysis?.audio_data?.voice_analysis ?? null
)

const scoreBars = computed(() => {
    const round = selectedRound.value
    if (!round) {
        return []
    }

    const toSafeScore = (value: number | null) => {
        if (typeof value !== 'number' || Number.isNaN(value)) {
            return null
        }
        return Math.max(0, Math.min(100, value))
    }

    const technical = toSafeScore(round.technical_score)
    const communication = toSafeScore(round.communication_score)
    const logic = toSafeScore(round.logic_score)
    const adaptability = toSafeScore(round.adaptability_score)

    return [
        {
            key: 'technical',
            label: '技术深度',
            value: technical,
            rawValue: round.technical_score
        },
        {
            key: 'communication',
            label: '沟通能力',
            value: communication,
            rawValue: round.communication_score
        },
        {
            key: 'logic',
            label: '逻辑思维',
            value: logic,
            rawValue: round.logic_score
        },
        {
            key: 'adaptability',
            label: '应变能力',
            value: adaptability,
            rawValue: round.adaptability_score
        }
    ]
})

type ScoreTone = {
    fillStart: string
    fillEnd: string
    chipBg: string
    chipBorder: string
    chipText: string
    glow: string
}

const getScoreTone = (value: number | null): ScoreTone => {
    if (typeof value !== 'number' || Number.isNaN(value)) {
        return {
            fillStart: 'hsl(160 8% 60%)',
            fillEnd: 'hsl(160 8% 42%)',
            chipBg: 'linear-gradient(130deg, #f2f4f3, #e7ecea)',
            chipBorder: '#ced7d3',
            chipText: '#51625c',
            glow: 'rgba(80, 98, 92, 0.2)'
        }
    }

    const safeScore = Math.max(0, Math.min(100, value))
    const ratio = safeScore / 100
    const hue = 18 + ratio * 145

    return {
        fillStart: `hsl(${hue.toFixed(1)} 82% 57%)`,
        fillEnd: `hsl(${hue.toFixed(1)} 70% 35%)`,
        chipBg: `linear-gradient(130deg, hsl(${hue.toFixed(1)} 76% 95%), hsl(${hue.toFixed(1)} 62% 88%))`,
        chipBorder: `hsl(${hue.toFixed(1)} 46% 72%)`,
        chipText: `hsl(${hue.toFixed(1)} 50% 26%)`,
        glow: `hsla(${hue.toFixed(1)} 72% 40% / 0.24)`
    }
}

const getScoreVisualStyle = (value: number | null, index: number): Record<string, string> => {
    const tone = getScoreTone(value)
    return {
        '--score-delay': `${index * 90}ms`,
        '--score-fill-start': tone.fillStart,
        '--score-fill-end': tone.fillEnd,
        '--score-chip-bg': tone.chipBg,
        '--score-chip-border': tone.chipBorder,
        '--score-chip-text': tone.chipText,
        '--score-glow': tone.glow
    }
}

const emotionLabelMap: Record<string, string> = {
    sad: '悲伤',
    calm: '平静',
    fear: '恐惧',
    angry: '愤怒',
    happy: '开心',
    disgust: '厌恶',
    neutral: '中性',
    surprise: '惊讶'
}

const emotionPieData = computed(() => {
    const voice = selectedVoiceAnalysis.value
    const audioEmotion =
        voice?.imentiv_emotion_analysis?.overall?.audio ||
        voice?.audio ||
        null

    if (!audioEmotion || typeof audioEmotion !== 'object') {
        return []
    }

    return Object.entries(audioEmotion)
        .filter(([, value]) => typeof value === 'number' && !Number.isNaN(value) && value > 0)
        .map(([emotionKey, value]) => ({
            name: emotionLabelMap[emotionKey] || emotionKey,
            value: Number((value * 100).toFixed(2))
        }))
})

const emotionPieOption = computed<echarts.EChartsOption>(() => ({
    tooltip: {
        trigger: 'item'
    },
    legend: {
        top: '5%',
        left: 'center'
    },
    series: [
        {
            name: 'Access From',
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            // itemStyle: {
            //     borderRadius: 10,
            //     borderColor: '#fff',
            //     borderWidth: 2
            // },
            // label: {
            //     show: false,
            //     position: 'center'
            // },
            // emphasis: {
            //     label: {
            //         show: true,
            //         fontSize: 40,
            //         fontWeight: 'bold'
            //     }
            // },
            // labelLine: {
            //     show: false
            // },
            label: {
                show: false,
                position: 'center'
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 40,
                    fontWeight: 'bold'
                }
            },
            labelLine: {
                show: false
            },
            data: emotionPieData.value
        }
    ]
}))

const isSelectedRoundAudioLoading = computed(() => loadingAudioRoundIds.value.has(selectedRoundId.value))

const selectedRoundAudioError = computed(() => audioAnalysisErrors.value[selectedRoundId.value] || '')

const roundNavItems = computed<RoundNavItem[]>(() => {
    if (!selectedInterview.value) {
        return []
    }
    return [{ id: OVERVIEW_ROUND_ID, label: '总览总结' }, ...selectedInterview.value.rounds]
})

const overviewRoundCount = computed(() => selectedInterview.value?.rounds.length ?? 0)

const overviewAnsweredCount = computed(
    () => selectedInterview.value?.rounds.filter(round => round.yourAnswer !== '暂无作答内容').length ?? 0
)

const overviewCategorySummary = computed(() => {
    if (!selectedInterview.value?.rounds.length) {
        return '暂无轮次数据'
    }

    const categories = selectedInterview.value.rounds.map(round =>
        round.summary.replace('题型：', '')
    )
    return categories.slice(0, 3).join('；')
})

const overviewInterviewDurationText = computed(() => {
    const durationSeconds = selectedInterview.value?.duration_seconds

    if (typeof durationSeconds !== 'number' || Number.isNaN(durationSeconds) || durationSeconds < 0) {
        return '暂无数据'
    }

    const totalSeconds = Math.floor(durationSeconds)
    const hours = Math.floor(totalSeconds / 3600)
    const minutes = Math.floor((totalSeconds % 3600) / 60)
    const seconds = totalSeconds % 60

    if (hours > 0) {
        return `${hours}小时${minutes}分${seconds}秒`
    }

    return `${minutes}分${seconds}秒`
})

const selectedInterviewVoiceLlmResult = computed<VoiceLLMResultData | null>(() => {
    const interviewId = selectedInterviewId.value
    if (!interviewId) {
        return null
    }
    return voiceLlmResultMap.value[interviewId] ?? null
})

const isSelectedInterviewVoiceLlmLoading = computed(() =>
    loadingVoiceLlmInterviewIds.value.has(selectedInterviewId.value)
)

const selectedInterviewVoiceLlmError = computed(() =>
    voiceLlmErrors.value[selectedInterviewId.value] || ''
)

const isSelectedInterviewVoiceLlmWaiting = computed(() =>
    !!voiceLlmWaitingMap.value[selectedInterviewId.value]
)

const voiceLlmScoreItems = computed(() => {
    const result = selectedInterviewVoiceLlmResult.value
    if (!result) {
        return []
    }

    return [
        { key: 'overall_audio_score', label: '整体语音表现:', value: result.overall_audio_score },
        { key: 'speech_rate_and_rhythm_score', label: '语速与节奏评分', value: result.speech_rate_and_rhythm_score },
        { key: 'fluency_score', label: '回答流畅度评分', value: result.fluency_score },
        {
            key: 'confidence_and_voice_energy_score',
            label: '自信度与声音能量评分',
            value: result.confidence_and_voice_energy_score
        },
        {
            key: 'emotional_stability_and_tone_score',
            label: '情绪稳定与语气评分',
            value: result.emotional_stability_and_tone_score
        }
    ]
})

const voiceLlmAnalysisItems = computed(() => {
    const result = selectedInterviewVoiceLlmResult.value
    if (!result) {
        return []
    }

    return [
        {
            key: 'speech_rate_and_rhythm',
            label: '语速与面试节奏',
            value: result.speech_rate_and_rhythm
        },
        { key: 'fluency', label: '流畅度', value: result.fluency },
        {
            key: 'confidence_and_voice_energy',
            label: '自信度与声音能量',
            value: result.confidence_and_voice_energy
        },
        {
            key: 'emotional_stability_and_tone',
            label: '情绪稳定性与语气',
            value: result.emotional_stability_and_tone
        }
    ]
})

const voiceLlmSuggestionItems = computed(() => {
    const result = selectedInterviewVoiceLlmResult.value
    if (!result) {
        return []
    }

    return [
        { key: 'strengths', label: '优势亮点', value: result.strengths },
        { key: 'improvements', label: '改进建议', value: result.improvements },
        {
            key: 'position_communication_tips',
            label: '岗位沟通建议',
            value: result.position_communication_tips
        }
    ]
})

const parseVoiceLlmGaugeScore = (value: number | string | null) => {
    const numericValue = typeof value === 'string' ? Number(value) : value
    if (typeof numericValue !== 'number' || Number.isNaN(numericValue)) {
        return null
    }

    return Math.max(0, Math.min(100, numericValue))
}

const voiceGaugeColorByKey: Record<string, string> = {
    overall_audio_score: '#ef4444',
    speech_rate_and_rhythm_score: '#f59e0b',
    fluency_score: '#22c55e',
    confidence_and_voice_energy_score: '#3b82f6',
    emotional_stability_and_tone_score: '#8b5cf6'
}

const getVoiceGaugeColor = (key: string) => voiceGaugeColorByKey[key] || '#64748b'

const voiceLlmGaugeItems = computed(() =>
    voiceLlmScoreItems.value
        .map(item => ({
            ...item,
            rawValue: parseVoiceLlmGaugeScore(item.value),
            color: getVoiceGaugeColor(item.key)
        }))
        .filter(item => item.rawValue !== null)
)


const buildVoiceScoreGaugeOption = (): echarts.EChartsOption => {
    const mainGaugeItem = voiceLlmGaugeItems.value.find(item => item.key === 'overall_audio_score')
    const mainGaugeColor = mainGaugeItem?.color || '#ef4444'
    const gaugeColorByLabel = voiceLlmGaugeItems.value.reduce<Record<string, string>>((acc, item) => {
        acc[item.label] = item.color
        return acc
    }, {})

    const secondaryGaugeItems = voiceLlmGaugeItems.value.filter(
        item => item.key !== 'overall_audio_score'
    )

    const pointerSeries = secondaryGaugeItems.map((item, index): echarts.GaugeSeriesOption => ({
        type: 'gauge' as const,
        startAngle: 180,
        endAngle: 0,
        center: ['50%', '75%'],
        radius: '100%',
        min: 0,
        max: 100,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },

        pointer: {
            icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
            length: '60%',
            width: 5,
            offsetCenter: [0, '-10%'],
            itemStyle: {
                color: item.color,
                shadowBlur: 6,
                shadowColor: item.color,
                shadowOffsetY: 3
            }
        },

        anchor: {
            show: true,
            showAbove: true,
            size: 8,
            itemStyle: {
                color: '#ffffff',
                borderColor: item.color,
                borderWidth: 2.5
            }
        },

        title: { show: false },
        detail: { show: false },

        data: [{
            value: item.rawValue ?? 0,
            name: item.label || `指标${index + 1}`
        }],

        emphasis: {
            focus: 'series' as const,
            blurScope: 'coordinateSystem' as const,
            itemStyle: {
                shadowBlur: 20,
                shadowColor: item.color,
                shadowOffsetY: 4
            }
        },

        animationDuration: 600 + index * 80,
        animationEasing: 'cubicOut' as const
    }))

    const mainGaugeSeries: echarts.GaugeSeriesOption = {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        center: ['50%', '75%'],
        radius: '92%',
        min: 0,
        max: 100,
        splitNumber: 8,                    // 增加细分刻度
        axisLine: {
            lineStyle: {
                width: 18,
                color: [
                    [0.25, '#FF6E76'],   // 较差
                    [0.5, '#FDDD60'],   // 一般
                    [0.75, '#58D9F9'],   // 良好
                    [1, '#7CFFB2']    // 优秀
                ]
            }
        },
        pointer: {
            show: true,
            icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
            length: '65%',
            width: 7,
            offsetCenter: [0, '-30%'],
            itemStyle: {
                color: mainGaugeColor,
                shadowBlur: 10,
                shadowColor: mainGaugeColor,
                shadowOffsetY: 3
            }
        },
        anchor: {
            show: true,
            showAbove: true,
            size: 9,
            itemStyle: {
                color: '#ffffff',
                borderColor: mainGaugeColor,
                borderWidth: 3
            }
        },
        // === 新增：刻度线 ===
        axisTick: {
            show: true,
            splitNumber: 4,               // 每个大段内细分小刻度
            length: 12,
            lineStyle: {
                color: '#94a3b8',
                width: 1.5
            }
        },
        splitLine: {
            show: true,
            length: 22,
            lineStyle: {
                color: '#64748b',
                width: 3
            }
        },
        // === 等级文字标签（优秀、良好、一般、较差）===
        axisLabel: {
            show: true,
            distance: -48,                // 标签向外距离，可微调
            fontSize: 15,
            fontWeight: 600,
            color: '#334155',
            rotate: 'tangential' as const,
            formatter: (value: number) => {
                if (Math.abs(value - 0) < 0.5) return '0'
                if (Math.abs(value - 50) < 0.5) return '50'
                if (Math.abs(value - 100) < 0.5) return '100'
                if (Math.abs(value - 87.5) < 1) return '优秀'
                if (Math.abs(value - 62.5) < 1) return '良好'
                if (Math.abs(value - 37.5) < 1) return '一般'
                if (Math.abs(value - 12.5) < 1) return '较差'
                return ''
            }
        },

        title: {
            show: true,
            offsetCenter: [0, '-28%'],
            fontSize: 22,
            fontWeight: 600,
            color: '#1e2937'
        },
    }

    return {
        backgroundColor: '#ffffff',
        tooltip: {
            trigger: 'item',
            confine: true,
            backgroundColor: 'transparent',
            borderWidth: 0,
            padding: 0,
            formatter: (params: unknown) => {
                const point = Array.isArray(params) ? params[0] : params
                const pointRecord = (point ?? {}) as Record<string, unknown>
                const label = typeof pointRecord.name === 'string' ? pointRecord.name : '指标'
                const rawValue = typeof pointRecord.value === 'number' ? pointRecord.value : Number(pointRecord.value)
                const valueText = Number.isFinite(rawValue) ? rawValue.toFixed(2) : '--'
                const markerColor = gaugeColorByLabel[label] || mainGaugeColor

                return `
                    <div style="display:flex;align-items:center;gap:8px;min-width:180px;padding:10px 12px;border-radius:10px;border:1.5px solid ${markerColor};background:#ffffff;box-shadow:0 8px 18px rgba(15, 23, 42, 0.12);">
                        <span style="width:12px;height:12px;border-radius:999px;background:${markerColor};display:inline-block;"></span>
                        <span style="color:#334155;">${label}</span>
                        <strong style="margin-left:auto;color:#334155;">${valueText}</strong>
                    </div>
                `
            }
        },
        series: [
            mainGaugeSeries,
            ...pointerSeries
        ]
    }
}

const disposeVoiceLlmGauges = () => {
    voiceScoreGaugeChartInstance.value?.dispose()
    voiceScoreGaugeChartInstance.value = null
}

const renderVoiceLlmGauges = async () => {
    if (!isOverviewSelected.value || !voiceLlmGaugeItems.value.length) {
        disposeVoiceLlmGauges()
        return
    }

    await nextTick()

    if (!voiceScoreGaugeChartRef.value) {
        return
    }

    try {
        if (!voiceScoreGaugeChartInstance.value || voiceScoreGaugeChartInstance.value.isDisposed?.()) {
            voiceScoreGaugeChartInstance.value = echarts.init(voiceScoreGaugeChartRef.value)
        }

        voiceScoreGaugeChartInstance.value.setOption(buildVoiceScoreGaugeOption(), true)
        voiceScoreGaugeChartInstance.value.resize()
    } catch (e) {
        console.error('Failed to render voice gauge chart:', e)
        disposeVoiceLlmGauges()
    }
}

const voiceLlmEncouragementItem = computed(() => {
    const result = selectedInterviewVoiceLlmResult.value
    if (!result) {
        return null
    }

    return {
        key: 'encouragement',
        label: '送你的一句话加油：',
        value: result.encouragement
    }
})

const calculateAverageScore = (values: Array<number | null>) => {
    const validScores = values.filter((value): value is number => {
        return typeof value === 'number' && !Number.isNaN(value)
    })

    if (!validScores.length) {
        return 0
    }

    const total = validScores.reduce((sum, score) => sum + score, 0)
    return Number((total / validScores.length).toFixed(2))
}

const radarOption = computed<echarts.EChartsOption>(() => {
    const rounds = selectedInterview.value?.rounds ?? []
    const overallAverage = calculateAverageScore(rounds.map(round => round.overall_score))
    const technicalAverage = calculateAverageScore(rounds.map(round => round.technical_score))
    const communicationAverage = calculateAverageScore(rounds.map(round => round.communication_score))
    const logicAverage = calculateAverageScore(rounds.map(round => round.logic_score))
    const adaptabilityAverage = calculateAverageScore(rounds.map(round => round.adaptability_score))

    return {
        color: ['#67F9D8', '#FFE434', '#56A3F1', '#FF917C'],
        title: {
            text: '面试总体表现'
        },
        legend: {},
        radar: [
            {
                indicator: [
                    { name: '综合得分', max: 100 },
                    { name: '技术深度', max: 100 },
                    { name: '沟通能力', max: 100 },
                    { name: '逻辑思维', max: 100 },
                    { name: '应变能力', max: 100 }
                ],
                center: ['50%', '50%'],
                radius: 100,
                startAngle: 90,
                splitNumber: 4,
                shape: 'circle',
                axisName: {
                    formatter: '{value}',
                    color: '#428BD4'
                },
                splitArea: {
                    areaStyle: {
                        color: ['#77EADF', '#26C3BE', '#64AFE9', '#428BD4'],
                        shadowColor: 'rgba(0, 0, 0, 0.2)',
                        shadowBlur: 10
                    }
                },
                axisLine: {
                    lineStyle: {
                        color: 'rgba(255, 228, 52, 0.6)'
                    }
                },
                splitLine: {
                    lineStyle: {
                        color: 'rgba(255, 228, 52, 0.6)'
                    }
                }
            }
        ],
        series: [
            {
                type: 'radar',
                emphasis: {
                    lineStyle: {
                        width: 4
                    }
                },
                data: [
                    {
                        value: [
                            overallAverage,
                            technicalAverage,
                            communicationAverage,
                            logicAverage,
                            adaptabilityAverage
                        ],
                        name: '轮次平均分',
                        areaStyle: {
                            color: 'rgba(255, 228, 52, 0.6)'
                        }
                    }
                ]
            }
        ]
    }
})

const scoreLineOption = computed<echarts.EChartsOption>(() => {
    const rounds = selectedInterview.value?.rounds ?? []
    const colors = ['#5470C6', '#EE6666', '#91CC75', '#FAC858', '#73C0DE']
    const toSeriesScore = (value: number | null) => {
        if (typeof value !== 'number' || Number.isNaN(value)) {
            return null
        }
        return Math.max(0, Math.min(100, value))
    }

    return {
        color: colors,
        title: {
            text: '得分情况'
        },
        tooltip: {
            trigger: 'none',
            axisPointer: {
                type: 'cross'
            }
        },
        legend: {},
        grid: {
            left: '4%',
            right: '4%',
            top: 70,
            bottom: 50,
            containLabel: true
        },
        xAxis: {
            type: 'category',
            axisTick: {
                alignWithLabel: true
            },
            data: rounds.map(round => `第${round.roundNumber}轮`)
        },
        yAxis: {
            type: 'value',
            min: 0,
            max: 100,
            interval: 20,
            axisLabel: {
                formatter: '{value}分'
            }
        },
        series: [
            {
                name: '综合得分',
                data: rounds.map(round => toSeriesScore(round.overall_score)),
                type: 'line',
                smooth: true,
                emphasis: {
                    focus: 'series'
                },
                connectNulls: true,
                showSymbol: true,
                symbolSize: 8,
                lineStyle: {
                    width: 3
                }
            },
            {
                name: '技术深度',
                data: rounds.map(round => toSeriesScore(round.technical_score)),
                type: 'line',
                smooth: true,
                emphasis: {
                    focus: 'series'
                },
                connectNulls: true,
                showSymbol: true,
                symbolSize: 8,
                lineStyle: {
                    width: 3
                }
            },
            {
                name: '沟通能力',
                data: rounds.map(round => toSeriesScore(round.communication_score)),
                type: 'line',
                smooth: true,
                emphasis: {
                    focus: 'series'
                },
                connectNulls: true,
                showSymbol: true,
                symbolSize: 8,
                lineStyle: {
                    width: 3
                }
            },
            {
                name: '逻辑思维',
                data: rounds.map(round => toSeriesScore(round.logic_score)),
                type: 'line',
                smooth: true,
                emphasis: {
                    focus: 'series'
                },
                connectNulls: true,
                showSymbol: true,
                symbolSize: 8,
                lineStyle: {
                    width: 3
                }
            },
            {
                name: '应变能力',
                data: rounds.map(round => toSeriesScore(round.adaptability_score)),
                type: 'line',
                smooth: true,
                emphasis: {
                    focus: 'series'
                },
                connectNulls: true,
                showSymbol: true,
                symbolSize: 8,
                lineStyle: {
                    width: 3
                }
            }
        ]
    }
})

const renderRadarChart = async () => {
    if (!isOverviewSelected.value || !selectedInterview.value) {
        return
    }

    await nextTick()

    if (!radarChartRef.value) {
        console.warn('Radar chart ref not found')
        return
    }

    try {
        if (!radarChartInstance.value) {
            radarChartInstance.value = echarts.init(radarChartRef.value)
        } else {
            // 如果实例存在，检查是否已被销毁
            if (radarChartInstance.value.isDisposed?.()) {
                radarChartInstance.value = echarts.init(radarChartRef.value)
            }
        }

        radarChartInstance.value.setOption(radarOption.value, true)
        radarChartInstance.value.resize()
    } catch (e) {
        console.error('Failed to render radar chart:', e)
    }
}

const renderScoreLineChart = async () => {
    if (!isOverviewSelected.value || !selectedInterview.value) {
        return
    }

    await nextTick()

    if (!scoreLineChartRef.value) {
        return
    }

    try {
        if (!scoreLineChartInstance.value) {
            scoreLineChartInstance.value = echarts.init(scoreLineChartRef.value)
        } else if (scoreLineChartInstance.value.isDisposed?.()) {
            scoreLineChartInstance.value = echarts.init(scoreLineChartRef.value)
        }

        scoreLineChartInstance.value.setOption(scoreLineOption.value, true)
        scoreLineChartInstance.value.resize()
    } catch (e) {
        console.error('Failed to render score line chart:', e)
    }
}

const disposeRadarChart = () => {
    radarChartInstance.value?.dispose()
    radarChartInstance.value = null
}

const disposeScoreLineChart = () => {
    scoreLineChartInstance.value?.dispose()
    scoreLineChartInstance.value = null
}

const renderEmotionChart = async () => {
    if (isOverviewSelected.value || !selectedRound.value || !emotionPieData.value.length) {
        disposeEmotionChart()
        return
    }

    await nextTick()

    if (!emotionChartRef.value) {
        return
    }

    try {
        if (!emotionChartInstance.value) {
            emotionChartInstance.value = echarts.init(emotionChartRef.value)
        } else if (emotionChartInstance.value.isDisposed?.()) {
            emotionChartInstance.value = echarts.init(emotionChartRef.value)
        }

        emotionChartInstance.value.setOption(emotionPieOption.value, true)
        emotionChartInstance.value.resize()
    } catch (e) {
        console.error('Failed to render emotion pie chart:', e)
    }
}

const disposeEmotionChart = () => {
    emotionChartInstance.value?.dispose()
    emotionChartInstance.value = null
}

const handleChartsResize = () => {
    radarChartInstance.value?.resize()
    scoreLineChartInstance.value?.resize()
    emotionChartInstance.value?.resize()
    voiceScoreGaugeChartInstance.value?.resize()
}

const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token')
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
    }
}

const statusMap: Record<string, string> = {
    pending: '待开始',
    in_progress: '进行中',
    paused: '已暂停',
    completed: '已完成',
    cancelled: '已取消'
}

const getStatusText = (status: string) => statusMap[status] || status

const mapRoundItem = (
    round: InterviewRoundApiItem,
    roundAnalysis?: InterviewRoundApiItem['analysis']
): RoundInfo => ({
    id: String(round.round_id),
    roundNumber: round.round_number,
    label: `第${round.round_number}轮${round.followup_depth > 0 ? `·追问${round.followup_depth}` : ''}`,
    interviewerQuestion: round.question_content || '暂无问题内容',
    yourAnswer: round.user_answer || '暂无作答内容',
    audioFileUrl: round.audio_file_url || null,
    overall_score: roundAnalysis?.overall_score ?? null,
    overall_comment: roundAnalysis?.overall_comment ?? null,
    technical_score: roundAnalysis?.technical_score ?? null,
    communication_score: roundAnalysis?.communication_score ?? null,
    logic_score: roundAnalysis?.logic_score ?? null,
    adaptability_score: roundAnalysis?.adaptability_score ?? null,
    summary: round.category_name
        ? `题型：${round.category_name}（链路${round.chain_index}）`
        : `题型：${round.category || '未知'}（链路${round.chain_index}）`,
    highlights: roundAnalysis?.highlights ?? [],
    weaknesses: roundAnalysis?.weaknesses ?? [],
    suggestions: roundAnalysis?.suggestions ?? [],
    audioAnalysis: null
})

const mergeRoundAudioAnalysis = (interviewId: string, roundId: string, audioAnalysis: RoundAudioAnalysis | null) => {
    interviewHistory.value = interviewHistory.value.map(interview => {
        if (interview.id !== interviewId) {
            return interview
        }

        return {
            ...interview,
            rounds: interview.rounds.map(round =>
                round.id === roundId
                    ? {
                        ...round,
                        audioAnalysis
                    }
                    : round
            )
        }
    })
}

const stopVoiceLlmPolling = (interviewId: string) => {
    const timer = voiceLlmPollTimerMap.get(interviewId)
    if (typeof timer !== 'undefined') {
        window.clearTimeout(timer)
        voiceLlmPollTimerMap.delete(interviewId)
    }
}

const scheduleVoiceLlmPolling = (interviewId: string, delayMs = 4000) => {
    stopVoiceLlmPolling(interviewId)
    const timer = window.setTimeout(() => {
        fetchInterviewVoiceLlmResult(interviewId, { autoTrigger: false })
    }, delayMs)
    voiceLlmPollTimerMap.set(interviewId, timer)
}

const triggerVoiceLlmGeneration = async (interviewId: string) => {
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/evaluations/interviews/${interviewId}/voice-llm-result/run/`,
            {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ force: false })
            }
        )

        if (!response.ok) {
            throw new Error('主动触发语音复盘总结失败')
        }

        const result = await response.json()
        const isWaiting = result?.code === 202
        voiceLlmWaitingMap.value = {
            ...voiceLlmWaitingMap.value,
            [interviewId]: isWaiting
        }

        if (isWaiting) {
            scheduleVoiceLlmPolling(interviewId)
        }
    } catch {
        voiceLlmWaitingMap.value = {
            ...voiceLlmWaitingMap.value,
            [interviewId]: true
        }
        scheduleVoiceLlmPolling(interviewId)
    }
}

const fetchInterviewVoiceLlmResult = async (
    interviewId: string,
    options: { autoTrigger?: boolean } = {}
) => {
    const autoTrigger = options.autoTrigger ?? true
    if (!interviewId || loadingVoiceLlmInterviewIds.value.has(interviewId)) {
        return
    }

    const nextLoadingIds = new Set(loadingVoiceLlmInterviewIds.value)
    nextLoadingIds.add(interviewId)
    loadingVoiceLlmInterviewIds.value = nextLoadingIds

    const nextErrors = { ...voiceLlmErrors.value }
    delete nextErrors[interviewId]
    voiceLlmErrors.value = nextErrors

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/evaluations/interviews/${interviewId}/voice-llm-result/`,
            {
                headers: getAuthHeaders()
            }
        )

        if (!response.ok) {
            throw new Error('获取语音复盘总结失败')
        }

        const result: VoiceLLMResultApiResponse = await response.json()
        if (result.code !== 200) {
            throw new Error(result.message || '获取语音复盘总结失败')
        }

        const voiceLlmResult = result.data?.voice_llm_result ?? null

        voiceLlmResultMap.value = {
            ...voiceLlmResultMap.value,
            [interviewId]: voiceLlmResult
        }

        if (voiceLlmResult && voiceLlmResult.status === 'success') {
            voiceLlmWaitingMap.value = {
                ...voiceLlmWaitingMap.value,
                [interviewId]: false
            }
            stopVoiceLlmPolling(interviewId)
            return
        }

        if (voiceLlmResult && voiceLlmResult.status === 'failed') {
            voiceLlmWaitingMap.value = {
                ...voiceLlmWaitingMap.value,
                [interviewId]: false
            }
            stopVoiceLlmPolling(interviewId)
            return
        }

        voiceLlmWaitingMap.value = {
            ...voiceLlmWaitingMap.value,
            [interviewId]: true
        }

        if (autoTrigger) {
            await triggerVoiceLlmGeneration(interviewId)
        } else {
            scheduleVoiceLlmPolling(interviewId)
        }
    } catch (error) {
        voiceLlmErrors.value = {
            ...voiceLlmErrors.value,
            [interviewId]: error instanceof Error ? error.message : '获取语音复盘总结失败'
        }
        voiceLlmWaitingMap.value = {
            ...voiceLlmWaitingMap.value,
            [interviewId]: true
        }
        scheduleVoiceLlmPolling(interviewId)
    } finally {
        const doneLoadingIds = new Set(loadingVoiceLlmInterviewIds.value)
        doneLoadingIds.delete(interviewId)
        loadingVoiceLlmInterviewIds.value = doneLoadingIds
    }
}

const fetchRoundAudioAnalysis = async (interviewId: string, roundId: string) => {
    if (!roundId || loadingAudioRoundIds.value.has(roundId)) {
        return
    }

    const interview = interviewHistory.value.find(item => item.id === interviewId)
    const round = interview?.rounds.find(item => item.id === roundId)
    if (round?.audioAnalysis) {
        return
    }

    const nextLoadingIds = new Set(loadingAudioRoundIds.value)
    nextLoadingIds.add(roundId)
    loadingAudioRoundIds.value = nextLoadingIds

    const nextAudioErrors = { ...audioAnalysisErrors.value }
    delete nextAudioErrors[roundId]
    audioAnalysisErrors.value = nextAudioErrors

    try {
        const response = await fetch(`${API_BASE_URL}/api/evaluations/rounds/${roundId}/audio-analysis/`, {
            headers: getAuthHeaders()
        })

        if (!response.ok) {
            throw new Error('获取音频分析数据失败')
        }

        const result: RoundAudioAnalysisApiResponse = await response.json()
        if (result.code !== 200) {
            throw new Error(result.message || '获取音频分析数据失败')
        }

        mergeRoundAudioAnalysis(interviewId, roundId, result.data || null)
    } catch (error) {
        audioAnalysisErrors.value = {
            ...audioAnalysisErrors.value,
            [roundId]: error instanceof Error ? error.message : '获取音频分析数据失败'
        }
    } finally {
        const doneLoadingIds = new Set(loadingAudioRoundIds.value)
        doneLoadingIds.delete(roundId)
        loadingAudioRoundIds.value = doneLoadingIds
    }
}

const fetchInterviewRounds = async (interviewId: string) => {
    if (!interviewId || loadedRoundInterviewIds.value.has(interviewId)) {
        return
    }

    loadingRounds.value = true
    roundError.value = ''

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId}/rounds/`, {
            headers: getAuthHeaders()
        })

        if (!response.ok) {
            roundError.value = '获取轮次数据失败'
            return
        }

        const result = await response.json()
        if (result.code !== 200) {
            roundError.value = result.message || '获取轮次数据失败'
            return
        }

        const rounds: RoundInfo[] = (result.data || []).map((item: InterviewRoundApiItem) => mapRoundItem(item, item.analysis))

        interviewHistory.value = interviewHistory.value.map(item =>
            item.id === interviewId ? { ...item, rounds } : item
        )

        const targetInterview = interviewHistory.value.find(item => item.id === interviewId)
        if (isVoiceEnabledInterviewMode(targetInterview?.mode)) {
            await Promise.all(rounds.map(round => fetchRoundAudioAnalysis(interviewId, round.id)))
        }

        loadedRoundInterviewIds.value.add(interviewId)
        selectedRoundId.value = OVERVIEW_ROUND_ID
    } catch {
        roundError.value = '获取轮次数据失败，请稍后重试'
    } finally {
        loadingRounds.value = false
    }
}

const fetchInterviewHistory = async () => {
    loadingInterviews.value = true
    interviewError.value = ''

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/interviews/`, {
            headers: getAuthHeaders()
        })

        if (!response.ok) {
            if (response.status === 401) {
                localStorage.removeItem('access_token')
                localStorage.removeItem('user')
                router.push('/auth')
                return
            }
            interviewError.value = '获取面试记录失败'
            return
        }

        const result = await response.json()
        if (result.code !== 200) {
            interviewError.value = result.message || '获取面试记录失败'
            return
        }

        interviewHistory.value = (result.data || []).map((item: InterviewListApiItem) => ({
            id: String(item.id),
            title: item.name?.trim() || `${item.position_name || '岗位'}面试`,
            date: item.start_time || item.created_at,
            position: item.position_name || '未知岗位',
            mode: item.mode || 'mixed',
            status: item.status,
            duration_seconds: item.duration_seconds ?? null,
            rounds: []
        }))

        selectedInterviewId.value = interviewHistory.value[0]?.id ?? ''
        if (selectedInterviewId.value) {
            await fetchInterviewRounds(selectedInterviewId.value)
            const firstInterview = interviewHistory.value.find(item => item.id === selectedInterviewId.value)
            if (isVoiceEnabledInterviewMode(firstInterview?.mode)) {
                fetchInterviewVoiceLlmResult(selectedInterviewId.value)
            }
        }
    } catch {
        interviewError.value = '获取面试记录失败，请稍后重试'
    } finally {
        loadingInterviews.value = false
    }
}

watch(selectedInterviewId, (newInterviewId) => {
    selectedRoundId.value = OVERVIEW_ROUND_ID

    if (newInterviewId) {
        fetchInterviewRounds(newInterviewId)
        const interview = interviewHistory.value.find(item => item.id === newInterviewId)
        if (isVoiceEnabledInterviewMode(interview?.mode)) {
            fetchInterviewVoiceLlmResult(newInterviewId)
        }
    }
})

const selectInterview = (id: string) => {
    selectedInterviewId.value = id
}

const clearHistoryFilters = () => {
    historySearchKeyword.value = ''
    historyDateStart.value = ''
    historyDateEnd.value = ''
    historyDateStartInputType.value = 'text'
    historyDateEndInputType.value = 'text'
}

const focusHistoryDateInput = (
    field: 'start' | 'end',
    event: FocusEvent
) => {
    if (field === 'start') {
        historyDateStartInputType.value = 'date'
    } else {
        historyDateEndInputType.value = 'date'
    }

    nextTick(() => {
        const target = event.target as HTMLInputElement | null
        if (target && typeof target.showPicker === 'function') {
            try {
                target.showPicker()
            } catch {
                // Some browsers block showPicker without direct gesture.
            }
        }
    })
}

const blurHistoryDateInput = (field: 'start' | 'end') => {
    if (field === 'start' && !historyDateStart.value) {
        historyDateStartInputType.value = 'text'
    }

    if (field === 'end' && !historyDateEnd.value) {
        historyDateEndInputType.value = 'text'
    }
}

const selectRound = (id: string) => {
    selectedRoundId.value = id
    if (id === OVERVIEW_ROUND_ID) {
        // 当选择总览时，确保雷达图会重新渲染
        nextTick(() => renderRadarChart())
        return
    }

    if (selectedInterviewId.value && selectedInterviewSupportsVoice.value) {
        fetchRoundAudioAnalysis(selectedInterviewId.value, id)
    }
}

const formatMetricValue = (value: number | null, unit = '') => {
    if (typeof value !== 'number' || Number.isNaN(value)) {
        return '暂无数据'
    }
    return `${value.toFixed(2)}${unit}`
}

const getValidPositiveNumber = (value: number | null | undefined): number | null => {
    if (typeof value !== 'number' || Number.isNaN(value) || value <= 0) {
        return null
    }
    return value
}

const estimateSpeechRatePerSecondFromTranscript = (
    transcript: string | null | undefined,
    durationSeconds: number | null | undefined
): number | null => {
    const safeDuration = getValidPositiveNumber(durationSeconds)
    if (!safeDuration || typeof transcript !== 'string') {
        return null
    }

    const normalizedText = transcript
        .replace(/暂无作答内容/g, '')
        .replace(/\s+/g, '')
        .replace(/[，。！？；：、“”‘’（）()【】\[\]{}《》,.!?;:"'`~@#$%^&*_+=<>/\\|-]/g, '')
    const textLength = normalizedText.length
    if (!textLength) {
        return null
    }

    return textLength / safeDuration
}

const getDisplayedSpeechRatePerSecond = (
    speechRatePerMinute: number | null | undefined,
    durationSeconds: number | null | undefined,
    transcript: string | null | undefined
): number | null => {
    const validPerMinute = getValidPositiveNumber(speechRatePerMinute)
    if (validPerMinute) {
        return validPerMinute / 60
    }

    return estimateSpeechRatePerSecondFromTranscript(transcript, durationSeconds)
}

const selectedSpeechRateValueText = computed(() => {
    const voice = selectedVoiceAnalysis.value
    const round = selectedRound.value
    if (!voice) {
        return '暂无数据'
    }

    const displayedRatePerSecond = getDisplayedSpeechRatePerSecond(
        voice.speech_rate,
        voice.duration_seconds,
        round?.yourAnswer ?? ''
    )

    if (typeof displayedRatePerSecond !== 'number' || Number.isNaN(displayedRatePerSecond)) {
        return '暂无数据'
    }

    return `${displayedRatePerSecond.toFixed(2)}字/秒`
})

const formatPercentValue = (value: number | null) => {
    if (typeof value !== 'number' || Number.isNaN(value)) {
        return '暂无数据'
    }
    return `${(value * 100).toFixed(2)}%`
}

const formatLevelText = (value: string | null) => value || '暂无数据'

const normalizeLevelText = (value: string | null) => (value || '').trim().toLowerCase()

const speechRateLevelMap: Record<string, LevelDisplay> = {
    slow: { label: '慢', tone: 'warning', hint: '语速偏慢，可适当加快提升信息密度' },
    normal: { label: '正常', tone: 'good', hint: '语速适中，表达节奏较好' },
    fast: { label: '快', tone: 'danger', hint: '语速偏快，建议放慢以增强清晰度' },
    慢: { label: '慢', tone: 'warning', hint: '语速偏慢，可适当加快提升信息密度' },
    正常: { label: '正常', tone: 'good', hint: '语速适中，表达节奏较好' },
    快: { label: '快', tone: 'danger', hint: '语速偏快，建议放慢以增强清晰度' }
}

const silenceLevelMap: Record<string, LevelDisplay> = {
    fluent: { label: '流利', tone: 'excellent', hint: '停顿控制优秀，表达非常连贯' },
    good: { label: '良好', tone: 'good', hint: '停顿控制良好，整体较流畅' },
    medium: { label: '中等偏下', tone: 'warning', hint: '无效停顿略多，可优化句间衔接' },
    poor: { label: '较差', tone: 'danger', hint: '停顿偏多，建议先组织要点再作答' },
    流利: { label: '流利', tone: 'excellent', hint: '停顿控制优秀，表达非常连贯' },
    良好: { label: '良好', tone: 'good', hint: '停顿控制良好，整体较流畅' },
    中等偏下: { label: '中等偏下', tone: 'warning', hint: '无效停顿略多，可优化句间衔接' },
    较差: { label: '较差', tone: 'danger', hint: '停顿偏多，建议先组织要点再作答' }
}

const getSpeechRateLevelDisplay = (value: string | null): LevelDisplay => {
    const normalized = normalizeLevelText(value)
    if (!normalized) {
        return { label: formatLevelText(value), tone: 'neutral', hint: '未检测到语速等级' }
    }

    return speechRateLevelMap[normalized] || {
        label: formatLevelText(value),
        tone: 'neutral',
        hint: '暂未匹配到语速等级映射'
    }
}

const getSilenceLevelDisplay = (value: string | null): LevelDisplay => {
    const normalized = normalizeLevelText(value)
    if (!normalized) {
        return { label: formatLevelText(value), tone: 'neutral', hint: '未检测到静音等级' }
    }

    return silenceLevelMap[normalized] || {
        label: formatLevelText(value),
        tone: 'neutral',
        hint: '暂未匹配到静音等级映射'
    }
}

const selectedSpeechRateLevelDisplay = computed(() =>
    getSpeechRateLevelDisplay(selectedVoiceAnalysis.value?.speech_rate_level ?? null)
)

const selectedSilenceLevelDisplay = computed(() =>
    getSilenceLevelDisplay(selectedVoiceAnalysis.value?.silence_ratio_level ?? null)
)

const getLevelToneClass = (tone: LevelTone) => `level-badge--${tone}`

const formatDate = (dateText: string) => {
    const date = new Date(dateText)
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(
        date.getDate()
    ).padStart(2, '0')}`
}

const formatVoiceLlmScore = (value: number | string | null) => {
    const numericValue = typeof value === 'string' ? Number(value) : value
    if (typeof numericValue !== 'number' || Number.isNaN(numericValue)) {
        return '暂无数据'
    }
    return numericValue.toFixed(2)
}

const parseVoiceLlmJsonLike = (text: string): unknown | null => {
    try {
        return JSON.parse(text)
    } catch {
        // Fall through to python-like structure parsing.
    }

    try {
        const pythonLike = text
            .replace(/\bNone\b/g, 'null')
            .replace(/\bTrue\b/g, 'true')
            .replace(/\bFalse\b/g, 'false')
            .replace(/'/g, '"')
        return JSON.parse(pythonLike)
    } catch {
        return null
    }
}

const normalizeVoiceLlmParsedValue = (value: unknown): string => {
    if (Array.isArray(value)) {
        const lines = value
            .map(item => (typeof item === 'string' ? item.trim() : String(item ?? '').trim()))
            .filter(Boolean)
        return lines.join('\n') || '暂无数据'
    }

    if (value && typeof value === 'object') {
        const lines = Object.values(value as Record<string, unknown>)
            .map(item => {
                if (typeof item === 'string') {
                    return item.trim()
                }
                if (Array.isArray(item)) {
                    return item
                        .map(inner => String(inner ?? '').trim())
                        .filter(Boolean)
                        .join('；')
                }
                return String(item ?? '').trim()
            })
            .filter(Boolean)
        return lines.join('\n') || '暂无数据'
    }

    if (typeof value === 'string') {
        return value.trim() || '暂无数据'
    }

    return String(value ?? '').trim() || '暂无数据'
}

const stripQuoteChars = (text: string): string => text.replace(/["'‘’“”]/g, '')

const toVoiceLlmLines = (text: string): string[] =>
    text
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        .split('\n')
        .map(line => line.trim())
        .filter(Boolean)
        .map(line => line.replace(/^[•·●\-]\s*/, '').trim())
        .filter(Boolean)

const normalizeVoiceLlmText = (value: string | null): string => {
    if (typeof value !== 'string') {
        return '暂无数据'
    }

    const trimmed = value.trim()
    if (!trimmed) {
        return '暂无数据'
    }

    const parsed = parseVoiceLlmJsonLike(trimmed)
    if (parsed !== null) {
        return stripQuoteChars(normalizeVoiceLlmParsedValue(parsed))
    }

    if ((trimmed.startsWith('[') && trimmed.endsWith(']')) || (trimmed.startsWith('{') && trimmed.endsWith('}'))) {
        const cleaned = trimmed
            .replace(/^[\[{]\s*/, '')
            .replace(/\s*[\]}]$/, '')
            .replace(/["']/g, '')
            .replace(/\s*,\s*/g, '\n')
            .trim()
        return stripQuoteChars(cleaned || '暂无数据')
    }

    return stripQuoteChars(trimmed)
}

const formatVoiceLlmBulletLines = (value: string | null): string[] => {
    const normalized = normalizeVoiceLlmText(value)
    if (normalized === '暂无数据') {
        return []
    }
    return toVoiceLlmLines(normalized)
}

const formatVoiceLlmText = (value: string | null) => {
    const normalized = normalizeVoiceLlmText(value)
    if (normalized === '暂无数据') {
        return normalized
    }

    const lines = toVoiceLlmLines(normalized)
    if (!lines.length) {
        return '暂无数据'
    }

    return lines.join('\n')
}

const expandedVoiceLlmTextMap = ref<Record<string, boolean>>({})

const makeVoiceLlmTextItemKey = (section: 'analysis' | 'suggestion', itemKey: string) =>
    `${section}:${itemKey}`

const isVoiceLlmTextExpanded = (section: 'analysis' | 'suggestion', itemKey: string) =>
    !!expandedVoiceLlmTextMap.value[makeVoiceLlmTextItemKey(section, itemKey)]

const toggleVoiceLlmTextExpanded = (section: 'analysis' | 'suggestion', itemKey: string) => {
    const key = makeVoiceLlmTextItemKey(section, itemKey)
    expandedVoiceLlmTextMap.value = {
        ...expandedVoiceLlmTextMap.value,
        [key]: !expandedVoiceLlmTextMap.value[key]
    }
}

const shouldShowVoiceLlmExpand = (value: string | null) => {
    const lines = formatVoiceLlmBulletLines(value)
    if (lines.length > 2) {
        return true
    }

    const text = formatVoiceLlmText(value)
    return text !== '暂无数据' && text.length > 92
}

const goBack = () => {
    if (window.history.length > 1) {
        router.back()
        return
    }
    router.push('/home?menu=evaluation')
}

onMounted(() => {
    fetchInterviewHistory()
    window.addEventListener('resize', handleChartsResize)
})

onBeforeUnmount(() => {
    window.removeEventListener('resize', handleChartsResize)
    disposeRadarChart()
    disposeScoreLineChart()
    disposeEmotionChart()
    disposeVoiceLlmGauges()
    for (const timer of voiceLlmPollTimerMap.values()) {
        window.clearTimeout(timer)
    }
    voiceLlmPollTimerMap.clear()
})

watch([isOverviewSelected, selectedInterview, loadingRounds, radarChartRef, scoreLineChartRef], ([overviewActive, interview, loading]) => {
    if (!overviewActive || !interview || loading) {
        disposeRadarChart()
        disposeScoreLineChart()
        return
    }

    renderRadarChart()
    renderScoreLineChart()
})

watch([isOverviewSelected, selectedVoiceAnalysis, isSelectedRoundAudioLoading, emotionChartRef], ([overviewActive, voice, loading]) => {
    if (overviewActive || loading || !voice) {
        disposeEmotionChart()
        return
    }

    renderEmotionChart()
})

watch(
    [
        isOverviewSelected,
        selectedInterviewVoiceLlmResult,
        isSelectedInterviewVoiceLlmWaiting,
        voiceScoreGaugeChartRef
    ],
    ([overviewActive, result, waiting, chartRef]) => {
        if (!overviewActive || waiting || !result || !voiceLlmGaugeItems.value.length || !chartRef) {
            disposeVoiceLlmGauges()
            return
        }

        renderVoiceLlmGauges()
    }
)

watch(selectedInterviewId, () => {
    if (!isOverviewSelected.value) {
        disposeVoiceLlmGauges()
        return
    }

    renderVoiceLlmGauges()
})

watch(filteredInterviewHistory, visibleItems => {
    if (!visibleItems.length) {
        selectedInterviewId.value = ''
        selectedRoundId.value = OVERVIEW_ROUND_ID
        return
    }

    const selectedStillVisible = visibleItems.some(item => item.id === selectedInterviewId.value)
    if (!selectedStillVisible) {
        const firstVisibleItem = visibleItems[0]
        if (typeof firstVisibleItem !== 'undefined') {
            selectedInterviewId.value = firstVisibleItem.id
        }
    }
})
</script>

<template>
    <div class="review-layout">
        <aside class="history-sidebar">
            <h2>面试历史</h2>
            <section class="history-filter-box">
                <input v-model="historySearchKeyword" type="text" class="history-search-input"
                    placeholder="搜索历史记录名称或岗位" />
                <div class="history-date-filter-row">
                    <label>
                        <span>开始日期</span>
                        <input v-model="historyDateStart" :type="historyDateStartInputType" class="history-date-input"
                            placeholder="" @focus="focusHistoryDateInput('start', $event)"
                            @blur="blurHistoryDateInput('start')" />
                    </label>
                    <label>
                        <span>结束日期</span>
                        <input v-model="historyDateEnd" :type="historyDateEndInputType" class="history-date-input"
                            placeholder="" @focus="focusHistoryDateInput('end', $event)"
                            @blur="blurHistoryDateInput('end')" />
                    </label>
                </div>
                <button v-if="hasActiveHistoryFilters" type="button" class="history-filter-reset"
                    @click="clearHistoryFilters">
                    清空筛选
                </button>
            </section>
            <div v-if="loadingInterviews" class="sidebar-tip">面试记录加载中...</div>
            <div v-else-if="interviewError" class="sidebar-tip error">{{ interviewError }}</div>
            <div v-else-if="!interviewHistory.length" class="sidebar-tip">暂无面试记录</div>
            <div v-else-if="!filteredInterviewHistory.length" class="sidebar-tip">未找到符合条件的面试记录</div>
            <ul v-else class="history-list">
                <li v-for="item in filteredInterviewHistory" :key="item.id"
                    :class="['history-item', { active: selectedInterviewId === item.id }]"
                    @click="selectInterview(item.id)">
                    <h3>{{ item.title }}</h3>
                    <p>{{ item.position }}</p>
                    <p class="status-text">状态：{{ getStatusText(item.status) }}</p>
                    <span>{{ formatDate(item.date) }}</span>
                </li>
            </ul>
        </aside>

        <section class="review-main">
            <div class="review-topbar">
                <button type="button" class="back-btn" @click="goBack">
                    <span class="icon" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M15 6L9 12L15 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"
                                stroke-linejoin="round" />
                        </svg>
                    </span>
                    <span>返回</span>
                </button>
            </div>

            <header class="round-navbar" v-if="selectedInterview">
                <button v-for="nav in roundNavItems" :key="nav.id"
                    :class="['round-tab', { active: selectedRoundId === nav.id }]" @click="selectRound(nav.id)">
                    {{ nav.label }}
                </button>
            </header>

            <div v-if="loadingRounds" class="empty-state empty-state--loading">
                <div class="dot-spinner" aria-label="加载中" role="status">
                    <span v-for="index in 8" :key="index" class="dot-spinner__dot"></span>
                </div>
                <p class="loading-text">轮次加载中...</p>
            </div>
            <div v-else-if="roundError" class="empty-state">{{ roundError }}</div>
            <article v-if="isOverviewSelected && selectedInterview" class="round-content">
                <section class="overview-card">
                    <div class="overview-summary-text">
                        <p class="overview-summary-title title-with-icon">
                            <span class="icon" aria-hidden="true">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <rect x="4" y="5" width="16" height="14" rx="3" stroke="currentColor"
                                        stroke-width="1.8" />
                                    <path d="M8 10H16" stroke="currentColor" stroke-width="1.8"
                                        stroke-linecap="round" />
                                    <path d="M8 14H13" stroke="currentColor" stroke-width="1.8"
                                        stroke-linecap="round" />
                                </svg>
                            </span>
                            <span>整体情况</span>
                        </p>
                        <p>共 {{ overviewRoundCount }} 个轮次，已作答 {{ overviewAnsweredCount }} 个轮次。</p>
                        <p>面试总时长：{{ overviewInterviewDurationText }}</p>
                        <p>题型概览：{{ overviewCategorySummary }}</p>
                    </div>

                    <h1>面试回答内容评估总结</h1>

                    <div class="overview-charts-row">
                        <div class="radar-wrapper">
                            <div ref="radarChartRef" class="radar-chart"></div>
                        </div>
                        <div class="line-chart-wrapper">
                            <div ref="scoreLineChartRef" class="score-line-chart"></div>
                        </div>
                    </div>

                    <section v-if="selectedInterviewSupportsVoice" class="voice-llm-summary-section">
                        <h1>面试音频部分评估总结</h1>
                        <div v-if="isSelectedInterviewVoiceLlmLoading" class="analysis-tip analysis-tip--loading">
                            <div class="dot-spinner" aria-label="加载中" role="status">
                                <span v-for="index in 8" :key="`voice-review-${index}`" class="dot-spinner__dot"></span>
                            </div>
                            <p class="loading-text">语音复盘总结加载中...</p>
                        </div>
                        <div v-else-if="selectedInterviewVoiceLlmError" class="analysis-tip error">{{
                            selectedInterviewVoiceLlmError }}</div>
                        <div v-else-if="!selectedInterviewVoiceLlmResult || isSelectedInterviewVoiceLlmWaiting"
                            class="analysis-tip">结果等待生成</div>

                        <div v-else class="voice-llm-panel">
                            <section class="voice-llm-subsection voice-llm-subsection--score">
                                <h3 class="title-with-icon">
                                    <span class="icon" aria-hidden="true">
                                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M6 17V11" stroke="currentColor" stroke-width="1.8"
                                                stroke-linecap="round" />
                                            <path d="M12 17V8" stroke="currentColor" stroke-width="1.8"
                                                stroke-linecap="round" />
                                            <path d="M18 17V13" stroke="currentColor" stroke-width="1.8"
                                                stroke-linecap="round" />
                                        </svg>
                                    </span>
                                    <span>表现分数</span>
                                </h3>
                                <div class="voice-llm-gauge-panel">
                                    <div ref="voiceScoreGaugeChartRef" class="voice-llm-gauge-chart-large"></div>
                                    <div class="voice-llm-score-legend">
                                        <article v-for="item in voiceLlmGaugeItems" :key="item.key"
                                            :class="['voice-llm-score-legend-item', { 'voice-llm-score-legend-item--overall': item.key === 'overall_audio_score' }]">
                                            <span v-if="item.key !== 'overall_audio_score'" class="voice-llm-score-dot"
                                                :style="{ backgroundColor: item.color }"></span>
                                            <span class="voice-llm-score-label">{{ item.label }}</span>
                                            <strong class="voice-llm-score-value">{{ formatVoiceLlmScore(item.value)
                                                }}</strong>
                                        </article>
                                    </div>
                                </div>
                            </section>

                            <section class="voice-llm-subsection voice-llm-subsection--text">
                                <h3 class="title-with-icon">
                                    <span class="icon" aria-hidden="true">
                                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M5 12H19" stroke="currentColor" stroke-width="1.8"
                                                stroke-linecap="round" />
                                            <path d="M12 5V19" stroke="currentColor" stroke-width="1.8"
                                                stroke-linecap="round" />
                                        </svg>
                                    </span>
                                    <span>分析</span>
                                </h3>
                                <div class="voice-llm-text-list">
                                    <article v-for="item in voiceLlmAnalysisItems" :key="item.key"
                                        class="voice-llm-text-item">
                                        <h4>{{ item.label }}</h4>
                                        <ul v-if="formatVoiceLlmBulletLines(item.value).length"
                                            :class="['voice-llm-bullet-list', { 'voice-llm-bullet-list--clamped': !isVoiceLlmTextExpanded('analysis', item.key) }]">
                                            <li v-for="(line, lineIndex) in formatVoiceLlmBulletLines(item.value)"
                                                :key="`${item.key}-${lineIndex}`">{{ line }}</li>
                                        </ul>
                                        <p v-else
                                            :class="['voice-llm-text-paragraph', { 'voice-llm-text-paragraph--clamped': !isVoiceLlmTextExpanded('analysis', item.key) }]">
                                            {{ formatVoiceLlmText(item.value) }}
                                        </p>
                                        <button v-if="shouldShowVoiceLlmExpand(item.value)" type="button"
                                            class="voice-llm-expand-btn"
                                            @click="toggleVoiceLlmTextExpanded('analysis', item.key)">
                                            <span class="voice-llm-expand-icon-wrap"
                                                :class="{ 'voice-llm-expand-icon-wrap--expanded': isVoiceLlmTextExpanded('analysis', item.key) }"
                                                aria-hidden="true">
                                                <svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                                                    <path d="M4 6.5L8 10L12 6.5" fill="none" stroke="currentColor"
                                                        stroke-width="1.8" stroke-linecap="round"
                                                        stroke-linejoin="round" />
                                                </svg>
                                            </span>
                                        </button>
                                    </article>
                                </div>
                            </section>

                            <section class="voice-llm-subsection voice-llm-subsection--text">
                                <h3 class="title-with-icon">
                                    <span class="icon" aria-hidden="true">
                                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M8 12L11 15L16 9" stroke="currentColor" stroke-width="1.8"
                                                stroke-linecap="round" stroke-linejoin="round" />
                                            <rect x="4" y="4" width="16" height="16" rx="3" stroke="currentColor"
                                                stroke-width="1.8" />
                                        </svg>
                                    </span>
                                    <span>建议</span>
                                </h3>
                                <div class="voice-llm-text-list">
                                    <article v-for="item in voiceLlmSuggestionItems" :key="item.key"
                                        :class="['voice-llm-text-item', { 'voice-llm-text-item--full-row': item.key === 'position_communication_tips' }]">
                                        <h4>{{ item.label }}</h4>
                                        <ul v-if="formatVoiceLlmBulletLines(item.value).length"
                                            :class="['voice-llm-bullet-list', { 'voice-llm-bullet-list--clamped': !isVoiceLlmTextExpanded('suggestion', item.key) }]">
                                            <li v-for="(line, lineIndex) in formatVoiceLlmBulletLines(item.value)"
                                                :key="`${item.key}-${lineIndex}`">{{ line }}</li>
                                        </ul>
                                        <p v-else
                                            :class="['voice-llm-text-paragraph', { 'voice-llm-text-paragraph--clamped': !isVoiceLlmTextExpanded('suggestion', item.key) }]">
                                            {{ formatVoiceLlmText(item.value) }}
                                        </p>
                                        <button v-if="shouldShowVoiceLlmExpand(item.value)" type="button"
                                            class="voice-llm-expand-btn"
                                            @click="toggleVoiceLlmTextExpanded('suggestion', item.key)">
                                            <span class="voice-llm-expand-icon-wrap"
                                                :class="{ 'voice-llm-expand-icon-wrap--expanded': isVoiceLlmTextExpanded('suggestion', item.key) }"
                                                aria-hidden="true">
                                                <svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                                                    <path d="M4 6.5L8 10L12 6.5" fill="none" stroke="currentColor"
                                                        stroke-width="1.8" stroke-linecap="round"
                                                        stroke-linejoin="round" />
                                                </svg>
                                            </span>
                                        </button>
                                    </article>
                                </div>
                            </section>

                            <section v-if="voiceLlmEncouragementItem"
                                class="voice-llm-subsection voice-llm-subsection--encouragement">
                                <article class="voice-llm-encouragement-card">
                                    <h4 class="title-with-icon">
                                        <span class="icon" aria-hidden="true">
                                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path
                                                    d="M12 4L14.6 9.3L20.4 10.1L16.2 14.1L17.2 19.8L12 17L6.8 19.8L7.8 14.1L3.6 10.1L9.4 9.3L12 4Z"
                                                    stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
                                            </svg>
                                        </span>
                                        <span>{{ voiceLlmEncouragementItem.label }}</span>
                                    </h4>
                                    <p class="voice-llm-encouragement-content">{{
                                        formatVoiceLlmText(voiceLlmEncouragementItem.value) }}</p>
                                </article>
                            </section>
                        </div>
                    </section>
                </section>

            </article>

            <article v-else-if="selectedRound" class="round-content">
                <div class="overview-card">
                    <p>{{ selectedRound.summary }}</p>
                    <div class="score">综合得分：{{ formatMetricValue(selectedRound.overall_score) }}</div>
                    <div class="comment">总体评价：{{ selectedRound.overall_comment || '暂无评价' }}</div>

                </div>

                <section class="qa-card">
                    <h2 class="title-with-icon">
                        <span class="icon" aria-hidden="true">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <rect x="4" y="5" width="16" height="14" rx="3" stroke="currentColor"
                                    stroke-width="1.8" />
                                <path d="M8 10H16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                            </svg>
                        </span>
                        <span>面试官问题</span>
                    </h2>
                    <p>{{ selectedRound.interviewerQuestion }}</p>

                    <h2 class="title-with-icon">
                        <span class="icon" aria-hidden="true">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M7 5H17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                                <path d="M7 10H17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                                <path d="M7 15H13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                            </svg>
                        </span>
                        <span>你的文字回答</span>
                    </h2>
                    <p>{{ selectedRound.yourAnswer }}</p>

                    <template v-if="selectedInterviewSupportsVoice">
                        <h2 class="title-with-icon">
                            <span class="icon" aria-hidden="true">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <rect x="9" y="4" width="6" height="10" rx="3" stroke="currentColor"
                                        stroke-width="1.8" />
                                    <path d="M6 11C6 14.3 8.7 17 12 17C15.3 17 18 14.3 18 11" stroke="currentColor"
                                        stroke-width="1.8" stroke-linecap="round" />
                                </svg>
                            </span>
                            <span>你的语音回答</span>
                        </h2>
                        <div v-if="selectedRoundAudioSrc" class="qa-audio-player-wrap">
                            <div class="qa-audio-shell">
                                <div class="qa-audio-head">
                                    <span class="qa-audio-badge">语音回放</span>
                                    <p class="qa-audio-tip">建议回听语速与停顿节奏，定位表达提升点</p>
                                </div>
                                <div class="qa-audio-visual" aria-hidden="true">
                                    <div class="qa-audio-wave-track">
                                        <svg class="qa-audio-wave-svg qa-audio-wave-svg--a" viewBox="0 0 520 36"
                                            preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
                                            <polyline
                                                points="0,18 6,13 12,23 18,12 24,24 30,11 36,22 42,10 48,23 54,12 60,25 66,11 72,23 78,13 84,24 90,12 96,22 102,10 108,23 114,12 120,25 126,11 132,23 138,13 144,24 150,12 156,22 162,10 168,23 174,12 180,25 186,11 192,23 198,13 204,24 210,12 216,22 222,10 228,23 234,12 240,25 246,11 252,23 258,13 264,24 270,12 276,22 282,10 288,23 294,12 300,25 306,11 312,23 318,13 324,24 330,12 336,22 342,10 348,23 354,12 360,25 366,11 372,23 378,13 384,24 390,12 396,22 402,10 408,23 414,12 420,25 426,11 432,23 438,13 444,24 450,12 456,22 462,10 468,23 474,12 480,25 486,11 492,23 498,13 504,24 510,12 516,22" />
                                        </svg>
                                        <svg class="qa-audio-wave-svg qa-audio-wave-svg--b" viewBox="0 0 520 36"
                                            preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
                                            <polyline
                                                points="0,19 6,14 12,24 18,13 24,25 30,12 36,23 42,11 48,24 54,13 60,26 66,12 72,24 78,14 84,25 90,13 96,23 102,11 108,24 114,13 120,26 126,12 132,24 138,14 144,25 150,13 156,23 162,11 168,24 174,13 180,26 186,12 192,24 198,14 204,25 210,13 216,23 222,11 228,24 234,13 240,26 246,12 252,24 258,14 264,25 270,13 276,23 282,11 288,24 294,13 300,26 306,12 312,24 318,14 324,25 330,13 336,23 342,11 348,24 354,13 360,26 366,12 372,24 378,14 384,25 390,13 396,23 402,11 408,24 414,13 420,26 426,12 432,24 438,14 444,25 450,13 456,23 462,11 468,24 474,13 480,26 486,12 492,24 498,14 504,25 510,13 516,23" />
                                        </svg>
                                    </div>
                                </div>
                                <audio class="qa-audio-player" :src="selectedRoundAudioSrc" controls preload="metadata">
                                    当前浏览器不支持音频播放。
                                </audio>
                            </div>
                        </div>
                        <p v-else class="qa-audio-empty">暂无该轮音频录音</p>
                    </template>
                </section>

                <section class="analysis-section">
                    <h2 class="title-with-icon">
                        <span class="icon" aria-hidden="true">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M6 17V11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                                <path d="M12 17V8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                                <path d="M18 17V13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                            </svg>
                        </span>
                        <span>结果分析</span>
                    </h2>
                    <div class="analysis-grid">
                        <section class="detail-card detail-card--full-row">
                            <h2>分数可视化</h2>
                            <div class="score-bars">
                                <div v-for="(item, index) in scoreBars" :key="item.key" class="score-bar-item"
                                    :style="getScoreVisualStyle(item.value, index)">
                                    <div class="score-bar-head">
                                        <span>{{ item.label }}</span>
                                        <strong class="score-value-chip">{{ formatMetricValue(item.rawValue) }}</strong>
                                    </div>
                                    <div class="score-bar-track">
                                        <div class="score-bar-fill" :style="{ width: `${item.value ?? 0}%` }"></div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <template v-if="selectedInterviewSupportsVoice">
                            <section v-if="isSelectedRoundAudioLoading" class="detail-card">
                                <h2>语音分析</h2>
                                <div class="analysis-tip analysis-tip--loading">
                                    <div class="dot-spinner" aria-label="加载中" role="status">
                                        <span v-for="index in 8" :key="`voice-audio-${index}`"
                                            class="dot-spinner__dot"></span>
                                    </div>
                                    <p class="loading-text">音频分析数据加载中...</p>
                                </div>
                            </section>
                            <section v-else-if="selectedRoundAudioError" class="detail-card">
                                <h2>语音分析</h2>
                                <div class="analysis-tip error">{{ selectedRoundAudioError }}</div>
                            </section>
                            <template v-else-if="selectedVoiceAnalysis">
                                <section class="detail-card">
                                    <!-- <h2>语音指标</h2> -->
                                    <div class="metric-group">
                                        <!-- <h3 class="metric-group-title">语音指标</h3> -->
                                        <h2>语音指标</h2>

                                        <ul class="metric-list">
                                            <li class="metric-item">
                                                <span class="metric-label">时长</span>
                                                <span class="metric-value">{{
                                                    formatMetricValue(selectedVoiceAnalysis.duration_seconds, ' 秒')
                                                }}</span>
                                            </li>
                                            <li class="metric-item">
                                                <span class="metric-label">语速</span>
                                                <span class="metric-value">{{ selectedSpeechRateValueText }}</span>
                                            </li>
                                            <li class="metric-item metric-item--stacked">
                                                <span class="metric-label">语速等级</span>
                                                <span class="metric-level-wrap">
                                                    <span
                                                        :class="['level-badge', getLevelToneClass(selectedSpeechRateLevelDisplay.tone)]">
                                                        {{ selectedSpeechRateLevelDisplay.label }}
                                                    </span>
                                                    <small class="metric-hint">{{ selectedSpeechRateLevelDisplay.hint
                                                    }}</small>
                                                </span>
                                            </li>
                                        </ul>
                                    </div>
                                    <div class="metric-group">
                                        <h2>停顿与空白</h2>
                                        <ul class="metric-list">
                                            <li class="metric-item">
                                                <span class="metric-label">静音占比</span>
                                                <span class="metric-value">{{
                                                    formatPercentValue(selectedVoiceAnalysis.silence_ratio) }}</span>
                                            </li>
                                            <li class="metric-item metric-item--stacked">
                                                <span class="metric-label">静音等级</span>
                                                <span class="metric-level-wrap">
                                                    <span
                                                        :class="['level-badge', getLevelToneClass(selectedSilenceLevelDisplay.tone)]">
                                                        {{ selectedSilenceLevelDisplay.label }}
                                                    </span>
                                                    <small class="metric-hint">{{ selectedSilenceLevelDisplay.hint
                                                    }}</small>
                                                </span>
                                            </li>
                                        </ul>
                                    </div>
                                </section>

                                <section class="detail-card">
                                    <h2>情绪分布</h2>
                                    <div v-if="emotionPieData.length" ref="emotionChartRef" class="emotion-chart"></div>
                                    <p v-else class="emotion-empty">暂无情绪分布数据</p>
                                </section>
                            </template>
                            <section v-else class="detail-card">
                                <h2>语音分析</h2>
                                <div class="analysis-tip">暂无音频分析数据</div>
                            </section>
                        </template>




                    </div>
                </section>



                <div class="detail-grid">
                    <section class="detail-card">
                        <h2>亮点表现</h2>
                        <ul v-if="selectedRoundHighlightLines.length">
                            <li v-for="(item, idx) in selectedRoundHighlightLines" :key="`hl-${idx}-${item}`">{{ item }}</li>
                        </ul>
                        <p v-else class="detail-list-empty">暂无</p>
                    </section>

                    <section class="detail-card">
                        <h2 class="title-with-icon">
                            <span class="icon" aria-hidden="true">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.8" />
                                    <path d="M12 8V12" stroke="currentColor" stroke-width="1.8"
                                        stroke-linecap="round" />
                                    <circle cx="12" cy="15.5" r="0.8" fill="currentColor" />
                                </svg>
                            </span>
                            <span>不足之处</span>
                        </h2>
                        <ul>
                            <li v-for="item in selectedRound.weaknesses" :key="item">{{ item }}</li>
                        </ul>
                    </section>

                    <section class="detail-card">
                        <h2 class="title-with-icon">
                            <span class="icon" aria-hidden="true">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M8 12L11 15L16 9" stroke="currentColor" stroke-width="1.8"
                                        stroke-linecap="round" stroke-linejoin="round" />
                                    <rect x="4" y="4" width="16" height="16" rx="3" stroke="currentColor"
                                        stroke-width="1.8" />
                                </svg>
                            </span>
                            <span>改进建议</span>
                        </h2>
                        <ul>
                            <li v-for="item in selectedRound.suggestions" :key="item">{{ item }}</li>
                        </ul>
                    </section>

                    <section class="detail-card">
                        <h2 class="title-with-icon">
                            <span class="icon" aria-hidden="true">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <circle cx="7" cy="12" r="2" stroke="currentColor" stroke-width="1.8" />
                                    <circle cx="17" cy="8" r="2" stroke="currentColor" stroke-width="1.8" />
                                    <circle cx="17" cy="16" r="2" stroke="currentColor" stroke-width="1.8" />
                                    <path d="M8.8 11L15.2 9" stroke="currentColor" stroke-width="1.8"
                                        stroke-linecap="round" />
                                    <path d="M8.8 13L15.2 15" stroke="currentColor" stroke-width="1.8"
                                        stroke-linecap="round" />
                                </svg>
                            </span>
                            <span>关联的知识点</span>
                        </h2>
                        <ul>
                            <li v-for="item in selectedRound.suggestions" :key="item">{{ item }}</li>
                        </ul>
                    </section>
                </div>
            </article>

            <div v-else-if="selectedInterviewId" class="empty-state">暂无可展示的轮次信息。</div>
            <div v-else class="empty-state">请选择一条面试记录进行复盘。</div>
        </section>
    </div>
</template>

<style scoped>
.review-layout {
    --bg: #f3f5f4;
    --surface: #ffffff;
    --surface-soft: #f8fbf9;
    --line: #dde5e1;
    --line-soft: #e8eeeb;
    --text: #1f2926;
    --muted: #66756f;
    --accent: #2f5d56;
    --accent-2: #3f655f;
    --danger: #a7564f;

    display: flex;
    min-height: 100vh;
    height: 100vh;
    background:
        radial-gradient(circle at top right, rgba(47, 93, 86, 0.08), transparent 38%),
        radial-gradient(circle at top left, rgba(31, 41, 38, 0.05), transparent 40%),
        var(--bg);
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--line);
    box-shadow: 0 14px 30px rgba(31, 41, 38, 0.08);
}

.history-sidebar {
    width: 288px;
    flex: 0 0 288px;
    background: rgba(255, 255, 255, 0.94);
    border-right: 1px solid var(--line);
    padding: 1rem 0.95rem;
    overflow-y: auto;
    backdrop-filter: blur(8px);
}

.history-sidebar h2 {
    margin: 0 0 0.85rem;
    font-size: 1.02rem;
    letter-spacing: 0.01em;
    color: var(--text);
}

.history-filter-box {
    margin-bottom: 0.95rem;
    padding: 0.78rem;
    border: 1px solid var(--line-soft);
    border-radius: 10px;
    background: var(--surface-soft);
    display: flex;
    flex-direction: column;
    gap: 0.56rem;
}

.history-search-input,
.history-date-input {
    width: 100%;
    border: 1px solid #d5dfda;
    border-radius: 8px;
    padding: 0.44rem 0.58rem;
    font-size: 0.85rem;
    color: var(--text);
    background: var(--surface);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.history-search-input:focus,
.history-date-input:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(47, 93, 86, 0.14);
}

/* Hide browser date hint text when value is empty; keep visible once focused or selected. */
.history-date-input:invalid::-webkit-datetime-edit {
    color: transparent;
}

.history-date-input:focus::-webkit-datetime-edit,
.history-date-input:valid::-webkit-datetime-edit {
    color: var(--text);
}

.history-date-filter-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.55rem;
}

.history-date-filter-row label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.78rem;
    color: var(--muted);
}

.history-filter-reset {
    align-self: flex-end;
    border: 1px solid #d3dfd9;
    border-radius: 999px;
    padding: 0.26rem 0.8rem;
    font-size: 0.76rem;
    color: #375951;
    background: #eef4f1;
    cursor: pointer;
    transition: all 0.2s ease;
}

.history-filter-reset:hover {
    color: var(--accent);
    border-color: #c8d8d1;
    background: #e7f0ec;
}

.history-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.68rem;
}

.history-item {
    border: 1px solid var(--line-soft);
    border-radius: 10px;
    padding: 0.76rem;
    cursor: pointer;
    transition: all 0.2s ease;
    background: var(--surface);
}

.history-item:hover {
    border-color: #c9d8d2;
    background: #f4f8f6;
}

.history-item.active {
    border-color: var(--accent);
    background: linear-gradient(135deg, rgba(63, 101, 95, 0.14), rgba(47, 93, 86, 0.12));
}

.history-item h3 {
    margin: 0 0 0.35rem;
    font-size: 0.93rem;
    color: var(--text);
}

.history-item p {
    margin: 0 0 0.3rem;
    font-size: 0.83rem;
    color: var(--muted);
}

.history-item span {
    font-size: 0.79rem;
    color: #6f7f79;
}

.status-text {
    margin: 0 0 0.3rem;
    font-size: 0.78rem;
    color: #3f655f;
}

.sidebar-tip {
    border: 1px dashed #cfdbd6;
    border-radius: 10px;
    padding: 0.8rem;
    color: #6d7b76;
    background: var(--surface);
}

.sidebar-tip.error {
    color: #8f3e37;
    border-color: #edc9c6;
    background: #fdf3f2;
}

.review-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 1.05rem 1.1rem 1.15rem;
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
}

.review-topbar {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 0.75rem;
}

.back-btn {
    border: 1px solid #d5e2dc;
    background: #eef4f1;
    color: #375951;
    border-radius: 10px;
    padding: 0.44rem 0.88rem;
    cursor: pointer;
    transition: all 0.2s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.38rem;
    font-weight: 600;
}

.back-btn:hover {
    border-color: #c9d8d2;
    color: var(--accent);
    background: #e7f0ec;
}

.round-navbar {
    display: flex;
    gap: 0.52rem;
    flex-wrap: wrap;
    border-bottom: 1px solid var(--line);
    padding-bottom: 0.78rem;
}

.round-tab {
    border: 1px solid #d5dfda;
    border-radius: 999px;
    padding: 0.38rem 0.92rem;
    background: var(--surface);
    color: var(--muted);
    cursor: pointer;
    font-weight: 600;
    transition: all 0.22s ease;
}

.round-tab:hover {
    border-color: #c9d8d2;
    color: var(--accent);
    background: #f3f8f6;
}

.round-tab.active {
    background: linear-gradient(135deg, var(--accent-2) 0%, var(--accent) 100%);
    border-color: var(--accent);
    color: white;
    box-shadow: 0 8px 18px rgba(47, 93, 86, 0.24);
}

.round-content {
    margin-top: 0.9rem;
    display: flex;
    flex-direction: column;
    flex: 1;
    gap: 0.92rem;
}

.round-content>.overview-card {
    flex: 1;
}

.qa-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1rem 1.02rem;
    box-shadow: 0 10px 20px rgba(31, 41, 38, 0.05);
}

.qa-card h2 {
    margin: 0 0 0.45rem;
    font-size: 1rem;
    color: var(--text);
}

.qa-card h2:not(:first-child) {
    margin-top: 0.92rem;
}

.qa-card p {
    margin: 0;
    color: var(--muted);
    line-height: 1.62;
}

.qa-audio-player-wrap {
    margin-top: 0.32rem;
}

.qa-audio-shell {
    border: 1px solid #cedfd8;
    border-radius: 14px;
    padding: 0.86rem 0.86rem 0.8rem;
    background:
        radial-gradient(circle at 88% -15%, rgba(104, 178, 156, 0.24), rgba(104, 178, 156, 0) 44%),
        linear-gradient(125deg, #f8fcfa 0%, #eef6f2 48%, #e7f1ed 100%);
    box-shadow: 0 14px 26px rgba(38, 73, 66, 0.12);
}

.qa-audio-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.7rem;
    margin-bottom: 0.62rem;
}

.qa-audio-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    border: 1px solid #84b8aa;
    background: rgba(255, 255, 255, 0.82);
    color: #2f5f58;
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    padding: 0.2rem 0.64rem;
    white-space: nowrap;
}

.qa-audio-tip {
    margin: 0;
    color: #4d6761;
    font-size: 0.8rem;
    line-height: 1.45;
    text-align: right;
}

.qa-audio-visual {
    position: relative;
    height: 38px;
    border: 1px solid #d4e4de;
    border-radius: 10px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.85), rgba(239, 246, 243, 0.95));
    overflow: hidden;
    margin-bottom: 0.62rem;
}

.qa-audio-visual::before {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    top: 50%;
    height: 1px;
    transform: translateY(-50%);
    background: rgba(85, 113, 106, 0.22);
}

.qa-audio-wave-track {
    position: absolute;
    inset: 0;
    overflow: hidden;
}

.qa-audio-wave-svg {
    position: absolute;
    top: 6px;
    width: 170%;
    height: 26px;
    opacity: 0.96;
}

.qa-audio-wave-svg polyline {
    fill: none;
    stroke: #2f6159;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.8;
}

.qa-audio-wave-svg--a {
    left: -22%;
    animation: qaAudioWaveDriftA 12s linear infinite;
}

.qa-audio-wave-svg--b {
    left: -6%;
    opacity: 0.44;
    transform: translateY(2px);
    animation: qaAudioWaveDriftB 16s linear infinite;
}

.qa-audio-player {
    width: 100%;
    border-radius: 12px;
    height: 48px;
    accent-color: #2f5d56;
}

.qa-audio-player::-webkit-media-controls-panel {
    background: linear-gradient(95deg, #f7fbf9 0%, #edf6f2 100%);
}

.qa-audio-player::-webkit-media-controls-play-button,
.qa-audio-player::-webkit-media-controls-mute-button {
    filter: saturate(1.1);
}

.qa-audio-empty {
    color: #6d7b76;
}

@keyframes qaAudioWaveDriftA {
    0% {
        transform: translateX(0);
    }

    100% {
        transform: translateX(-22%);
    }
}

@keyframes qaAudioWaveDriftB {
    0% {
        transform: translateX(0) translateY(2px);
    }

    100% {
        transform: translateX(-18%) translateY(2px);
    }
}

.analysis-section h2 {
    margin: 0;
    font-size: 1.02rem;
    color: var(--text);
}

.analysis-grid {
    margin-top: 0.72rem;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem;
}

.analysis-tip {
    margin-top: 0.72rem;
    border: 1px dashed #cfdbd6;
    border-radius: 10px;
    padding: 0.78rem;
    color: #6d7b76;
    background: var(--surface);
}

.analysis-tip--loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.7rem;
    min-height: 120px;
}

.analysis-tip.error {
    color: #8f3e37;
    border-color: #edc9c6;
    background: #fdf3f2;
}

.score-bars {
    display: flex;
    flex-direction: column;
    gap: 0.82rem;
}

.score-bar-item {
    display: flex;
    flex-direction: column;
    gap: 0.42rem;
    padding: 0.62rem 0.72rem;
    border: 1px solid #dbe5e1;
    border-radius: 11px;
    background:
        linear-gradient(120deg, rgba(255, 255, 255, 0.9), rgba(244, 250, 247, 0.92));
    box-shadow: 0 7px 14px rgba(31, 41, 38, 0.05);
    animation: scoreItemReveal 0.56s ease-out both;
    animation-delay: var(--score-delay, 0ms);
}

.score-bar-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.88rem;
    color: #3b4b46;
}

.score-bar-head strong {
    color: var(--text);
}

.score-value-chip {
    padding: 0.12rem 0.55rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--score-chip-text, #234a43);
    border: 1px solid var(--score-chip-border, #bdd0c8);
    background: var(--score-chip-bg, linear-gradient(130deg, #f2f8f5, #dfeee8));
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.score-bar-track {
    position: relative;
    width: 100%;
    height: 11px;
    border-radius: 999px;
    overflow: hidden;
    background: linear-gradient(90deg, #dde6e2, #e6efeb);
}

.score-bar-track::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: repeating-linear-gradient(-45deg,
            rgba(255, 255, 255, 0.06),
            rgba(255, 255, 255, 0.06) 10px,
            rgba(0, 0, 0, 0) 10px,
            rgba(0, 0, 0, 0) 20px);
    pointer-events: none;
}

.score-bar-fill {
    position: relative;
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--score-fill-start, #3e6e66) 0%, var(--score-fill-end, #274f49) 100%);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.22) inset, 0 5px 10px var(--score-glow, rgba(47, 93, 86, 0.22));
    transform-origin: left center;
    animation: scoreFillGrow 0.9s cubic-bezier(0.2, 0.76, 0.24, 1) both;
    animation-delay: calc(var(--score-delay, 0ms) + 80ms);
    transition: width 0.38s ease;
}

.score-bar-fill::after {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: -35%;
    width: 35%;
    transform: skewX(-18deg);
    background: linear-gradient(90deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.55), rgba(255, 255, 255, 0));
    animation: scoreSheen 2.3s ease-in-out infinite;
    animation-delay: calc(var(--score-delay, 0ms) + 700ms);
}

@keyframes scoreItemReveal {
    from {
        opacity: 0;
        transform: translateY(6px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes scoreFillGrow {
    from {
        transform: scaleX(0.12);
        filter: saturate(0.85);
    }

    to {
        transform: scaleX(1);
        filter: saturate(1);
    }
}

@keyframes scoreSheen {
    0% {
        left: -38%;
        opacity: 0;
    }

    25% {
        opacity: 1;
    }

    55% {
        left: 108%;
        opacity: 0;
    }

    100% {
        left: 108%;
        opacity: 0;
    }
}

@media (prefers-reduced-motion: reduce) {

    .score-bar-item,
    .score-bar-fill,
    .score-bar-fill::after,
    .qa-audio-visual::before,
    .qa-audio-wave-svg--a,
    .qa-audio-wave-svg--b,
    .dot-spinner__dot {
        animation: none;
    }

    .dot-spinner__dot {
        opacity: 0.85;
        filter: none;
    }
}

.overview-cards-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.overview-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1rem 1.02rem;
    box-shadow: 0 10px 20px rgba(31, 41, 38, 0.05);
}

.overview-summary-text {
    text-align: center;
    padding-bottom: 0.25rem;
}

.overview-card p.overview-summary-title {
    font-size: 1.2rem;
    line-height: 1.35;
    font-weight: 700 !important;
    color: var(--text);
}

.overview-card h1 {
    margin: 0 0 0.5rem;
    color: var(--text);
    font-size: 1.16rem;
    letter-spacing: -0.01em;
}

.overview-card p {
    margin: 0;
    color: var(--muted);
    line-height: 1.58;
}

.overview-charts-row {
    margin-top: 0.86rem;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem;
    align-items: stretch;
}

.radar-wrapper {
    border: 1px solid var(--line-soft);
    border-radius: 10px;
    padding: 0.75rem;
    background: var(--surface-soft);
}

.radar-chart {
    width: 100%;
    height: 360px;
}

.line-chart-wrapper {
    border: 1px solid var(--line-soft);
    border-radius: 10px;
    padding: 0.75rem;
    background: var(--surface-soft);
}

.score-line-chart {
    width: 100%;
    height: 360px;
}

.voice-llm-summary-section {
    margin-top: 0.86rem;
}

.voice-llm-summary-section h2 {
    margin: 0 0 0.7rem;
    color: var(--text);
    font-size: 1rem;
}

.voice-llm-panel {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
}

.voice-llm-subsection {
    border: 1px solid var(--line-soft);
    border-radius: 10px;
    background: var(--surface-soft);
    padding: 0.8rem;
}

.voice-llm-subsection h3 {
    margin: 0 0 0.85rem;
    color: var(--text);
    font-size: 1rem;
    font-weight: 700;
}

.voice-llm-subtitle {
    margin: 0.35rem 0 0.7rem;
    color: #6d7b76;
    font-size: 0.82rem;
    line-height: 1.6;
}

.voice-llm-gauge-panel {
    display: grid;
    grid-template-columns: minmax(0, 1.0fr) minmax(0, 1.0fr);
    gap: 0.8rem;
    align-items: stretch;
}

.voice-llm-gauge-chart-large {
    width: 100%;
    min-height: 330px;
    border: 1px solid var(--line-soft);
    border-radius: 10px;
    background: var(--surface);
}

.voice-llm-score-legend {
    border: 1px solid var(--line-soft);
    border-radius: 10px;
    background: var(--surface);
    padding: 0.72rem;
    display: flex;
    flex-direction: column;
    gap: 0.56rem;
    justify-content: center;
}

.voice-llm-score-legend-item {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.55rem;
    align-items: center;
    border-bottom: 1px dashed #d8e2dd;
    padding-bottom: 0.45rem;
}

.voice-llm-score-legend-item:last-child {
    border-bottom: none;
    padding-bottom: 0;
}

.voice-llm-score-legend-item--overall {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1.2rem;
}

.voice-llm-score-legend-item--overall .voice-llm-score-label {
    font-size: 1.22rem;
    font-weight: 700;
    color: var(--text);
    flex: none;
}

.voice-llm-score-legend-item--overall .voice-llm-score-value {
    font-size: 1.22rem;
    font-weight: 700;
    flex: none;
}

.voice-llm-score-dot {
    width: 0.6rem;
    height: 0.6rem;
    border-radius: 50%;
}

.voice-llm-score-label {
    display: block;
    color: #3b4b46;
    font-size: 0.8rem;
    line-height: 1.4;
}

.voice-llm-score-value {
    color: var(--text);
    font-size: 1.08rem;
    font-weight: 700;
}

.voice-llm-text-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
}

.voice-llm-text-item {
    border: 1px solid var(--line-soft);
    border-radius: 10px;
    background: var(--surface);
    padding: 0.7rem 0.72rem;
    position: relative;
    padding-bottom: 2rem;
}

.voice-llm-text-item--full-row {
    grid-column: 1 / -1;
}

.voice-llm-text-item h4 {
    margin: 0 0 0.35rem;
    color: #3b4b46;
    font-size: 0.88rem;
    font-weight: 600;
}

.voice-llm-text-item p {
    margin: 0;
    color: var(--text);
    font-size: 0.9rem;
    line-height: 1.58;
    white-space: pre-wrap;
    word-break: break-word;
}

.voice-llm-bullet-list {
    margin: 0;
    padding-left: 1.1rem;
    color: var(--text);
}

.voice-llm-bullet-list--clamped {
    max-height: 5.2rem;
    overflow: hidden;
    position: relative;
}

.voice-llm-bullet-list--clamped::after {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 1.45rem;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0), var(--surface));
    pointer-events: none;
}

.voice-llm-bullet-list li {
    font-size: 0.9rem;
    line-height: 1.58;
    word-break: break-word;
}

.voice-llm-bullet-list li::marker {
    font-size: 1.06em;
    color: #66756f;
}

.voice-llm-text-paragraph {
    margin: 0;
    color: var(--text);
    font-size: 0.9rem;
    line-height: 1.58;
    white-space: pre-wrap;
    word-break: break-word;
}

.voice-llm-text-paragraph--clamped {
    display: -webkit-box;
    overflow: hidden;
    line-clamp: 3;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
}

.voice-llm-expand-btn {
    position: absolute;
    right: 0.72rem;
    bottom: 0.56rem;
    border: none;
    background: transparent;
    color: var(--accent);
    line-height: 0;
    padding: 0;
    cursor: pointer;
}

.voice-llm-expand-btn:hover {
    color: #264c45;
}

.voice-llm-expand-icon-wrap {
    width: 1.45rem;
    height: 1.45rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    border: 1px solid #c8d8d1;
    background: #eef5f2;
    box-shadow: 0 2px 6px rgba(47, 93, 86, 0.12);
    transition: transform 0.2s ease, background-color 0.2s ease, border-color 0.2s ease;
}

.voice-llm-expand-icon-wrap svg {
    width: 0.82rem;
    height: 0.82rem;
}

.voice-llm-expand-icon-wrap--expanded {
    transform: rotate(180deg);
}

.voice-llm-expand-btn:hover .voice-llm-expand-icon-wrap {
    border-color: #b7ccc4;
    background: #e6efeb;
}

.voice-llm-encouragement-card {
    border: 1px solid #d6e4de;
    border-radius: 12px;
    background: linear-gradient(135deg, #f7fbf9 0%, #edf5f1 100%);
    padding: 0.82rem;
}

.voice-llm-encouragement-card h4 {
    margin: 0;
    color: var(--accent);
    font-size: 0.92rem;
    font-weight: 700;
}

.voice-llm-encouragement-lead {
    margin: 0.35rem 0 0;
    color: #57766e;
    font-size: 0.82rem;
    line-height: 1.5;
}

.voice-llm-encouragement-content {
    margin: 0.35rem 0 0;
    color: var(--text);
    font-size: 0.92rem;
    line-height: 1.62;
    white-space: pre-wrap;
    word-break: break-word;
}

.emotion-chart {
    width: 100%;
    height: 300px;
}

.emotion-empty {
    margin: 0;
    color: #6d7b76;
}

.score {
    margin-top: 0.72rem;
    font-size: 0.92rem;
    font-weight: 700;
    color: var(--accent);
}

.comment {
    margin-top: 0.72rem;
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--text);
}

.detail-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem;
}

.detail-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.95rem 0.98rem;
    box-shadow: 0 10px 20px rgba(31, 41, 38, 0.05);
}

.detail-card--full-row {
    grid-column: 1 / -1;
}

.detail-card h2 {
    margin: 0 0 0.62rem;
    font-size: 0.98rem;
    color: var(--text);
}

.detail-card ul {
    margin: 0;
    padding-left: 1.1rem;
    color: #475569;
    line-height: 1.7;
}

.detail-list-empty {
    margin: 0;
    color: #64748b;
    font-size: 0.92rem;
    line-height: 1.7;
}

.metric-list {
    list-style: none;
    padding-left: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.metric-group+.metric-group {
    margin-top: 0.9rem;
    padding-top: 0.85rem;
    border-top: 1px solid #dce6e1;
}

.metric-group-title {
    margin: 0 0 0.55rem;
    font-size: 0.86rem;
    color: #5a6f68;
    letter-spacing: 0.01em;
}

.metric-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.8rem;
}

.metric-item--stacked {
    align-items: flex-start;
}

.metric-label {
    color: var(--muted);
    font-size: 0.9rem;
}

.metric-value {
    color: var(--text);
    font-weight: 600;
}

.metric-level-wrap {
    display: inline-flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.25rem;
}

.metric-hint {
    color: #6f7f79;
    font-size: 0.78rem;
    line-height: 1.4;
    text-align: right;
    max-width: 220px;
}

.level-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.72rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    border: 1px solid transparent;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.24);
}

.level-badge::before {
    content: '';
    width: 0.42rem;
    height: 0.42rem;
    border-radius: 50%;
    background: currentColor;
    opacity: 0.8;
}

.level-badge--excellent {
    color: #2f5d56;
    background: #dff1ea;
    border-color: #82b9ab;
}

.level-badge--good {
    color: #3f655f;
    background: #e4eeea;
    border-color: #9cbab0;
}

.level-badge--warning {
    color: #8f5a33;
    background: #f5ead8;
    border-color: #d8b083;
}

.level-badge--danger {
    color: #8f3e37;
    background: #f4dedd;
    border-color: #d3a7a4;
}

.level-badge--neutral {
    color: #4f615b;
    background: #e7edea;
    border-color: #ccd8d3;
}

.empty-state {
    margin-top: 0.9rem;
    padding: 1.8rem;
    border: 1px dashed #cfdbd6;
    border-radius: 12px;
    color: #6d7b76;
    text-align: center;
    background: var(--surface);
}

.empty-state--loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.8rem;
}

.loading-text {
    margin: 0;
    color: #5f6f69;
    font-size: 0.9rem;
    letter-spacing: 0.01em;
}

.dot-spinner {
    --spinner-size: 54px;
    --dot-size: 10px;
    --dot-color: #111111;

    position: relative;
    width: var(--spinner-size);
    height: var(--spinner-size);
}

.dot-spinner__dot {
    position: absolute;
    top: 50%;
    left: 50%;
    width: var(--dot-size);
    height: var(--dot-size);
    margin-left: calc(var(--dot-size) * -0.5);
    margin-top: calc(var(--dot-size) * -0.5);
    border-radius: 50%;
    background: var(--dot-color);
    animation: dotSpinnerFade 0.96s linear infinite;
}

.dot-spinner__dot:nth-child(1) {
    transform: rotate(0deg) translateY(calc(var(--spinner-size) * -0.41));
    animation-delay: -0.84s;
}

.dot-spinner__dot:nth-child(2) {
    transform: rotate(45deg) translateY(calc(var(--spinner-size) * -0.41));
    animation-delay: -0.72s;
}

.dot-spinner__dot:nth-child(3) {
    transform: rotate(90deg) translateY(calc(var(--spinner-size) * -0.41));
    animation-delay: -0.6s;
}

.dot-spinner__dot:nth-child(4) {
    transform: rotate(135deg) translateY(calc(var(--spinner-size) * -0.41));
    animation-delay: -0.48s;
}

.dot-spinner__dot:nth-child(5) {
    transform: rotate(180deg) translateY(calc(var(--spinner-size) * -0.41));
    animation-delay: -0.36s;
}

.dot-spinner__dot:nth-child(6) {
    transform: rotate(225deg) translateY(calc(var(--spinner-size) * -0.41));
    animation-delay: -0.24s;
}

.dot-spinner__dot:nth-child(7) {
    transform: rotate(270deg) translateY(calc(var(--spinner-size) * -0.41));
    animation-delay: -0.12s;
}

.dot-spinner__dot:nth-child(8) {
    transform: rotate(315deg) translateY(calc(var(--spinner-size) * -0.41));
    animation-delay: 0s;
}

@keyframes dotSpinnerFade {

    0%,
    20% {
        opacity: 1;
        filter: blur(0);
    }

    100% {
        opacity: 0.2;
        filter: blur(0.35px);
    }
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

.title-with-icon {
    display: inline-flex;
    align-items: center;
    gap: 0.36rem;
    line-height: 1.3;
}

@media (max-width: 900px) {
    .review-layout {
        flex-direction: column;
        height: auto;
        min-height: 0;
        overflow: visible;
    }

    .history-sidebar {
        width: 100%;
        flex: none;
        border-right: none;
        border-bottom: 1px solid var(--line);
        max-height: none;
        overflow: visible;
    }

    .review-main {
        overflow: visible;
        padding: 0.88rem;
    }

    .overview-cards-container {
        grid-template-columns: 1fr;
    }

    .overview-charts-row {
        grid-template-columns: 1fr;
    }

    .detail-grid {
        grid-template-columns: 1fr;
    }

    .analysis-grid {
        grid-template-columns: 1fr;
    }

    .voice-llm-gauge-panel,
    .voice-llm-text-list {
        grid-template-columns: 1fr;
    }

    .voice-llm-gauge-chart-large {
        min-height: 340px;
    }

    .qa-audio-head {
        flex-direction: column;
        align-items: flex-start;
    }

    .qa-audio-tip {
        text-align: left;
    }

    .radar-chart {
        height: 300px;
    }

    .score-line-chart {
        height: 300px;
    }
}
</style>
