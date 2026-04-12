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
    status: string
    duration_seconds: number | null
    rounds: RoundInfo[]
}

interface InterviewListApiItem {
    id: number
    name: string
    position_name: string
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

const voiceGaugePointerColors = ['#ef4444', '#f59e0b', '#22c55e', '#3b82f6', '#8b5cf6']

const voiceLlmGaugeItems = computed(() =>
    voiceLlmScoreItems.value
        .map((item, index) => ({
            ...item,
            rawValue: parseVoiceLlmGaugeScore(item.value),
            color: voiceGaugePointerColors[index % voiceGaugePointerColors.length]
        }))
        .filter(item => item.rawValue !== null)
)


const buildVoiceScoreGaugeOption = (): echarts.EChartsOption => {
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
                color: '#ef4444',
                shadowBlur: 10,
                shadowColor: 'rgba(239, 68, 68, 0.45)',
                shadowOffsetY: 3
            }
        },
        anchor: {
            show: true,
            showAbove: true,
            size: 9,
            itemStyle: {
                color: '#ffffff',
                borderColor: '#ef4444',
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
        tooltip: { /* 保持你原来的 tooltip 配置 */ },
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

    if (!voiceScoreGaugeChartInstance.value || voiceScoreGaugeChartInstance.value.isDisposed?.()) {
        voiceScoreGaugeChartInstance.value = echarts.init(voiceScoreGaugeChartRef.value)
    }

    voiceScoreGaugeChartInstance.value.setOption(buildVoiceScoreGaugeOption(), true)
    voiceScoreGaugeChartInstance.value.resize()
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

const radarOption: echarts.EChartsOption = {
    color: ['#67F9D8', '#FFE434', '#56A3F1', '#FF917C'],
    title: {
        text: '面试总体表现'
    },
    legend: {},
    radar: [
        {
            indicator: [
                { name: 'Indicator1' },
                { name: 'Indicator2' },
                { name: 'Indicator3' },
                { name: 'Indicator4' },
                { name: 'Indicator5' }
            ],
            center: ['50%', '50%'],
            radius: 100,
            startAngle: 90,
            splitNumber: 4,
            shape: 'circle',
            axisName: {
                formatter: '【{value}】',
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
                    value: [60, 5, 0.3, -100, 1500],
                    name: 'Data B',
                    areaStyle: {
                        color: 'rgba(255, 228, 52, 0.6)'
                    }
                }
            ]
        }
    ]
}

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
                connectNulls: false,
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
                connectNulls: false,
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
                connectNulls: false,
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
                connectNulls: false,
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
                connectNulls: false,
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

        radarChartInstance.value.setOption(radarOption)
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

const fetchInterviewVoiceLlmResult = async (interviewId: string) => {
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

        voiceLlmResultMap.value = {
            ...voiceLlmResultMap.value,
            [interviewId]: result.data?.voice_llm_result ?? null
        }
    } catch (error) {
        voiceLlmErrors.value = {
            ...voiceLlmErrors.value,
            [interviewId]: error instanceof Error ? error.message : '获取语音复盘总结失败'
        }
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

        await Promise.all(rounds.map(round => fetchRoundAudioAnalysis(interviewId, round.id)))

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
            status: item.status,
            duration_seconds: item.duration_seconds ?? null,
            rounds: []
        }))

        selectedInterviewId.value = interviewHistory.value[0]?.id ?? ''
        if (selectedInterviewId.value) {
            await fetchInterviewRounds(selectedInterviewId.value)
            fetchInterviewVoiceLlmResult(selectedInterviewId.value)
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
        fetchInterviewVoiceLlmResult(newInterviewId)
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

    if (selectedInterviewId.value) {
        fetchRoundAudioAnalysis(selectedInterviewId.value, id)
    }
}

const formatMetricValue = (value: number | null, unit = '') => {
    if (typeof value !== 'number' || Number.isNaN(value)) {
        return '暂无数据'
    }
    return `${value.toFixed(2)}${unit}`
}

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

const fillerWordItems = computed(() => {
    const counts = selectedVoiceAnalysis.value?.filler_word_counts
    if (!counts) {
        return []
    }
    return Object.entries(counts)
})

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

const addDotPrefixForMultiLine = (text: string): string => {
    if (text === '暂无数据') {
        return text
    }

    const lines = text
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        .split('\n')
        .map(line => line.trim())
        .filter(Boolean)

    if (lines.length <= 1) {
        return text
    }

    return lines
        .map(line => (line.startsWith('●') ? line : `● ${line.replace(/^[•·●]\s*/, '')}`))
        .join('\n')
}

