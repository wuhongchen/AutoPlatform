<script setup>
import { computed, ref, watch } from 'vue'
import { normalizePipelineStage } from '../lib/pipeline'

const props = defineProps({
  pipelineItems: { type: Array, default: () => [] },
  jobs: { type: Array, default: () => [] },
  activeAccount: { type: Object, default: () => ({}) },
  activeAccountId: { type: String, default: '' },
})
const emit = defineEmits(['refresh', 'run-selected', 'run-pipeline', 'open-job'])

const selectedTraceId = ref('')

function validDocUrl(url) {
  return /^https?:\/\/(www\.)?feishu\.cn\/docx\/[A-Za-z0-9]{20,}/.test(String(url || '').trim())
}

function validHttpUrl(url) {
  return /^https?:\/\//.test(String(url || '').trim())
}

function classify(item) {
  const stage = normalizePipelineStage(item.status)
  const remark = String(item.remark || '')
  const rewritten = String(item.rewritten_doc || '').trim()
  const hasDocIssue = !rewritten || !validDocUrl(rewritten)

  if (hasDocIssue && (stage.includes('发布') || stage.includes('失败') || remark.includes('文档'))) {
    return '改后文档链接异常'
  }
  if ((stage.includes('失败') || remark.includes('发布失败') || remark.includes('发布')) && !stage.includes('待')) {
    if (remark.includes('发布') || stage.includes('发布')) return '发布失败'
    return '改写失败'
  }
  return '待排查异常'
}

const pipelineItems = computed(() => props.pipelineItems || [])

const traceItems = computed(() => {
  return pipelineItems.value
    .filter((item) => {
      const stage = normalizePipelineStage(item.status)
      const remark = String(item.remark || '')
      const rewritten = String(item.rewritten_doc || '').trim()
      const badDoc = !rewritten || !validDocUrl(rewritten)
      return stage.includes('失败') || remark.includes('失败') || badDoc
    })
    .map((item) => ({
      ...item,
      trace_type: classify(item),
      stage: normalizePipelineStage(item.status),
      bad_doc: !String(item.rewritten_doc || '').trim() || !validDocUrl(item.rewritten_doc),
    }))
})

const failedJobs = computed(() => (props.jobs || []).filter((it) => it.status === 'failed'))

const stats = computed(() => {
  const rewriteFailed = traceItems.value.filter((it) => it.trace_type === '改写失败').length
  const publishFailed = traceItems.value.filter((it) => it.trace_type === '发布失败').length
  const docInvalid = traceItems.value.filter((it) => it.trace_type === '改后文档链接异常').length
  return {
    rewriteFailed,
    publishFailed,
    docInvalid,
    failedJobs: failedJobs.value.length,
  }
})

const selectedTrace = computed(() => traceItems.value.find((it) => it.record_id === selectedTraceId.value) || traceItems.value[0] || null)

watch(
  traceItems,
  (list) => {
    if (!selectedTraceId.value || !list.some((it) => it.record_id === selectedTraceId.value)) {
      selectedTraceId.value = list[0]?.record_id || ''
    }
  },
  { immediate: true }
)
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>追踪中心</h1>
        <p>聚合改写与发布异常，提供统一排查入口，避免灵感记录与流水线记录断裂。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" @click="emit('refresh')">刷新追踪</button>
        <button class="primary-btn" @click="emit('run-pipeline')">重试追踪</button>
      </div>
    </div>

    <div class="metrics-grid metrics-grid-trace">
      <article class="metric-card bad">
        <div class="metric-head"><h3>改写失败</h3></div>
        <div class="metric-value">{{ stats.rewriteFailed }}</div>
      </article>
      <article class="metric-card bad">
        <div class="metric-head"><h3>发布失败</h3></div>
        <div class="metric-value">{{ stats.publishFailed }}</div>
      </article>
      <article class="metric-card warn">
        <div class="metric-head"><h3>文档链接失效</h3></div>
        <div class="metric-value">{{ stats.docInvalid }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-head"><h3>任务失败</h3></div>
        <div class="metric-value">{{ stats.failedJobs }}</div>
      </article>
    </div>

    <div class="trace-grid">
      <div class="panel-card panel-soft">
        <h3>异常链路（{{ traceItems.length }}）</h3>
        <div class="trace-table-wrap">
          <table class="publish-table">
            <thead>
              <tr>
                <th>记录ID</th>
                <th>阶段</th>
                <th>异常类型</th>
                <th>标题</th>
                <th>备注</th>
                <th>改后文档</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in traceItems"
                :key="item.record_id"
                :class="{ active: selectedTraceId === item.record_id }"
                @click="selectedTraceId = item.record_id"
              >
                <td><code>{{ item.record_id }}</code></td>
                <td>{{ item.stage }}</td>
                <td><span class="badge" :class="item.trace_type.includes('链接') ? 'warn' : 'bad'">{{ item.trace_type }}</span></td>
                <td>{{ item.title || '-' }}</td>
                <td class="cmd-cell">{{ item.remark || '-' }}</td>
                <td>
                  <a v-if="validHttpUrl(item.rewritten_doc)" :href="item.rewritten_doc" target="_blank" rel="noreferrer">打开</a>
                  <span v-else>-</span>
                </td>
              </tr>
              <tr v-if="!traceItems.length">
                <td colspan="6"><div class="empty-block">暂无失败链路，当前状态稳定。</div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <aside class="trace-side">
        <div class="panel-card" v-if="selectedTrace">
          <h3>重解流踪时间</h3>
          <div class="trace-timeline">
            <div class="trace-step">
              <span class="step-dot">1</span>
              <div>
                <h4>灵感记录</h4>
                <p>{{ selectedTrace.title || '-' }}</p>
                <a v-if="validHttpUrl(selectedTrace.url)" :href="selectedTrace.url" target="_blank" rel="noreferrer">原文入口</a>
              </div>
            </div>
            <div class="trace-step">
              <span class="step-dot">2</span>
              <div>
                <h4>管道记录</h4>
                <p>阶段：{{ selectedTrace.stage }}，类型：{{ selectedTrace.trace_type }}</p>
                <p>失败备注：{{ selectedTrace.remark || '无' }}</p>
              </div>
            </div>
            <div class="trace-step">
              <span class="step-dot">3</span>
              <div>
                <h4>修复动作</h4>
                <div class="detail-actions">
                  <button class="ghost-btn" @click="emit('run-selected', selectedTrace)">重试重写</button>
                  <button class="primary-btn" @click="emit('run-pipeline')">重试发布链路</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="panel-card">
          <h3>失败任务日志</h3>
          <div class="trace-job-list">
            <div v-for="job in failedJobs.slice(0, 8)" :key="job.id" class="trace-job-item">
              <strong>{{ job.name }}</strong>
              <p>{{ job.account_name || job.account_id || '-' }} · {{ job.ended_at || '-' }}</p>
              <button class="ghost-btn inline-btn" @click="emit('open-job', job.id)">查看任务日志</button>
            </div>
            <div v-if="!failedJobs.length" class="empty-block">当前没有失败任务日志。</div>
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>
