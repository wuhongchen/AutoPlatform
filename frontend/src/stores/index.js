import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

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
  
  const loading = ref(false)
  
  async function fetchStats(accountId) {
    try {
      const data = await api.accounts.stats(accountId || 'default')
      stats.value = data
      return data
    } catch (error) {
      console.error('获取统计失败:', error)
      return null
    }
  }
  
  return {
    stats,
    loading,
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
  
  return {
    inspirations,
    fetchInspirations,
    collect,
    approve
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
