<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PathwayRouteMap from '../components/PathwayRouteMap.vue'
import {
  completePathwayTask,
  fetchCurrentPathwayPlan,
  fetchLatestPathwayGeneration,
  fetchPathwayGenerationStatus,
  startPathwayGeneration,
} from '../api'
import type { PathwayGenerationJob, PathwayPlan, PathwayTask } from '../types'

const router = useRouter()

const loading = ref(false)
const generating = ref(false)
const updating = ref(false)
const errorMessage = ref('')
const plan = ref<PathwayPlan | null>(null)
const generationJob = ref<PathwayGenerationJob | null>(null)

let pollTimer: ReturnType<typeof setInterval> | null = null

const hasPlan = computed(() => !!plan.value && plan.value.tasks.length > 0)

const dimensionLabelMap: Record<string, string> = {
  technical: '技术能力',
  expression: '表达能力',
  communication: '沟通能力',
  logic: '逻辑能力',
  adaptability: '应变能力',
}

const profileUpperBound = computed(() => {
  const v = Number(plan.value?.profile?.dimensions?.score_upper_bound)
  return Number.isFinite(v) && v > 0 ? v : 100
})

const abilityItems = computed(() => {
  const dims = plan.value?.profile?.dimensions || {}
  const keys = ['technical', 'expression', 'communication', 'logic', 'adaptability']
  return keys
    .map((key) => {
      const scoreRaw = dims[key]
      const score = typeof scoreRaw === 'number' ? scoreRaw : null
      const max = profileUpperBound.value
      const percent = score === null ? 0 : Math.max(0, Math.min(100, (score / max) * 100))
      return {
        key,
        label: dimensionLabelMap[key] || key,
        score,
        percent,
      }
    })
    .sort((a, b) => b.percent - a.percent)
})

const topWeaknesses = computed(() => {
  const list = plan.value?.profile?.weaknesses || []
  return [...list].sort((a, b) => (b.severity || 0) - (a.severity || 0)).slice(0, 5)
})

const totalMinutes = computed(() => {
  const tasks = plan.value?.tasks || []
  return tasks.reduce((sum, task) => sum + (task.estimatedMinutes || 0), 0)
})

const goBack = () => {
  router.push('/evaluation')
}

const stopPolling = () => {
  if (!pollTimer) return
  clearInterval(pollTimer)
  pollTimer = null
}

const loadPlan = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await fetchCurrentPathwayPlan()
    if (res.code !== 200 || !res.data?.plan) {
      plan.value = null
      return
    }
    plan.value = res.data.plan
  } catch (error) {
    plan.value = null
    errorMessage.value = error instanceof Error ? error.message : '加载失败'
  } finally {
    loading.value = false
  }
}

const syncJobStatus = async (jobId: number) => {
  const res = await fetchPathwayGenerationStatus(jobId)
  if (res.code !== 200 || !res.data?.job) {
    throw new Error(res.message || '获取生成进度失败')
  }

  const job = res.data.job
  generationJob.value = job
  generating.value = job.status === 'pending' || job.status === 'running'

  if (job.status === 'success') {
    stopPolling()
    if (res.data.plan) {
      plan.value = res.data.plan
    } else {
      await loadPlan()
    }
    return
  }

  if (job.status === 'failed') {
    stopPolling()
    errorMessage.value = job.errorMessage || '生成失败，请重试'
  }
}

const startPolling = (jobId: number) => {
  stopPolling()
  pollTimer = setInterval(() => {
    syncJobStatus(jobId).catch((error) => {
      stopPolling()
      generating.value = false
      errorMessage.value = error instanceof Error ? error.message : '轮询生成进度失败'
    })
  }, 1200)
}

const resumeLatestJob = async () => {
  try {
    const res = await fetchLatestPathwayGeneration()
    const job = res.data?.job
    if (!job) return

    generationJob.value = job
    if (job.status === 'pending' || job.status === 'running') {
      generating.value = true
      startPolling(job.jobId)
      await syncJobStatus(job.jobId)
    }
  } catch {
    // ignore resume failure
  }
}

const createPlan = async () => {
  generating.value = true
  errorMessage.value = ''
  try {
    const res = await startPathwayGeneration(7)
    if (res.code !== 200 || !res.data?.job) {
      throw new Error(res.message || '生成任务启动失败')
    }

    generationJob.value = res.data.job
    await syncJobStatus(res.data.job.jobId)

    if (res.data.job.status === 'pending' || res.data.job.status === 'running') {
      startPolling(res.data.job.jobId)
    }
  } catch (error) {
    generating.value = false
    errorMessage.value = error instanceof Error ? error.message : '生成失败'
  }
}

