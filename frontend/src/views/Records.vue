<template>
  <div class="records-page">
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-rewritten">
          <div class="stat-value">{{ rewrittenCount }}</div>
          <div class="stat-label">改写完成</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-published">
          <div class="stat-value">{{ publishedCount }}</div>
          <div class="stat-label">发布完成</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-failed">
          <div class="stat-value">{{ failedCount }}</div>
          <div class="stat-label">失败记录</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-active">
          <div class="stat-value">{{ activeCount }}</div>
          <div class="stat-label">处理中</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <div class="filter-group">
          <el-radio-group v-model="filters.stage" size="small">
            <el-radio-button label="">全部阶段</el-radio-button>
            <el-radio-button label="rewrite">改写记录</el-radio-button>
            <el-radio-button label="publish">发布记录</el-radio-button>
          </el-radio-group>
          <el-radio-group v-model="filters.status" size="small">
            <el-radio-button label="">全部状态</el-radio-button>
            <el-radio-button label="rewriting">改写中</el-radio-button>
            <el-radio-button label="rewritten">已改写</el-radio-button>
            <el-radio-button label="publishing">发布中</el-radio-button>
            <el-radio-button label="published">已发布</el-radio-button>
            <el-radio-button label="failed">失败</el-radio-button>
          </el-radio-group>
        </div>
        <div class="filter-actions">
          <el-input v-model="filters.keyword" placeholder="搜索标题" clearable style="width: 220px" />
          <el-button @click="loadData" :loading="loading">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table :data="filteredRecords" v-loading="loading" stripe>
        <el-table-column label="标题" min-width="320">
          <template #default="{ row }">
            <div class="record-title">{{ row.source_title || '无标题' }}</div>
            <div class="record-subtitle">
              <el-tag size="small" type="info">{{ row.account_id || '-' }}</el-tag>
              <span class="record-time">更新于 {{ formatTime(row.updated_at || row.created_at) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="当前状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="改写记录" min-width="240">
          <template #default="{ row }">
            <div class="task-brief">
              <el-tag :type="taskStatusType(row.rewriteTask?.status)" size="small">
                {{ row.rewriteTask ? taskStatusLabel(row.rewriteTask.status) : rewriteSummary(row.status) }}
              </el-tag>
              <div v-if="row.rewriteTask?.completed_at" class="task-time">
                {{ formatTime(row.rewriteTask.completed_at) }}
              </div>
              <div v-if="row.rewriteTask?.error_message" class="task-error">
                {{ row.rewriteTask.error_message }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="发布记录" min-width="240">
          <template #default="{ row }">
            <div class="task-brief">
              <el-tag :type="taskStatusType(row.publishTask?.status)" size="small">
                {{ row.publishTask ? taskStatusLabel(row.publishTask.status) : publishSummary(row.status) }}
              </el-tag>
              <div v-if="row.publishTask?.completed_at" class="task-time">
                {{ formatTime(row.publishTask.completed_at) }}
              </div>
              <div v-if="row.publishTask?.error_message" class="task-error">
                {{ row.publishTask.error_message }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" @click="openDetail(row)">查看记录</el-button>
              <el-button size="small" type="primary" @click="goRewrite(row.id)">去改写页</el-button>
              <el-button
                v-if="row.status === 'rewritten'"
                size="small"
                type="success"
                @click="openPublishDialog(row.id)"
              >
                发布
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && !filteredRecords.length" description="当前账户还没有 AI 记录" />
    </el-card>

    <el-dialog v-model="detailVisible" title="AI 记录详情" width="920px">
      <div v-if="currentRecord" class="record-detail">
        <div class="detail-header">
          <div>
            <div class="detail-title">{{ currentRecord.source_title || '未命名文章' }}</div>
            <div class="detail-meta">
              <el-tag :type="statusType(currentRecord.status)" size="small">
                {{ statusLabel(currentRecord.status) }}
              </el-tag>
              <el-tag v-if="currentRecord.rewrite_style" type="info" size="small">
                {{ currentRecord.rewrite_style }}
              </el-tag>
              <span>{{ currentRecord.account_id || '-' }}</span>
            </div>
          </div>
          <div class="detail-actions">
            <el-button size="small" @click="goRewrite(currentRecord.id)">去改写页</el-button>
            <el-button
              v-if="currentRecord.status === 'rewritten'"
              size="small"
              type="success"
              @click="openPublishDialog(currentRecord.id)"
            >
              发布
            </el-button>
          </div>
        </div>

        <el-row :gutter="16" class="detail-grid">
          <el-col :span="12">
            <div class="detail-panel">
              <div class="detail-panel-title">改写任务</div>
              <div v-if="currentRecord.rewriteTask">
                <div class="detail-line">
                  <span>状态</span>
                  <el-tag :type="taskStatusType(currentRecord.rewriteTask.status)" size="small">
                    {{ taskStatusLabel(currentRecord.rewriteTask.status) }}
                  </el-tag>
                </div>
                <div class="detail-line"><span>任务ID</span><code>{{ currentRecord.rewriteTask.id }}</code></div>
                <div class="detail-line"><span>开始时间</span><span>{{ formatTime(currentRecord.rewriteTask.started_at) }}</span></div>
                <div class="detail-line"><span>完成时间</span><span>{{ formatTime(currentRecord.rewriteTask.completed_at) }}</span></div>
                <div v-if="currentRecord.rewriteTask.error_message" class="detail-error">
                  {{ currentRecord.rewriteTask.error_message }}
                </div>
              </div>
              <el-empty v-else description="暂无改写任务记录" />
            </div>
          </el-col>

          <el-col :span="12">
            <div class="detail-panel">
              <div class="detail-panel-title">发布任务</div>
              <div v-if="currentRecord.publishTask">
                <div class="detail-line">
                  <span>状态</span>
                  <el-tag :type="taskStatusType(currentRecord.publishTask.status)" size="small">
                    {{ taskStatusLabel(currentRecord.publishTask.status) }}
                  </el-tag>
                </div>
                <div class="detail-line"><span>任务ID</span><code>{{ currentRecord.publishTask.id }}</code></div>
                <div class="detail-line"><span>开始时间</span><span>{{ formatTime(currentRecord.publishTask.started_at) }}</span></div>
                <div class="detail-line"><span>完成时间</span><span>{{ formatTime(currentRecord.publishTask.completed_at) }}</span></div>
                <div v-if="currentRecord.publishTask.error_message" class="detail-error">
                  {{ currentRecord.publishTask.error_message }}
                </div>
              </div>
              <el-empty v-else description="暂无发布任务记录" />
            </div>
          </el-col>
        </el-row>

        <div v-if="currentRecord.rewritten_html" class="detail-panel detail-content-panel">
          <div class="detail-panel-title">改写成稿</div>
          <div class="detail-content" v-html="currentRecord.rewritten_html" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAppStore, useArticleStore, useTaskStore } from '../stores'

const router = useRouter()
const appStore = useAppStore()
const articleStore = useArticleStore()
const taskStore = useTaskStore()

const loading = ref(false)
const detailVisible = ref(false)
const currentRecord = ref(null)
const refreshTimer = ref(null)

const filters = reactive({
  stage: '',
  status: '',
  keyword: ''
})

const records = computed(() => {
  const taskMap = new Map()
  for (const task of taskStore.tasks) {
    const targetId = task.target_id || task.payload?.article_id
    if (!targetId) continue
    if (!taskMap.has(targetId)) taskMap.set(targetId, { rewrite: [], publish: [] })
    if (task.name === 'rewrite') taskMap.get(targetId).rewrite.push(task)
    if (task.name === 'publish') taskMap.get(targetId).publish.push(task)
  }

  const sortByLatest = (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)
  taskMap.forEach((bucket) => {
    bucket.rewrite.sort(sortByLatest)
    bucket.publish.sort(sortByLatest)
  })

  return articleStore.articles.map((article) => {
    const bucket = taskMap.get(article.id) || { rewrite: [], publish: [] }
    return {
      ...article,
      rewriteTask: bucket.rewrite[0] || null,
      publishTask: bucket.publish[0] || null
    }
  }).sort((a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0))
})

const filteredRecords = computed(() => {
  return records.value.filter((record) => {
    if (filters.status && record.status !== filters.status) return false
    if (filters.stage === 'rewrite' && !record.rewriteTask && !['rewriting', 'rewritten', 'failed'].includes(record.status)) return false
    if (filters.stage === 'publish' && !record.publishTask && !['publishing', 'published'].includes(record.status)) return false
    if (filters.keyword && !(record.source_title || '').toLowerCase().includes(filters.keyword.toLowerCase())) return false
    return true
  })
})

const rewrittenCount = computed(() => records.value.filter(item => item.status === 'rewritten').length)
const publishedCount = computed(() => records.value.filter(item => item.status === 'published').length)
const failedCount = computed(() => records.value.filter(item => item.status === 'failed').length)
const activeCount = computed(() => records.value.filter(item => ['rewriting', 'publishing'].includes(item.status)).length)

function statusType(status) {
  return {
    pending: 'warning',
    rewriting: 'primary',
    rewritten: 'success',
    publishing: 'primary',
    published: 'success',
    failed: 'danger'
  }[status] || 'info'
}

function statusLabel(status) {
  return {
    pending: '草稿',
    rewriting: '改写中',
    rewritten: '已改写',
    publishing: '发布中',
    published: '已发布',
    failed: '失败'
  }[status] || status
}

function taskStatusType(status) {
  return {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }[status] || 'info'
}

function taskStatusLabel(status) {
  return {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }[status] || status
}

function rewriteSummary(articleStatus) {
  if (articleStatus === 'rewritten') return '已改写'
  if (articleStatus === 'rewriting') return '改写中'
  if (articleStatus === 'failed') return '失败'
  return '未开始'
}

function publishSummary(articleStatus) {
  if (articleStatus === 'published') return '已发布'
  if (articleStatus === 'publishing') return '发布中'
  return '未发布'
}

function formatTime(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return value
  }
}

async function loadData() {
  loading.value = true
  const params = appStore.selectedAccountId ? { account_id: appStore.selectedAccountId } : undefined
  try {
    await Promise.all([
      articleStore.fetchArticles(params),
      taskStore.fetchTasks(params || {})
    ])
  } finally {
    loading.value = false
    ensureAutoRefresh()
  }
}

function ensureAutoRefresh() {
  const hasActive = records.value.some(item => ['rewriting', 'publishing'].includes(item.status))
  if (hasActive && !refreshTimer.value) {
    refreshTimer.value = setInterval(() => {
      loadData()
    }, 5000)
    return
  }
  if (!hasActive && refreshTimer.value) {
    clearInterval(refreshTimer.value)
    refreshTimer.value = null
  }
}

function openDetail(row) {
  currentRecord.value = row
  detailVisible.value = true
}

function goRewrite(id) {
  router.push({ name: 'Rewrite', query: { id } })
}

function openPublishDialog(id) {
  router.push({ name: 'Articles', query: { publish: id } })
  ElMessage.info('已跳转到我的文章页，请在文章列表完成发布。')
}

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
    refreshTimer.value = null
  }
})

