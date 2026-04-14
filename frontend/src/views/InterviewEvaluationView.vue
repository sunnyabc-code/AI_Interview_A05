<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { API_BASE_URL } from '@/utils/api'

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

/** 圆环按百分制 0–100 显示，与接口均分一致（满分 100 = 整圆） */
function scoreRingPercent(v: number | null | undefined): number | null {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return null
  const n = Number(v)
  return Math.min(100, Math.max(0, n))
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
          <svg class="head-hero__sparkle" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 48" fill="none" aria-hidden="true">
            <circle cx="62" cy="14" r="3" fill="var(--accent)" fill-opacity="0.14" />
            <circle cx="48" cy="32" r="2" fill="var(--accent)" fill-opacity="0.2" />
            <circle cx="70" cy="36" r="1.5" fill="var(--accent)" fill-opacity="0.25" />
          </svg>
          <p class="kicker">Evaluation report</p>
          <h1 class="title-gradient">面试评估报告</h1>
          <p v-if="summary" class="sub">
            {{ summary.position_name }} · 面试 #{{ summary.interview_id }}
          </p>
        </div>
      </header>

      <div v-if="errorMsg" class="card card--err">{{ errorMsg }}</div>
      <div v-else-if="summary" class="content">
        <section class="card card--lift">
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
          class="card card--lift"
        >
          <h2>{{ aspectLabels[key] }} — 各追问链均分</h2>
          <p v-if="!summary.aspects?.[key]?.chains?.length" class="muted">暂无数据（可能尚未完成打分）</p>
          <div
            v-for="chain in summary.aspects?.[key]?.chains || []"
            :key="`${key}-${chain.chain_index}`"
            class="chain-block anim-chain"
          >
            <h3>追问链 {{ chain.chain_index }}（共 {{ chain.round_count }} 轮）</h3>
            <table class="dim-table">
              <tbody>
                <tr v-for="(dim, dk) in chain.dimensions || {}" :key="dk" class="anim-row">
                  <td>
                    <span class="row-dot" aria-hidden="true" />
                    {{ dim.label }}
                  </td>
                  <td class="num">
                    <span v-if="scoreRingPercent(dim.score) !== null" class="score-wrap">
                      <span
                        class="score-ring"
                        :style="{ '--score': String(scoreRingPercent(dim.score)) }"
                        aria-hidden="true"
                      />
                      <span class="num-text">{{ scoreText(dim.score) }}</span>
                    </span>
                    <span v-else class="num-text">{{ scoreText(dim.score) }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="card card--lift">
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
              <tr v-for="kp in summary.technical_knowledge_points" :key="kp.chain_index" class="anim-row">
                <td>{{ kp.chain_topic_label || '—' }}</td>
                <td>{{ kp.job_knowledge_serial ?? '—' }}</td>
                <td class="num">
                  <span v-if="scoreRingPercent(kp.technical_accuracy) !== null" class="score-wrap">
                    <span
                      class="score-ring"
                      :style="{ '--score': String(scoreRingPercent(kp.technical_accuracy)) }"
                      aria-hidden="true"
                    />
                    <span class="num-text">{{ scoreText(kp.technical_accuracy) }}</span>
                  </span>
                  <span v-else class="num-text">{{ scoreText(kp.technical_accuracy) }}</span>
                </td>
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
  --accent-2: #3f655f;
  --danger: #9d4a43;
  --ease-smooth: cubic-bezier(0.33, 1, 0.68, 1);
  --ease-pop: cubic-bezier(0.72, -0.2, 0.7, 1.4);
  --ease-card: cubic-bezier(0.6, 0.2, 0.34, 1.14);

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
  position: relative;
  overflow: hidden;
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

.head-hero__sparkle {
  position: absolute;
  right: 0.5rem;
  bottom: 0.35rem;
  width: 72px;
  height: 44px;
  pointer-events: none;
  opacity: 0.9;
  animation: eval-sparkle 4s var(--ease-smooth) infinite alternate;
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
  transition:
    border-color 0.32s var(--ease-smooth),
    background 0.32s var(--ease-smooth),
    box-shadow 0.32s var(--ease-smooth),
    transform 0.26s var(--ease-smooth);
}

.back:hover {
  border-color: rgba(47, 93, 86, 0.35);
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(47, 93, 86, 0.1);
  transform: translateY(-1px);
}

.back:active {
  transform: translateY(0);
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
  position: relative;
  overflow: hidden;
  background: linear-gradient(
    180deg,
    rgba(250, 252, 251, 0.99) 0%,
    rgba(255, 255, 255, 0.98) 18%,
    rgba(252, 253, 252, 0.97) 100%
  );
  border-radius: 16px;
  padding: 1.15rem 1.2rem 1.2rem;
  margin-bottom: 1.25rem;
  border: 1px solid var(--line);
  border-top: 3px solid rgba(47, 93, 86, 0.1);
  box-shadow:
    0 4px 24px rgba(47, 93, 86, 0.06),
    0 8px 24px rgba(31, 41, 38, 0.04),
    inset 0 1.5px 0 0 #fff;
  transition:
    box-shadow 0.28s var(--ease-card),
    transform 0.23s var(--ease-smooth),
    border-color 0.28s var(--ease-smooth);
  animation: eval-fade-up 0.7s var(--ease-smooth) both;
}

.card--lift:hover {
  box-shadow:
    0 10px 32px rgba(47, 93, 86, 0.13),
    0 14px 36px rgba(31, 41, 38, 0.06),
    inset 0 2px 0 #fff;
  transform: translateY(-2px) scale(1.012);
}

.card::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 52px;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(47, 93, 86, 0.045) 0%, transparent 100%);
  border-radius: 16px 16px 0 0;
}

