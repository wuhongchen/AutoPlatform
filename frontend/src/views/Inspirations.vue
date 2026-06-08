<template>
  <div class="inspirations-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="toolbar-left">
            <el-input
              v-model="searchQuery"
              placeholder="搜索素材..."
              :prefix-icon="Search"
              style="width: 260px"
              clearable
            />
            <el-select v-model="scoreFilter" placeholder="评分筛选" clearable style="width: 130px" size="default">
              <el-option label="⭐ 高分 (80+)" :value="80" />
              <el-option label="👍 中上 (60+)" :value="60" />
              <el-option label="📋 未评分" value="unrated" />
            </el-select>
          </div>
          <div class="toolbar-right">
            <el-button @click="scoreUnrated" :loading="scoring" :disabled="!hasUnrated">
              <el-icon><MagicStick /></el-icon>AI 评分
            </el-button>
            <el-button type="primary" @click="openCollectDialog">
              <el-icon><Plus /></el-icon>采集素材
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredInspirations" v-loading="loading" stripe>
        <el-table-column label="标题" min-width="250">
          <template #default="{ row }">
            <div class="inspiration-title">{{ row.title || '无标题' }}</div>
            <div class="inspiration-tags">
              <el-tag v-if="row.source_type === 'wechat_login_state'" size="small" type="success">公众号雷达</el-tag>
              <el-tag v-if="row.source_type === 'rss'" size="small" type="warning">RSS</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="来源" width="120" prop="source_account" />
        <el-table-column label="评分" width="90" sortable prop="ai_score">
          <template #default="{ row }">
            <span v-if="row.ai_score != null" :class="scoreClass(row.ai_score)" class="score-badge">
              {{ row.ai_score }}
            </span>
            <span v-else class="score-none">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === '已采集' ? 'success' : 'warning'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="采集时间" width="160">
          <template #default="{ row }">{{ formatDate(row.collected_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="340" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" type="primary" @click="createArticle(row.id)">改写</el-button>
              <el-button size="small" @click="viewDetail(row)">查看</el-button>
              <el-button size="small" @click="openOriginal(row.source_url)">原文</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showCollectDialog" title="采集素材" width="500px">
      <el-form :model="collectForm" label-width="100px">
        <el-form-item label="文章链接">
          <el-input v-model="collectForm.url" placeholder="输入微信公众号文章链接..." />
        </el-form-item>
        <el-form-item label="账户">
          <el-select v-model="collectForm.account_id" style="width: 100%">
            <el-option v-for="acc in accountStore.accounts" :key="acc.account_id" :label="acc.name" :value="acc.account_id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCollectDialog = false">取消</el-button>
        <el-button type="primary" @click="collect" :loading="collecting">开始采集</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDetailDialog" title="素材详情" width="920px">
      <div v-if="selectedInspiration" class="detail-layout">
        <div class="detail-meta-panel">
          <div class="detail-meta-eyebrow">文章阅读预览</div>
          <h3 class="detail-title">{{ selectedInspiration.title }}</h3>
          <div class="detail-meta-row">
            <div class="detail-meta-item"><span class="detail-meta-label">来源</span><span class="detail-meta-value">{{ selectedInspiration.source_account || '未标注' }}</span></div>
            <div class="detail-meta-item"><span class="detail-meta-label">作者</span><span class="detail-meta-value">{{ selectedInspiration.author || '未知作者' }}</span></div>
            <div class="detail-meta-item"><span class="detail-meta-label">采集时间</span><span class="detail-meta-value">{{ formatDate(selectedInspiration.collected_at) }}</span></div>
          </div>
          <div class="detail-source-actions">
            <el-button type="primary" plain @click="openOriginal(selectedInspiration.source_url)">查看原文</el-button>
          </div>
        </div>
        <div class="detail-preview-shell">
          <div class="detail-preview-device">
            <div class="detail-preview-header"><div class="detail-preview-dots"><span/><span/><span/></div><div class="detail-preview-caption">公众号文章预览</div></div>
            <div class="detail-article">
              <header class="detail-article-header"><h1>{{ selectedInspiration.title }}</h1></header>
              <div ref="contentRef" class="content-box article-content" v-html="displayContentHtml" />
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, Plus, Search } from '@element-plus/icons-vue'
import { useInspirationStore, useAccountStore, useAppStore } from '../stores'
import api from '../api'

const inspirationStore = useInspirationStore()
const accountStore = useAccountStore()
const appStore = useAppStore()

