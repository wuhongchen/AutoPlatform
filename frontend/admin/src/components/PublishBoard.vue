<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { dashboardApi } from '../lib/api'

const props = defineProps({
  jobs: { type: Array, default: () => [] },
  publishRows: { type: Array, default: () => [] },
  accounts: { type: Array, default: () => [] },
  activeAccountId: { type: String, default: '' },
  initialJobId: { type: String, default: '' },
  pipelineItems: { type: Array, default: () => [] },
})
const emit = defineEmits(['refresh', 'run-selected', 'run-pipeline', 'open-job'])

const busy = ref(false)
const loadingDetail = ref(false)
const message = ref('')
const errorMessage = ref('')

const statusFilter = ref('all')
const accountFilter = ref('all')
const keyword = ref('')

const selectedJobId = ref('')
const selectedDetail = ref(null)


const accountNameMap = computed(() => {
  const out = {}
  for (const item of props.accounts || []) {
    out[item.id] = item.name || item.id
  }
  return out
})
const knownJobIds = computed(() => {
  const out = new Set()
  for (const job of props.jobs || []) {
    if (job?.id) out.add(job.id)
  }
  return out
})

const orderedJobs = computed(() => {
  const list = [...(props.jobs || [])]
  list.sort((a, b) => {
    const ak = `${a.started_at || ''}${a.id || ''}`
    const bk = `${b.started_at || ''}${b.id || ''}`
    return bk.localeCompare(ak)
  })
  return list
})

const filteredJobs = computed(() => {
  const q = String(keyword.value || '').trim().toLowerCase()
  return orderedJobs.value.filter((job) => {
    if (statusFilter.value !== 'all' && job.status !== statusFilter.value) return false
    if (accountFilter.value !== 'all' && (job.account_id || '') !== accountFilter.value) return false
    if (!q) return true
    const haystack = [
      job.id,
      job.name,
      job.account_id,
      job.account_name,
      job.command,
      job.status,
    ].join(' ').toLowerCase()
    return haystack.includes(q)
  })
})

const publishStatusOptions = computed(() => {
  const map = new Map()
  for (const row of props.publishRows || []) {
    const st = String(row.publish_status || row.result || '未标记').trim() || '未标记'
    map.set(st, (map.get(st) || 0) + 1)
  }
  return Array.from(map.entries()).map(([value, count]) => ({ value, count }))
})

const selectedPublishStatus = ref('all')
const publishKeyword = ref('')
const filteredPublishRows = computed(() => {
  const status = String(selectedPublishStatus.value || 'all').trim()
  const kw = String(publishKeyword.value || '').trim().toLowerCase()
  return (props.publishRows || []).filter((row) => {
    const st = String(row.publish_status || row.result || '未标记').trim() || '未标记'
    if (status !== 'all' && st !== status) return false
    if (!kw) return true
    return [
      row.record_id,
      row.title,
      row.publish_status,
      row.result,
      row.remark,
      row.url,
      row.rewritten_doc,
      row.published_at,
    ]
      .join(' ')
      .toLowerCase()
      .includes(kw)
  })
})

function setInfo(text) {
  message.value = text || ''
  errorMessage.value = ''
}

function setError(err) {
  errorMessage.value = err?.message || String(err || '操作失败')
}

function statusClass(status) {
  if (status === 'success') return 'ok'
  if (status === 'failed') return 'bad'
  if (status === 'running') return 'warn'
  return 'plain'
}

function shortCommand(command) {
  const text = String(command || '').trim()
  if (text.length <= 72) return text
  return `${text.slice(0, 72)}...`
}

// 异常追踪相关逻辑
function normalizePipelineStage(status) {
  const map = {
    'pending': '待处理',
    'analyzed': '待改写',
    'rewritten': '待排版',
    'formatted': '待发布',
    'published': '已发布',
    'failed': '处理失败',
    'skipped': '已跳过'
  }
  return map[status] || status || '未知'
}

function validDocUrl(url) {
  return /^https?:\/\/(www\.)?feishu\.cn\/docx\/[A-Za-z0-9]{20,}/.test(String(url || '').trim())
}

function validHttpUrl(url) {
  return /^https?:\/\//.test(String(url || '').trim())
}

