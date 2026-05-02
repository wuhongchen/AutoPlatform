<template>
  <div class="tasks-page">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-pending">
          <div class="stat-value">{{ taskStore.pendingCount }}</div>
          <div class="stat-label">执行中 / 待执行</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-completed">
          <div class="stat-value">{{ taskStore.completedCount }}</div>
          <div class="stat-label">已完成</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-failed">
          <div class="stat-value">{{ taskStore.failedCount }}</div>
          <div class="stat-label">失败</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-total">
          <div class="stat-value">{{ taskStore.tasks.length }}</div>
          <div class="stat-label">当前列表</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 140px">
            <el-option label="待执行" value="pending" />
            <el-option label="执行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="filters.name" placeholder="全部类型" clearable style="width: 140px">
            <el-option label="采集" value="collect" />
            <el-option label="改写" value="rewrite" />
            <el-option label="发布" value="publish" />
            <el-option label="批量处理" value="batch" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTasks" :loading="taskStore.loading">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
          <el-button @click="clearFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务列表 -->
    <el-card shadow="never" class="table-card">
      <el-table
        :data="taskStore.tasks"
        v-loading="taskStore.loading"
        stripe
        style="width: 100%"
        @row-click="showDetail"
      >
        <el-table-column prop="name" label="任务类型" width="120">
          <template #default="{ row }">
            <el-tag :type="taskTypeColor(row.name)" size="small">
              {{ taskTypeLabel(row.name) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusColor(row.status)" size="small" effect="dark">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="目标" min-width="200">
          <template #default="{ row }">
            <div class="task-target">
              <div v-if="row.target_id" class="target-id">ID: {{ row.target_id }}</div>
              <div v-else-if="row.payload?.article_id" class="target-id">文章: {{ row.payload.article_id }}</div>
              <div v-else-if="row.payload?.url" class="target-url">{{ row.payload.url }}</div>
              <div v-else class="text-gray">-</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="account_id" label="账户" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.account_id" size="small" type="info">{{ row.account_id }}</el-tag>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column label="时间" width="180">
          <template #default="{ row }">
            <div class="time-info">
              <div>{{ formatTime(row.created_at) }}</div>
              <div v-if="row.completed_at" class="time-completed">
                完成: {{ formatTime(row.completed_at) }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status !== 'running'"
              type="danger"
              link
              size="small"
              @click.stop="removeTask(row.id)"
            >
              删除
            </el-button>
            <el-button v-else type="info" link size="small" disabled>执行中</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!taskStore.loading && taskStore.tasks.length === 0" description="暂无任务" />
    </el-card>

    <!-- 任务详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="任务详情"
      width="560px"
      destroy-on-close
    >
      <div v-if="currentTask" class="task-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="任务ID">{{ currentTask.id }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag :type="taskTypeColor(currentTask.name)">
              {{ taskTypeLabel(currentTask.name) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusColor(currentTask.status)" effect="dark">
              {{ statusLabel(currentTask.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="账户">{{ currentTask.account_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="目标">{{ currentTask.target_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(currentTask.created_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentTask.started_at" label="开始时间">
            {{ formatTime(currentTask.started_at) }}
          </el-descriptions-item>
          <el-descriptions-item v-if="currentTask.completed_at" label="完成时间">
            {{ formatTime(currentTask.completed_at) }}
          </el-descriptions-item>
          <el-descriptions-item v-if="currentTask.retry_count > 0" label="重试次数">
            {{ currentTask.retry_count }} / {{ currentTask.max_retries }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="currentTask.error_message" class="error-block">
          <div class="error-title">错误信息</div>
          <div class="error-content">{{ currentTask.error_message }}</div>
        </div>

        <div v-if="Object.keys(currentTask.result || {}).length > 0" class="result-block">
          <div class="result-title">执行结果</div>
          <pre class="result-content">{{ JSON.stringify(currentTask.result, null, 2) }}</pre>
        </div>

        <div class="result-title" style="margin-top: 12px;">参数</div>
        <pre class="result-content">{{ JSON.stringify(currentTask.payload, null, 2) }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore, useTaskStore } from '../stores'

const appStore = useAppStore()
const taskStore = useTaskStore()

const filters = reactive({
  status: '',
  name: '',
})

const detailVisible = ref(false)
const currentTask = ref(null)
const autoRefreshTimer = ref(null)

function loadTasks() {
  const params = {}
  if (appStore.selectedAccountId) params.account_id = appStore.selectedAccountId
  if (filters.status) params.status = filters.status
  if (filters.name) params.name = filters.name
  taskStore.fetchTasks(params)
}

function clearFilters() {
  filters.status = ''
  filters.name = ''
  loadTasks()
}

async function showDetail(row) {
  currentTask.value = row
  detailVisible.value = true
}

async function removeTask(id) {
  try {
    await ElMessageBox.confirm('确定删除这个任务？', '确认删除', { type: 'warning' })
    await taskStore.deleteTask(id)
    ElMessage.success('删除成功')
    loadTasks()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '删除失败')
    }
  }
}

function statusColor(status) {
  const map = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[status] || 'info'
}

function statusLabel(status) {
  const map = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[status] || status
}

function taskTypeColor(name) {
  const map = {
    collect: 'primary',
    rewrite: 'warning',
    publish: 'success',
    batch: 'danger',
  }
  return map[name] || 'info'
}

function taskTypeLabel(name) {
  const map = {
    collect: '采集',
    rewrite: '改写',
    publish: '发布',
    batch: '批量处理',
  }
  return map[name] || name
}

function formatTime(iso) {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return iso
  }
}

// 自动刷新
function startAutoRefresh() {
  if (autoRefreshTimer.value) return
  autoRefreshTimer.value = setInterval(() => {
    loadTasks()
  }, 3000)
}

function stopAutoRefresh() {
  if (autoRefreshTimer.value) {
    clearInterval(autoRefreshTimer.value)
    autoRefreshTimer.value = null
  }
}

onMounted(() => {
  loadTasks()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})

watch(() => filters.status, () => loadTasks())
watch(() => filters.name, () => loadTasks())
watch(() => appStore.selectedAccountId, () => loadTasks())
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

.stat-pending .stat-value { color: #f59e0b; }
.stat-completed .stat-value { color: #10b981; }
.stat-failed .stat-value { color: #ef4444; }
.stat-total .stat-value { color: #6366f1; }

.filter-card {
  margin-bottom: 16px;
}

.filter-card :deep(.el-card__body) {
  padding: 16px 20px;
}

.table-card :deep(.el-card__body) {
  padding: 0;
}

.task-target {
  font-size: 13px;
}

.target-id {
  color: #1e293b;
  font-weight: 500;
}

.target-url {
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.time-info {
  font-size: 12px;
  color: #64748b;
}

.time-completed {
  color: #10b981;
  margin-top: 2px;
}

.text-gray {
  color: #94a3b8;
}

.task-detail {
  max-height: 60vh;
  overflow-y: auto;
}

.error-block {
  margin-top: 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 12px;
}

.error-title {
  font-size: 13px;
  font-weight: 600;
  color: #dc2626;
  margin-bottom: 8px;
}

.error-content {
  font-size: 12px;
  color: #7f1d1d;
  word-break: break-all;
  white-space: pre-wrap;
}

.result-block {
  margin-top: 16px;
}

.result-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.result-content {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  color: #475569;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
