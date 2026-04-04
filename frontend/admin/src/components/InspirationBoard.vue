<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { dashboardApi } from '../lib/api'

const props = defineProps({
  activeAccount: { type: Object, default: () => ({}) },
})

const busy = ref(false)
const message = ref('')
const errorMessage = ref('')

const feishuInspiration = ref([])
const inspirationMeta = ref(null)

const statusFilter = ref('all')
const keywordFilter = ref('')

const activeAccount = computed(() => props.activeAccount || {})
const accountId = computed(() => activeAccount.value?.id || '')

const statusOptions = computed(() => {
  const map = new Map()
  for (const row of feishuInspiration.value || []) {
    const st = String(row.status || '').trim() || '未标记'
    map.set(st, (map.get(st) || 0) + 1)
  }
  return Array.from(map.entries()).map(([value, count]) => ({ value, count }))
})

const withDocCount = computed(() => {
  return (feishuInspiration.value || []).filter((x) => validHttpUrl(x.doc_url)).length
})

const displayedInspiration = computed(() => {
  const kw = String(keywordFilter.value || '').trim().toLowerCase()
  const st = String(statusFilter.value || 'all').trim()
  return (feishuInspiration.value || []).filter((row) => {
    if (st !== 'all' && (String(row.status || '').trim() || '未标记') !== st) return false
    if (!kw) return true
    const hit = [row.title, row.url, row.doc_url, row.record_id, row.remark, row.captured_at, row.status]
      .map((x) => String(x || '').toLowerCase())
      .join(' ')
    return hit.includes(kw)
  })
})

function validHttpUrl(url) {
  return /^https?:\/\//.test(String(url || '').trim())
}

function normalizedStatus(status) {
  return String(status || '').trim() || '未标记'
}

function statusBadgeClass(status) {
  const text = normalizedStatus(status)
  if (text.includes('失败') || text.includes('异常')) return 'bad'
  if (text.includes('已处理') || text.includes('已发布') || text.includes('完成')) return 'ok'
  if (text.includes('已跳过')) return 'warn'
  if (text.includes('待分析') || text.includes('待处理')) return 'info'
  return 'plain'
}

function setInfo(text) {
  message.value = text || ''
  errorMessage.value = ''
}

function setError(err) {
  errorMessage.value = err?.message || String(err || '操作失败')
}

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

async function reloadFeishuInspiration() {
  if (!accountId.value) return
  const data = await dashboardApi.inspirationList({
    accountId: accountId.value,
    status: '',
    keyword: '',
    limit: 500,
  })
  feishuInspiration.value = data.items || []
  inspirationMeta.value = data.meta || null
}

async function bootstrap() {
  await withBusy(async () => {
    await reloadFeishuInspiration()
    setInfo('灵感库已刷新：当前展示飞书多维表格中的主数据。')
  })
}

onMounted(() => {
  bootstrap()
})

watch(
  () => accountId.value,
  () => {
    feishuInspiration.value = []
    statusFilter.value = 'all'
    keywordFilter.value = ''
    bootstrap()
  }
)
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>灵感库</h1>
        <p>以飞书多维表格为主数据源，仅负责灵感内容展示与筛选。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" :disabled="busy" @click="bootstrap">刷新列表</button>
      </div>
    </div>

    <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
    <div v-if="message" class="global-info">{{ message }}</div>

    <div class="panel-card panel-soft">
      <div class="inspiration-status-bar">
        <div class="status-chip-block">
          <span class="status-label">当前账户</span>
          <strong>{{ activeAccount?.name || activeAccount?.id || '-' }}</strong>
        </div>
        <div class="status-chip-block">
          <span class="status-label">灵感总数</span>
          <strong>{{ feishuInspiration.length }}</strong>
        </div>
        <div class="status-chip-block">
          <span class="status-label">含原文文档</span>
          <strong>{{ withDocCount }}</strong>
        </div>
        <div class="status-chip-block">
          <span class="status-label">来源表</span>
          <strong>{{ inspirationMeta?.table_name || '-' }}</strong>
        </div>
      </div>
    </div>

    <div class="panel-card">
      <div class="publish-filter-row">
        <label>
          处理状态
          <select v-model="statusFilter">
            <option value="all">全部</option>
            <option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.value }}（{{ item.count }}）</option>
          </select>
        </label>
        <label>
          关键词
          <input v-model="keywordFilter" type="text" placeholder="标题 / URL / 记录ID / 抓取时间" />
        </label>
      </div>

      <div class="inspiration-table-wrap">
        <table class="inspiration-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>标题</th>
              <th>状态</th>
              <th>原文档链接</th>
              <th>飞书文档链接</th>
              <th>抓取时间</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in displayedInspiration" :key="item.record_id">
              <td>
                <code class="inspiration-record-id">{{ item.record_id || '-' }}</code>
              </td>
              <td>
                <div class="inspiration-title-cell">{{ item.title || '未命名标题' }}</div>
              </td>
              <td>
                <span class="badge inspiration-status-badge" :class="statusBadgeClass(item.status)">{{ normalizedStatus(item.status) }}</span>
              </td>
              <td>
                <a
                  v-if="validHttpUrl(item.url)"
                  class="inspiration-table-link url"
                  :href="item.url"
                  target="_blank"
                  rel="noreferrer"
                >
                  打开原文
                </a>
                <span v-else class="table-empty-cell">-</span>
              </td>
              <td>
                <a
                  v-if="validHttpUrl(item.doc_url)"
                  class="inspiration-table-link doc"
                  :href="item.doc_url"
                  target="_blank"
                  rel="noreferrer"
                >
                  打开飞书文档
                </a>
                <span v-else class="table-empty-cell">-</span>
              </td>
              <td>
                <span class="inspiration-time-cell">{{ item.captured_at || '-' }}</span>
              </td>
              <td>
                <span class="inspiration-remark-cell">{{ item.remark || '-' }}</span>
              </td>
            </tr>
            <tr v-if="!displayedInspiration.length">
              <td colspan="7">
                <div class="empty-block">当前账户暂无灵感记录，或筛选条件下没有数据。</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