watch(() => appStore.selectedAccountId, () => {
  loadData()
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
  padding: 8px 0;
  border-radius: 12px;
}

.stat-card :deep(.el-card__body) {
  padding: 16px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}

.stat-rewritten .stat-value { color: #10b981; }
.stat-published .stat-value { color: #4f46e5; }
.stat-failed .stat-value { color: #ef4444; }
.stat-active .stat-value { color: #f59e0b; }

.filter-card {
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-group,
.filter-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.record-title {
  font-weight: 600;
  color: #0f172a;
}

.record-subtitle {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.record-time {
  font-size: 12px;
  color: #64748b;
}

.task-brief {
  font-size: 12px;
  line-height: 1.6;
}

.task-time {
  margin-top: 6px;
  color: #64748b;
}

.task-error {
  margin-top: 6px;
  color: #dc2626;
}

.record-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.detail-title {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.detail-meta {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  font-size: 12px;
  color: #64748b;
}

.detail-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.detail-grid {
  margin-top: 4px;
}

.detail-panel {
  height: 100%;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
}

.detail-panel-title {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.detail-line {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 13px;
  color: #334155;
}

.detail-line code {
  font-size: 12px;
  color: #475569;
}

.detail-error {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  font-size: 12px;
  line-height: 1.6;
}

.detail-content-panel {
  padding-bottom: 0;
}

.detail-content {
  max-height: 56vh;
  overflow: auto;
  padding-right: 8px;
  line-height: 1.8;
  color: #1e293b;
}

.detail-content :deep(h2) {
  margin: 24px 0 12px;
  font-size: 24px;
  line-height: 1.35;
}

.detail-content :deep(h3) {
  margin: 18px 0 10px;
  font-size: 18px;
  line-height: 1.45;
}

@media (max-width: 1200px) {
  .detail-header {
    flex-direction: column;
  }
}
</style>
