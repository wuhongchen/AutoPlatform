<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { dashboardApi } from '../lib/api'

const props = defineProps({
  activeAccount: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['refresh'])

const busy = ref(false)
const message = ref('')
const errorMessage = ref('')

// 任务列表
const tasks = ref([])
const selectedTaskId = ref('')

// 筛选
const typeFilter = ref('all') // all | ai_score | ai_rewrite | publish
const statusFilter = ref('all') // all | pending | running | success | failed
const keyword = ref('')

const accountId = computed(() => props.activeAccount?.id || '')

// 任务类型选项
const taskTypes = [
  { value: 'all', label: '全部类型', icon: '🔹' },
  { value: 'collect', label: '采集', icon: '📥' },
  { value: 'ai_score', label: 'AI评分', icon: '📊' },
  { value: 'ai_rewrite', label: 'AI改写', icon: '✍️' },
  { value: 'publish', label: '发布', icon: '📤' },
]

// 状态选项
const statusOptions = [
  { value: 'all', label: '全部状态', color: '' },
  { value: 'pending', label: '待执行', color: 'info' },
  { value: 'running', label: '运行中', color: 'warn' },
  { value: 'success', label: '成功', color: 'ok' },
  { value: 'failed', label: '失败', color: 'bad' },
]

// 筛选后的任务
const filteredTasks = computed(() => {
  let result = tasks.value || []

  // 按类型筛选
  if (typeFilter.value !== 'all') {
    result = result.filter(t => t.plugin_type === typeFilter.value)
  }

  // 按状态筛选
  if (statusFilter.value !== 'all') {
    result = result.filter(t => t.status === statusFilter.value)
  }

  // 按关键词筛选
  const kw = keyword.value.trim().toLowerCase()
  if (kw) {
    result = result.filter(t => {
      const text = [
        t.task_id,
        t.record_id,
        t.plugin_type,
        t.status,
        t.error_msg,
      ].join(' ').toLowerCase()
      return text.includes(kw)
    })
  }

  // 按时间倒序
  return result.sort((a, b) => {
    const ta = b.created_at || ''
    const tb = a.created_at || ''
    return ta.localeCompare(tb)
  })
})

// 统计
const stats = computed(() => {
  const all = tasks.value || []
  return {
    total: all.length,
    pending: all.filter(t => t.status === 'pending').length,
    running: all.filter(t => t.status === 'running').length,
    success: all.filter(t => t.status === 'success').length,
    failed: all.filter(t => t.status === 'failed').length,
  }
})

// 选中任务详情（解析 JSON 字段）
const selectedTask = computed(() => {
  const task = tasks.value.find(t => t.task_id === selectedTaskId.value)
  if (!task) return null

  // 解析 params_json 和 result_json
  let params = {}
  let result = {}
  try {
    params = JSON.parse(task.params_json || '{}')
  } catch (e) {
    params = {}
  }
  try {
    result = JSON.parse(task.result_json || '{}')
  } catch (e) {
    result = {}
  }

  return {
    ...task,
    params,
    result
  }
})

// 获取任务类型显示
function getTaskTypeLabel(type) {
  const map = {
    'collect': '采集',
    'ai_score': 'AI评分',
    'ai_rewrite': 'AI改写',
    'publish': '发布',
  }
  return map[type] || type
}

// 获取任务类型图标
function getTaskTypeIcon(type) {
  const map = {
    'collect': '📥',
    'ai_score': '📊',
    'ai_rewrite': '✍️',
    'publish': '📤',
  }
  return map[type] || '🔹'
}

// 获取状态样式
function getStatusStyle(status) {
  const map = {
    'pending': { badge: 'info', icon: '⏳' },
    'running': { badge: 'warn', icon: '🔄' },
    'success': { badge: 'ok', icon: '✅' },
    'failed': { badge: 'bad', icon: '❌' },
  }
  return map[status] || { badge: 'default', icon: '•' }
}

// 格式化时间
function formatTime(timeStr) {
  if (!timeStr) return '-'
  return timeStr.slice(5, 16) // MM-DD HH:mm
}

// 格式化耗时
function formatDuration(start, end) {
  if (!start || !end) return '-'
  const startTime = new Date(start.replace(' ', 'T'))
  const endTime = new Date(end.replace(' ', 'T'))
  const diff = Math.round((endTime - startTime) / 1000)
  if (diff < 60) return `${diff}s`
  return `${Math.round(diff / 60)}m ${diff % 60}s`
}

function setInfo(text) {
  message.value = text || ''
  errorMessage.value = ''
}

function setError(err) {
  errorMessage.value = err?.message || String(err || '操作失败')
}

async function loadTasks() {
  if (!accountId.value) return
  busy.value = true
  try {
    const data = await dashboardApi.listPluginTasks({
      accountId: accountId.value,
      limit: 500,
    })
    tasks.value = data.tasks || []
    setInfo(`已加载 ${tasks.value.length} 个任务`)
  } catch (err) {
    setError(err)
  } finally {
    busy.value = false
  }
}

async function retryTask(task) {
  if (!confirm(`确定要重试任务：${getTaskTypeLabel(task.plugin_type)}？`)) {
    return
  }
  setInfo(`正在重试任务...`)
  // TODO: 实现重试逻辑
  emit('refresh')
}

// 自动刷新
let refreshTimer = null
onMounted(() => {
  loadTasks()
  refreshTimer = setInterval(() => {
    if (stats.value.running > 0) {
      loadTasks()
    }
  }, 3000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

watch(() => accountId.value, () => {
  tasks.value = []
  loadTasks()
})
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>任务中心</h1>
        <p>查看和管理所有插件任务的执行状态，支持筛选和重试。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" :disabled="busy" @click="loadTasks">
          {{ busy ? '加载中...' : '刷新任务' }}
        </button>
      </div>
    </div>

    <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
    <div v-if="message" class="global-info">{{ message }}</div>

    <!-- 统计卡片 -->
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-head"><h3>全部任务</h3></div>
        <div class="metric-value">{{ stats.total }}</div>
      </div>
      <div class="metric-card info">
        <div class="metric-head"><h3>待执行</h3></div>
        <div class="metric-value">{{ stats.pending }}</div>
      </div>
      <div class="metric-card warn">
        <div class="metric-head"><h3>运行中</h3></div>
        <div class="metric-value">{{ stats.running }}</div>
      </div>
      <div class="metric-card ok">
        <div class="metric-head"><h3>成功</h3></div>
        <div class="metric-value">{{ stats.success }}</div>
      </div>
      <div class="metric-card bad">
        <div class="metric-head"><h3>失败</h3></div>
        <div class="metric-value">{{ stats.failed }}</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="panel-card">
      <div class="publish-filter-row">
        <label>
          任务类型
          <select v-model="typeFilter">
            <option v-for="t in taskTypes" :key="t.value" :value="t.value">
              {{ t.icon }} {{ t.label }}
            </option>
          </select>
        </label>
        <label>
          状态
          <select v-model="statusFilter">
            <option v-for="s in statusOptions" :key="s.value" :value="s.value">
              {{ s.label }}
            </option>
          </select>
        </label>
        <label>
          搜索
          <input v-model="keyword" type="text" placeholder="任务ID / 记录ID / 错误信息" />
        </label>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="panel-card">
      <h3>任务列表（{{ filteredTasks.length }}）</h3>
      <div class="task-table-wrap">
        <table class="task-table">
          <thead>
            <tr>
              <th>任务ID</th>
              <th>类型</th>
              <th>关联文章</th>
              <th>状态</th>
              <th>创建时间</th>
              <th>耗时</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in filteredTasks"
              :key="task.task_id"
              :class="{ active: selectedTaskId === task.task_id }"
              @click="selectedTaskId = task.task_id"
            >
              <td><code class="task-id">{{ task.task_id }}</code></td>
              <td>
                <span class="task-type-badge">
                  {{ getTaskTypeIcon(task.plugin_type) }} {{ getTaskTypeLabel(task.plugin_type) }}
                </span>
              </td>
              <td>
                <code class="record-id">{{ task.record_id?.slice(0, 12) }}...</code>
              </td>
              <td>
                <span class="badge" :class="getStatusStyle(task.status).badge">
                  {{ getStatusStyle(task.status).icon }} {{ task.status }}
                </span>
              </td>
              <td>{{ formatTime(task.created_at) }}</td>
              <td>{{ formatDuration(task.started_at, task.ended_at) }}</td>
              <td>
                <button
                  v-if="task.status === 'failed'"
                  class="action-btn action-btn-warn"
                  @click.stop="retryTask(task)"
                >
                  重试
                </button>
                <span v-else class="table-empty-cell">-</span>
              </td>
            </tr>
            <tr v-if="!filteredTasks.length">
              <td colspan="7">
                <div class="empty-block">暂无任务记录</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 任务详情 -->
    <div v-if="selectedTask" class="panel-card task-detail-card">
      <div class="task-detail-header">
        <h3>
          {{ getTaskTypeIcon(selectedTask.plugin_type) }} {{ getTaskTypeLabel(selectedTask.plugin_type) }} 任务详情
          <span class="task-status-badge" :class="getStatusStyle(selectedTask.status).badge">
            {{ getStatusStyle(selectedTask.status).icon }} {{ selectedTask.status }}
          </span>
        </h3>
        <button class="close-btn" @click="selectedTaskId = ''">✕</button>
      </div>

      <div class="task-detail-body">
        <!-- 左侧：基本信息 -->
        <div class="detail-section">
          <h4 class="section-title">📋 基本信息</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">任务ID</span>
              <code class="detail-value">{{ selectedTask.task_id }}</code>
            </div>
            <div class="detail-item">
              <span class="detail-label">关联文章ID</span>
              <code class="detail-value">{{ selectedTask.record_id }}</code>
            </div>
            <div class="detail-item">
              <span class="detail-label">创建时间</span>
              <span class="detail-value">{{ selectedTask.created_at || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">开始时间</span>
              <span class="detail-value">{{ selectedTask.started_at || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">结束时间</span>
              <span class="detail-value">{{ selectedTask.ended_at || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">耗时</span>
              <span class="detail-value">{{ formatDuration(selectedTask.started_at, selectedTask.ended_at) }}</span>
            </div>
          </div>
        </div>

        <!-- 任务参数 -->
        <div v-if="selectedTask.params && Object.keys(selectedTask.params).length" class="detail-section">
          <h4 class="section-title">⚙️ 任务参数</h4>
          <div class="params-list">
            <div v-for="(value, key) in selectedTask.params" :key="key" class="param-item">
              <span class="param-key">{{ key }}</span>
              <span class="param-value">{{ value }}</span>
            </div>
          </div>
        </div>

        <!-- 执行结果 -->
        <div v-if="selectedTask.result && Object.keys(selectedTask.result).length" class="detail-section">
          <h4 class="section-title">✅ 执行结果</h4>
          <div class="result-content">
            <div v-for="(value, key) in selectedTask.result" :key="key" class="result-item">
              <span class="result-key">{{ key }}</span>
              <span v-if="typeof value === 'string' && value.length < 100" class="result-value">{{ value }}</span>
              <code v-else-if="typeof value === 'string'" class="result-value code">{{ value.slice(0, 100) }}...</code>
              <code v-else class="result-value code">{{ JSON.stringify(value).slice(0, 100) }}</code>
            </div>
          </div>
        </div>

        <!-- 错误信息 -->
        <div v-if="selectedTask.error_msg" class="detail-section error-section">
          <h4 class="section-title">❌ 错误信息</h4>
          <div class="error-content">
            <pre>{{ selectedTask.error_msg }}</pre>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.metric-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}

.metric-card.info {
  border-color: #3b82f6;
  background: #eff6ff;
}

.metric-card.warn {
  border-color: #f59e0b;
  background: #fffbeb;
}

.metric-card.ok {
  border-color: #10b981;
  background: #ecfdf5;
}

.metric-card.bad {
  border-color: #ef4444;
  background: #fef2f2;
}

.metric-head h3 {
  font-size: 13px;
  color: var(--text-soft);
  margin: 0 0 8px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
}

.task-table-wrap {
  overflow-x: auto;
  margin-top: 16px;
}

.task-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.task-table th {
  text-align: left;
  padding: 12px;
  border-bottom: 1px solid var(--line);
  color: var(--text-soft);
  font-weight: 500;
}

.task-table td {
  padding: 12px;
  border-bottom: 1px solid var(--line);
  vertical-align: middle;
}

.task-table tr:hover {
  background: var(--surface-soft);
}

.task-table tr.active {
  background: rgba(59, 130, 246, 0.1);
}

.task-id {
  font-size: 12px;
  color: var(--text-soft);
}

.record-id {
  font-size: 11px;
  color: var(--text-soft);
}

.task-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(245, 249, 255, 0.96);
  border-radius: 6px;
  font-size: 12px;
}

.task-detail-card {
  margin-top: 20px;
}

.task-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}

.task-detail-header h3 {
  margin: 0;
  font-size: 16px;
}

.task-detail-content {
  display: grid;
  gap: 12px;
}

.detail-row {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 16px;
  align-items: start;
}

.detail-label {
  font-size: 13px;
  color: var(--text-soft);
}

.detail-value {
  font-size: 13px;
  word-break: break-all;
}

.detail-value.error-text {
  color: #ef4444;
  background: #fef2f2;
  padding: 8px 12px;
  border-radius: 6px;
}

.detail-value.result-json {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  line-height: 1.5;
}

/* 新的任务详情样式 */
.task-detail-body {
  display: grid;
  gap: 20px;
}

.detail-section {
  background: rgba(245, 249, 255, 0.5);
  border-radius: 12px;
  padding: 16px;
}

.detail-section.error-section {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 12px;
  color: var(--text-soft);
}

.detail-value {
  font-size: 13px;
  font-weight: 500;
  word-break: break-all;
}

.task-status-badge {
  margin-left: 8px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
}

.task-status-badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.task-status-badge.warn {
  background: #fef3c7;
  color: #92400e;
}

.task-status-badge.ok {
  background: #d1fae5;
  color: #065f46;
}

.task-status-badge.bad {
  background: #fee2e2;
  color: #991b1b;
}

/* 参数列表 */
.params-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
}

.param-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: white;
  border-radius: 8px;
  font-size: 13px;
}

.param-key {
  color: var(--text-soft);
  font-size: 12px;
}

.param-value {
  color: var(--text);
  font-weight: 500;
  word-break: break-all;
}

/* 结果内容 */
.result-content {
  display: grid;
  gap: 8px;
}

.result-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 12px;
  background: white;
  border-radius: 8px;
}

.result-key {
  color: var(--text-soft);
  font-size: 12px;
  min-width: 80px;
  flex-shrink: 0;
}

.result-value {
  color: var(--text);
  font-size: 13px;
  word-break: break-all;
}

.result-value.code {
  font-family: monospace;
  font-size: 11px;
  background: #f3f4f6;
  padding: 4px 8px;
  border-radius: 4px;
}

/* 错误内容 */
.error-content {
  background: white;
  border-radius: 8px;
  padding: 12px;
}

.error-content pre {
  margin: 0;
  font-size: 12px;
  color: #dc2626;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
