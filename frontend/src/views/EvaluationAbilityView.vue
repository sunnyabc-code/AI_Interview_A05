<script setup lang="ts">
import * as d3 from 'd3'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

interface AbilityNode {
    name: string
    score: number
    children?: AbilityNode[]
}

type NodePoint = d3.HierarchyPointNode<AbilityNode>
type LinkPoint = d3.HierarchyPointLink<AbilityNode>
type PositionedNode = d3.HierarchyNode<AbilityNode> & { x: number; y: number }
type PositionedLink = d3.HierarchyLink<AbilityNode> & {
    source: PositionedNode
    target: PositionedNode
}

const router = useRouter()
const chartHost = ref<HTMLDivElement | null>(null)
let cleanupResize: (() => void) | null = null

const abilityTreeData: AbilityNode = {
    name: '面试能力根',
    score: 86,
    children: [
        {
            name: '技术深度',
            score: 84,
            children: [
                { name: '数据库', score: 82 },
                { name: '系统设计', score: 79 },
                { name: '工程实践', score: 88 }
            ]
        },
        {
            name: '表达沟通',
            score: 89,
            children: [
                { name: '结构化表达', score: 90 },
                { name: '追问应对', score: 86 },
                { name: '业务理解', score: 87 }
            ]
        },
        {
            name: '问题求解',
            score: 83,
            children: [
                { name: '边界意识', score: 81 },
                { name: '抽象建模', score: 85 },
                { name: '优化策略', score: 82 }
            ]
        },
        {
            name: '成长执行',
            score: 91,
            children: [
                { name: '复盘质量', score: 92 },
                { name: '行动闭环', score: 90 },
                { name: '反馈吸收', score: 91 }
            ]
        }
    ]
}

const goBack = () => {
    if (window.history.length > 1) {
        router.back()
        return
    }
    router.push('/home?menu=evaluation')
}

const radialLink = d3
    .linkRadial<LinkPoint, NodePoint>()
    .angle((d: NodePoint) => d.x)
    .radius((d: NodePoint) => d.y)

const renderTree = () => {
    if (!chartHost.value) {
        return
    }

    const host = chartHost.value
    host.innerHTML = ''

    const width = Math.max(760, host.clientWidth)
    const height = 700
    const radius = Math.min(width, height) * 0.39

    const root = d3.hierarchy(abilityTreeData)
    const tree = d3.tree<AbilityNode>().size([2 * Math.PI, radius])
    tree(root)

    const svg = d3
        .select(host)
        .append('svg')
        .attr('viewBox', `${-width / 2} ${-height / 2} ${width} ${height}`)
        .attr('class', 'ability-tree-svg')

    const glow = svg
        .append('defs')
        .append('filter')
        .attr('id', 'node-glow')
        .attr('x', '-50%')
        .attr('y', '-50%')
        .attr('width', '200%')
        .attr('height', '200%')

    glow.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur')
    glow.append('feMerge')
        .selectAll('feMergeNode')
        .data(['blur', 'SourceGraphic'])
        .join('feMergeNode')
        .attr('in', (d: string) => d)

    const linkGroup = svg.append('g').attr('class', 'link-group')
    const nodeGroup = svg.append('g').attr('class', 'node-group')

    linkGroup
        .selectAll('path')
        .data(root.links())
        .join('path')
        .attr('fill', 'none')
        .attr('stroke', '#2f855a')
        .attr('stroke-opacity', 0.55)
        .attr('stroke-width', (d: d3.HierarchyLink<AbilityNode>) => {
            const link = d as PositionedLink
            return Math.max(1.6, 4 - link.target.depth)
        })
        .attr('d', (d: d3.HierarchyLink<AbilityNode>) => radialLink(d as LinkPoint) ?? '')
        .each(function (this: d3.BaseType) {
            if (!(this instanceof SVGPathElement)) {
                return
            }
            const length = this.getTotalLength()
            d3.select(this)
                .attr('stroke-dasharray', `${length} ${length}`)
                .attr('stroke-dashoffset', length)
                .transition()
                .duration(900)
                .ease(d3.easeCubicOut)
                .delay((_d, i: number) => i * 90)
                .attr('stroke-dashoffset', 0)
        })

    const nodeEnter = nodeGroup
        .selectAll('g')
        .data(root.descendants())
        .join('g')
        .attr('transform', (d: d3.HierarchyNode<AbilityNode>) => {
            const node = d as PositionedNode
            const angle = (node.x * 180) / Math.PI - 90
            return `rotate(${angle}) translate(${node.y},0)`
        })
        .attr('opacity', 0)

    nodeEnter
        .append('circle')
        .attr('r', 0)
        .attr('fill', (d: d3.HierarchyNode<AbilityNode>) => {
            if (d.depth === 0) return '#166534'
            if (d.depth === 1) return '#16a34a'
            return '#4ade80'
        })
        .attr('stroke', '#f0fdf4')
        .attr('stroke-width', 2)
        .style('filter', 'url(#node-glow)')
        .transition()
        .duration(850)
        .delay((_d, i: number) => i * 80)
        .ease(d3.easeBackOut.overshoot(1.1))
        .attr('r', (d: d3.HierarchyNode<AbilityNode>) => {
            if (d.depth === 0) return 18
            if (d.depth === 1) return 12
            return 8
        })

    nodeEnter
        .append('text')
        .attr('dy', '0.32em')
        .attr('x', (d: d3.HierarchyNode<AbilityNode>) => {
            const node = d as PositionedNode
            return node.x < Math.PI === !node.children ? 14 : -14
        })
        .attr('text-anchor', (d: d3.HierarchyNode<AbilityNode>) => {
            const node = d as PositionedNode
            return node.x < Math.PI === !node.children ? 'start' : 'end'
        })
        .attr('transform', (d: d3.HierarchyNode<AbilityNode>) => {
            const node = d as PositionedNode
            return node.x >= Math.PI ? 'rotate(180)' : null
        })
        .text((d: d3.HierarchyNode<AbilityNode>) => `${d.data.name} ${d.data.score}`)
        .attr('font-size', (d: d3.HierarchyNode<AbilityNode>) => (d.depth === 0 ? 16 : d.depth === 1 ? 13 : 11))
        .attr('font-weight', (d: d3.HierarchyNode<AbilityNode>) => (d.depth <= 1 ? 700 : 500))
        .attr('fill', '#14532d')
        .attr('opacity', 0)
        .transition()
        .duration(600)
        .delay((_d, i: number) => 350 + i * 60)
        .attr('opacity', 1)

    nodeEnter
        .transition()
        .duration(500)
        .delay((_d, i: number) => 120 + i * 60)
        .attr('opacity', 1)
}

