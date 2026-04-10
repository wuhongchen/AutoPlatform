<template>
  <div class="inspirations-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <el-input 
            v-model="searchQuery" 
            placeholder="搜索灵感..." 
            prefix-icon="Search"
            style="width: 300px"
            clearable
          />
          <el-button type="primary" @click="showCollectDialog = true">
            <el-icon><Plus /></el-icon>采集灵感
          </el-button>
        </div>
      </template>

      <el-table :data="filteredInspirations" v-loading="loading" stripe>
        <el-table-column label="标题" min-width="250">
          <template #default="{ row }">
            <div class="inspiration-title">{{ row.title || '无标题' }}</div>
            <div class="inspiration-url">{{ row.source_url }}</div>
          </template>
        </el-table-column>
        
        <el-table-column label="来源" width="120" prop="source_account" />
        
        <el-table-column label="AI评分" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.ai_score" :type="getScoreType(row.ai_score)">
              {{ row.ai_score }}
            </el-tag>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="采集时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.collected_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                v-if="row.status === '待决策'"
                size="small" 
                type="primary"
                @click="approve(row.id)"
              >
                采纳
              </el-button>
              <el-button size="small" @click="viewDetail(row)">
                查看
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 采集对话框 -->
    <el-dialog v-model="showCollectDialog" title="采集灵感" width="500px">
      <el-form :model="collectForm" label-width="100px">
        <el-form-item label="文章链接">
          <el-input 
            v-model="collectForm.url" 
            placeholder="输入微信公众号文章链接..."
          />
        </el-form-item>
        <el-form-item label="账户">
          <el-select v-model="collectForm.account_id" style="width: 100%">
            <el-option 
              v-for="acc in accountStore.accounts" 
              :key="acc.account_id"
              :label="acc.name"
              :value="acc.account_id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCollectDialog = false">取消</el-button>
        <el-button type="primary" @click="collect" :loading="collecting">
          开始采集
        </el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="灵感详情" width="700px">
      <div v-if="selectedInspiration">
        <h3>{{ selectedInspiration.title }}</h3>
        <p class="text-gray-500 mb-4">{{ selectedInspiration.source_url }}</p>
        <div class="content-box" v-html="selectedInspiration.content_html || selectedInspiration.content" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { useInspirationStore, useAccountStore } from '../stores'

const inspirationStore = useInspirationStore()
const accountStore = useAccountStore()

const loading = ref(false)
const searchQuery = ref('')
const showCollectDialog = ref(false)
const showDetailDialog = ref(false)
const selectedInspiration = ref(null)
const collecting = ref(false)

const collectForm = ref({
  url: '',
  account_id: ''
})

const filteredInspirations = computed(() => {
  if (!searchQuery.value) return inspirationStore.inspirations
  const search = searchQuery.value.toLowerCase()
  return inspirationStore.inspirations.filter(i => 
    i.title?.toLowerCase().includes(search) ||
    i.content?.toLowerCase().includes(search)
  )
})

function getScoreType(score) {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
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
  await Promise.all([
    inspirationStore.fetchInspirations(),
    accountStore.fetchAccounts()
  ]).finally(() => {
    loading.value = false
  })
}

async function collect() {
  if (!collectForm.value.url) {
    ElMessage.warning('请输入链接')
    return
  }
  collecting.value = true
  try {
    await inspirationStore.collect(collectForm.value.url, collectForm.value.account_id || 'default')
    ElMessage.success('采集成功')
    showCollectDialog.value = false
    collectForm.value = { url: '', account_id: '' }
    loadData()
  } catch (error) {
    ElMessage.error(error.message || '采集失败')
  } finally {
    collecting.value = false
  }
}

async function approve(id) {
  try {
    await inspirationStore.approve(id)
    ElMessage.success('已采纳并创建文章')
    loadData()
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

function viewDetail(row) {
  selectedInspiration.value = row
  showDetailDialog.value = true
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

.inspiration-title {
  font-weight: 500;
}

.inspiration-url {
  font-size: 12px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.content-box {
  max-height: 400px;
  overflow-y: auto;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  line-height: 1.8;
}

.text-gray-500 {
  color: #64748b;
}
</style>
