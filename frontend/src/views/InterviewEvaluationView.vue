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
    for (let i = 0; i < 48; i++) {
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
    <div v-if="loading" class="loading-screen">
      <div class="loading-spinner" />
      <p class="loading-title">正在加载评估结果</p>
      <p class="loading-hint">若后台仍在打分，将自动重试…</p>
    </div>

    <template v-else>
      <header class="head">
        <button type="button" class="back" @click="router.push('/home?menu=interview')">← 返回</button>
        <h1>面试评估</h1>
        <p v-if="summary" class="sub">
          {{ summary.position_name }} · ID {{ summary.interview_id }}
        </p>
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
    </template>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  max-width: 880px;
  margin: 0 auto;
  padding: 24px 16px 48px;
  color: #1a1a1a;
}

.loading-screen {
  min-height: 60vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.loading-spinner {
  width: 52px;
  height: 52px;
  border: 4px solid #e5e7eb;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: eval-spin 0.85s linear infinite;
}

.loading-title {
  margin: 1.25rem 0 0.35rem;
  font-size: 1.1rem;
  font-weight: 600;
}

.loading-hint {
  margin: 0;
  font-size: 0.88rem;
  color: #6b7280;
}

@keyframes eval-spin {
  to {
    transform: rotate(360deg);
  }
}

.head h1 {
  margin: 8px 0 4px;
  font-size: 1.35rem;
}
.sub {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}
.back {
  border: none;
  background: none;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
  font-size: 0.95rem;
}
.card {
  background: #fff;
  border-radius: 10px;
  padding: 16px 18px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.card.err {
  color: #b91c1c;
}
.content h2 {
  margin: 0 0 12px;
  font-size: 1.05rem;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  list-style: none;
  padding: 0;
  margin: 0;
}
.tags li {
  padding: 6px 12px;
  border-radius: 999px;
  background: #f3f4f6;
  font-size: 0.9rem;
}
.tags li.on {
  background: #dbeafe;
  color: #1d4ed8;
}
.muted {
  color: #6b7280;
  font-size: 0.9rem;
}
.chain-block {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
}
.chain-block:last-child {
  border-bottom: none;
}
.chain-block h3 {
  margin: 0 0 8px;
  font-size: 0.95rem;
  color: #374151;
}
.dim-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}
.dim-table td {
  padding: 6px 8px;
  border-bottom: 1px solid #f3f4f6;
}
.dim-table td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.kp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.kp-table th,
.kp-table td {
  padding: 8px;
  text-align: left;
  border-bottom: 1px solid #eee;
}
.kp-table th {
  color: #6b7280;
  font-weight: 600;
}
.kp-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
