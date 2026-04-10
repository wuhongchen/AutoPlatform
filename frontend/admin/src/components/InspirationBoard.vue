<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { dashboardApi } from '../lib/api'

const props = defineProps({
  activeAccount: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['refresh'])

const busy = ref(false)
const message = ref('')
const errorMessage = ref('')
const deletingId = ref('')
const retryingId = ref('')
const rewritingId = ref('')
const publishingId = ref('')
const addModalOpen = ref(false)
const addUrlsText = ref('')
const addDefaultStatus = ref('待采集')

// 操作弹窗
const actionModalOpen = ref(false)
const actionItem = ref(null)
const actionType = ref('') // 'rewrite' | 'publish'
const actionLoading = ref(false)
const actionResult = ref(null)

// 预览弹窗
const previewModalOpen = ref(false)
const previewItem = ref(null)
const previewType = ref('original') // 'original' | 'rewritten'
const previewUrl = ref('')
const previewLoading = ref(false)

const inspirationList = ref([])
const inspirationMeta = ref(null)

const statusFilter = ref('all')
const keywordFilter = ref('')

const activeAccount = computed(() => props.activeAccount || {})
const accountId = computed(() => activeAccount.value?.id || '')

const statusOptions = computed(() => {
  const map = new Map()
  for (const row of inspirationList.value || []) {
    const st = String(row.status || '').trim() || '未标记'
    map.set(st, (map.get(st) || 0) + 1)
  }
  return Array.from(map.entries()).map(([value, count]) => ({ value, count }))
})



// 状态分组选项（与后端 article_state.py 一致）
const STATE_GROUPS = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '📥 待处理' },
  { value: 'processing', label: '📡 处理中' },
  { value: 'completed', label: '✅ 已完成' },
  { value: 'failed', label: '❌ 失败' },
  { value: 'skipped', label: '⏭️ 已跳过' },
]

// 获取状态样式（与后端 STATE_STYLES 一致）
function getStateStyle(status) {
  const stateMap = {
    '待采集': { badge: 'info', icon: '📥' },
    '采集中': { badge: 'progress', icon: '📡' },
    '采集失败': { badge: 'danger', icon: '❌' },
    '采集完成': { badge: 'info', icon: '📄' },
    '待改写': { badge: 'waiting', icon: '📝' },
    '改写中': { badge: 'progress', icon: '✍️' },
    '改写失败': { badge: 'danger', icon: '❌' },
    '已改写': { badge: 'success', icon: '✨' },
    '待发布': { badge: 'waiting', icon: '🚀' },
    '发布中': { badge: 'progress', icon: '📤' },
    '发布失败': { badge: 'danger', icon: '❌' },
    '已发布': { badge: 'success', icon: '✅' },
    '已跳过': { badge: 'muted', icon: '⏭️' },
  }
  return stateMap[status] || { badge: 'default', icon: '•' }
}

// 获取状态分组（与后端 STATE_GROUPS 一致）
function getStateGroup(status) {
  const pending = ['待采集', '采集完成', '待改写']
  const processing = ['采集中', '改写中', '发布中']
  const completed = ['已改写', '已发布']
  const failed = ['采集失败', '改写失败', '发布失败']

  if (pending.includes(status)) return 'pending'
  if (processing.includes(status)) return 'processing'
  if (completed.includes(status)) return 'completed'
  if (failed.includes(status)) return 'failed'
  if (status === '已跳过') return 'skipped'
  return 'other'
}

