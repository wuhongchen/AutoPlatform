import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

const SELECTED_ACCOUNT_KEY = 'autoplatform:selectedAccountId'

function readSelectedAccountId() {
  if (typeof window === 'undefined') return ''
  return window.localStorage.getItem(SELECTED_ACCOUNT_KEY) || ''
}

function persistSelectedAccountId(value) {
  if (typeof window === 'undefined') return
  if (value) {
    window.localStorage.setItem(SELECTED_ACCOUNT_KEY, value)
  } else {
    window.localStorage.removeItem(SELECTED_ACCOUNT_KEY)
  }
}

// 账户状态
export const useAccountStore = defineStore('accounts', () => {
  const accounts = ref([])
  
  async function fetchAccounts() {
    const data = await api.accounts.list()
    accounts.value = data
    return data
  }
  
  async function createAccount(data) {
    return await api.accounts.create(data)
  }
  
  return {
    accounts,
    fetchAccounts,
    createAccount
  }
})

// 全局状态
export const useAppStore = defineStore('app', () => {
  const stats = ref({
    articles: {},
    pipeline: {},
    inspiration: {}
  })

  const selectedAccountId = ref(readSelectedAccountId())
  const loading = ref(false)

  function setSelectedAccount(accountId) {
    selectedAccountId.value = accountId || ''
    persistSelectedAccountId(selectedAccountId.value)
  }

  async function fetchStats(accountId) {
    try {
      const targetAccountId = accountId ?? selectedAccountId.value
      const params = targetAccountId ? { account_id: targetAccountId } : undefined
      const data = await api.stats(params)
      stats.value = data
      return data
    } catch (error) {
      console.error('获取统计失败:', error)
      return null
    }
  }
  
  return {
    stats,
    selectedAccountId,
    loading,
    setSelectedAccount,
    fetchStats
  }
})

// 风格预设状态
export const useStyleStore = defineStore('styles', () => {
  const styles = ref([])
  const currentStyle = ref(null)
  
  const activeStyles = computed(() => 
    styles.value.filter(s => s.is_active !== false)
  )
  
  async function fetchStyles(includeInactive = false) {
    const data = await api.styles.list({ include_inactive: includeInactive })
    styles.value = data
    return data
  }
  
  async function createStyle(data) {
    const result = await api.styles.create(data)
    await fetchStyles(true)
    return result
  }
  
  async function updateStyle(id, data) {
    const result = await api.styles.update(id, data)
    await fetchStyles(true)
    return result
  }
  
  async function deleteStyle(id) {
    await api.styles.delete(id)
    await fetchStyles(true)
  }
  
  async function toggleStyle(id) {
    await api.styles.toggle(id)
    await fetchStyles(true)
  }
  
  return {
    styles,
    currentStyle,
    activeStyles,
    fetchStyles,
    createStyle,
    updateStyle,
    deleteStyle,
    toggleStyle
  }
})

// 灵感库状态
export const useInspirationStore = defineStore('inspirations', () => {
  const inspirations = ref([])
  
  async function fetchInspirations(params) {
    const data = await api.inspirations.list(params)
    inspirations.value = data
    return data
  }
  
  async function collect(url, accountId) {
    return await api.inspirations.collect({ url, account_id: accountId })
  }
  
  async function approve(id) {
    return await api.inspirations.approve(id)
  }

  async function deleteInspiration(id) {
    return await api.inspirations.delete(id)
  }

  return {
    inspirations,
    fetchInspirations,
    collect,
    approve,
    deleteInspiration
  }
})

// 文章状态
export const useArticleStore = defineStore('articles', () => {
  const articles = ref([])
  const currentArticle = ref(null)
  
  async function fetchArticles(params) {
    const data = await api.articles.list(params)
    articles.value = data
    return data
  }
  
  async function getArticle(id) {
    const data = await api.articles.get(id)
    currentArticle.value = data
    return data
  }
  
  async function rewrite(id, data) {
    return await api.articles.rewrite(id, data)
  }
  
  async function publish(id, template) {
    return await api.articles.publish(id, { template })
  }
  
  return {
    articles,
    currentArticle,
    fetchArticles,
    getArticle,
    rewrite,
    publish
  }
})

// 任务状态
export const useTaskStore = defineStore('tasks', () => {
  const tasks = ref([])
  const taskStats = ref({})
  const loading = ref(false)
  
  async function fetchTasks(params = {}) {
    loading.value = true
    try {
      const data = await api.tasks.list(params)
      tasks.value = data
      return data
    } finally {
      loading.value = false
    }
  }
  
  async function getTask(id) {
    const data = await api.tasks.get(id)
    return data
  }
  
  async function createTask(data) {
    return await api.tasks.create(data)
  }
  
  async function deleteTask(id) {
    await api.tasks.delete(id)
  }
  
  async function pollTask(id, interval = 2000, maxAttempts = 60) {
    // 轮询任务状态直到完成或失败
    for (let i = 0; i < maxAttempts; i++) {
      const task = await getTask(id)
      if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
        return task
      }
      await new Promise(resolve => setTimeout(resolve, interval))
    }
    throw new Error('轮询超时')
  }
  
  const pendingCount = computed(() => {
    const stats = taskStats.value || {}
    return (stats.pending || 0) + (stats.running || 0)
  })
  
  const completedCount = computed(() => {
    const stats = taskStats.value || {}
    return stats.completed || 0
  })
  
  const failedCount = computed(() => {
    const stats = taskStats.value || {}
    return stats.failed || 0
  })
  
  return {
    tasks,
    taskStats,
    loading,
    pendingCount,
    completedCount,
    failedCount,
    fetchTasks,
    getTask,
    createTask,
    deleteTask,
    pollTask
  }
})
