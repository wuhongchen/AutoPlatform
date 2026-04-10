<script setup>
import { computed } from 'vue'
import MetricCard from './MetricCard.vue'

const props = defineProps({
  overview: { type: Object, default: null },
  jobs: { type: Array, default: () => [] },
})
const emit = defineEmits(['run-scan', 'add-article'])

// 基于新状态系统的概览卡片
const cards = computed(() => {
  const summary = props.overview?.summary || {}
  return [
    {
      title: '全部文章',
      value: summary.total_articles || 0,
      meta: `已完成: ${summary.published || 0}`,
      tone: ''
    },
    {
      title: '待处理',
      value: summary.pending || 0,
      meta: '等待采集/评分/改写',
      tone: 'info'
    },
    {
      title: '处理中',
      value: summary.processing || 0,
      meta: '正在进行中',
      tone: 'warn'
    },
    {
      title: '失败/跳过',
      value: (summary.failed || 0) + (summary.skipped || 0),
      meta: `失败: ${summary.failed || 0} | 跳过: ${summary.skipped || 0}`,
      tone: summary.failed ? 'bad' : ''
    },
  ]
})

// 状态分组统计
const stateGroups = computed(() => {
  return props.overview?.state_groups || {}
})

// 详细状态分布
const statusBreakdown = computed(() => {
  return props.overview?.status_breakdown || {}
})

// 插件任务统计
const taskStats = computed(() => {
  return props.overview?.tasks || {}
})

// 最近活跃
const recentItems = computed(() => {
  return props.overview?.recent_items || []
})
</script>

<template>
  <section class="page-section">
    <div class="page-headline">
      <div>
        <h1>概览</h1>
        <p>基于新状态系统的文章管理和统计概览，不再使用定时巡检。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" @click="emit('run-scan')">灵感库扫描</button>
        <button class="primary-btn" @click="emit('add-article')">+ 添加文章</button>
      </div>
    </div>

    <!-- 核心指标 -->
    <div class="metrics-grid">
      <MetricCard v-for="card in cards" :key="card.title" v-bind="card" />
    </div>

    <div class="overview-grid">
      <!-- 账户信息 -->
      <div class="panel-card panel-soft">
        <h3>账户信息</h3>
        <ul class="bullet-list">
          <li>当前账户：{{ overview?.account?.name || overview?.account?.id || '-' }}</li>
          <li>默认模型：{{ overview?.account?.pipeline_model || 'auto' }}</li>
          <li>默认角色：{{ overview?.account?.pipeline_role || 'tech_expert' }}</li>
          <li>数据更新时间：{{ overview?.sync_time || '-' }}</li>
        </ul>
      </div>

      <!-- 状态分组统计 -->
      <div class="panel-card">
        <h3>状态分布</h3>
        <div class="status-grid">
          <div class="status-item">
            <span class="status-label">待处理</span>
            <span class="status-value">{{ stateGroups.pending || 0 }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">处理中</span>
            <span class="status-value">{{ stateGroups.processing || 0 }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">已完成</span>
            <span class="status-value">{{ stateGroups.completed || 0 }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">失败</span>
            <span class="status-value">{{ stateGroups.failed || 0 }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">已跳过</span>
            <span class="status-value">{{ stateGroups.skipped || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- 插件任务统计 -->
      <div class="panel-card">
        <h3>插件任务</h3>
        <div class="status-grid">
          <div class="status-item">
            <span class="status-label">待执行</span>
            <span class="status-value">{{ taskStats.pending || 0 }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">运行中</span>
            <span class="status-value">{{ taskStats.running || 0 }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">成功</span>
            <span class="status-value text-success">{{ taskStats.success || 0 }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">失败</span>
            <span class="status-value text-danger">{{ taskStats.failed || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- 最近活跃 -->
      <div class="panel-card">
        <h3>最近更新</h3>
        <div v-if="recentItems.length" class="recent-list">
          <div v-for="item in recentItems" :key="item.record_id" class="recent-row">
            <div class="recent-title">{{ item.title || '未命名' }}</div>
            <div class="recent-meta">
              <span class="badge" :class="item.status === '已发布' ? 'ok' : 'info'">
                {{ item.status }}
              </span>
              <span class="time">{{ item.updated_at?.slice(5, 16) || '-' }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-block">暂无最近更新记录。</div>
      </div>

      <!-- 最近任务 -->
      <div class="panel-card">
        <h3>最近任务</h3>
        <div v-if="jobs.length" class="recent-list">
          <div v-for="job in jobs.slice(0, 6)" :key="job.id" class="recent-row">
            <div class="recent-title">{{ job.name }}</div>
            <div class="recent-meta">
              <span class="badge" :class="job.status === 'success' ? 'ok' : job.status === 'failed' ? 'bad' : 'warn'">
                {{ job.status }}
              </span>
              <span class="time">{{ job.started_at?.slice(5, 16) || '-' }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-block">暂无后台任务记录。</div>
      </div>
    </div>

    <!-- 详细状态分布 -->
    <div class="panel-card" style="margin-top: 20px;">
      <h3>详细状态统计</h3>
      <div class="status-breakdown">
        <div v-for="(count, status) in statusBreakdown" :key="status" class="breakdown-item">
          <span class="breakdown-status">{{ status }}</span>
          <span class="breakdown-count">{{ count }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(245, 249, 255, 0.5);
  border-radius: 8px;
}

.status-label {
  font-size: 13px;
  color: var(--text-soft);
}

.status-value {
  font-weight: 600;
  font-size: 16px;
}

.text-success {
  color: var(--success);
}

.text-danger {
  color: var(--danger);
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recent-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: rgba(245, 249, 255, 0.5);
  border-radius: 8px;
}

.recent-title {
  font-size: 14px;
  font-weight: 500;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.recent-meta .time {
  font-size: 12px;
  color: var(--text-soft);
}

.status-breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.breakdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(245, 249, 255, 0.5);
  border-radius: 6px;
  font-size: 13px;
}

.breakdown-status {
  color: var(--text-soft);
}

.breakdown-count {
  font-weight: 600;
  min-width: 24px;
  text-align: center;
}
</style>
