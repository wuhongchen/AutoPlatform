<template>
  <div class="pipeline-page">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span>流水线任务</span>
          <el-button type="primary" @click="runPipeline" :loading="running">
            <el-icon><VideoPlay /></el-icon>
            {{ running ? '运行中...' : '运行流水线' }}
          </el-button>
        </div>
      </template>

      <!-- 配置面板 -->
      <el-form :model="config" label-width="100px" class="pipeline-config">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="改写风格">
              <el-select v-model="config.style" placeholder="使用账户默认" clearable style="width: 100%">
                <el-option 
                  v-for="style in styleStore.activeStyles" 
                  :key="style.id" 
                  :label="style.name" 
                  :value="style.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发布模板">
              <el-select v-model="config.template" style="width: 100%">
                <el-option 
                  v-for="(tpl, key) in templates" 
                  :key="key" 
                  :label="tpl.name" 
                  :value="key"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="批处理数量">
              <el-slider v-model="config.batch_size" :min="1" :max="10" show-stops />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标账户">
              <el-tag v-if="appStore.selectedAccountId" type="info">{{ appStore.selectedAccountId }}</el-tag>
              <el-tag v-else type="warning">未选择</el-tag>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <el-divider />

      <!-- 统计信息 -->
      <el-row :gutter="20" class="stats-row">
        <el-col :span="8">
          <div class="stat-item">
            <div class="stat-value">{{ pendingCount }}</div>
            <div class="stat-label">待处理文章</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-item">
            <div class="stat-value">{{ appStore.stats.articles?.published || 0 }}</div>
            <div class="stat-label">已发布</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-item">
            <div class="stat-value">{{ appStore.stats.articles?.failed || 0 }}</div>
            <div class="stat-label">失败</div>
          </div>
        </el-col>
      </el-row>

      <el-empty v-if="!appStore.selectedAccountId" description="请先在顶部选择一个账户">
        <template #description>
          <p>流水线必须绑定具体账户运行</p>
          <p class="text-gray-400 text-sm mt-2">在顶部导航栏选择账户后点击运行</p>
        </template>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useAppStore, useStyleStore } from '../stores'

const appStore = useAppStore()
const styleStore = useStyleStore()

const running = ref(false)
const templates = ref({})

const config = ref({
  style: '',
  template: 'default',
  batch_size: 3
})

const pendingCount = computed(() => {
  const articles = appStore.stats.articles || {}
  return (articles.pending || 0) + (articles.rewriting || 0)
})

async function loadTemplates() {
  try {
    const data = await api.templates.list()
    templates.value = data
  } catch (error) {
    console.error('加载模板失败:', error)
  }
}

async function runPipeline() {
  if (!appStore.selectedAccountId) {
    ElMessage.warning('请先在顶部选择一个账户再运行流水线')
    return
  }

  running.value = true
  try {
    await api.pipeline.process({
      account_id: appStore.selectedAccountId,
      batch_size: config.value.batch_size,
      style: config.value.style || undefined,
      template: config.value.template
    })
    ElMessage.success('流水线运行完成')
    appStore.fetchStats()
  } catch (error) {
    ElMessage.error(error.message || '运行失败')
  } finally {
    running.value = false
  }
}

onMounted(() => {
  loadTemplates()
  styleStore.fetchStyles()
  appStore.fetchStats()
})
</script>

<style scoped>
.pipeline-config {
  max-width: 700px;
}

.stats-row {
  margin-top: 8px;
}

.stat-item {
  text-align: center;
  padding: 20px;
  background: #f8fafc;
  border-radius: 12px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #1e293b;
}

.stat-label {
  font-size: 14px;
  color: #64748b;
  margin-top: 4px;
}

.text-gray-400 {
  color: #94a3b8;
}
</style>
