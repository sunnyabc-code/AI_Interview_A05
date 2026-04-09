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
    radial-gradient(circle at 8% 10%, #fff7ed 0, transparent 24%),
    radial-gradient(circle at 90% 0%, #fef9c3 0, transparent 28%),
    #fffdfa;
}

.back-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
  border-radius: 8px;
  padding: 0.3rem 0.65rem;
  cursor: pointer;
  margin-bottom: 0.5rem;
}

h1 {
  margin: 0;
  color: #0f172a;
}

header p {
  margin: 0.3rem 0 0;
  color: #64748b;
}

.actions {
  margin-top: 0.8rem;
  display: flex;
  gap: 0.5rem;
}

button {
  border: 1px solid #93c5fd;
  background: #fff;
  color: #1d4ed8;
  border-radius: 8px;
  padding: 0.4rem 0.72rem;
  cursor: pointer;
}

.error {
  margin-top: 0.7rem;
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #991b1b;
  border-radius: 8px;
  padding: 0.6rem;
}

.generating-banner {
  margin-top: 0.7rem;
  border: 1px solid #93c5fd;
  background: #eff6ff;
  color: #1e3a8a;
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
  background: #dbeafe;
  overflow: hidden;
}

.progress-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #2563eb 0%, #38bdf8 100%);
}

.progress-tip {
  margin: 0.4rem 0 0;
  font-size: 0.75rem;
  color: #1e40af;
}

.profile-card,
.plan-card,
.empty {
  margin-top: 0.8rem;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #f8fbff;
  padding: 0.8rem;
}

.profile-card {
  margin-top: 0.9rem;
  background:
    radial-gradient(circle at 18% -10%, #fde68a 0, transparent 45%),
    radial-gradient(circle at 100% 0%, #fde68a 0, transparent 30%),
    linear-gradient(180deg, #fffdf6 0%, #fff9eb 100%);
  border-color: #f5deb3;
}

.profile-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
}

.profile-tag {
  border-radius: 999px;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 0.74rem;
  padding: 0.16rem 0.56rem;
}

.profile-goal {
  margin: 0.46rem 0 0;
  color: #7c2d12;
}

.profile-grid {
  margin-top: 0.65rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
}

.profile-metric {
  border: 1px solid #f5d0a9;
  border-radius: 12px;
  background: #fffdf8;
  padding: 0.55rem;
}

.profile-metric strong {
  display: block;
  font-size: 1.22rem;
  color: #0f172a;
}

.profile-metric span {
  font-size: 0.76rem;
  color: #7c6a4a;
}

.ability-panel,
.weakness-panel {
  margin-top: 0.7rem;
  border: 1px dashed #e8c79a;
  border-radius: 12px;
  background: #fffefb;
  padding: 0.62rem;
}

.ability-panel h3,
.weakness-panel h3 {
  margin: 0;
  font-size: 0.95rem;
  color: #92400e;
}

.ability-list {
  margin-top: 0.5rem;
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
  color: #78350f;
  font-size: 0.78rem;
}

.ability-track {
  position: relative;
  height: 10px;
  border-radius: 999px;
  background: #ffedd5;
  overflow: hidden;
}

.ability-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #fb923c 0%, #f97316 70%, #ea580c 100%);
}

.ability-score {
  text-align: right;
  font-size: 0.78rem;
  color: #7c2d12;
}

.weakness-list {
  margin-top: 0.45rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.45rem;
}

.weakness-item {
  border: 1px solid #fed7aa;
  border-radius: 10px;
  background: #fff7ed;
  padding: 0.48rem;
}

.weakness-item strong {
  display: block;
  color: #9a3412;
  font-size: 0.8rem;
}

.weakness-item span {
  display: block;
  margin-top: 0.2rem;
  color: #c2410c;
  font-size: 0.74rem;
}

.weakness-item p {
  margin: 0.2rem 0 0;
  color: #7c2d12;
  font-size: 0.74rem;
}

.plan-card h2,
.empty h2 {
  margin: 0;
  color: #1e293b;
}

.empty p {
  margin: 0.35rem 0 0;
  color: #475569;
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
