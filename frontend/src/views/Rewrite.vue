<template>
  <div class="rewrite-page">
    <el-row :gutter="24">
      <!-- 左侧：文章内容 -->
      <el-col :span="16">
        <el-card shadow="never" class="content-card">
          <template #header>
            <div class="card-header">
              <span>原文内容</span>
              <el-tag v-if="article">{{ article.source_title }}</el-tag>
            </div>
          </template>
          
          <div v-if="!articleId" class="empty-state">
            <el-empty description="请选择要改写的文章">
              <el-button type="primary" @click="$router.push('/articles')">
                去文章列表
              </el-button>
            </el-empty>
          </div>
          
          <template v-else>
            <div class="article-info" v-if="article">
              <h3>{{ article.source_title }}</h3>
              <p class="author">{{ article.source_author || '未知作者' }}</p>
            </div>
            <div class="article-content" v-html="article?.original_html || article?.original_content" />
          </template>
        </el-card>

        <!-- 改写结果 -->
        <el-card v-if="result || activeTask" shadow="never" class="result-card">
          <template #header>
            <div class="card-header">
              <span>改写结果</span>
              <div v-if="activeTask">
                <el-tag :type="taskStatusType" size="small" effect="dark" class="mr-2">
                  {{ taskStatusLabel }}
                </el-tag>
                <el-button v-if="activeTask.status === 'completed'" type="primary" link size="small" @click="refreshArticle">
                  <el-icon><Refresh /></el-icon>刷新
                </el-button>
              </div>
              <div v-else>
                <el-tag type="info" class="mr-2">风格: {{ result.rewrite_style }}</el-tag>
                <el-tag type="success">参考: {{ result.metadata?.reference_count || 0 }}篇</el-tag>
              </div>
            </div>
          </template>
          
          <div v-if="activeTask && activeTask.status === 'running'" class="task-running">
            <el-skeleton :rows="6" animated />
            <p class="task-hint">任务正在后台执行中，可前往任务看板查看进度...</p>
          </div>
          
          <div v-else-if="activeTask && activeTask.status === 'failed'" class="task-failed">
            <el-result icon="error" title="改写失败">
              <template #sub-title>
                <p>{{ activeTask.error_message }}</p>
              </template>
            </el-result>
          </div>
          
          <template v-else>
            <div class="rewritten-content" v-html="result?.rewritten_html || article?.rewritten_html" />
            
            <div class="result-actions">
              <el-button type="primary" @click="openPublishDialog">
                <el-icon><Promotion /></el-icon>发布文章
              </el-button>
              <el-button @click="copyResult">
                <el-icon><CopyDocument /></el-icon>复制内容
              </el-button>
            </div>
          </template>
        </el-card>
      </el-col>

      <!-- 右侧：改写配置 -->
      <el-col :span="8">
        <div class="config-panel">
          <!-- 风格选择 -->
          <el-card shadow="never" class="mb-4">
            <template #header>改写风格</template>
            <el-select v-model="config.style" style="width: 100%">
              <el-option 
                v-for="style in styleStore.activeStyles" 
                :key="style.id" 
                :label="style.name" 
                :value="style.id"
              >
                <span>{{ style.name }}</span>
                <span class="text-gray-400 text-xs ml-2">{{ style.description }}</span>
              </el-option>
            </el-select>
            <div v-if="selectedStyle" class="style-info mt-4">
              <p class="text-sm text-gray-500">{{ selectedStyle.description }}</p>
              <div class="mt-2">
                <el-tag size="small" class="mr-2">语气: {{ selectedStyle.tone }}</el-tag>
                <el-tag size="small">温度: {{ selectedStyle.temperature }}</el-tag>
              </div>
            </div>
          </el-card>

          <!-- 改写模式 -->
          <el-card shadow="never" class="mb-4">
            <template #header>改写模式</template>
            <el-radio-group v-model="config.rewrite_mode" style="width: 100%">
              <el-radio-button label="manual">手动参考</el-radio-button>
              <el-radio-button label="auto">自动参考</el-radio-button>
              <el-radio-button label="none">无参考</el-radio-button>
            </el-radio-group>
            <p class="mode-desc">{{ modeDescription }}</p>
          </el-card>

          <!-- 灵感选择 -->
          <el-card v-if="config.rewrite_mode === 'manual'" shadow="never" class="mb-4">
            <template #header>
              <div class="flex justify-between items-center">
                <span>参考灵感</span>
                <span class="text-xs text-gray-400">已选 {{ selectedInspirations.length }}/5</span>
              </div>
            </template>
            
            <el-input 
              v-model="inspirationSearch" 
              placeholder="搜索灵感..." 
              prefix-icon="Search"
              class="mb-3"
            />
            
            <div class="inspiration-list">
              <el-checkbox-group v-model="selectedInspirations">
                <div 
                  v-for="insp in filteredInspirations" 
                  :key="insp.id"
                  class="inspiration-item"
                >
                  <el-checkbox :label="insp.id" :disabled="isMaxSelected && !selectedInspirations.includes(insp.id)">
                    <div class="inspiration-content">
                      <div class="title">{{ insp.title || '无标题' }}</div>
                      <div class="source">{{ insp.source_account || '未知来源' }}</div>
                    </div>
                  </el-checkbox>
                </div>
              </el-checkbox-group>
            </div>
          </el-card>

          <!-- 额外指令 -->
          <el-card shadow="never" class="mb-4">
            <template #header>额外指令</template>
            <el-input 
              v-model="config.instructions" 
              type="textarea" 
              :rows="4"
              placeholder="输入额外要求，例如：
