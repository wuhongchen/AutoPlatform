<script setup>
import { computed } from 'vue'
import MetricCard from './MetricCard.vue'
import { countsFromPipeline } from '../lib/pipeline'

const props = defineProps({
  overview: { type: Object, default: null },
  jobs: { type: Array, default: () => [] },
})
const emit = defineEmits(['run-scan', 'run-pipeline', 'run-full'])

const pipelineCounts = computed(() => countsFromPipeline(props.overview?.recent?.pipeline || []))
const cards = computed(() => {
  const meta = props.overview?.meta || {}
  return [
    { title: '总计灵感项目', value: meta.inspiration_total || 0, meta: `当前灵感表：${meta.inspiration_table_name || '-'}` },
    { title: '待重写项目', value: pipelineCounts.value.waitingRewrite, meta: `流水线记录：${meta.pipeline_total || 0}`, tone: 'warn' },
    { title: '待发布项目', value: pipelineCounts.value.waitingPublish, meta: `已发布：${pipelineCounts.value.published}`, tone: 'warn' },
    { title: '失败任务', value: pipelineCounts.value.failed, meta: '建议优先去追踪中心处理', tone: pipelineCounts.value.failed ? 'bad' : '' },
  ]
})
</script>

<template>
  <section class="page-section">
    <div class="page-headline">
      <div>
        <h1>商户概览</h1>
        <p>面向当前激活账户的灵感抓取、改写流水线、失败预警与运行状态总览。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" @click="emit('run-scan')">灵感库扫描</button>
        <button class="ghost-btn" @click="emit('run-full')">全流程单次巡检</button>
        <button class="primary-btn" @click="emit('run-pipeline')">流水线单次巡检</button>
      </div>
    </div>

    <div class="metrics-grid">
      <MetricCard v-for="card in cards" :key="card.title" v-bind="card" />
    </div>

    <div class="overview-grid">
      <div class="panel-card panel-soft">
        <h3>账户健康概况</h3>
        <ul class="bullet-list">
          <li>当前激活账户：{{ overview?.account?.name || overview?.account?.id || '-' }}</li>
          <li>默认模型：{{ overview?.account?.pipeline_model || 'auto' }}</li>
          <li>默认角色：{{ overview?.account?.pipeline_role || 'tech_expert' }}</li>
          <li>数据更新时间：{{ overview?.meta?.updated_at || '-' }}</li>
        </ul>
      </div>
      <div class="panel-card">
        <h3>最近任务</h3>
        <div v-if="jobs.length" class="job-list-simple">
          <div v-for="job in jobs.slice(0, 6)" :key="job.id" class="job-row-simple">
            <strong>{{ job.name }}</strong>
            <span>{{ job.status }}</span>
          </div>
        </div>
        <div v-else class="empty-block">当前还没有最近任务记录。</div>
      </div>
    </div>
  </section>
</template>