const loading = ref(false)
const searchQuery = ref('')
const scoreFilter = ref(null)
const scoring = ref(false)
const showCollectDialog = ref(false)
const showDetailDialog = ref(false)
const selectedInspiration = ref(null)
const collecting = ref(false)
const contentRef = ref(null)

const collectForm = ref({ url: '', account_id: '' })

const filteredInspirations = computed(() => {
  let list = inspirationStore.inspirations
  // 搜索
  if (searchQuery.value) {
    const s = searchQuery.value.toLowerCase()
    list = list.filter(i => i.title?.toLowerCase().includes(s) || i.content?.toLowerCase().includes(s))
  }
  // 评分筛选
  if (scoreFilter.value === 'unrated') {
    list = list.filter(i => i.ai_score == null)
  } else if (scoreFilter.value) {
    list = list.filter(i => i.ai_score != null && i.ai_score >= scoreFilter.value)
  }
  return list
})

const hasUnrated = computed(() =>
  inspirationStore.inspirations.some(i => i.ai_score == null)
)

function scoreClass(score) {
  if (score >= 80) return 'score-high'
  if (score >= 60) return 'score-mid'
  return 'score-low'
}

async function scoreUnrated() {
  scoring.value = true
  try {
    // 调用后端评分 API
    const data = await api.inspirations.scoreUnrated({
      account_id: appStore.selectedAccountId || ''
    })
    ElMessage.success(`已评分 ${data.scored || 0} 条`)
    loadData()
  } catch (e) {
    ElMessage.error(e.message || '评分失败')
  } finally { scoring.value = false }
}

const displayContentHtml = computed(() => {
  if (!selectedInspiration.value) return ''
  return sanitizeInspirationHtml(selectedInspiration.value.content_html || selectedInspiration.value.content || '')
})

