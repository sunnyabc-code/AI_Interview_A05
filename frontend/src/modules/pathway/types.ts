export type PathwayTaskType = 'resource' | 'question' | 'practice' | 'review'

export interface PathwayRecommendedLink {
  id: number
  title: string
  url: string
  resourceType: string
  focusArea: string
  topic?: string
}

export interface PathwayTask {
  id?: number
  dayIndex: number
  taskType: PathwayTaskType
  title: string
  reason: string
  estimatedMinutes: number
  status?: 'pending' | 'done' | 'skipped'
  priority?: number
  recommendedLinks?: PathwayRecommendedLink[]
}

export interface PathwayWeakness {
  key: string
  weakness_type: string
  severity: number
  trend: number
  evidence?: string[]
}

export interface PathwayProfile {
  technicalScore: number | null
  expressionScore: number | null
  dimensions: Record<string, number | null>
  weaknesses: PathwayWeakness[]
  strengths: string[]
  confidenceLevel: number
  snapshotTime: string | null
}

export interface PathwayPlan {
  planId?: number
  cycleDays: number
  goalSummary: string
  expectedGain: Record<string, number>
  generationMeta?: {
    mode?: string
    llm_used?: boolean
    llm_model?: string
    prompt_version?: string
    fallback_reason?: string
  }
  profile?: PathwayProfile
  tasks: PathwayTask[]
}

export interface PathwayGenerationJob {
  jobId: number
  status: 'pending' | 'running' | 'success' | 'failed'
  cycleDays: number
  currentDay: number
  totalDays: number
  progressPercent: number
  message: string
  errorMessage?: string
  planId?: number
  meta?: Record<string, unknown>
}

export interface PathwayOverviewResponse {
  code: number
  message: string
  data?: {
    plan: PathwayPlan | null
  }
}

export interface PathwayGenerationResponse {
  code: number
  message: string
  data?: {
    job: PathwayGenerationJob | null
    plan?: PathwayPlan
  }
}

export interface PathwayEffect {
  planId?: number
  status?: string
  completionRate: number
  doneTasks: number
  totalTasks: number
  deltas: Record<string, number>
}

export interface PathwayEffectResponse {
  code: number
  message: string
  data?: PathwayEffect
}

export interface PathwayTaskCompleteResponse {
  code: number
  message: string
  data?: {
    taskId: number
    status: 'pending' | 'done' | 'skipped'
    doneAt?: string | null
  }
}
