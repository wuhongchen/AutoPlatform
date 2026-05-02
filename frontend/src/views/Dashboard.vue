<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="stat in statsList" :key="stat.key">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" :style="{ background: stat.bgColor, color: stat.color }">
            <el-icon :size="24"><component :is="stat.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作 -->
    <el-card class="action-card" shadow="hover">
      <template #header>
        <span>快捷操作</span>
      </template>
      <el-row :gutter="16">
        <el-col :span="6" v-for="action in quickActions" :key="action.path">
          <div class="action-item" @click="$router.push(action.path)">
            <el-icon :size="40" color="#4f46e5"><component :is="action.icon" /></el-icon>
            <span>{{ action.label }}</span>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useAppStore } from '../stores'

const appStore = useAppStore()

const statsList = computed(() => [
  {
    key: 'total',
    label: '文章总数',
    value: totalArticles.value,
    icon: 'Document',
    bgColor: '#dbeafe',
    color: '#1e40af'
  },
  {
    key: 'published',
    label: '已发布',
    value: appStore.stats.articles?.published || 0,
    icon: 'CircleCheck',
    bgColor: '#d1fae5',
    color: '#065f46'
  },
  {
    key: 'pending',
    label: '待处理',
    value: pendingArticles.value,
    icon: 'Clock',
    bgColor: '#fef3c7',
    color: '#92400e'
  },
  {
    key: 'inspiration',
    label: '灵感总数',
    value: Object.values(appStore.stats.inspiration || {}).reduce((sum, count) => sum + count, 0),
    icon: 'Lightbulb',
    bgColor: '#fce7f3',
    color: '#9d174d'
  }
])

const totalArticles = computed(() => {
  return Object.values(appStore.stats.articles || {}).reduce((sum, count) => sum + count, 0)
})

const pendingArticles = computed(() => {
  const articles = appStore.stats.articles || {}
  return (articles.pending || 0) + (articles.rewriting || 0) + (articles.reviewing || 0)
})

const quickActions = [
  { label: '采集灵感', icon: 'Plus', path: '/inspirations' },
  { label: '改写发布', icon: 'MagicStick', path: '/articles' },
  { label: '管理风格', icon: 'BrushFilled', path: '/styles' },
  { label: '账户设置', icon: 'Setting', path: '/accounts' },
  { label: '任务看板', icon: 'List', path: '/tasks' }
]

async function loadData() {
  appStore.fetchStats()
}

onMounted(() => {
  loadData()
})

watch(() => appStore.selectedAccountId, () => {
  loadData()
})
</script>

<style scoped>
.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.2;
}

.stat-label {
  color: #64748b;
  font-size: 14px;
  margin-top: 4px;
}

.action-card {
  margin-top: 24px;
}

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px 20px;
  border-radius: 12px;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.2s;
}

.action-item:hover {
  background: #eef2ff;
  transform: translateY(-2px);
}

.action-item span {
  font-weight: 500;
  color: #1e293b;
}
</style>
