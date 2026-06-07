<template>
  <div class="feeds-page">
    <div class="page-header">
      <div>
        <h2>信息源</h2>
        <p class="page-desc">通过 RSS 订阅自动采集内容到素材库</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>添加订阅
      </el-button>
    </div>

    <!-- 列表 -->
    <div v-if="feeds.length > 0" class="feed-grid">
      <div v-for="feed in feeds" :key="feed.id" class="feed-card" :class="{ inactive: !feed.is_active }">
        <div class="feed-top">
          <div class="feed-header">
            <span class="feed-name">{{ feed.name }}</span>
            <el-switch v-model="feed.is_active" size="small" @change="toggleFeed(feed)" />
          </div>
          <div class="feed-url" :title="feed.url">{{ feed.url }}</div>
          <div class="feed-meta">
            <el-tag size="small" type="info">{{ feed.category || '未分类' }}</el-tag>
            <el-tag size="small" v-if="feed.account_id">{{ feed.account_id }}</el-tag>
          </div>
        </div>

        <div class="feed-stats">
          <div class="stat-item">
            <span class="stat-num">{{ feed.item_count || 0 }}</span>
            <span class="stat-label">累计抓取</span>
          </div>
          <div class="stat-item">
            <span class="stat-num">{{ formatDate(feed.last_fetched_at) }}</span>
            <span class="stat-label">上次抓取</span>
          </div>
        </div>

        <div class="feed-actions">
          <el-button size="small" type="primary" @click="fetchFeed(feed)" :loading="fetchingId === feed.id">
            <el-icon><Refresh /></el-icon>抓取
          </el-button>
          <el-button size="small" @click="openEditDialog(feed)">编辑</el-button>
          <el-button size="small" type="danger" plain @click="handleDelete(feed)">删除</el-button>
        </div>
      </div>
    </div>

    <el-empty v-else description="还没有添加任何信息源">
      <el-button type="primary" @click="openCreateDialog">添加第一个订阅</el-button>
    </el-empty>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑信息源' : '添加信息源'"
      width="560px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如 36氪、少数派" />
        </el-form-item>

        <el-form-item label="RSS 地址" prop="url">
          <el-input v-model="form.url" placeholder="https://example.com/feed.xml" />
        </el-form-item>

        <el-form-item label="账户" prop="account_id">
          <el-select v-model="form.account_id" style="width: 100%">
            <el-option
              v-for="acc in accountStore.accounts"
              :key="acc.account_id"
              :label="`${acc.name} (${acc.account_id})`"
              :value="acc.account_id"
            />
          </el-select>
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类">
              <el-input v-model="form.category" placeholder="如 科技、商业" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="抓取间隔">
              <el-input-number v-model="form.fetch_interval" :min="10" :max="1440" :step="10" style="width: 100%" />
              <span class="form-tip">分钟</span>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { useAccountStore, useAppStore } from '../stores'
import api from '../api'

const accountStore = useAccountStore()
const appStore = useAppStore()

const feeds = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const fetchingId = ref(null)
const formRef = ref(null)

const form = ref({
  name: '',
  url: '',
  account_id: '',
  category: '',
  fetch_interval: 60,
})

const rules = {
  name: [{ required: true, message: '请输入名称' }],
  url: [{ required: true, message: '请输入 RSS 地址' }],
  account_id: [{ required: true, message: '请选择账户' }],
}

async function loadFeeds() {
  try {
    const params = appStore.selectedAccountId ? { account_id: appStore.selectedAccountId } : undefined
    feeds.value = await api.feeds.list(params)
  } catch (e) {
    ElMessage.error('加载信息源失败')
  }
}

function openCreateDialog() {
  isEdit.value = false
  form.value = {
    name: '',
    url: '',
    account_id: appStore.selectedAccountId || accountStore.accounts[0]?.account_id || '',
    category: '',
    fetch_interval: 60,
  }
  dialogVisible.value = true
}

function openEditDialog(feed) {
  isEdit.value = true
  form.value = { ...feed }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (isEdit.value) {
      await api.feeds.update(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.feeds.create(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadFeeds()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function fetchFeed(feed) {
  fetchingId.value = feed.id
  try {
    const result = await api.feeds.fetch(feed.id)
    if (result.new_items > 0) {
      ElMessage.success(`抓取完成：新增 ${result.new_items} 条，跳过 ${result.skipped} 条`)
    } else {
      ElMessage.info('没有新内容')
    }
    loadFeeds()
  } catch (e) {
    ElMessage.error(e.message || '抓取失败')
  } finally {
    fetchingId.value = null
  }
}

async function toggleFeed(feed) {
  try {
    await api.feeds.toggle(feed.id)
  } catch (e) {
    feed.is_active = !feed.is_active // 回滚
    ElMessage.error('操作失败')
  }
}

async function handleDelete(feed) {
  try {
    await ElMessageBox.confirm(`确定删除「${feed.name}」？`, '确认删除', { type: 'warning' })
    await api.feeds.delete(feed.id)
    ElMessage.success('已删除')
    loadFeeds()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.message || '删除失败')
  }
}

function formatDate(val) {
  if (!val) return '从未'
  try {
    return new Date(val).toLocaleString('zh-CN', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return val }
}

onMounted(async () => {
  await accountStore.fetchAccounts()
  loadFeeds()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.page-header h2 { margin: 0; font-size: 22px; font-weight: 700; color: var(--text-primary); }
.page-desc { margin: 6px 0 0; font-size: 14px; color: var(--text-secondary); }

.feed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.feed-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.feed-card:hover { border-color: var(--accent); box-shadow: var(--shadow); }
.feed-card.inactive { opacity: 0.6; }

.feed-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.feed-name { font-size: 16px; font-weight: 650; color: var(--text-primary); }
.feed-url {
  font-size: 12px; color: var(--text-muted); overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; margin-bottom: 8px;
}
.feed-meta { display: flex; gap: 6px; flex-wrap: wrap; }

.feed-stats {
  display: flex; gap: 24px; margin: 14px 0; padding: 12px 0;
  border-top: 1px solid var(--border-light); border-bottom: 1px solid var(--border-light);
}
.stat-item { display: flex; flex-direction: column; gap: 2px; }
.stat-num { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.stat-label { font-size: 11px; color: var(--text-muted); }

.feed-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.form-tip { font-size: 12px; color: var(--text-secondary); margin-left: 8px; }
</style>
