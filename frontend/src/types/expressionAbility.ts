export type VoiceLlmStatus = 'pending' | 'running' | 'success' | 'failed' | string

export interface VoiceLlmResultRecord {
  id: number
  interview_id: number
  status: VoiceLlmStatus
  overall_audio_score: number
  speech_rate_and_rhythm_score: number
  speech_rate_and_rhythm: string
  fluency_score: number
  fluency: string
  confidence_and_voice_energy_score: number
  confidence_and_voice_energy: string
  emotional_stability_and_tone_score: number
  emotional_stability_and_tone: string
  strengths: string
  improvements: string
  position_communication_tips: string
  encouragement: string
  llm_model: string
  prompt_version: string
  raw_input_json: Record<string, unknown>
  raw_output_json: Record<string, unknown>
  generated_at: string | null
  error_message: string
  retry_count: number
  created_at: string
  updated_at: string
}

export type ExpressionDimensionKey =
  | 'speech_rate_and_rhythm_score'
  | 'fluency_score'
  | 'confidence_and_voice_energy_score'
  | 'emotional_stability_and_tone_score'

export interface ExpressionDimensionMeta {
  key: ExpressionDimensionKey
  label: string
  textField:
    | 'speech_rate_and_rhythm'
    | 'fluency'
    | 'confidence_and_voice_energy'
    | 'emotional_stability_and_tone'
}

export interface ExpressionTrendPoint {
  id: number
  dateLabel: string
  timestamp: number
  overall: number
  speech_rate_and_rhythm_score: number
  fluency_score: number
  confidence_and_voice_energy_score: number
  emotional_stability_and_tone_score: number
}

export interface ExpressionInsight {
  text: string
  count: number
}

export interface ExpressionOverviewState {
  currentScore: number | null
  previousScore: number | null
  scoreDelta: number | null
  averageScore: number | null
  sampleCount: number
  dimensionsAverage: Record<ExpressionDimensionKey, number | null>
  trend: ExpressionTrendPoint[]
  strengthsTop: ExpressionInsight[]
  improvementsTop: ExpressionInsight[]
  positionTipsTop: ExpressionInsight[]
  encouragement: string
  modelInfo: {
    llmModel: string
    promptVersion: string
  } | null
}

export interface ExpressionOverviewApiData {
  records: VoiceLlmResultRecord[]
}

export interface ExpressionOverviewApiResponse {
  code: number
  message: string
  data?: ExpressionOverviewApiData
}
