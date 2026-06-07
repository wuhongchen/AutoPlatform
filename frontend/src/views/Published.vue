<template>
  <div class="published-page">
    <div class="page-header">
      <div>
        <h2>已发文章</h2>
        <p class="page-desc">查看已发布文章，可从微信同步最新数据</p>
      </div>
      <el-button type="primary" @click="syncFromWechat" :loading="syncing">
        <el-icon><Refresh /></el-icon>从微信同步
      </el-button>
    </div>

    <el-card v-if="!hasCredentials" shadow="never" class="warning-card">
      <el-icon><WarningFilled /></el-icon>
      当前账户未配置微信凭证，无法从微信同步。请先在
      <el-button type="primary" link @click="$router.push('/accounts')">账户管理</el-button>
      或
      <el-button type="primary" link @click="$router.push('/account-settings')">账号设置</el-button>
      中配置 AppID 和 Secret。
    </el-card>

    <el-card shadow="never">
      <el-table :data="publishedArticles" v-loading="loading" stripe>
        <el-table-column label="标题" min-width="300">
          <template #default="{ row }">
            <div class="article-title">{{ row.source_title || '无标题' }}</div>
          </template>
        </el-table-column>

        <el-table-column label="账户" width="130">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.account_id || '-' }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="发布模板" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.metadata?.template || 'default' }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="草稿 ID" width="180">
          <template #default="{ row }">
            <code v-if="row.wechat_draft_id" class="draft-id">{{ row.wechat_draft_id }}</code>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="发布时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.published_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && !publishedArticles.length" description="还没有已发布的文章" />
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="文章详情" width="720px">
      <div v-if="detailArticle" class="detail-body">
        <div class="detail-title">{{ detailArticle.source_title }}</div>
        <div class="detail-tags">
          <el-tag size="small">{{ detailArticle.account_id }}</el-tag>
          <el-tag size="small" type="success">已发布</el-tag>
          <el-tag v-if="detailArticle.rewrite_style" size="small" type="info">{{ detailArticle.rewrite_style }}</el-tag>
        </div>
        <div class="detail-section">
          <div class="detail-label">发布时间</div>
          <div>{{ formatDate(detailArticle.published_at) }}</div>
        </div>
        <div class="detail-section">
          <div class="detail-label">草稿 ID</div>
          <code>{{ detailArticle.wechat_draft_id || '-' }}</code>
        </div>
        <div v-if="detailArticle.metadata?.template" class="detail-section">
          <div class="detail-label">发布模板</div>
          <div>{{ detailArticle.metadata.template }}</div>
        </div>
        <div v-if="detailArticle.rewritten_html" class="detail-section">
          <div class="detail-label">已发布内容预览</div>
          <div class="detail-content" v-html="detailArticle.rewritten_html" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, WarningFilled } from '@element-plus/icons-vue'
import { useAccountStore, useAppStore, useArticleStore } from '../stores'
import api from '../api'

const accountStore = useAccountStore()
const appStore = useAppStore()
const articleStore = useArticleStore()

const loading = ref(false)
const syncing = ref(false)
const detailVisible = ref(false)
const detailArticle = ref(null)

const hasCredentials = computed(() => {
  const acc = accountStore.accounts.find(a => a.account_id === appStore.selectedAccountId)
  return acc?.wechat_appid && acc?.wechat_secret
})

const publishedArticles = computed(() =>
  articleStore.articles.filter(a => a.status === 'published')
)

async function loadData() {
  loading.value = true
  const params = appStore.selectedAccountId
    ? { account_id: appStore.selectedAccountId }
    : undefined
  try {
    await Promise.all([
      articleStore.fetchArticles(params),
      accountStore.fetchAccounts(),
    ])
  } finally {
    loading.value = false
  }
}

async function syncFromWechat() {
  if (!hasCredentials.value) {
    ElMessage.warning('请先配置微信凭证')
    return
  }
  syncing.value = true
  try {
    const result = await api.articles.syncPublished({
      account_id: appStore.selectedAccountId,
    })
    if (result.synced > 0) {
      ElMessage.success(`同步完成：新增 ${result.synced} 条`)
      loadData()
    } else {
      ElMessage.info('没有新的已发文章')
    }
  } catch (e) {
    ElMessage.error(e.message || '同步失败')
  } finally {
    syncing.value = false
  }
}

function openDetail(row) { detailArticle.value = row; detailVisible.value = true }

function formatDate(val) {
  if (!val) return '-'
  try { return new Date(val).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }
  catch { return val }
}

onMounted(async () => { await accountStore.fetchAccounts(); loadData() })
watch(() => appStore.selectedAccountId, loadData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-header h2 { margin: 0; font-size: 22px; font-weight: 700; color: var(--text-primary); }
.page-desc { margin: 6px 0 0; font-size: 14px; color: var(--text-secondary); }

.warning-card {
  margin-bottom: 16px;
  display: flex; align-items: center; gap: 10px;
  color: var(--warning); background: var(--warning-light); border-color: #fde68a;
}
.warning-card :deep(.el-card__body) { display: flex; align-items: center; gap: 8px; }

.article-title { font-weight: 600; color: var(--text-primary); }
.draft-id { font-size: 12px; color: var(--text-secondary); background: #f8fafc; padding: 2px 6px; border-radius: 4px; }
.text-muted { color: var(--text-muted); }

.detail-body { display: flex; flex-direction: column; gap: 16px; }
.detail-title { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.detail-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.detail-section { padding: 12px; background: #f8fafc; border-radius: var(--radius); }
.detail-label { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; font-weight: 600; }
.detail-content { max-height: 400px; overflow-y: auto; line-height: 1.8; }
</style>
