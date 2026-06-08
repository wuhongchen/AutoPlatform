<template>
  <div class="dashboard">
    <!-- 欢迎区 -->
    <div class="welcome">
      <h1 class="welcome-title">👋 欢迎回来</h1>
      <p class="welcome-sub">今天也要高效产出好内容</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="stat in statsList" :key="stat.key" :style="{'--stat-color': stat.color, '--stat-bg': stat.bgColor}">
        <div class="stat-accent" />
        <div class="stat-body">
          <div class="stat-icon-box">
            <el-icon :size="18"><component :is="stat.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="section-header">
      <h3>快捷操作</h3>
    </div>
    <div class="actions-grid">
      <div
        v-for="action in quickActions"
        :key="action.path"
        class="action-card"
        @click="$router.push(action.path)"
      >
        <div class="action-icon" :style="{ background: action.gradient }">
          <el-icon :size="22" color="#fff"><component :is="action.icon" /></el-icon>
        </div>
        <div class="action-info">
          <span class="action-label">{{ action.label }}</span>
          <span class="action-desc">{{ action.desc }}</span>
        </div>
        <el-icon class="action-arrow" color="#94a3b8"><component :is="'ArrowRight'" /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import { useAppStore } from '../stores'

const appStore = useAppStore()

const statsList = computed(() => [
  {
    key: 'total',
    label: '文章总数',
    value: totalArticles.value,
    icon: 'Document',
    color: '#6366f1',
    bgColor: '#eef2ff'
  },
  {
    key: 'published',
    label: '已发布',
    value: appStore.stats.articles?.published || 0,
    icon: 'CircleCheck',
    color: '#10b981',
    bgColor: '#d1fae5'
  },
  {
    key: 'pending',
    label: '待处理',
    value: pendingArticles.value,
    icon: 'Clock',
    color: '#f59e0b',
    bgColor: '#fef3c7'
  },
  {
    key: 'inspiration',
    label: '灵感素材',
    value: Object.values(appStore.stats.inspiration || {}).reduce((sum, count) => sum + count, 0),
    icon: 'Lightbulb',
    color: '#ec4899',
    bgColor: '#fce7f3'
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
  { label: '链接成稿', desc: '链接一步生成文章', icon: 'MagicStick', path: '/content-flow', gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)' },
  { label: '我的文章', desc: '管理改写与发布', icon: 'Document', path: '/articles', gradient: 'linear-gradient(135deg, #3b82f6, #06b6d4)' },
  { label: '素材采集', desc: 'URL采集灵感素材', icon: 'Plus', path: '/inspirations', gradient: 'linear-gradient(135deg, #10b981, #34d399)' },
  { label: '任务看板', desc: '查看异步任务进度', icon: 'List', path: '/tasks', gradient: 'linear-gradient(135deg, #f59e0b, #fbbf24)' }
]

async function loadData() {
  appStore.fetchStats()
}

onMounted(() => loadData())
watch(() => appStore.selectedAccountId, () => loadData())
</script>

<style scoped>
/* === 欢迎区 === */
.welcome {
  margin-bottom: 28px;
}
.welcome-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin: 0 0 6px;
}
.welcome-sub {
  color: var(--text-secondary);
  font-size: 15px;
  margin: 0;
}

/* === 统计卡片 === */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s;
}
.stat-card:hover {
  box-shadow: var(--shadow-md);
}

.stat-accent {
  height: 3px;
  background: var(--stat-color);
}

.stat-body {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-icon-box {
  width: 40px;
  height: 40px;
  border-radius: var(--radius);
  background: var(--stat-bg);
  color: var(--stat-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

/* === 快捷操作区 === */
.section-header {
  margin-bottom: 16px;
}
.section-header h3 {
  font-size: 16px;
  font-weight: 650;
  color: var(--text-primary);
  margin: 0;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.action-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: var(--accent);
}

.action-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.action-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.action-desc {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.action-arrow {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s;
}
.action-card:hover .action-arrow {
  opacity: 1;
}

@media (max-width: 1200px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .actions-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
