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
        <!-- <header class="page-header">
            <h1>评估中心</h1>
            <p>请选择需要进入的评估模块。</p>
        </header> -->

        <section class="module-grid">
            <article class="module-card" @click="goToInterviewReview">
                <h2>面试复盘</h2>
                <p>查看历次面试表现，按轮次对比问题回答、亮点与改进建议。</p>
                <button type="button" class="enter-btn">进入复盘</button>
            </article>

            <article class="module-card" @click="goToAbilityOverview">
                <h2>能力总览区</h2>
                <p>整合沟通表达、技术深度、结构化思维等核心能力维度，提供阶段性成长画像。</p>
                <button type="button" class="enter-btn">进入总览</button>
            </article>

            <article class="module-card" @click="goToPathway">
                <h2>个性化提升路径</h2>
                <p>根据你的面试表现自动生成可执行任务计划，支持每日打卡与效果追踪。</p>
                <button type="button" class="enter-btn">进入路径</button>
            </article>
        </section>
    </div>
</template>

<style scoped>
.evaluation-page {
    padding: 2rem;
}

.page-header h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: #1f2937;
}

.page-header p {
    margin: 0;
    color: #6b7280;
}

.module-grid {
    margin-top: 1.5rem;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 340px));
    gap: 1rem;
}

.module-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.25rem;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.module-card:hover {
    transform: translateY(-2px);
    border-color: #60a5fa;
    box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
}

.module-tag {
    display: inline-block;
    font-size: 0.75rem;
    color: #1d4ed8;
    background: #dbeafe;
    border-radius: 999px;
    padding: 0.25rem 0.6rem;
    margin-bottom: 0.8rem;
}

.module-card h2 {
    margin: 0;
    color: #111827;
    font-size: 1.25rem;
}

.module-card p {
    margin: 0.85rem 0 1.2rem;
    color: #4b5563;
    line-height: 1.6;
}

.enter-btn {
    border: none;
    border-radius: 8px;
    background: #667eea;
    color: #fff;
    padding: 0.55rem 1rem;
    font-size: 0.95rem;
    cursor: pointer;
}

.enter-btn:disabled {
    cursor: not-allowed;
    background: #94a3b8;
}

@media (max-width: 768px) {
    .evaluation-page {
        padding: 1rem;
    }
}
</style>