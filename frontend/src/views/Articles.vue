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
                @click="publish(row.id)"
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
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useArticleStore } from '../stores'

const router = useRouter()
const articleStore = useArticleStore()

const loading = ref(false)
const filterStatus = ref('')

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
  await articleStore.fetchArticles().finally(() => {
    loading.value = false
  })
}

function goRewrite(id) {
  router.push(`/rewrite?id=${id}`)
}

async function publish(id) {
  try {
    await ElMessageBox.confirm('确定要发布这篇文章吗？', '确认发布')
    await articleStore.publish(id, 'default')
    ElMessage.success('发布成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '发布失败')
    }
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
</style>
