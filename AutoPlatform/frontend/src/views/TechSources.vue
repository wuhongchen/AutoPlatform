<template>
  <div class="tech-sources-page">
    <!-- 顶部 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">三方技术信息源</h2>
        <p class="page-desc">Discourse · Hacker News · Reddit · Dev.to · GitHub · RSS — 统一采集，输出 Markdown，自动入库素材</p>
      </div>
      <el-button @click="fetchAllSources" type="primary" :loading="fetchingAll">
        <el-icon><Download /></el-icon> 一键采集全部
      </el-button>
    </div>

    <!-- 列表表格 -->
    <el-card shadow="never">
      <el-table :data="flatSources" stripe v-loading="loading" style="width:100%">
        <el-table-column label="平台" width="120">
          <template #default="{ row }">
            <el-tag :type="row.tagType" size="small" effect="plain">{{ row.platform }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="信息源名称" min-width="160">
          <template #default="{ row }">
            <div class="source-name-cell">
              <el-icon :size="16" style="margin-right:6px"><component :is="row.icon" /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="描述" min-width="280">
          <template #default="{ row }">
            <span class="source-desc">{{ row.desc }}</span>
          </template>
        </el-table-column>

        <el-table-column label="来源类型" width="110">
          <template #default="{ row }">
            <span class="source-type-mono">{{ row.sourceType }}</span>
          </template>
        </el-table-column>

        <el-table-column label="上次采集" width="160">
          <template #default="{ row }">
            <span v-if="row.lastFetched" class="fetch-time">{{ row.lastFetched }}</span>
            <span v-else class="fetch-never">尚未采集</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              @click="fetchSource(row)"
              :loading="fetchingId === row.key"
            >
              采集
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 结果提示 -->
    <div v-if="lastResult" class="result-bar">
      <el-alert
        :title="lastResult.message"
        :type="lastResult.error ? 'error' : 'success'"
        closable
        show-icon
        @close="lastResult = null"
      />
      <div v-if="lastResult.total !== undefined" class="result-link">
        本次采集 {{ lastResult.collected ?? lastResult.total }} 篇，
        <router-link to="/inspirations">去素材库查看 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ChatDotSquare, Connection, Link, Collection, TrendCharts, Download,
} from '@element-plus/icons-vue'
import api from '../api'
import { useAppStore } from '../stores'

const appStore = useAppStore()

const loading = ref(false)
const presets = ref({})
const fetchHistory = ref({})
const fetchingId = ref(null)
const fetchingAll = ref(false)
const lastResult = ref(null)

const platformConfig = {
  discourse:  { label: 'Discourse',  icon: ChatDotSquare, tagType: 'success' },
  hackernews: { label: 'Hacker News', icon: TrendCharts,   tagType: 'primary' },
  reddit:     { label: 'Reddit',     icon: Connection,     tagType: 'danger' },
  devto:      { label: 'Dev.to',     icon: Link,           tagType: '' },
  github:     { label: 'GitHub',     icon: Collection,     tagType: 'info' },
  rss:        { label: 'RSS',        icon: Download,       tagType: 'warning' },
}

const flatSources = ref([])

// --- 本地采集历史 ---
const HISTORY_KEY = 'autoplatform:tech_source_fetch_history'

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    fetchHistory.value = raw ? JSON.parse(raw) : {}
  } catch { fetchHistory.value = {} }
}

function saveHistory() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(fetchHistory.value))
}

function recordFetch(sourceType, sourceName) {
  const key = `${sourceType}/${sourceName}`
  const now = new Date()
  fetchHistory.value[key] = now.toISOString()
  saveHistory()
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// --- 构建扁平列表 ---
function buildFlatList() {
  const items = []
  for (const [type, config] of Object.entries(platformConfig)) {
    const sources = presets.value[type] || []
    for (const s of sources) {
      const key = `${type}/${s.name}`
      items.push({
        key,
        platform: config.label,
        icon: config.icon,
        tagType: config.tagType,
        sourceType: type,
        name: s.name,
        desc: s.desc || '',
        config: { ...s },
        lastFetched: formatTime(fetchHistory.value[key]),
      })
    }
  }
  flatSources.value = items
}

async function loadPresets() {
  loading.value = true
  try {
    loadHistory()
    presets.value = await api.techSources.listPresets()
    buildFlatList()
  } catch (e) {
    ElMessage.error('加载预置信息源失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function fetchSource(row) {
  fetchingId.value = row.key
  lastResult.value = null
  try {
    const result = await api.techSources.fetch({
      source_type: row.sourceType,
      config: row.config,
      account_id: appStore.selectedAccountId || 'default',
      limit: 20,
    })
    if (result.task_id) {
      const task = await pollTask(result.task_id)
      const collected = task.result?.collected ?? 0
      const total = task.result?.total ?? 0
      lastResult.value = {
        message: task.status === 'completed'
          ? `「${row.name}」采集完成，新增 ${collected} 篇`
          : `「${row.name}」采集失败: ${task.error_message || task.status}`,
        total: collected,
        collected,
        error: task.status !== 'completed',
      }
      if (task.status === 'completed') {
        recordFetch(row.sourceType, row.name)
        buildFlatList()
      }
    }
  } catch (e) {
    ElMessage.error(`采集失败: ${e.message}`)
  } finally {
    fetchingId.value = null
  }
}

async function fetchAllSources() {
  fetchingAll.value = true
  lastResult.value = null
  try {
    const result = await api.techSources.fetchAll({
      account_id: appStore.selectedAccountId || 'default',
      limit: 10,
    })
    if (result.task_id) {
      const task = await pollTask(result.task_id)
      const total = task.result?.total_collected ?? 0
      lastResult.value = {
        message: task.status === 'completed'
          ? `一键采集完成，共导入 ${total} 篇新素材`
          : `全量采集失败: ${task.error_message || task.status}`,
        total,
        collected: total,
        error: task.status !== 'completed',
      }
      if (task.status === 'completed') {
        const now = new Date().toISOString()
        for (const item of flatSources.value) {
          fetchHistory.value[item.key] = now
        }
        saveHistory()
        buildFlatList()
      }
    }
  } catch (e) {
    ElMessage.error('全量采集失败: ' + e.message)
  } finally {
    fetchingAll.value = false
  }
}

async function pollTask(taskId, maxAttempts = 60) {
  for (let i = 0; i < maxAttempts; i++) {
    const task = await api.tasks.get(taskId)
    if (task.status === 'completed' || task.status === 'failed') return task
    await new Promise(r => setTimeout(r, 2000))
  }
  throw new Error('任务超时')
}

onMounted(() => { loadPresets() })
</script>

<style scoped>
.tech-sources-page { padding: 0; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.page-title { margin: 0; font-size: 20px; font-weight: 700; }
.page-desc { margin: 4px 0 0; color: #999; font-size: 13px; }

.source-name-cell { display: flex; align-items: center; font-weight: 500; }
.source-desc { color: #666; font-size: 13px; line-height: 1.5; }
.source-type-mono { font-family: monospace; color: #888; font-size: 12px; }

.fetch-time { color: #67c23a; font-size: 12px; }
.fetch-never { color: #c0c4cc; font-size: 12px; }

.result-bar { margin-top: 16px; }
.result-link { margin-top: 8px; color: #666; font-size: 13px; }
</style>