onMounted(() => {
    renderTree()

    const onResize = () => renderTree()
    window.addEventListener('resize', onResize)
    cleanupResize = () => window.removeEventListener('resize', onResize)
})

onBeforeUnmount(() => {
    cleanupResize?.()
    cleanupResize = null
})
</script>

<template>
    <section class="ability-page">
        <div class="ability-toolbar">
            <button type="button" class="back-btn" @click="goBack">返回</button>
            <div class="ability-title-block">
                <!-- <h1>能力总览区</h1> -->
                <p>从面试能力根向外生长，观察核心维度能力的阶段成长轨迹。</p>
            </div>
        </div>

        <div class="tree-stage">
            <div ref="chartHost" class="tree-host" />
        </div>
    </section>
</template>

<style scoped>
.ability-page {
    min-height: calc(100vh - 120px);
    padding: 1.2rem;
    border: 1px solid #dcfce7;
    border-radius: 14px;
    background:
        radial-gradient(circle at 22% 14%, rgba(187, 247, 208, 0.42), transparent 46%),
        radial-gradient(circle at 78% 86%, rgba(134, 239, 172, 0.42), transparent 44%),
        linear-gradient(140deg, #f0fdf4, #ecfdf5 45%, #f7fee7 100%);
}

.ability-toolbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
}

.back-btn {
    border: 1px solid #86efac;
    background: #ffffff;
    color: #14532d;
    border-radius: 8px;
    padding: 0.42rem 0.85rem;
    cursor: pointer;
    transition: all 0.2s ease;
}

.back-btn:hover {
    border-color: #22c55e;
    background: #f0fdf4;
}

.ability-title-block h1 {
    margin: 0;
    color: #14532d;
    font-size: 1.45rem;
}

.ability-title-block p {
    margin: 0.3rem 0 0;
    color: #166534;
}

.tree-stage {
    border: 1px solid #bbf7d0;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.74);
    min-height: 700px;
    overflow: auto;
}

.tree-host {
    min-width: 760px;
    height: 700px;
}

:deep(.ability-tree-svg) {
    width: 100%;
    height: 100%;
}

@media (max-width: 900px) {
    .ability-page {
        padding: 0.9rem;
    }

    .ability-toolbar {
        flex-direction: column;
        align-items: flex-start;
    }
}
</style>
