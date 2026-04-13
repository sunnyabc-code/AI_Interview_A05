<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const API_BASE_URL = 'http://localhost:8000'
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const errorMsg = ref('')
const summary = ref<Record<string, any> | null>(null)

const aspectLabels: Record<string, string> = {
  technical: '技术知识',
  project: '项目经历',
  scenario: '场景题',
}

function getAuthHeaders() {
  const token = localStorage.getItem('access_token')
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function fetchSummary(): Promise<{
  ok: boolean
  data?: any
  retry?: boolean
  message?: string
}> {
  const id = route.params.id
  const res = await fetch(
    `${API_BASE_URL}/api/v1/interviews/${id}/evaluation-summary/`,
    { headers: getAuthHeaders() },
  )
  const json = await res.json()
  if (json.code === 200) {
    return { ok: true, data: json.data }
  }
  const msg = (json.message || '') as string
  if (json.code === 400 && (msg.includes('未完成') || msg.includes('暂无'))) {
    return { ok: false, retry: true }
  }
  return { ok: false, retry: false, message: msg || '加载失败' }
}

onMounted(async () => {
  loading.value = true
  errorMsg.value = ''
  try {
    for (let i = 0; i < 120; i++) {
      const result = await fetchSummary()
      if (result.ok && result.data) {
        summary.value = result.data
        break
      }
      if (result.retry) {
        await sleep(1500)
        continue
      }
      errorMsg.value = result.message || '加载失败'
      break
    }
    if (!summary.value && !errorMsg.value) {
      errorMsg.value = '评估数据暂不可用，请稍后在记录中查看'
    }
  } catch {
    errorMsg.value = '网络错误'
  } finally {
    loading.value = false
  }
})

function scoreText(v: number | null | undefined) {
  if (v === null || v === undefined) return '—'
  return String(v)
}
</script>

<template>
  <div class="page">
    <div class="bg-shape bg-shape-left" aria-hidden="true" />
    <div class="bg-shape bg-shape-right" aria-hidden="true" />

    <div v-if="loading" class="page-inner loading-screen">
      <div class="loading-spinner" aria-hidden="true" />
      <p class="loading-title title-gradient-static">正在加载评估报告</p>
      <p class="loading-hint">报告保存在服务端；若后台仍在打分，将自动重试。</p>
    </div>

    <div v-else class="page-inner">
      <header class="head">
        <button type="button" class="back" @click="router.push('/home?menu=interview')">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M15 6L9 12L15 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          返回面试
        </button>
        <div class="head-hero">
          <p class="kicker">Evaluation report</p>
          <h1 class="title-gradient">面试评估报告</h1>
          <p v-if="summary" class="sub">
            {{ summary.position_name }} · 面试 #{{ summary.interview_id }}
          </p>
        </div>
      </header>

      <div v-if="errorMsg" class="card err">{{ errorMsg }}</div>
      <div v-else-if="summary" class="content">
        <section class="card">
          <h2>本次考察范围</h2>
          <ul class="tags">
            <li v-if="summary.enabled_aspects?.technical" class="on">技术知识题</li>
            <li v-if="summary.enabled_aspects?.project" class="on">项目经历题</li>
            <li v-if="summary.enabled_aspects?.scenario" class="on">场景题</li>
          </ul>
        </section>

        <section
          v-for="key in ['technical', 'project', 'scenario'] as const"
          :key="key"
          v-show="summary.enabled_aspects?.[key]"
          class="card"
        >
          <h2>{{ aspectLabels[key] }} — 各追问链均分</h2>
          <p v-if="!summary.aspects?.[key]?.chains?.length" class="muted">暂无数据（可能尚未完成打分）</p>
          <div
            v-for="chain in summary.aspects?.[key]?.chains || []"
            :key="`${key}-${chain.chain_index}`"
            class="chain-block"
          >
            <h3>追问链 {{ chain.chain_index }}（共 {{ chain.round_count }} 轮）</h3>
            <table class="dim-table">
              <tbody>
                <tr v-for="(dim, dk) in chain.dimensions || {}" :key="dk">
                  <td>{{ dim.label }}</td>
                  <td class="num">{{ scoreText(dim.score) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="card">
          <h2>技术知识点 · 技术准确性（按追问链）</h2>
          <p v-if="!summary.technical_knowledge_points?.length" class="muted">无技术题或未打分</p>
          <table v-else class="kp-table">
            <thead>
              <tr>
                <th>知识点</th>
                <th>序号</th>
                <th>技术准确性（均分）</th>
                <th>轮次</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="kp in summary.technical_knowledge_points" :key="kp.chain_index">
                <td>{{ kp.chain_topic_label || '—' }}</td>
                <td>{{ kp.job_knowledge_serial ?? '—' }}</td>
                <td class="num">{{ scoreText(kp.technical_accuracy) }}</td>
                <td>{{ kp.round_count }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  --bg: #f3f5f4;
  --surface: #ffffff;
  --line: #dde5e1;
  --line-soft: #e8eeeb;
  --text: #1f2926;
  --muted: #66756f;
  --accent: #2f5d56;
  --danger: #9d4a43;

  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
  color: var(--text);
  background: linear-gradient(180deg, #e8f2ec 0%, #f3f8f5 100%);
}

.bg-shape {
  position: fixed;
  border-radius: 999px;
  pointer-events: none;
  filter: blur(1px);
  z-index: 0;
}

.bg-shape-left {
  width: 280px;
  height: 280px;
  left: -100px;
  top: 42%;
  background: radial-gradient(circle, rgba(76, 105, 93, 0.12) 0%, rgba(76, 105, 93, 0) 70%);
}

.bg-shape-right {
  width: 240px;
  height: 240px;
  right: -80px;
  bottom: 8%;
  background: radial-gradient(circle, rgba(102, 120, 110, 0.11) 0%, rgba(102, 120, 110, 0) 70%);
}

.page-inner {
  position: relative;
  z-index: 1;
  max-width: 880px;
  margin: 0 auto;
  padding: 1.25rem 1rem 3rem;
}

.loading-screen {
  min-height: 60vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  text-align: center;
}

.title-gradient-static {
  background: linear-gradient(120deg, #1a302c 0%, #2f5d56 45%, #3d8a7a 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.loading-spinner {
  width: 44px;
  height: 44px;
  border: 3px solid var(--line-soft);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: eval-spin 0.85s linear infinite;
}

.loading-title {
  margin: 1.1rem 0 0.4rem;
  font-size: 1.05rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.loading-hint {
  margin: 0;
  max-width: 22rem;
  font-size: 0.88rem;
  color: var(--muted);
  line-height: 1.45;
}

@keyframes eval-spin {
  to {
    transform: rotate(360deg);
  }
}

.head {
  margin-bottom: 1.35rem;
}

.head-hero {
  margin-top: 0.35rem;
  padding: 1.15rem 1.2rem 1.25rem;
  border-radius: 18px;
  background: linear-gradient(
    155deg,
    rgba(255, 255, 255, 0.97) 0%,
    rgba(250, 252, 251, 0.98) 38%,
    rgba(234, 244, 239, 0.88) 100%
  );
  border: 1px solid var(--line);
  box-shadow:
    0 16px 40px rgba(31, 41, 38, 0.07),
    inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.kicker {
  margin: 0 0 0.5rem;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--muted);
  font-weight: 600;
}

.title-gradient {
  margin: 0 0 0.45rem;
  font-size: clamp(1.55rem, 4.2vw, 2.05rem);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.18;
  background: linear-gradient(118deg, #152a27 0%, #2f5d56 32%, #3d8f7e 58%, #2a524c 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.sub {
  margin: 0;
  color: var(--muted);
  font-size: 0.92rem;
  line-height: 1.45;
}

.back {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid var(--line);
  background: linear-gradient(180deg, #ffffff 0%, #f6faf8 100%);
  color: var(--text);
  cursor: pointer;
  padding: 0.45rem 0.75rem;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 500;
  margin-bottom: 0.65rem;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.back:hover {
  border-color: rgba(47, 93, 86, 0.35);
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(47, 93, 86, 0.08);
}

.back .icon {
  width: 18px;
  height: 18px;
  display: inline-flex;
}

.back .icon svg {
  width: 100%;
  height: 100%;
}

.card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(252, 253, 252, 0.96) 100%);
  border-radius: 16px;
  padding: 1.15rem 1.2rem;
  margin-bottom: 0.9rem;
  border: 1px solid var(--line);
  box-shadow:
    0 12px 32px rgba(31, 41, 38, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.card.err {
  color: var(--danger);
  border-color: #e8d5d0;
  background: #fff8f7;
}

.content h2 {
  margin: 0 0 0.75rem;
  font-size: 1.02rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: #24332e;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--line-soft);
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  list-style: none;
  padding: 0;
  margin: 0;
}

.tags li {
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  background: #f4f7f5;
  border: 1px solid var(--line-soft);
  font-size: 0.86rem;
  color: var(--muted);
}

.tags li.on {
  background: rgba(47, 93, 86, 0.1);
  border-color: rgba(47, 93, 86, 0.25);
  color: var(--accent);
}

.muted {
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.45;
}

.chain-block {
  margin-bottom: 1rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid var(--line-soft);
}

.chain-block:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.chain-block h3 {
  margin: 0 0 0.5rem;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text);
}

.dim-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.dim-table td {
  padding: 0.45rem 0.35rem;
  border-bottom: 1px solid var(--line-soft);
}

.dim-table td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--text);
}

.kp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}

.kp-table th,
.kp-table td {
  padding: 0.55rem 0.4rem;
  text-align: left;
  border-bottom: 1px solid var(--line-soft);
}

.kp-table th {
  color: var(--muted);
  font-weight: 600;
  font-size: 0.8rem;
}

.kp-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 640px) {
  .page-inner {
    padding: 1rem 0.75rem 2.5rem;
  }

  .head-hero {
    padding: 1rem 1rem 1.1rem;
    border-radius: 14px;
  }

  .card {
    padding: 1rem;
  }
}
</style>