const onCompleteTask = async (task: PathwayTask, status: 'done' | 'skipped') => {
  if (!task.id || updating.value) return
  updating.value = true
  errorMessage.value = ''
  try {
    const res = await completePathwayTask(task.id, status)
    if (res.code !== 200) {
      throw new Error(res.message || '更新失败')
    }
    await loadPlan()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '更新失败'
  } finally {
    updating.value = false
  }
}

onMounted(async () => {
  await loadPlan()
  await resumeLatestJob()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <section class="pathway-home">
    <header>
      <button type="button" class="back-btn" @click="goBack">返回上层</button>
      <h1>个性化提升路径</h1>
      <p>基于近期面试表现自动生成 7 天任务计划，支持打卡与效果追踪。</p>
    </header>

    <div class="actions">
      <button type="button" :disabled="loading" @click="loadPlan">刷新路径</button>
      <button type="button" :disabled="generating || updating" @click="createPlan">
        {{ generating ? '生成中...' : '生成7天路径' }}
      </button>
    </div>

    <div v-if="generating && generationJob" class="generating-banner">
      <div class="progress-head">
        <span>{{ generationJob.message || '正在生成学习路径...' }}</span>
        <span>第 {{ generationJob.currentDay }}/{{ generationJob.totalDays }} 天</span>
      </div>
      <div class="progress-track">
        <i class="progress-fill" :style="{ width: `${generationJob.progressPercent}%` }" />
      </div>
      <p class="progress-tip">生成在后端持续执行，刷新或切换页面后返回仍可查看进度。</p>
    </div>

    <div v-if="errorMessage" class="error">{{ errorMessage }}</div>

    <article v-if="plan" class="profile-card">
      <div class="profile-head">
        <h2>用户画像</h2>
        <span class="profile-tag">能力现状诊断</span>
      </div>
      <p class="profile-goal">{{ plan.goalSummary }}</p>
      <div class="profile-grid">
        <div class="profile-metric">
          <strong>{{ plan.profile?.technicalScore ?? '--' }}</strong>
          <span>技术总分</span>
        </div>
        <div class="profile-metric">
          <strong>{{ plan.profile?.expressionScore ?? '--' }}</strong>
          <span>表达总分</span>
        </div>
        <div class="profile-metric">
          <strong>{{ totalMinutes }}</strong>
          <span>总训练时长(分钟)</span>
        </div>
      </div>

      <div class="ability-panel" v-if="abilityItems.length">
        <h3>当前能力情况</h3>
        <div class="ability-list">
          <div v-for="item in abilityItems" :key="item.key" class="ability-row">
            <span class="ability-name">{{ item.label }}</span>
            <div class="ability-track">
              <i class="ability-fill" :style="{ width: `${item.percent}%` }" />
            </div>
            <span class="ability-score">{{ item.score ?? '--' }}</span>
          </div>
        </div>
      </div>

      <div class="weakness-panel" v-if="topWeaknesses.length">
        <h3>待弥补短板</h3>
        <div class="weakness-list">
          <article v-for="w in topWeaknesses" :key="`${w.key}-${w.trend}`" class="weakness-item">
            <strong>{{ dimensionLabelMap[w.key] || w.key }}</strong>
            <span>薄弱度 {{ w.severity }} · 趋势 {{ w.trend >= 0 ? '+' : '' }}{{ w.trend }}</span>
            <p>{{ (w.evidence && w.evidence[0]) || '暂无证据描述' }}</p>
          </article>
        </div>
      </div>
    </article>

    <article v-if="hasPlan && plan" class="plan-card">
      <h2>7 天学习路线图</h2>
      <PathwayRouteMap :tasks="plan.tasks" :updating="updating" @complete="onCompleteTask" />
    </article>

    <article v-if="!loading && !hasPlan" class="empty">
      <h2>暂无路径</h2>
      <p>你可以先点击“生成7天路径”。</p>
    </article>
  </section>
</template>

<style scoped>
.pathway-home {
  padding: 1rem;
  background:
    radial-gradient(circle at 8% 10%, rgba(204, 227, 219, 0.4) 0, transparent 24%),
    radial-gradient(circle at 90% 0%, rgba(235, 248, 242, 0.8) 0, transparent 28%),
    #ffffff;
}

.back-btn {
  border: 1px solid #cce3db;
  background: rgba(255, 255, 255, 0.8);
  color: #2f5d56;
  border-radius: 8px;
  padding: 0.3rem 0.65rem;
  cursor: pointer;
  margin-bottom: 0.5rem;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: #2f5d56;
  color: white;
}

h1 {
  margin: 0;
  color: #1f2926;
}

header p {
  margin: 0.3rem 0 0;
  color: #66756f;
}

.actions {
  margin-top: 0.8rem;
  display: flex;
  gap: 0.5rem;
}

button {
  border: 1px solid #cce3db;
  background: rgba(255, 255, 255, 0.8);
  color: #2f5d56;
  border-radius: 8px;
  padding: 0.4rem 0.72rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

button:hover:not(:disabled) {
  background: #2f5d56;
  color: white;
}

button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.error {
  margin-top: 0.7rem;
  border: 1px solid #ffcdd2;
  background: #fff5f5;
  color: #d32f2f;
  border-radius: 8px;
  padding: 0.6rem;
}

.generating-banner {
  margin-top: 0.7rem;
  border: 1px solid #cce3db;
  background: rgba(235, 248, 242, 0.4);
  color: #2f5d56;
  border-radius: 10px;
  padding: 0.56rem 0.7rem;
}

.progress-head {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.82rem;
}

.progress-track {
  margin-top: 0.42rem;
  height: 8px;
  border-radius: 999px;
  background: #e6f2eb;
  overflow: hidden;
}

.progress-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #2f5d56 0%, #479e91 100%);
}

.progress-tip {
  margin: 0.4rem 0 0;
  font-size: 0.75rem;
  color: #234741;
}

.plan-card,
.empty {
  margin-top: 0.8rem;
  border: 1px solid #cce3db;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  padding: 0.8rem;
}

.profile-card {
  margin-top: 0.9rem;
  border-radius: 12px;
  padding: 0.8rem;
  background:
    radial-gradient(circle at 18% -10%, rgba(255, 255, 255, 0.08) 0, transparent 45%),
    radial-gradient(circle at 100% 0%, rgba(204, 227, 219, 0.12) 0, transparent 30%),
    linear-gradient(135deg, #2f5d56, #1f423d);
  border: 1px solid #1a332f;
  color: #ffffff;
  box-shadow: 0 6px 20px rgba(31, 41, 38, 0.3);
}

.profile-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
}

.profile-head h2 {
  color: #ffffff;
  margin: 0;
}

.profile-tag {
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
  font-size: 0.74rem;
  padding: 0.16rem 0.56rem;
}

.profile-goal {
  margin: 0.46rem 0 0;
  color: rgba(255, 255, 255, 0.85);
}

.profile-grid {
  margin-top: 0.65rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
}

.profile-metric {
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  padding: 0.55rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.profile-metric strong {
  display: block;
  font-size: 1.22rem;
  color: #2f5d56;
}

.profile-metric span {
  font-size: 0.76rem;
  color: #66756f;
}

.ability-panel,
.weakness-panel {
  margin-top: 0.7rem;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  padding: 0.8rem;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
}

.ability-panel h3,
.weakness-panel h3 {
  margin: 0;
  font-size: 0.95rem;
  color: #1f2926;
}

.ability-list {
  margin-top: 0.6rem;
  display: grid;
  gap: 0.45rem;
}

.ability-row {
  display: grid;
  grid-template-columns: 84px 1fr 58px;
  align-items: center;
  gap: 0.45rem;
}

.ability-name {
  color: #1f2926;
  font-size: 0.78rem;
  font-weight: 500;
}

.ability-track {
  position: relative;
  height: 10px;
  border-radius: 999px;
  background: #e6f2eb;
  overflow: hidden;
}

.ability-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #6ee7b7 0%, #34d399 70%, #10b981 100%);
}

.ability-score {
  text-align: right;
  font-size: 0.78rem;
  color: #2f5d56;
  font-weight: 600;
}

.weakness-list {
  margin-top: 0.6rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.5rem;
}

.weakness-item {
  border: 1px solid #cce3db;
  border-radius: 10px;
  background: #ffffff;
  padding: 0.6rem;
  box-shadow: 0 2px 8px rgba(47, 93, 86, 0.04);
}

.weakness-item strong {
  display: block;
  color: #1f2926;
  font-size: 0.8rem;
  font-weight: 600;
}

.weakness-item span {
  display: block;
  margin-top: 0.25rem;
  color: #66756f;
  font-size: 0.74rem;
}

.weakness-item p {
  margin: 0.35rem 0 0;
  color: #3f655f;
  font-size: 0.74rem;
}

.plan-card h2,
.empty h2 {
  margin: 0;
  color: #1f2926;
}

.empty p {
  margin: 0.35rem 0 0;
  color: #66756f;
}

@media (max-width: 780px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }

  .progress-head {
    flex-direction: column;
    gap: 0.25rem;
  }
}
</style>