function classifyPipelineItem(item) {
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

const traceItems = computed(() => {
  return props.pipelineItems
    .filter((item) => {
      const stage = normalizePipelineStage(item.status)
      const remark = String(item.remark || '')
      const rewritten = String(item.rewritten_doc || '').trim()
      const badDoc = !rewritten || !validDocUrl(rewritten)
      return stage.includes('失败') || remark.includes('失败') || badDoc
    })
    .map((item) => ({
      ...item,
      trace_type: classifyPipelineItem(item),
      stage: normalizePipelineStage(item.status),
      bad_doc: !String(item.rewritten_doc || '').trim() || !validDocUrl(item.rewritten_doc),
    }))
})

const failedJobs = computed(() => (props.jobs || []).filter((it) => it.status === 'failed'))

const traceStats = computed(() => {
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

// 视图切换：all / trace
const viewMode = ref('all')

async function withBusy(fn) {
  busy.value = true
  errorMessage.value = ''
  try {
    await fn()
  } catch (err) {
    setError(err)
  } finally {
    busy.value = false
  }
}

async function loadJobDetail(jobId) {
  if (!jobId) {
    selectedDetail.value = null
    return
  }
  if (!knownJobIds.value.has(jobId)) {
    selectedDetail.value = null
    setInfo(`任务 ${jobId} 不在当前任务缓存中，已自动等待最新任务刷新。`)
    return
  }
  loadingDetail.value = true
  try {
    const data = await dashboardApi.jobDetail(jobId, { allow404: true })
    if (data?.not_found) {
      selectedDetail.value = null
      setInfo(`任务 ${jobId} 日志不存在（通常是服务重启后内存清空），请选择列表中的最新任务。`)
      return
    }
    selectedDetail.value = data.item || null
  } catch (err) {
    setError(err)
  } finally {
    loadingDetail.value = false
  }
}


watch(
  () => props.activeAccountId,
  (value) => {
    accountFilter.value = value || 'all'
  },
  { immediate: true }
)

watch(
  () => props.initialJobId,
  (jobId) => {
    if (!jobId) return
    selectedJobId.value = String(jobId)
  },
  { immediate: true }
)

watch(
  filteredJobs,
  (list) => {
    const first = list[0]?.id || ''
    if (!selectedJobId.value || !list.some((item) => item.id === selectedJobId.value)) {
      selectedJobId.value = first
    }
  },
  { immediate: true }
)

watch(
  selectedJobId,
  (value) => {
    loadJobDetail(value)
  },
  { immediate: true }
)

// 自动刷新任务状态
const refreshTimer = ref(null)

onMounted(() => {
  // 每3秒自动刷新一次任务状态
  refreshTimer.value = setInterval(() => {
    // 如果有正在运行的任务，触发父组件刷新
    if (props.jobs.some(job => job.status === 'running' || job.status === 'queued')) {
      emit('refresh')
    }
  }, 3000)
})

onUnmounted(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
})
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>任务中心</h1>
        <p>整合任务执行日志、发布记录与异常追踪，统一管理全流程任务，支持排查与快速重试。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" :disabled="busy" @click="emit('refresh')">刷新任务</button>
      </div>
    </div>

    <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
    <div v-if="message" class="global-info">{{ message }}</div>

    <!-- 异常统计面板 -->
    <div class="metrics-grid metrics-grid-trace" style="margin-bottom: 20px;">
      <article class="metric-card bad">
        <div class="metric-head"><h3>改写失败</h3></div>
        <div class="metric-value">{{ traceStats.rewriteFailed }}</div>
      </article>
      <article class="metric-card bad">
        <div class="metric-head"><h3>发布失败</h3></div>
        <div class="metric-value">{{ traceStats.publishFailed }}</div>
      </article>
      <article class="metric-card warn">
        <div class="metric-head"><h3>文档链接失效</h3></div>
        <div class="metric-value">{{ traceStats.docInvalid }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-head"><h3>任务失败</h3></div>
        <div class="metric-value">{{ traceStats.failedJobs }}</div>
      </article>
    </div>

    <div class="panel-card">
      <div class="publish-filter-row">
        <label>
          状态
          <select v-model="statusFilter">
            <option value="all">全部</option>
            <option value="queued">queued</option>
            <option value="running">running</option>
            <option value="success">success</option>
            <option value="failed">failed</option>
          </select>
        </label>
        <label>
          账户
          <select v-model="accountFilter">
            <option value="all">全部账户</option>
            <option v-for="item in accounts" :key="item.id" :value="item.id">{{ item.name || item.id }}</option>
          </select>
        </label>
        <label>
          搜索
          <input v-model="keyword" type="text" placeholder="任务名 / 命令 / 账户 / 状态" />
        </label>
      </div>

    </div>

    <div class="publish-grid">
      <div class="panel-card panel-soft">
        <h3>任务列表（{{ filteredJobs.length }}）</h3>
        <div class="publish-table-wrap">
          <table class="publish-table">
            <thead>
              <tr>
                <th>任务ID</th>
                <th>账户</th>
                <th>任务名称</th>
                <th>状态</th>
                <th>开始时间</th>
                <th>结束时间</th>
                <th>命令</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="job in filteredJobs"
                :key="job.id"
                :class="{ active: selectedJobId === job.id }"
                @click="selectedJobId = job.id"
              >
                <td><code>{{ job.id }}</code></td>
                <td>{{ job.account_name || accountNameMap[job.account_id] || job.account_id || '-' }}</td>
                <td>{{ job.name }}</td>
                <td>
                  <span class="badge" :class="statusClass(job.status)">{{ job.status }}</span>
                </td>
                <td>{{ job.started_at || '-' }}</td>
                <td>{{ job.ended_at || '-' }}</td>
                <td class="cmd-cell">{{ shortCommand(job.command) }}</td>
              </tr>
              <tr v-if="!filteredJobs.length">
                <td colspan="7">
                  <div class="empty-block">暂无任务记录</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="panel-card">
        <h3>任务详情</h3>
        <div v-if="loadingDetail" class="loading-card">正在加载任务日志...</div>
        <template v-else-if="selectedDetail">
          <div class="kv-list">
            <div><span>任务ID</span><strong>{{ selectedDetail.id }}</strong></div>
            <div><span>状态</span><strong>{{ selectedDetail.status }}</strong></div>
            <div><span>账户</span><strong>{{ selectedDetail.account_name || selectedDetail.account_id || '-' }}</strong></div>
            <div><span>开始</span><strong>{{ selectedDetail.started_at || '-' }}</strong></div>
            <div><span>结束</span><strong>{{ selectedDetail.ended_at || '-' }}</strong></div>
            <div><span>返回码</span><strong>{{ selectedDetail.return_code ?? '-' }}</strong></div>
          </div>
          <p class="panel-tip">{{ selectedDetail.command }}</p>
          <div class="log-panel">
            <pre>{{ (selectedDetail.logs || []).join('\n') }}</pre>
          </div>
        </template>
        <div v-else class="empty-block">点击左侧任务后，这里展示实时日志与执行结果。</div>
      </div>
    </div>

    <div class="panel-card">
      <h3>发布记录（{{ filteredPublishRows.length }}）</h3>
      <div class="publish-filter-row">
        <label>
          发布状态
          <select v-model="selectedPublishStatus">
            <option value="all">全部</option>
            <option v-for="item in publishStatusOptions" :key="item.value" :value="item.value">{{ item.value }}（{{ item.count }}）</option>
          </select>
        </label>
        <label>
          关键词
          <input v-model="publishKeyword" type="text" placeholder="标题 / 结果 / 备注 / 链接" />
        </label>
      </div>
      <div class="publish-table-wrap">
        <table class="publish-table">
          <thead>
            <tr>
              <th>记录ID</th>
              <th>标题</th>
              <th>发布状态</th>
              <th>结果</th>
              <th>发布时间</th>
              <th>链接</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredPublishRows" :key="row.record_id">
              <td><code>{{ row.record_id || '-' }}</code></td>
              <td>{{ row.title || '-' }}</td>
              <td>{{ row.publish_status || '-' }}</td>
              <td>{{ row.result || '-' }}</td>
              <td>{{ row.published_at || '-' }}</td>
              <td>
                <a v-if="/^https?:\/\//.test(String(row.rewritten_doc || '').trim())" :href="row.rewritten_doc" target="_blank" rel="noreferrer">改后文档</a>
                <a v-else-if="/^https?:\/\//.test(String(row.url || '').trim())" :href="row.url" target="_blank" rel="noreferrer">原文</a>
                <span v-else>-</span>
              </td>
              <td class="cmd-cell">{{ row.remark || '-' }}</td>
            </tr>
            <tr v-if="!filteredPublishRows.length">
              <td colspan="7"><div class="empty-block">当前账户暂无发布记录。</div></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