const stripQuoteChars = (text: string): string => text.replace(/["'‘’“”]/g, '')

const formatVoiceLlmText = (value: string | null) => {
    if (typeof value !== 'string') {
        return '暂无数据'
    }

    const trimmed = value.trim()
    if (!trimmed) {
        return '暂无数据'
    }

    const parsed = parseVoiceLlmJsonLike(trimmed)
    if (parsed !== null) {
        return addDotPrefixForMultiLine(stripQuoteChars(normalizeVoiceLlmParsedValue(parsed)))
    }

    if ((trimmed.startsWith('[') && trimmed.endsWith(']')) || (trimmed.startsWith('{') && trimmed.endsWith('}'))) {
        const cleaned = trimmed
            .replace(/^[\[{]\s*/, '')
            .replace(/\s*[\]}]$/, '')
            .replace(/["']/g, '')
            .replace(/\s*,\s*/g, '\n')
            .trim()
        return addDotPrefixForMultiLine(stripQuoteChars(cleaned || '暂无数据'))
    }

    return addDotPrefixForMultiLine(stripQuoteChars(trimmed))
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

watch([isOverviewSelected, selectedInterviewVoiceLlmResult], ([overviewActive, result]) => {
    if (!overviewActive || !result || !voiceLlmGaugeItems.value.length) {
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
                <button type="button" class="back-btn" @click="goBack">返回</button>
            </div>

            <header class="round-navbar" v-if="selectedInterview">
                <button v-for="nav in roundNavItems" :key="nav.id"
                    :class="['round-tab', { active: selectedRoundId === nav.id }]" @click="selectRound(nav.id)">
                    {{ nav.label }}
                </button>
            </header>

            <div v-if="loadingRounds" class="empty-state">轮次加载中...</div>
            <div v-else-if="roundError" class="empty-state">{{ roundError }}</div>
            <article v-if="isOverviewSelected && selectedInterview" class="round-content">
                <section class="overview-card">
                    <div class="overview-summary-text">
                        <p class="overview-summary-title">整体情况</p>
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

                    <section class="voice-llm-summary-section">
                        <h1>面试音频部分评估总结</h1>
                        <div v-if="isSelectedInterviewVoiceLlmLoading" class="analysis-tip">语音复盘总结加载中...</div>
                        <div v-else-if="selectedInterviewVoiceLlmError" class="analysis-tip error">{{
                            selectedInterviewVoiceLlmError }}</div>
                        <div v-else-if="!selectedInterviewVoiceLlmResult" class="analysis-tip">暂无语音复盘总结数据</div>

                        <div v-else class="voice-llm-panel">
                            <section class="voice-llm-subsection voice-llm-subsection--score">
                                <h3>表现分数</h3>
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
                                <h3>分析</h3>
                                <div class="voice-llm-text-list">
                                    <article v-for="item in voiceLlmAnalysisItems" :key="item.key"
                                        class="voice-llm-text-item">
                                        <h4>{{ item.label }}</h4>
                                        <p>{{ formatVoiceLlmText(item.value) }}</p>
                                    </article>
                                </div>
                            </section>

                            <section class="voice-llm-subsection voice-llm-subsection--text">
                                <h3>建议</h3>
                                <div class="voice-llm-text-list">
                                    <article v-for="item in voiceLlmSuggestionItems" :key="item.key"
                                        :class="['voice-llm-text-item', { 'voice-llm-text-item--full-row': item.key === 'position_communication_tips' }]">
                                        <h4>{{ item.label }}</h4>
                                        <p>{{ formatVoiceLlmText(item.value) }}</p>
                                    </article>
                                </div>
                            </section>

                            <section v-if="voiceLlmEncouragementItem"
                                class="voice-llm-subsection voice-llm-subsection--encouragement">
                                <article class="voice-llm-encouragement-card">
                                    <h4>{{ voiceLlmEncouragementItem.label }}</h4>
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
                    <h2>面试官问题</h2>
                    <p>{{ selectedRound.interviewerQuestion }}</p>

                    <h2>你的文字回答</h2>
                    <p>{{ selectedRound.yourAnswer }}</p>

                    <h2>你的语音回答</h2>
                    <div v-if="selectedRoundAudioSrc" class="qa-audio-player-wrap">
                        <audio class="qa-audio-player" :src="selectedRoundAudioSrc" controls preload="metadata">
                            当前浏览器不支持音频播放。
                        </audio>
                    </div>
                    <p v-else class="qa-audio-empty">暂无该轮音频录音</p>
                </section>

                <section class="analysis-section">
                    <h2>结果分析</h2>
                    <div v-if="isSelectedRoundAudioLoading" class="analysis-tip">音频分析数据加载中...</div>
                    <div v-else-if="selectedRoundAudioError" class="analysis-tip error">{{ selectedRoundAudioError }}
                    </div>
                    <div v-else-if="!selectedVoiceAnalysis" class="analysis-tip">暂无音频分析数据</div>

                    <div v-else class="analysis-grid">
                        <section class="detail-card">
                            <h2>分数可视化</h2>
                            <div class="score-bars">
                                <div v-for="item in scoreBars" :key="item.key" class="score-bar-item">
                                    <div class="score-bar-head">
                                        <span>{{ item.label }}</span>
                                        <strong>{{ formatMetricValue(item.rawValue) }}</strong>
                                    </div>
                                    <div class="score-bar-track">
                                        <div class="score-bar-fill" :style="{ width: `${item.value ?? 0}%` }"></div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <section class="detail-card">
                            <h2>语音指标</h2>
                            <ul class="metric-list">
                                <li class="metric-item">
                                    <span class="metric-label">时长</span>
                                    <span class="metric-value">{{
                                        formatMetricValue(selectedVoiceAnalysis.duration_seconds, ' 秒') }}</span>
                                </li>
                                <li class="metric-item">
                                    <span class="metric-label">语速</span>
                                    <span class="metric-value">{{ formatMetricValue(selectedVoiceAnalysis.speech_rate,
                                        '字/秒') }}</span>
                                </li>
                                <li class="metric-item metric-item--stacked">
                                    <span class="metric-label">语速等级</span>
                                    <span class="metric-level-wrap">
                                        <span
                                            :class="['level-badge', getLevelToneClass(selectedSpeechRateLevelDisplay.tone)]">
                                            {{ selectedSpeechRateLevelDisplay.label }}
                                        </span>
                                        <small class="metric-hint">{{ selectedSpeechRateLevelDisplay.hint }}</small>
                                    </span>
                                </li>
                            </ul>
                        </section>

                        <section class="detail-card">
                            <h2>停顿与空白</h2>
                            <ul>
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
                                        <small class="metric-hint">{{ selectedSilenceLevelDisplay.hint }}</small>
                                    </span>
                                </li>
                                <li>总停顿次数：{{ selectedVoiceAnalysis.filler_word_total ?? '暂无数据' }}</li>
                                <li v-for="item in fillerWordItems" :key="item[0]">{{ item[0] }}：{{ item[1] }}</li>
                            </ul>
                        </section>

                        <section class="detail-card">
                            <h2>情绪分布</h2>
                            <div v-if="emotionPieData.length" ref="emotionChartRef" class="emotion-chart"></div>
                            <p v-else class="emotion-empty">暂无情绪分布数据</p>
                        </section>




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
                        <h2>不足之处</h2>
                        <ul>
                            <li v-for="item in selectedRound.weaknesses" :key="item">{{ item }}</li>
                        </ul>
                    </section>

                    <section class="detail-card">
                        <h2>改进建议</h2>
                        <ul>
                            <li v-for="item in selectedRound.suggestions" :key="item">{{ item }}</li>
                        </ul>
                    </section>

                    <section class="detail-card">
                        <h2>关联的知识点</h2>
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
    display: flex;
    min-height: calc(100vh - 0px);
    height: calc(100vh - 0px);
    background: #f8fafc;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}

.history-sidebar {
    width: 280px;
    flex: 0 0 280px;
    background: #ffffff;
    border-right: 1px solid #e2e8f0;
    padding: 1rem;
    overflow-y: auto;
}

.history-sidebar h2 {
    margin: 0 0 0.8rem;
    font-size: 1.1rem;
    color: #0f172a;
}

.history-filter-box {
    margin-bottom: 0.9rem;
    padding: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
}

.history-search-input,
.history-date-input {
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 0.42rem 0.55rem;
    font-size: 0.85rem;
    color: #0f172a;
    background: #ffffff;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.history-search-input:focus,
.history-date-input:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

/* Hide browser date hint text when value is empty; keep visible once focused or selected. */
.history-date-input:invalid::-webkit-datetime-edit {
    color: transparent;
}

.history-date-input:focus::-webkit-datetime-edit,
.history-date-input:valid::-webkit-datetime-edit {
    color: #0f172a;
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
    color: #475569;
}

.history-filter-reset {
    align-self: flex-end;
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    padding: 0.25rem 0.75rem;
    font-size: 0.76rem;
    color: #334155;
    background: #ffffff;
    cursor: pointer;
    transition: all 0.2s ease;
}

.history-filter-reset:hover {
    color: #1d4ed8;
    border-color: #60a5fa;
    background: #eff6ff;
}

.history-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
}

.history-item {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.75rem;
    cursor: pointer;
    transition: all 0.2s ease;
    background: #fff;
}

.history-item:hover {
    border-color: #60a5fa;
    background: #eff6ff;
}

.history-item.active {
    border-color: #2563eb;
    background: #dbeafe;
}

.history-item h3 {
    margin: 0 0 0.35rem;
    font-size: 0.95rem;
    color: #0f172a;
}

.history-item p {
    margin: 0 0 0.3rem;
    font-size: 0.85rem;
    color: #475569;
}

.history-item span {
    font-size: 0.8rem;
    color: #64748b;
}

.status-text {
    margin: 0 0 0.3rem;
    font-size: 0.8rem;
    color: #1e40af;
}

.sidebar-tip {
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    padding: 0.8rem;
    color: #64748b;
    background: #ffffff;
}

.sidebar-tip.error {
    color: #b91c1c;
    border-color: #fecaca;
    background: #fef2f2;
}

.review-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 1.2rem;
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
}

.review-topbar {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 0.8rem;
}

.back-btn {
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: #334155;
    border-radius: 8px;
    padding: 0.42rem 0.85rem;
    cursor: pointer;
    transition: all 0.2s ease;
}

.back-btn:hover {
    border-color: #60a5fa;
    color: #1d4ed8;
    background: #eff6ff;
}

.round-navbar {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.8rem;
}

.round-tab {
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    padding: 0.4rem 0.95rem;
    background: #fff;
    color: #334155;
    cursor: pointer;
}

.round-tab.active {
    background: #667eea;
    border-color: #667eea;
    color: #fff;
}

.round-content {
    margin-top: 1rem;
    display: flex;
    flex-direction: column;
    flex: 1;
    gap: 1rem;
}

.round-content>.overview-card {
    flex: 1;
}

.qa-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem;
}

.qa-card h2 {
    margin: 0 0 0.5rem;
    font-size: 1.05rem;
    color: #0f172a;
}

.qa-card h2:not(:first-child) {
    margin-top: 1rem;
}

.qa-card p {
    margin: 0;
    color: #475569;
    line-height: 1.7;
}

.qa-audio-player-wrap {
    margin-top: 0.25rem;
}

.qa-audio-player {
    width: 100%;
}

.qa-audio-empty {
    color: #64748b;
}

.analysis-section h2 {
    margin: 0;
    font-size: 1.1rem;
    color: #0f172a;
}

.analysis-grid {
    margin-top: 0.8rem;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
}

.analysis-tip {
    margin-top: 0.8rem;
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    padding: 0.8rem;
    color: #64748b;
    background: #ffffff;
}

.analysis-tip.error {
    color: #b91c1c;
    border-color: #fecaca;
    background: #fef2f2;
}

.score-bars {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
}

.score-bar-item {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.score-bar-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.88rem;
    color: #334155;
}

.score-bar-head strong {
    color: #0f172a;
}

.score-bar-track {
    width: 100%;
    height: 10px;
    border-radius: 999px;
    overflow: hidden;
    background: #e2e8f0;
}

.score-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #0ea5e9, #2563eb);
    transition: width 0.35s ease;
}

.overview-cards-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.overview-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem;
}

.overview-summary-text {
    text-align: center;
}

.overview-card p.overview-summary-title {
    font-size: 30px;
    line-height: 1.25;
    font-weight: 700 !important;
    color: #000000;
}

.overview-card h1 {
    margin: 0 0 0.55rem;
    color: #0f172a;
    font-size: 1.25rem;
}

.overview-card p {
    margin: 0;
    color: #475569;
    line-height: 1.6;
}

.overview-charts-row {
    margin-top: 1rem;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
    align-items: stretch;
}

.radar-wrapper {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.8rem;
    background: #f8fafc;
}

.radar-chart {
    width: 100%;
    height: 360px;
}

.line-chart-wrapper {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.8rem;
    background: #f8fafc;
}

.score-line-chart {
    width: 100%;
    height: 360px;
}

.voice-llm-summary-section {
    margin-top: 1rem;
}

.voice-llm-summary-section h2 {
    margin: 0 0 0.8rem;
    color: #0f172a;
    font-size: 1.05rem;
}

.voice-llm-panel {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
}

.voice-llm-subsection {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #f8fafc;
    padding: 0.85rem;
}

.voice-llm-subsection h3 {
    margin: 0 0 1rem;
    color: #0f172a;
    font-size: 1.1rem;
    font-weight: 700;
}

.voice-llm-subtitle {
    margin: 0.35rem 0 0.7rem;
    color: #64748b;
    font-size: 0.82rem;
    line-height: 1.6;
}

.voice-llm-gauge-panel {
    display: grid;
    grid-template-columns: minmax(0, 1.0fr) minmax(0, 1.0fr);
    gap: 0.9rem;
    align-items: stretch;
}

.voice-llm-gauge-chart-large {
    width: 100%;
    min-height: 330px;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #ffffff;
}

.voice-llm-score-legend {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #ffffff;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    justify-content: center;
}

.voice-llm-score-legend-item {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.55rem;
    align-items: center;
    border-bottom: 1px dashed #e2e8f0;
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
    font-size: 1.3rem;
    font-weight: 700;
    color: #1e293b;
    flex: none;
}

.voice-llm-score-legend-item--overall .voice-llm-score-value {
    font-size: 1.3rem;
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
    color: #334155;
    font-size: 0.8rem;
    line-height: 1.4;
}

.voice-llm-score-value {
    color: #0f172a;
    font-size: 1.2rem;
    font-weight: 700;
    font-weight: 1500;
}

.voice-llm-text-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.8rem;
}

.voice-llm-text-item {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #ffffff;
    padding: 0.75rem;
}

.voice-llm-text-item--full-row {
    grid-column: 1 / -1;
}

.voice-llm-text-item h4 {
    margin: 0 0 0.35rem;
    color: #334155;
    font-size: 0.9rem;
    font-weight: 600;
}

.voice-llm-text-item p {
    margin: 0;
    color: #0f172a;
    font-size: 0.92rem;
    line-height: 1.65;
    white-space: pre-wrap;
    word-break: break-word;
}

.voice-llm-encouragement-card {
    border: 1px solid #fcd34d;
    border-radius: 12px;
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    padding: 0.85rem;
}

.voice-llm-encouragement-card h4 {
    margin: 0;
    color: #92400e;
    font-size: 0.95rem;
    font-weight: 700;
}

.voice-llm-encouragement-lead {
    margin: 0.35rem 0 0;
    color: #b45309;
    font-size: 0.82rem;
    line-height: 1.5;
}

.voice-llm-encouragement-content {
    margin: 0.35rem 0 0;
    color: #0f172a;
    font-size: 0.94rem;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
}

.emotion-chart {
    width: 100%;
    height: 300px;
}

.emotion-empty {
    margin: 0;
    color: #64748b;
}

.score {
    margin-top: 0.85rem;
    font-size: 0.95rem;
    font-weight: 700;
    color: #d8581d;
}

.comment {
    margin-top: 0.85rem;
    font-size: 0.95rem;
    font-weight: 700;
    color: #0f172a;
}

.detail-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
}

.detail-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem;
}

.detail-card h2 {
    margin: 0 0 0.7rem;
    font-size: 1.05rem;
    color: #0f172a;
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
    color: #475569;
    font-size: 0.92rem;
}

.metric-value {
    color: #0f172a;
    font-weight: 600;
}

.metric-level-wrap {
    display: inline-flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.25rem;
}

.metric-hint {
    color: #64748b;
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
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.2);
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
    color: #065f46;
    background: #bbf7d0;
    border-color: #22c55e;
}

.level-badge--good {
    color: #1e3a8a;
    background: #bfdbfe;
    border-color: #3b82f6;
}

.level-badge--warning {
    color: #92400e;
    background: #fde68a;
    border-color: #f59e0b;
}

.level-badge--danger {
    color: #991b1b;
    background: #fecaca;
    border-color: #ef4444;
}

.level-badge--neutral {
    color: #334155;
    background: #e2e8f0;
    border-color: #cbd5e1;
}

.empty-state {
    margin-top: 1rem;
    padding: 2rem;
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    color: #64748b;
    text-align: center;
    background: #ffffff;
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
        border-bottom: 1px solid #e2e8f0;
        max-height: none;
        overflow: visible;
    }

    .review-main {
        overflow: visible;
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
        min-height: 360px;
    }

    .radar-chart {
        height: 300px;
    }

    .score-line-chart {
        height: 300px;
    }
}
</style>