function formatDate(dateStr) {
  if (!dateStr) return '-'
  try { return new Date(dateStr).toLocaleString('zh-CN', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' }) }
  catch { return dateStr }
}

function preferredAccountId() {
  return appStore.selectedAccountId || accountStore.accounts[0]?.account_id || 'default'
}

async function loadData() {
  loading.value = true
  const params = appStore.selectedAccountId ? { account_id: appStore.selectedAccountId } : undefined
  try {
    await inspirationStore.fetchInspirations(params)
    await accountStore.fetchAccounts()
  } finally { loading.value = false }
}

async function collect() {
  if (!collectForm.value.url) { ElMessage.warning('请输入链接'); return }
  collecting.value = true
  try {
    await inspirationStore.collect(collectForm.value.url, collectForm.value.account_id || preferredAccountId())
    ElMessage.success('采集任务已创建')
    showCollectDialog.value = false
    collectForm.value = { url: '', account_id: '' }
    setTimeout(loadData, 3000)
  } catch (error) {
    ElMessage.error(error.message || '采集失败')
  } finally { collecting.value = false }
}

function openCollectDialog() {
  collectForm.value.account_id = preferredAccountId()
  showCollectDialog.value = true
}

async function createArticle(id) {
  try {
    const article = await inspirationStore.createArticle(id)
    ElMessage.success('已创建文章')
    window.location.href = `/rewrite?id=${article.id}`
  } catch (error) { ElMessage.error(error.message || '创建文章失败') }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title || '无标题'}」？`, '确认删除', { type: 'warning' })
    await inspirationStore.deleteInspiration(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (error) { if (error !== 'cancel') ElMessage.error(error.message || '删除失败') }
}

function openOriginal(url) {
  if (!url) { ElMessage.warning('没有原文链接'); return }
  window.open(url, '_blank', 'noopener,noreferrer')
}

function viewDetail(row) { openInspirationDetail(row.id) }

function sanitizeInspirationHtml(html) {
  if (!html) return ''
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')
  doc.body.querySelectorAll('img').forEach(node => {
    const dataSrc = node.getAttribute('data-src') || ''
    if (dataSrc && !node.getAttribute('src')) node.setAttribute('src', dataSrc)
    node.setAttribute('referrerpolicy', 'no-referrer')
    node.setAttribute('loading', 'lazy')
  })
  doc.body.querySelectorAll('[style]').forEach(node => {
    const style = node.getAttribute('style') || ''
    const declarations = style.split(';').map(s => s.trim()).filter(Boolean)
      .filter(s => !/^visibility\s*:\s*hidden$/i.test(s))
      .filter(s => !/^opacity\s*:\s*0(?:\.0+)?$/i.test(s))
    if (declarations.length) node.setAttribute('style', declarations.join('; '))
    else node.removeAttribute('style')
  })
  return doc.body.innerHTML
}

async function openInspirationDetail(id) {
  try {
    selectedInspiration.value = await inspirationStore.getInspiration(id)
    showDetailDialog.value = true
    nextTick(() => { if (contentRef.value) contentRef.value.querySelectorAll('img').forEach(img => { img.referrerPolicy = 'no-referrer' }) })
  } catch (error) { ElMessage.error(error.message || '加载详情失败') }
}

onMounted(loadData)
watch(() => appStore.selectedAccountId, loadData)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.toolbar-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.toolbar-right { display: flex; align-items: center; gap: 8px; }

.score-badge { font-weight: 700; font-size: 14px; padding: 2px 8px; border-radius: var(--radius-sm); }
.score-high { color: #059669; background: #d1fae5; }
.score-mid { color: #d97706; background: #fef3c7; }
.score-low { color: #dc2626; background: #fee2e2; }
.score-none { color: var(--text-muted); font-size: 14px; }

.inspiration-title { font-weight: 600; color: var(--text-primary); }
.inspiration-tags { margin-top: 6px; display: flex; gap: 6px; }

.content-box { max-height: 70vh; overflow-y: auto; line-height: 1.8; }
.detail-layout { display: grid; grid-template-columns: minmax(220px, 280px) minmax(0, 1fr); gap: 24px; align-items: start; }
.detail-meta-panel { padding: 20px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: linear-gradient(180deg, #f8fbff 0%, #f8fafc 100%); position: sticky; top: 0; }
.detail-meta-eyebrow { font-size: 12px; color: var(--accent); font-weight: 600; }
.detail-title { margin: 12px 0 0; font-size: 24px; line-height: 1.4; color: var(--text-primary); }
.detail-meta-row { display: grid; gap: 12px; margin-top: 20px; }
.detail-meta-item { padding: 12px 14px; border-radius: var(--radius); background: rgba(255,255,255,0.86); border: 1px solid var(--border); }
.detail-meta-label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
.detail-meta-value { display: block; font-size: 14px; color: var(--text-primary); font-weight: 600; }
.detail-source-actions { margin-top: 18px; }

.detail-preview-shell { padding: 18px; border-radius: 18px; background: linear-gradient(180deg, #eef4ff 0%, #f8fafc 100%); border: 1px solid #dbeafe; }
.detail-preview-device { max-width: 520px; margin: 0 auto; border-radius: 24px; background: #fff; border: 1px solid #dbe2ea; box-shadow: 0 18px 48px rgba(15,23,42,0.08); overflow: hidden; }
.detail-preview-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid #eef2f7; background: #f8fafc; }
.detail-preview-dots { display: flex; gap: 6px; }
.detail-preview-dots span { width: 8px; height: 8px; border-radius: 999px; background: #cbd5e1; display: inline-block; }
.detail-preview-caption { font-size: 12px; color: var(--text-secondary); }
.detail-article { background: #fff; }
.detail-article-header { padding: 24px 24px 16px; border-bottom: 1px solid var(--border-light); }
.detail-article-header h1 { margin: 0; font-size: 28px; line-height: 1.42; color: var(--text-primary); font-weight: 700; }
.article-content { padding: 0 24px 28px; font-size: 17px; color: var(--text-primary); background: #fff; }
.article-content :deep(p) { margin: 0 0 1.15em; line-height: 1.95; color: var(--text-primary); }
.article-content :deep(h2) { padding: 10px 14px 10px 16px; font-size: 21px; font-weight: 700; border-left: 4px solid #3b82f6; border-radius: 0 var(--radius-lg) var(--radius-lg) 0; background: linear-gradient(90deg, #eff6ff 0%, #f8fbff 100%); }
.article-content :deep(h3) { padding-left: 12px; font-size: 18px; font-weight: 700; border-left: 3px solid #cbd5e1; }
.article-content :deep(img) { max-width: 100%; height: auto; border-radius: var(--radius-lg); margin: 18px auto; background: #f8fafc; }
.article-content :deep(blockquote) { margin: 1.4em 0; padding: 14px 16px; border-left: 4px solid #60a5fa; background: #f8fbff; color: #334155; }
.article-content :deep(li) { margin-bottom: 0.6em; line-height: 1.9; }

@media (max-width: 960px) {
  .detail-layout { grid-template-columns: 1fr; }
  .detail-meta-panel { position: static; }
  .detail-preview-device { max-width: 100%; }
}
</style>