const displayedInspiration = computed(() => {
  const kw = String(keywordFilter.value || '').trim().toLowerCase()
  const st = String(statusFilter.value || 'all').trim()
  return (inspirationList.value || []).filter((row) => {
    const rowStatus = String(row.status || '').trim() || '待采集'
    // 按分组筛选
    if (st !== 'all') {
      const group = getStateGroup(rowStatus)
      if (group !== st) return false
    }
    if (!kw) return true
    const hit = [row.title, row.url, row.record_id, row.remark, row.captured_at, row.status]
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

// 按钮显示逻辑
function canCapture(item) {
  const status = normalizedStatus(item.status)
  // 待采集、采集失败时可以触发采集
  return ['待采集', '采集失败', ''].includes(status) || !status
}

function canRewrite(item) {
  const status = normalizedStatus(item.status)
  // 待改写、已改写、改写失败都可以触发改写
  return ['待改写', '已改写', '改写失败', '采集完成'].includes(status)
}

function canPublish(item) {
  const status = normalizedStatus(item.status)
  // 已改写或已发布可以再次发布
  return ['已改写', '已发布'].includes(status)
}

function canRetry(item) {
  const status = normalizedStatus(item.status)
  // 失败或已跳过可以重试
  return status.includes('失败') || status === '已跳过'
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

async function reloadInspiration() {
  if (!accountId.value) return
  const data = await dashboardApi.inspirationList({
    accountId: accountId.value,
    status: '',
    keyword: '',
    limit: 500,
  })
  inspirationList.value = data.items || []
  inspirationMeta.value = data.meta || null
}

async function handleDelete(item) {
  if (!confirm(`确定要删除文章：${item.title || item.record_id}？删除后无法恢复。`)) {
    return
  }
  await withBusy(async () => {
    deletingId.value = item.record_id
    await dashboardApi.inspirationDelete({
      accountId: accountId.value,
      recordId: item.record_id,
    })
    setInfo(`删除成功：${item.title || item.record_id}`)
    await reloadInspiration()
    deletingId.value = ''
  })
}

async function handleRetry(item) {
  if (!confirm(`确定要重试分析文章：${item.title || item.record_id}？会重新抓取并分析内容。`)) {
    return
  }
  await withBusy(async () => {
    retryingId.value = item.record_id
    await dashboardApi.inspirationRetry({
      accountId: accountId.value,
      recordId: item.record_id,
    })
    setInfo(`已提交重试任务，稍后刷新列表查看结果`)
    await reloadInspiration()
    retryingId.value = ''
  })
}

// 采集文章
async function handleCapture(item) {
  if (!confirm(`确定要采集文章：${item.title || item.record_id}？`)) {
    return
  }
  await withBusy(async () => {
    const data = await dashboardApi.inspirationCapture({
      accountId: accountId.value,
      recordId: item.record_id,
    })
    setInfo(`采集任务已提交: ${data.message || '请查看任务进度'}`)
    await reloadInspiration()
  })
}

// 打开 AI 改写弹窗
function openRewriteModal(item) {
  actionItem.value = item
  actionType.value = 'rewrite'
  actionResult.value = null
  actionModalOpen.value = true
}

// 打开发布弹窗
function openPublishModal(item) {
  actionItem.value = item
  actionType.value = 'publish'
  actionResult.value = null
  actionModalOpen.value = true
}

// 打开预览弹窗
function openPreviewModal(item, type = 'original') {
  previewItem.value = item
  previewType.value = type
  previewModalOpen.value = true
  previewLoading.value = true

  // 构建预览 URL
  const url = `/api/articles/${item.record_id}/preview-wechat?account_id=${encodeURIComponent(accountId.value)}&type=${type}`
  previewUrl.value = url

  // 模拟加载完成
  setTimeout(() => {
    previewLoading.value = false
  }, 500)
}

// 关闭预览弹窗
function closePreviewModal() {
  previewModalOpen.value = false
  previewItem.value = null
  previewUrl.value = ''
}

// 执行 AI 改写
async function executeRewrite() {
  if (!actionItem.value) return
  actionLoading.value = true
  errorMessage.value = ''
  try {
    // 使用灵感库专用改写API
    const data = await dashboardApi.inspirationRewrite({
      accountId: accountId.value,
      recordId: actionItem.value.record_id,
      role: 'tech_expert',
      model: 'auto',
    })
    actionResult.value = { ok: true, message: 'AI 改写任务已提交', jobId: data?.job_id }
    setInfo(`AI 改写任务已提交: ${actionItem.value.title || actionItem.value.record_id}`)
    // 立即刷新列表
    await reloadInspiration()
    emit('refresh')
  } catch (err) {
    setError(err)
    actionResult.value = { ok: false, message: err?.message || '改写失败' }
  } finally {
    actionLoading.value = false
  }
}

// 执行发布
async function executePublish() {
  if (!actionItem.value) return
  actionLoading.value = true
  errorMessage.value = ''
  try {
    const data = await dashboardApi.publishDraft({
      account_id: accountId.value,
      record_id: actionItem.value.record_id,
      title: actionItem.value.title,
    })
    actionResult.value = { ok: true, message: '发布任务已提交', jobId: data?.job_id }
    setInfo(`发布任务已提交: ${actionItem.value.title || actionItem.value.record_id}`)
    // 立即刷新列表
    await reloadInspiration()
    emit('refresh')
  } catch (err) {
    setError(err)
    actionResult.value = { ok: false, message: err?.message || '发布失败' }
  } finally {
    actionLoading.value = false
  }
}

function closeActionModal() {
  actionModalOpen.value = false
  actionItem.value = null
  actionResult.value = null
}

async function handleAddSubmit() {
  if (!addUrlsText.value.trim()) {
    setError('请输入文章链接')
    return
  }
  await withBusy(async () => {
    await dashboardApi.inspirationAdd({
      accountId: accountId.value,
      urls: addUrlsText.value,
      defaultStatus: addDefaultStatus.value,
    })
    setInfo('添加成功，列表已刷新')
    addUrlsText.value = ''
    addModalOpen.value = false
    await reloadInspiration()
  })
}

async function handleCaptureAll() {
  await withBusy(async () => {
    await dashboardApi.inspirationScanCapture({
      accountId: accountId.value,
    })
    setInfo(`已开始全局灵感库抓取，请到「最近任务」或「追踪中心」查看进度`)
  })
}

async function bootstrap() {
  await withBusy(async () => {
    await reloadInspiration()
    setInfo('灵感库已刷新：当前展示本地数据库中的数据。')
  })
}

onMounted(() => {
  bootstrap()
})

watch(
  () => accountId.value,
  () => {
    inspirationList.value = []
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
        <p>本地数据库存储，支持筛选、AI改写、发布、删除等独立操作。</p>
      </div>
      <div class="page-actions">
        <button class="primary-btn" :disabled="busy" @click="addModalOpen = true">+ 添加文章</button>
        <button class="ghost-btn" :disabled="busy" @click="handleCaptureAll">灵感抓取</button>
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
          <strong>{{ inspirationList.length }}</strong>
        </div>

      </div>
    </div>

    <div class="panel-card">
      <div class="publish-filter-row">
        <label>
          处理状态
          <select v-model="statusFilter">
            <option value="all">全部</option>
            <option v-for="item in STATE_GROUPS" :key="item.value" :value="item.value">{{ item.label }}</option>
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
              <th>原文链接</th>
              <th>抓取时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in displayedInspiration" :key="item.record_id">
              <td>
                <code class="inspiration-record-id">{{ item.record_id || '-' }}</code>
              </td>
              <td>
                <div class="inspiration-title-cell">{{ item.title || '未命名标题' }}</div>
                <div v-if="item.remark" class="inspiration-remark-small">{{ item.remark.slice(0, 50) }}{{ item.remark.length > 50 ? '...' : '' }}</div>
              </td>
              <td>
                <span class="badge inspiration-status-badge" :class="getStateStyle(item.status).badge">
                {{ getStateStyle(item.status).icon }} {{ item.status || '待采集' }}
              </span>
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
                <span class="inspiration-time-cell">{{ item.captured_at || '-' }}</span>
              </td>
              <td>
                <div class="inspiration-actions">
                  <!-- 采集按钮：待采集、采集失败时显示（蓝色主按钮）-->
                  <button
                    v-if="canCapture(item)"
                    class="action-btn action-btn-primary"
                    :disabled="busy"
                    @click="handleCapture(item)"
                    title="采集文章"
                  >
                    📥 采集
                  </button>
                  <!-- 改写按钮：待改写、已改写、改写失败、采集完成时显示（紫色次按钮）-->
                  <button
                    v-if="canRewrite(item)"
                    class="action-btn action-btn-purple"
                    :disabled="busy"
                    @click="openRewriteModal(item)"
                    title="AI改写"
                  >
                    🤖 改写
                  </button>
                  <!-- 预览按钮：始终显示 -->
                  <button
                    class="action-btn action-btn-info"
                    :disabled="busy"
                    @click="openPreviewModal(item, 'original')"
                    title="预览原文"
                  >
                    👁️ 预览
                  </button>
                  <!-- 发布按钮：已改写或已发布时显示 -->
                  <button
                    v-if="canPublish(item)"
                    class="action-btn action-btn-success"
                    :disabled="busy"
                    @click="openPublishModal(item)"
                    title="发布到微信"
                  >
                    📤 发布
                  </button>
                  <!-- 重试按钮：失败或已跳过时显示 -->
                  <button
                    v-if="canRetry(item)"
                    class="action-btn action-btn-warn"
                    :disabled="busy && retryingId === item.record_id"
                    @click="handleRetry(item)"
                  >
                    {{ (busy && retryingId === item.record_id) ? '重试中...' : '重试' }}
                  </button>
                  <!-- 删除按钮：始终显示 -->
                  <button
                    class="action-btn action-btn-danger"
                    :disabled="busy && deletingId === item.record_id"
                    @click="handleDelete(item)"
                  >
                    {{ (busy && deletingId === item.record_id) ? '删除中...' : '删除' }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!displayedInspiration.length">
              <td colspan="6">
                <div class="empty-block">当前账户暂无灵感记录，或筛选条件下没有数据。</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 添加文章弹窗 -->
    <div v-if="addModalOpen" class="modal-mask" @click.self="addModalOpen = false">
      <div class="modal-card modal-detail-card">
        <div class="modal-detail-header">
          <h3>添加文章到灵感库</h3>
          <button class="close-btn" @click="addModalOpen = false">✕</button>
        </div>
        <div class="form-grid-1">
          <div class="form-row">
            <label>文章链接（每行一个）</label>
            <textarea
              v-model="addUrlsText"
              placeholder="格式：&#10;https://mp.weixin.qq.com/s/xxxxxxx&#10;文章标题 https://mp.weixin.qq.com/s/xxxxxxx"
              rows="8"
            ></textarea>
          </div>
          <div class="form-row">
            <label>默认状态</label>
            <select v-model="addDefaultStatus">
              <option value="待采集">📥 待采集 (刚添加，等待采集)</option>
              <option value="待改写">📝 待改写 (跳过采集，直接改写)</option>
              <option value="已改写">✨ 已改写 (跳过流程，标记完成)</option>
              <option value="已跳过">⏭️ 已跳过 (低质量内容)</option>
            </select>
          </div>
        </div>
        <div class="modal-footer" style="margin-top: 16px; text-align: right;">
          <button class="ghost-btn" style="margin-right: 8px;" @click="addModalOpen = false">取消</button>
          <button class="primary-btn" :disabled="busy" @click="handleAddSubmit">{{ busy ? '添加中...' : '确认添加' }}</button>
        </div>
      </div>
    </div>

    <!-- AI改写/发布 操作弹窗 -->
    <div v-if="actionModalOpen" class="modal-mask" @click.self="closeActionModal">
      <div class="modal-card modal-detail-card">
        <div class="modal-detail-header">
          <h3>{{ actionType === 'rewrite' ? '🤖 AI 改写' : '📤 发布到微信' }}</h3>
          <button class="close-btn" @click="closeActionModal">✕</button>
        </div>
        <div v-if="actionItem" class="form-grid-1">
          <div class="form-row">
            <label>文章标题</label>
            <div style="padding: 10px; background: rgba(245,249,255,0.96); border-radius: 10px; font-weight: 600;">
              {{ actionItem.title || '未命名标题' }}
            </div>
          </div>
          <div class="form-row">
            <label>来源链接</label>
            <a :href="actionItem.url" target="_blank" rel="noreferrer" style="word-break: break-all; color: var(--brand);">
              {{ actionItem.url }}
            </a>
          </div>
          <div v-if="actionResult" class="form-row">
            <label>执行结果</label>
            <div :class="actionResult.ok ? 'global-info' : 'global-error'" style="margin: 0;">
              {{ actionResult.message }}
              <div v-if="actionResult.jobId" style="margin-top: 8px; font-size: 12px; color: var(--text-soft);">
                任务ID: {{ actionResult.jobId }}
              </div>
              <div v-if="actionResult.draftId" style="margin-top: 8px; font-size: 12px; color: var(--text-soft);">
                草稿ID: {{ actionResult.draftId }}
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer" style="margin-top: 16px; display: flex; gap: 10px; justify-content: flex-end;">
          <button class="ghost-btn" @click="closeActionModal">关闭</button>
          <button
            v-if="!actionResult"
            class="primary-btn"
            :disabled="actionLoading"
            @click="actionType === 'rewrite' ? executeRewrite() : executePublish()"
          >
            {{ actionLoading ? '执行中...' : (actionType === 'rewrite' ? '开始改写' : '确认发布') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 公众号预览弹窗 -->
    <div v-if="previewModalOpen" class="modal-mask preview-modal-mask" @click.self="closePreviewModal">
      <div class="modal-card preview-modal-card">
        <div class="modal-detail-header preview-header">
          <div class="preview-title-section">
            <h3>👁️ 公众号预览</h3>
            <span class="preview-badge">{{ previewType === 'rewritten' ? '改写后' : '原文' }}</span>
          </div>
          <button class="close-btn" @click="closePreviewModal">✕</button>
        </div>
        <div class="preview-content-wrapper">
          <div v-if="previewLoading" class="preview-loading">
            <div class="loading-spinner"></div>
            <p>正在加载预览内容...</p>
          </div>
          <iframe
            v-else
            :src="previewUrl"
            class="preview-iframe"
            sandbox="allow-same-origin allow-scripts"
            frameborder="0"
          ></iframe>
        </div>
        <div class="modal-footer preview-footer">
          <div class="preview-actions">
            <button
              class="ghost-btn"
              :class="{ 'active': previewType === 'original' }"
              @click="openPreviewModal(previewItem, 'original')"
            >
              原文
            </button>
            <button
              class="ghost-btn"
              :class="{ 'active': previewType === 'rewritten' }"
              @click="openPreviewModal(previewItem, 'rewritten')"
            >
              改写后
            </button>
          </div>
          <button class="primary-btn" @click="closePreviewModal">关闭</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.preview-modal-mask {
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-modal-card {
  width: 90vw;
  max-width: 900px;
  height: 85vh;
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--line);
  padding: 16px 20px;
}

.preview-title-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.preview-title-section h3 {
  margin: 0;
  font-size: 18px;
}

.preview-badge {
  display: inline-block;
  padding: 2px 10px;
  background: #07c160;
  color: white;
  font-size: 12px;
  border-radius: 3px;
  font-weight: 500;
}

.preview-content-wrapper {
  flex: 1;
  overflow: hidden;
  background: #f5f5f5;
  position: relative;
}

.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-soft);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e0e0e0;
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.preview-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-top: 1px solid var(--line);
  gap: 12px;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.preview-actions .ghost-btn.active {
  background: var(--brand);
  color: white;
  border-color: var(--brand);
}
</style>