.card--err {
  color: var(--danger);
  border-color: #e8d5d0;
  background: #fff8f7;
  border-top-color: rgba(157, 74, 67, 0.2);
  animation: none;
}

.card--err:hover {
  transform: none;
  box-shadow:
    0 4px 20px rgba(157, 74, 67, 0.08),
    inset 0 1.5px 0 0 #fff;
}

.content h2 {
  position: relative;
  z-index: 1;
  margin: 0 0 0.85rem;
  padding: 0 0 0.55rem 0.88em;
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #1a2824;
}

.content h2::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.35rem;
  width: 6px;
  height: 18px;
  border-radius: 6px;
  background: linear-gradient(170deg, var(--accent) 0%, var(--muted) 82%);
  box-shadow: 0 2px 8px rgba(47, 93, 86, 0.15);
}

.content h2::after {
  content: '';
  position: absolute;
  left: 0.88em;
  right: 0;
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, rgba(47, 93, 86, 0.12), var(--line-soft) 55%, transparent);
  opacity: 0.9;
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
  transition:
    background 0.28s var(--ease-smooth),
    border-color 0.28s var(--ease-smooth),
    color 0.24s var(--ease-smooth),
    box-shadow 0.28s var(--ease-smooth),
    transform 0.22s var(--ease-smooth);
}

.tags li.on {
  background: linear-gradient(90deg, rgba(47, 93, 86, 0.12) 0%, rgba(47, 93, 86, 0.02) 100%);
  border-color: rgba(47, 93, 86, 0.28);
  color: var(--accent);
  box-shadow: 0 2px 8px rgba(47, 93, 86, 0.07) inset;
  font-weight: 600;
}

.tags li.on:hover {
  transform: translateY(-1px);
  box-shadow:
    0 2px 8px rgba(47, 93, 86, 0.09) inset,
    0 4px 12px rgba(47, 93, 86, 0.08);
}

.muted {
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.45;
}

.chain-block {
  position: relative;
  margin-bottom: 1rem;
  padding: 0.65rem 0 0.95rem;
  padding-left: 0.5rem;
  border-bottom: 1px dashed rgba(47, 93, 86, 0.12);
}

.chain-block::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.55rem;
  bottom: 0.85rem;
  width: 3px;
  border-radius: 3px;
  background: linear-gradient(180deg, rgba(47, 93, 86, 0.2), rgba(47, 93, 86, 0.04));
}

.chain-block:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.chain-block:last-child::before {
  bottom: 0;
}

.chain-block h3 {
  margin: 0 0 0.55rem;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.chain-block h3::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  opacity: 0.35;
  flex-shrink: 0;
}

.anim-chain {
  animation: eval-fade-up 0.65s var(--ease-smooth) both;
}

.dim-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.dim-table td {
  padding: 0.5rem 0.4rem;
  border-bottom: 1px solid var(--line-soft);
  transition: background 0.22s var(--ease-smooth);
}

.dim-table tbody tr:hover td {
  background: rgba(47, 93, 86, 0.03);
}

.dim-table td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--text);
}

.row-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  margin-right: 0.45rem;
  vertical-align: middle;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  opacity: 0.45;
  box-shadow: 0 0 0 2px rgba(47, 93, 86, 0.06);
}

