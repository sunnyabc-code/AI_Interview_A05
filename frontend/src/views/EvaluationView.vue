<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goToInterviewReview = () => {
    router.push('/evaluation/review')
}

const goToAbilityOverview = () => {
    router.push('/evaluation/ability')
}

const goToPathway = () => {
    router.push('/evaluation/pathway')
}
</script>

<template>
    <div class="evaluation-page">
        <div class="bg-shape bg-shape-left" aria-hidden="true"></div>
        <div class="bg-shape bg-shape-right" aria-hidden="true"></div>

        <header class="page-header">
            <p class="kicker">Evaluation Center</p>
            <h1>评估中心</h1>
            <p class="intro">聚焦关键能力信号，帮助你以更专业的节奏复盘、迭代与提升。</p>
        </header>

        <section class="module-grid" aria-label="评估模块">
            <article class="module-card" @click="goToInterviewReview">
                <div class="card-top">
                    <span class="icon-wrap" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path
                                d="M6 7.2C6 6.54 6.54 6 7.2 6H16.8C17.46 6 18 6.54 18 7.2V16.8C18 17.46 17.46 18 16.8 18H7.2C6.54 18 6 17.46 6 16.8V7.2Z"
                                stroke="currentColor" stroke-width="1.5" />
                            <path d="M8.6 10H15.4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                            <path d="M8.6 13H13.4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                        </svg>
                    </span>
                    <span class="tag">Review</span>
                </div>
                <h2>面试复盘</h2>
                <p>查看历次面试表现，按轮次对比问题回答、亮点与改进建议。</p>
                <button type="button" class="enter-btn">进入复盘</button>
            </article>

            <article class="module-card" @click="goToAbilityOverview">
                <div class="card-top">
                    <span class="icon-wrap" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M6.5 17.5V12.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                            <path d="M12 17.5V9.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                            <path d="M17.5 17.5V6.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                            <path d="M5.2 17.5H18.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                        </svg>
                    </span>
                    <span class="tag">Overview</span>
                </div>
                <h2>能力总览区</h2>
                <p>整合沟通表达、技术深度、结构化思维等核心能力维度，提供阶段性成长画像。</p>
                <button type="button" class="enter-btn">进入总览</button>
            </article>

            <article class="module-card" @click="goToPathway">
                <div class="card-top">
                    <span class="icon-wrap" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M7 17L17 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                            <path d="M9 7H17V15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"
                                stroke-linejoin="round" />
                            <path d="M6 18H18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                        </svg>
                    </span>
                    <span class="tag">Pathway</span>
                </div>
                <h2>个性化提升路径</h2>
                <p>根据你的面试表现自动生成可执行任务计划，支持每日打卡与效果追踪。</p>
                <button type="button" class="enter-btn">进入路径</button>
            </article>
        </section>
    </div>
</template>

<style scoped>
.evaluation-page {
    --bg: #f3f5f4;
    --surface: rgba(255, 255, 255, 0.92);
    --line: #dde5e1;
    --line-strong: #c9d4cf;
    --text: #1f2926;
    --muted: #66756f;
    --accent: #2f5d56;
    --accent-press: #264a45;

    min-height: 100%;
    position: relative;
    overflow: hidden;
    padding: 34px clamp(18px, 3.2vw, 42px) 40px;
    color: var(--text);
    background: transparent;
}

.bg-shape {
    position: absolute;
    border-radius: 999px;
    pointer-events: none;
    filter: blur(1px);
    z-index: 0;
}

.bg-shape-left {
    width: 320px;
    height: 320px;
    left: -120px;
    top: 48%;
    background: radial-gradient(circle, rgba(76, 105, 93, 0.14) 0%, rgba(76, 105, 93, 0) 70%);
}

.bg-shape-right {
    width: 260px;
    height: 260px;
    right: -90px;
    bottom: -30px;
    background: radial-gradient(circle, rgba(102, 120, 110, 0.13) 0%, rgba(102, 120, 110, 0) 70%);
}

.page-header {
    position: relative;
    z-index: 1;
    margin-bottom: 24px;
    max-width: 760px;
}

.kicker {
    margin: 0;
    color: var(--muted);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    font-size: 11px;
    font-weight: 600;
}

.page-header h1 {
    margin: 8px 0 0;
    font-size: clamp(30px, 5vw, 44px);
    line-height: 1.15;
    font-weight: 600;
    letter-spacing: -0.02em;
}

.intro {
    margin: 11px 0 0;
    color: var(--muted);
    line-height: 1.7;
    font-size: clamp(14px, 2vw, 16px);
    max-width: 620px;
}

.module-grid {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: clamp(12px, 1.7vw, 18px);
}

.module-card {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.9) 0%, rgba(251, 252, 250, 0.9) 100%);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: clamp(16px, 2vw, 22px);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    min-height: 248px;
    transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
    box-shadow: 0 10px 26px rgba(34, 44, 39, 0.06);
}

.module-card:hover {
    transform: translateY(-3px);
    border-color: var(--line-strong);
    box-shadow: 0 16px 30px rgba(34, 44, 39, 0.09);
}

.card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}

.icon-wrap {
    width: 38px;
    height: 38px;
    border-radius: 11px;
    border: 1px solid var(--line);
    color: #365146;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.84);
}

.icon-wrap svg {
    width: 20px;
    height: 20px;
}

.tag {
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #6f7c73;
    font-weight: 600;
}

.module-card h2 {
    margin: 0;
    font-size: clamp(18px, 2.1vw, 22px);
    line-height: 1.32;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.module-card p {
    margin: 10px 0 20px;
    color: var(--muted);
    line-height: 1.7;
    font-size: 14px;
    flex: 1;
}

.enter-btn {
    align-self: flex-start;
    border: 1px solid transparent;
    border-radius: 10px;
    background: var(--accent);
    color: #fff;
    padding: 9px 14px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.01em;
    cursor: pointer;
    transition: background-color 0.22s ease, transform 0.22s ease;
}

.module-card:hover .enter-btn {
    transform: translateY(-1px);
}

.enter-btn:hover {
    background: var(--accent-press);
}

.enter-btn:focus-visible,
.module-card:focus-visible {
    outline: 2px solid rgba(61, 91, 79, 0.45);
    outline-offset: 2px;
}

@media (max-width: 1120px) {
    .module-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 768px) {
    .evaluation-page {
        padding: 24px 14px 28px;
    }

    .page-header {
        margin-bottom: 16px;
    }

    .module-grid {
        grid-template-columns: 1fr;
        gap: 12px;
    }

    .module-card {
        min-height: 0;
        border-radius: 14px;
        padding: 14px;
    }

    .module-card p {
        margin: 8px 0 14px;
    }
}
</style>