• 增加数据支撑
• 语气更幽默
• 适合小白阅读"
            />
          </el-card>

          <!-- 操作按钮 -->
          <el-button 
            type="primary" 
            size="large" 
            style="width: 100%"
            :loading="rewriting"
            :disabled="!articleId"
            @click="startRewrite"
          >
            <el-icon class="mr-1"><MagicStick /></el-icon>
            {{ rewriting ? '创建任务中...' : '开始改写' }}
          </el-button>
          
          <div v-if="activeTask" class="task-link">
            <el-button type="info" link @click="$router.push('/tasks')">
              去任务看板查看进度 →
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>

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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MagicStick, Promotion, CopyDocument, Search, Document, Refresh } from '@element-plus/icons-vue'
import { useStyleStore, useInspirationStore, useArticleStore, useAppStore, useTaskStore } from '../stores'
import api from '../api'

const route = useRoute()
const router = useRouter()
const styleStore = useStyleStore()
const inspirationStore = useInspirationStore()
const articleStore = useArticleStore()
const appStore = useAppStore()
const taskStore = useTaskStore()

const articleId = computed(() => route.query.id)
const article = computed(() => articleStore.currentArticle)

const config = ref({
  style: '',
  instructions: '',
  rewrite_mode: 'manual'
})

const inspirationSearch = ref('')
const selectedInspirations = ref([])
const rewriting = ref(false)
const result = ref(null)
const activeTask = ref(null)
const pollTimer = ref(null)

const publishDialogVisible = ref(false)
const publishing = ref(false)
const templates = ref({})
const selectedTemplate = ref('default')

const selectedStyle = computed(() => {
  return styleStore.styles.find(s => s.id === config.value.style)
})

const taskStatusType = computed(() => {
  const map = { pending: 'info', running: 'warning', completed: 'success', failed: 'danger', cancelled: 'info' }
  return map[activeTask.value?.status] || 'info'
})

const taskStatusLabel = computed(() => {
  const map = { pending: '待执行', running: '执行中', completed: '已完成', failed: '失败', cancelled: '已取消' }
  return map[activeTask.value?.status] || activeTask.value?.status
})

const modeDescription = computed(() => {
  const desc = {
    manual: '仅使用下方手动勾选的文章作为参考',
    auto: '系统自动从灵感库筛选最相关的文章作为参考',
    none: '不使用任何参考，仅基于原文改写'
  }
  return desc[config.value.rewrite_mode] || ''
})

const filteredInspirations = computed(() => {
  if (!inspirationSearch.value) return inspirationStore.inspirations
  const search = inspirationSearch.value.toLowerCase()
  return inspirationStore.inspirations.filter(i => 
    i.title?.toLowerCase().includes(search) ||
    i.content?.toLowerCase().includes(search)
  )
})

const isMaxSelected = computed(() => selectedInspirations.value.length >= 5)

async function loadData() {
  if (articleId.value) {
    try {
      await articleStore.getArticle(articleId.value)
    } catch (e) {
      console.error('加载文章失败:', e)
      ElMessage.error('加载文章失败: ' + (e.message || '未知错误'))
    }
  }
  await styleStore.fetchStyles()
  await loadInspirations()
  
  if (styleStore.activeStyles.length > 0 && !config.value.style) {
    config.value.style = styleStore.activeStyles[0].id
  }
}