.score-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.45rem;
}

.score-ring {
  --score: 0;
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: conic-gradient(var(--accent) calc(var(--score) * 1%), rgba(47, 93, 86, 0.12) 0);
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.92),
    0 1px 3px rgba(47, 93, 86, 0.08);
}

.num-text {
  font-weight: 600;
  color: var(--text);
}

.dim-table td.num .num-text,
.kp-table .num .num-text {
  animation: eval-pop-in 0.34s 0.06s var(--ease-pop) backwards;
}

.kp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
  border-radius: 12px;
  overflow: hidden;
}

.kp-table thead {
  background: linear-gradient(180deg, rgba(47, 93, 86, 0.06) 0%, rgba(47, 93, 86, 0.02) 100%);
}

.kp-table th,
.kp-table td {
  padding: 0.55rem 0.45rem;
  text-align: left;
  vertical-align: middle;
  border-bottom: 1px solid var(--line-soft);
  transition: background 0.22s var(--ease-smooth);
}

.kp-table th {
  color: var(--muted);
  font-weight: 600;
  font-size: 0.8rem;
}

.kp-table thead th:nth-child(3) {
  text-align: center;
}

.kp-table tbody tr:hover td {
  background: rgba(47, 93, 86, 0.035);
}

.kp-table .num {
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.kp-table td.num .score-wrap {
  justify-content: center;
}

.anim-row {
  animation: eval-fade-up 0.55s var(--ease-smooth) both;
}

.content .card:nth-child(1) {
  animation-delay: 0.04s;
}

.content .card:nth-child(2) {
  animation-delay: 0.08s;
}

.content .card:nth-child(3) {
  animation-delay: 0.12s;
}

.content .card:nth-child(4) {
  animation-delay: 0.16s;
}

.content .card:nth-child(5) {
  animation-delay: 0.2s;
}

.dim-table tbody tr.anim-row:nth-child(1) {
  animation-delay: 0.05s;
}

.dim-table tbody tr.anim-row:nth-child(2) {
  animation-delay: 0.09s;
}

.dim-table tbody tr.anim-row:nth-child(3) {
  animation-delay: 0.13s;
}

.dim-table tbody tr.anim-row:nth-child(4) {
  animation-delay: 0.17s;
}

.dim-table tbody tr.anim-row:nth-child(5) {
  animation-delay: 0.21s;
}

.dim-table tbody tr.anim-row:nth-child(6) {
  animation-delay: 0.25s;
}

.dim-table tbody tr.anim-row:nth-child(7) {
  animation-delay: 0.29s;
}

.dim-table tbody tr.anim-row:nth-child(8) {
  animation-delay: 0.33s;
}

.kp-table tbody tr.anim-row:nth-child(1) {
  animation-delay: 0.06s;
}

.kp-table tbody tr.anim-row:nth-child(2) {
  animation-delay: 0.1s;
}

.kp-table tbody tr.anim-row:nth-child(3) {
  animation-delay: 0.14s;
}

.kp-table tbody tr.anim-row:nth-child(4) {
  animation-delay: 0.18s;
}

.kp-table tbody tr.anim-row:nth-child(5) {
  animation-delay: 0.22s;
}

@keyframes eval-fade-up {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes eval-pop-in {
  0% {
    transform: scale(0.8);
  }
  70% {
    transform: scale(1.13);
  }
  100% {
    transform: scale(1);
  }
}

@keyframes eval-sparkle {
  from {
    opacity: 0.65;
    transform: translateY(2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 640px) {
  .page-inner {
    padding: 1.15rem 0.9rem 2.75rem;
  }

  .head-hero {
    padding: 1.15rem 1.05rem 1.2rem;
    border-radius: 16px;
  }

  .title-gradient {
    font-size: clamp(1.45rem, 5.5vw, 1.85rem);
  }

  .card {
    padding: 1.25rem 1.1rem 1.3rem;
    border-radius: 18px;
    margin-bottom: 1.1rem;
  }

  .content h2 {
    font-size: 1.08rem;
    padding-left: 0.85em;
  }

  .tags li {
    font-size: 0.9rem;
    padding: 0.45rem 0.82rem;
  }

  .dim-table,
  .kp-table {
    font-size: 0.92rem;
  }

  .kp-table th {
    font-size: 0.82rem;
  }

  .chain-block h3 {
    font-size: 0.95rem;
  }
}
</style>
