<template>
  <div class="articles-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <el-radio-group v-model="filterStatus" size="small">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="pending">待改写</el-radio-button>
            <el-radio-button label="rewritten">已改写</el-radio-button>
            <el-radio-button label="published">已发布</el-radio-button>
          </el-radio-group>
          <el-button type="primary" @click="loadData">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </div>
      </template>

      <el-table :data="filteredArticles" v-loading="loading" stripe>
        <el-table-column label="标题" min-width="280">
          <template #default="{ row }">
            <div class="article-title" :title="row.source_title">
              {{ row.source_title || '无标题' }}
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="账户" width="140">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.account_id || '-' }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="来源" width="120">
          <template #default="{ row }">
            {{ row.source_author || '-' }}
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="改写风格" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.rewrite_style" type="info" size="small">
              {{ row.rewrite_style }}
            </el-tag>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                v-if="canRewrite(row.status)"
                size="small" 
                type="primary"
                @click="goRewrite(row.id)"
              >
                改写
              </el-button>
              <el-button 
                v-if="row.status === 'rewritten'"
                size="small"
                @click="goRewrite(row.id)"
              >
                查看
              </el-button>
              <el-button 
                v-if="row.status === 'rewritten'"
                size="small" 
                type="success"
                @click="openPublishDialog(row.id)"
              >
                发布
              </el-button>
              <el-button
                v-if="row.status === 'published'"
                size="small"
                @click="viewDraft(row.wechat_draft_id)"
              >
                查看
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <!-- 发布对话框 -->
      <el-dialog v-model="publishDialogVisible" title="选择发布模板" width="500px">
        <div class="template-grid">
          <div 
            v-for="(tpl, key) in templates" 
            :key="key"
            class="template-item"
            :class="{ active: selectedTemplate === key }"
            @click="selectedTemplate = key"
          >
            <el-icon :size="32" class="mb-2"><Document /></el-icon>
            <div class="name">{{ tpl.name }}</div>
            <div class="desc">{{ tpl.description }}</div>
          </div>
        </div>
        <template #footer>
          <el-button @click="publishDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmPublish" :loading="publishing">
            确认发布
          </el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Document } from '@element-plus/icons-vue'
import api from '../api'
import { useArticleStore, useAppStore } from '../stores'

const router = useRouter()
const articleStore = useArticleStore()
const appStore = useAppStore()

const loading = ref(false)
const filterStatus = ref('')
const publishDialogVisible = ref(false)
const publishArticleId = ref('')
const templates = ref({})
const selectedTemplate = ref('default')
const publishing = ref(false)

const filteredArticles = computed(() => {
  if (!filterStatus.value) return articleStore.articles
  return articleStore.articles.filter(a => a.status === filterStatus.value)
})

const statusMap = {
  pending: { label: '待改写', type: 'warning' },
  rewriting: { label: '改写中', type: 'primary' },
  rewritten: { label: '已改写', type: 'success' },
  publishing: { label: '发布中', type: 'primary' },
  published: { label: '已发布', type: 'success' },
  failed: { label: '失败', type: 'danger' }
}

function getStatusLabel(status) {
  return statusMap[status]?.label || status
}

function getStatusType(status) {
  return statusMap[status]?.type || 'info'
}

function canRewrite(status) {
  return status === 'pending' || status === 'failed'
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function loadData() {
  loading.value = true
  const params = appStore.selectedAccountId
    ? { account_id: appStore.selectedAccountId }
    : undefined
  await articleStore.fetchArticles(params).finally(() => {
    loading.value = false
  })
}

function goRewrite(id) {
  router.push({ name: 'Rewrite', query: { id } })
}

async function openPublishDialog(id) {
  publishArticleId.value = id
  try {
    const data = await api.templates.list()
    templates.value = data
    selectedTemplate.value = 'default'
    publishDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载模板失败')
  }
}

async function confirmPublish() {
  publishing.value = true
  try {
    const result = await articleStore.publish(publishArticleId.value, selectedTemplate.value)
    ElMessage.success(`发布任务已创建: ${result.task_id?.slice(0, 8)}...`)
    publishDialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.message || '发布失败')
  } finally {
    publishing.value = false
  }
}

function viewDraft(draftId) {
  if (draftId) {
    window.open('https://mp.weixin.qq.com/', '_blank')
  } else {
    ElMessage.info('暂无草稿链接')
  }
}

onMounted(() => {
  loadData()
})

watch(() => appStore.selectedAccountId, () => {
  loadData()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.article-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-gray-400 {
  color: #94a3b8;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.template-item {
  padding: 24px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.template-item:hover {
  border-color: #4f46e5;
}

.template-item.active {
  border-color: #4f46e5;
  background: #eef2ff;
}

.template-item .name {
  font-weight: 500;
  margin-bottom: 4px;
}

.template-item .desc {
  font-size: 12px;
  color: #64748b;
}
</style>
