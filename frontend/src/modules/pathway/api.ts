import api from '@/utils/api'
import type {
  PathwayEffectResponse,
  PathwayGenerationResponse,
  PathwayOverviewResponse,
  PathwayTaskCompleteResponse,
} from './types'

export const fetchCurrentPathwayPlan = async (): Promise<PathwayOverviewResponse> => {
  return (await api.get('/api/pathway/plan/current/')) as PathwayOverviewResponse
}

export const generatePathwayPlan = async (cycleDays = 7): Promise<PathwayOverviewResponse> => {
  return (await api.post('/api/pathway/plan/generate/', { cycle_days: cycleDays })) as PathwayOverviewResponse
}

export const startPathwayGeneration = async (cycleDays = 7): Promise<PathwayGenerationResponse> => {
  return (await api.post('/api/pathway/plan/generate-async/', { cycle_days: cycleDays })) as PathwayGenerationResponse
}

export const fetchPathwayGenerationStatus = async (jobId: number): Promise<PathwayGenerationResponse> => {
  return (await api.get(`/api/pathway/plan/generation-status/${jobId}/`)) as PathwayGenerationResponse
}

export const fetchLatestPathwayGeneration = async (): Promise<PathwayGenerationResponse> => {
  return (await api.get('/api/pathway/plan/generation-latest/')) as PathwayGenerationResponse
}

export const completePathwayTask = async (
  taskId: number,
  status: 'done' | 'skipped' = 'done',
): Promise<PathwayTaskCompleteResponse> => {
  return (await api.post(`/api/pathway/tasks/${taskId}/complete/`, { status })) as PathwayTaskCompleteResponse
}

export const fetchPathwayEffect = async (): Promise<PathwayEffectResponse> => {
  return (await api.get('/api/pathway/effect/')) as PathwayEffectResponse
}