async function loadInspirations() {
  const accountId = appStore.selectedAccountId || article.value?.account_id || ''
  const params = accountId ? { account_id: accountId } : undefined
  await inspirationStore.fetchInspirations(params)
}

async function startRewrite() {
  if (!articleId.value) return
  
  rewriting.value = true
  try {
    const mode = config.value.rewrite_mode
    const taskResult = await articleStore.rewrite(articleId.value, {
      style: config.value.style,
      instructions: config.value.instructions,
      use_references: mode !== 'none',
      inspiration_ids: mode === 'manual' ? selectedInspirations.value : undefined
    })
    
    ElMessage.success(`改写任务已创建: ${taskResult.task_id?.slice(0, 8)}...`)
    activeTask.value = { id: taskResult.task_id, status: 'pending' }
    
    // 开始轮询
    startPolling(taskResult.task_id)
  } catch (error) {
    ElMessage.error(error.message || '改写失败')
  } finally {
    rewriting.value = false
  }
}

function startPolling(taskId) {
  stopPolling()
  pollTimer.value = setInterval(async () => {
    try {
      const task = await taskStore.getTask(taskId)
      activeTask.value = task
      
      if (task.status === 'completed') {
        stopPolling()
        // 自动刷新文章数据以获取改写结果
        await articleStore.getArticle(articleId.value)
        result.value = articleStore.currentArticle
        ElMessage.success('改写完成')
      } else if (task.status === 'failed') {
        stopPolling()
        ElMessage.error(task.error_message || '改写失败')
      }
    } catch (e) {
      console.error('轮询失败:', e)
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

async function refreshArticle() {
  await articleStore.getArticle(articleId.value)
  result.value = articleStore.currentArticle
}

async function openPublishDialog() {
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
    const taskResult = await articleStore.publish(articleId.value, selectedTemplate.value)
    ElMessage.success(`发布任务已创建: ${taskResult.task_id?.slice(0, 8)}...`)
    publishDialogVisible.value = false
    // 跳转到任务看板
    setTimeout(() => router.push('/tasks'), 800)
  } catch (error) {
    ElMessage.error(error.message || '发布失败')
  } finally {
    publishing.value = false
  }
}

function copyResult() {
  const content = result.value?.rewritten_html || article.value?.rewritten_html || ''
  const text = content.replace(/<[^>]+>/g, '')
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('内容已复制')
  })
}

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  stopPolling()
})

// 监听路由 id 变化（从文章列表点击不同文章时）
watch(() => route.query.id, (newId, oldId) => {
  if (newId && newId !== oldId) {
    result.value = null
    activeTask.value = null
    stopPolling()
    loadData()
  }
})

watch(() => appStore.selectedAccountId, () => {
  loadInspirations()
})
</script>

<style scoped>
.content-card, .result-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-state {
  padding: 60px 0;
}

.article-info {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.article-info h3 {
  margin: 0 0 8px 0;
}

.article-info .author {
  color: #64748b;
  margin: 0;
}

.article-content {
  line-height: 1.8;
  max-height: 500px;
  overflow-y: auto;
}

.rewritten-content {
  background: #f8fafc;
  padding: 20px;
  border-radius: 8px;
  line-height: 1.8;
  max-height: 600px;
  overflow-y: auto;
}

.result-actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
}

.config-panel {
  position: sticky;
  top: 20px;
}

.mb-4 {
  margin-bottom: 16px;
}

.style-info {
  padding: 12px;
  background: #f8fafc;
  border-radius: 6px;
}

.mode-desc {
  font-size: 12px;
  color: #64748b;
  margin-top: 8px;
  line-height: 1.5;
}

.inspiration-list {
  max-height: 300px;
  overflow-y: auto;
}

.inspiration-item {
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
}

.inspiration-content {
  display: flex;
  flex-direction: column;
}

.inspiration-content .title {
  font-size: 13px;
  font-weight: 500;
}

.inspiration-content .source {
  font-size: 12px;
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

:deep(.el-checkbox__label) {
  flex: 1;
}

.task-running {
  padding: 20px 0;
}

.task-hint {
  text-align: center;
  color: #64748b;
  margin-top: 16px;
  font-size: 14px;
}

.task-failed {
  padding: 20px 0;
}

.task-link {
  text-align: center;
  margin-top: 12px;
}
</style>
