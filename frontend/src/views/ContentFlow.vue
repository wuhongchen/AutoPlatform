<template>
  <div class="content-flow-page">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="never" class="flow-panel">
          <template #header>
            <div class="panel-header">
              <span>链接成稿</span>
              <el-tag v-if="activeTask" :type="taskStatusType" size="small">
                {{ taskStatusLabel }}
              </el-tag>
            </div>
          </template>

          <el-form :model="form" label-position="top">
            <el-form-item label="文章链接">
              <el-input
                v-model="form.url"
                type="textarea"
                :rows="3"
                placeholder="https://mp.weixin.qq.com/s/..."
                clearable
              />
            </el-form-item>

            <el-form-item label="账户">
              <el-select v-model="form.account_id" style="width: 100%">
                <el-option
                  v-for="acc in accountStore.accounts"
                  :key="acc.account_id"
                  :label="`${acc.name} (${acc.account_id})`"
                  :value="acc.account_id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="账户风格">
              <el-select v-model="form.style" style="width: 100%">
                <el-option
                  v-for="style in styleStore.activeStyles"
                  :key="style.id"
                  :label="style.name"
                  :value="style.id"
                >
                  <span>{{ style.name }}</span>
                  <span class="option-desc">{{ style.description }}</span>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="公众号模板">
              <el-select v-model="form.template" style="width: 100%" @change="refreshWechatCopy">
                <el-option
                  v-for="tpl in templateOptions"
                  :key="tpl.key"
                  :label="tpl.name"
                  :value="tpl.key"
                >
                  <span>{{ tpl.name }}</span>
                  <span class="option-desc">{{ tpl.description }}</span>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="参考素材">
              <el-switch
                v-model="form.use_references"
                active-text="启用"
                inactive-text="关闭"
              />
            </el-form-item>

            <el-form-item label="补充要求">
              <el-input
                v-model="form.instructions"
                type="textarea"
                :rows="4"
                placeholder="可选"
              />
            </el-form-item>
          </el-form>

          <el-button
            type="primary"
            size="large"
            class="run-button"
            :loading="running"
            :disabled="!canRun"
            @click="startFlow"
          >
            <el-icon><MagicStick /></el-icon>
            一次性生成
          </el-button>

          <div v-if="activeTask?.id" class="task-actions">
            <el-button type="info" link @click="router.push('/tasks')">
              任务看板
            </el-button>
            <el-button v-if="result?.article_id" type="primary" link @click="openArticle">
              文章详情
            </el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="never" class="flow-panel">
          <template #header>
            <div class="panel-header">
              <span>流程状态</span>
              <el-button :icon="Refresh" size="small" @click="refreshCurrentTask" :disabled="!activeTask?.id">
                刷新
              </el-button>
            </div>
          </template>

          <el-steps :active="stepActive" finish-status="success" process-status="process" align-center>
            <el-step title="采集" />
            <el-step title="文章" />
            <el-step title="改写" />
            <el-step title="排版" />
          </el-steps>

          <div v-if="activeTask && !isTaskDone" class="running-state">
            <el-skeleton :rows="6" animated />
          </div>

          <div v-else-if="activeTask?.status === 'failed'" class="failed-state">
            <el-result icon="error" title="任务失败" :sub-title="activeTask.error_message || '请查看任务看板中的错误信息'" />
          </div>

          <el-empty v-else-if="!result" description="暂无成稿" />

          <div v-else class="result-layout">
            <div class="result-toolbar">
              <div class="result-title">
                <div class="title-text">{{ result.title || currentArticle?.source_title || '无标题' }}</div>
                <div class="title-meta">
                  <el-tag size="small" type="success">已改写</el-tag>
                  <el-tag size="small" type="info">{{ result.style }}</el-tag>
                  <el-tag size="small" type="warning">{{ result.template }}</el-tag>
                </div>
              </div>
              <div class="result-buttons">
                <el-button @click="refreshWechatCopy" :loading="formatting">
                  <el-icon><Refresh /></el-icon>
                  重排版
                </el-button>
                <el-button
                  type="primary"
                  @click="copyWechatHtml"
                  :loading="copying || clipboardPreparing"
                  :disabled="!wechatHtml || copying || clipboardPreparing"
                >
                  <el-icon><CopyDocument /></el-icon>
                  复制公众号格式
                </el-button>
              </div>
            </div>

            <div class="module-links">
              <el-button @click="router.push('/inspirations')">
                <el-icon><Collection /></el-icon>
                素材库
              </el-button>
              <el-button @click="router.push('/articles')">
                <el-icon><Document /></el-icon>
                我的文章
              </el-button>
              <el-button @click="router.push({ name: 'Rewrite', query: { id: result.article_id } })">
                <el-icon><MagicStick /></el-icon>
                AI 改写
              </el-button>
            </div>

            <div class="preview-shell">
              <div class="preview-header">
                <span>微信公众号格式预览</span>
                <span>{{ copyTextLength }} 字</span>
              </div>
              <div class="wechat-preview" v-html="previewHtml" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Collection, CopyDocument, Document, MagicStick, Refresh } from '@element-plus/icons-vue'
import { useAccountStore, useAppStore, useArticleStore, useInspirationStore, useStyleStore, useTaskStore } from '../stores'
import api from '../api'

const router = useRouter()
const accountStore = useAccountStore()
const appStore = useAppStore()
const styleStore = useStyleStore()
const taskStore = useTaskStore()
const articleStore = useArticleStore()
const inspirationStore = useInspirationStore()

const form = reactive({
  url: '',
  account_id: '',
  style: '',
  template: 'default',
  use_references: true,
  instructions: '',
})

const templates = ref({})
const activeTask = ref(null)
const result = ref(null)
const currentArticle = ref(null)
const clipboardHtml = ref('')
const running = ref(false)
const formatting = ref(false)
const copying = ref(false)
const clipboardPreparing = ref(false)
const pollTimer = ref(null)

const MAX_INLINE_IMAGE_BYTES = 8 * 1024 * 1024
const MAX_INLINE_TOTAL_IMAGE_BYTES = 18 * 1024 * 1024

const currentAccount = computed(() => {
  return accountStore.accounts.find(acc => acc.account_id === form.account_id) || null
})

const templateOptions = computed(() => {
  return Object.entries(templates.value || {}).map(([key, tpl]) => ({
    key,
    name: tpl.name || key,
    description: tpl.description || '',
  }))
})

const canRun = computed(() => {
  return Boolean(form.url.trim() && form.account_id && form.style && form.template)
})

const isTaskDone = computed(() => {
  return ['completed', 'failed', 'cancelled'].includes(activeTask.value?.status)
})

const taskStatusType = computed(() => {
  const map = { pending: 'info', running: 'warning', completed: 'success', failed: 'danger', cancelled: 'info' }
  return map[activeTask.value?.status] || 'info'
})

const taskStatusLabel = computed(() => {
  const map = { pending: '待执行', running: '执行中', completed: '已完成', failed: '失败', cancelled: '已取消' }
  return map[activeTask.value?.status] || activeTask.value?.status || ''
})

const stepActive = computed(() => {
  if (!activeTask.value) return 0
  if (activeTask.value.status === 'completed') return 4
  if (activeTask.value.status === 'failed') return 1
  if (activeTask.value.status === 'running') return 2
  return 1
})

const wechatHtml = computed(() => result.value?.formatted_html || '')
const previewHtml = computed(() => wechatHtml.value.replace(/<style[\s\S]*?<\/style>/gi, ''))
const copyTextLength = computed(() => (result.value?.copy_text || '').length)

function selectDefaults() {
  if (!form.account_id) {
    form.account_id = appStore.selectedAccountId || accountStore.accounts[0]?.account_id || ''
  }

  const accountStyle = currentAccount.value?.pipeline_role
  const hasAccountStyle = styleStore.activeStyles.some(item => item.id === accountStyle)
  if (!form.style || !styleStore.activeStyles.some(item => item.id === form.style)) {
    form.style = hasAccountStyle ? accountStyle : (styleStore.activeStyles[0]?.id || '')
  }

  if (!templates.value[form.template]) {
    form.template = templates.value.default ? 'default' : (templateOptions.value[0]?.key || 'default')
  }
}

async function loadData() {
  await Promise.all([
    accountStore.fetchAccounts(),
    styleStore.fetchStyles(),
    loadTemplates(),
  ])
  selectDefaults()
}

async function loadTemplates() {
  templates.value = await api.templates.list()
  return templates.value
}

async function startFlow() {
  if (!canRun.value) return

  running.value = true
  result.value = null
  currentArticle.value = null
  clipboardHtml.value = ''
  activeTask.value = null
  stopPolling()

  try {
    const taskInfo = await api.contentFlow.run({
      url: form.url.trim(),
      account_id: form.account_id,
      style: form.style,
      template: form.template,
      use_references: form.use_references,
      instructions: form.instructions,
    })
    activeTask.value = { id: taskInfo.task_id, status: taskInfo.status }
    ElMessage.success(`任务已创建: ${taskInfo.task_id.slice(0, 8)}...`)
    startPolling(taskInfo.task_id)
  } catch (error) {
    ElMessage.error(error.message || '任务创建失败')
  } finally {
    running.value = false
  }
}

function startPolling(taskId) {
  stopPolling()
  pollTimer.value = setInterval(async () => {
    await pollTask(taskId)
  }, 2000)
  pollTask(taskId)
}

async function pollTask(taskId) {
  try {
    const task = await taskStore.getTask(taskId)
    activeTask.value = task
    if (task.status === 'completed') {
      stopPolling()
      result.value = task.result || null
      if (result.value?.article_id) {
        currentArticle.value = await articleStore.getArticle(result.value.article_id)
        await refreshWechatCopy(false)
      }
      if (form.account_id) {
        articleStore.fetchArticles({ account_id: form.account_id })
        inspirationStore.fetchInspirations({ account_id: form.account_id })
      }
      ElMessage.success('成稿已生成')
    } else if (task.status === 'failed') {
      stopPolling()
      ElMessage.error(task.error_message || '任务失败')
    }
  } catch (error) {
    console.error('轮询任务失败:', error)
  }
}

async function refreshCurrentTask() {
  if (!activeTask.value?.id) return
  await pollTask(activeTask.value.id)
}

async function refreshWechatCopy(showMessage = true) {
  if (!result.value?.article_id) return
  formatting.value = true
  try {
    const data = await api.articles.wechatCopy(result.value.article_id, { template: form.template })
    result.value = {
      ...result.value,
      template: data.template,
      formatted_html: data.html,
      copy_text: data.text,
    }
    clipboardHtml.value = await prepareClipboardHtml(data.html)
    if (showMessage) {
      ElMessage.success('排版已更新')
    }
  } catch (error) {
    ElMessage.error(error.message || '排版失败')
  } finally {
    formatting.value = false
  }
}

async function copyWechatHtml() {
  const rawHtml = wechatHtml.value
  if (!rawHtml) return

  copying.value = true
  const text = result.value?.copy_text || rawHtml.replace(/<[^>]+>/g, '')
  let htmlForClipboard = clipboardHtml.value || rawHtml
  try {
    if (!clipboardHtml.value) {
      htmlForClipboard = await prepareClipboardHtml(rawHtml)
      clipboardHtml.value = htmlForClipboard
    }
    if (navigator.clipboard && window.ClipboardItem) {
      await navigator.clipboard.write([
        new window.ClipboardItem({
          'text/html': new Blob([htmlForClipboard], { type: 'text/html' }),
          'text/plain': new Blob([text], { type: 'text/plain' }),
        }),
      ])
      ElMessage.success('已复制公众号格式')
      return
    }

    copyRichHtmlBySelection(htmlForClipboard)
    ElMessage.success('已复制公众号格式')
  } catch (error) {
    try {
      copyRichHtmlBySelection(htmlForClipboard)
      ElMessage.success('已复制公众号格式')
    } catch {
      try {
        copyPlainTextBySelection(text)
        ElMessage.success('已复制纯文本')
      } catch {
        ElMessage.error(error.message || '复制失败')
      }
    }
  } finally {
    copying.value = false
  }
}

function copyRichHtmlBySelection(html) {
  const container = document.createElement('div')
  container.setAttribute('contenteditable', 'true')
  container.style.position = 'fixed'
  container.style.left = '-9999px'
  container.style.top = '0'
  container.style.width = '1px'
  container.style.height = '1px'
  container.style.overflow = 'hidden'
  container.innerHTML = html
  document.body.appendChild(container)

  const selection = window.getSelection()
  const range = document.createRange()
  range.selectNodeContents(container)
  selection.removeAllRanges()
  selection.addRange(range)
  container.focus()

  try {
    const ok = document.execCommand('copy')
    if (!ok) {
      throw new Error('浏览器拒绝复制')
    }
  } finally {
    selection.removeAllRanges()
    document.body.removeChild(container)
  }
}

async function prepareClipboardHtml(rawHtml) {
  clipboardPreparing.value = true
  const container = document.createElement('div')
  try {
    container.innerHTML = rawHtml

    let inlinedBytes = 0
    const images = Array.from(container.querySelectorAll('img'))
    for (const img of images) {
      const source = (img.getAttribute('src') || img.getAttribute('data-src') || '').trim()
      if (!source) continue

      const absoluteUrl = normalizeImageUrl(source)
      if (!absoluteUrl) continue

      img.setAttribute('src', absoluteUrl)
      img.setAttribute('data-src', absoluteUrl)
      img.removeAttribute('loading')
      img.removeAttribute('referrerpolicy')

      if (!isLocalImageUrl(absoluteUrl)) continue
      if (inlinedBytes >= MAX_INLINE_TOTAL_IMAGE_BYTES) continue

      const inlined = await fetchImageAsDataUrl(
        absoluteUrl,
        MAX_INLINE_TOTAL_IMAGE_BYTES - inlinedBytes,
      )
      if (!inlined?.dataUrl) continue

      inlinedBytes += inlined.size
      img.setAttribute('src', inlined.dataUrl)
      img.setAttribute('data-src', inlined.dataUrl)
    }

    return container.innerHTML
  } finally {
    clipboardPreparing.value = false
  }
}

function normalizeImageUrl(source) {
  if (!source) return ''
  if (/^(data:|blob:)/i.test(source)) return source
  try {
    return new URL(source, window.location.origin).href
  } catch {
    return source
  }
}

function isLocalImageUrl(source) {
  try {
    const url = new URL(source, window.location.origin)
    return url.origin === window.location.origin && url.pathname.startsWith('/local_images/')
  } catch {
    return false
  }
}

async function fetchImageAsDataUrl(url, remainingBytes) {
  try {
    const response = await fetch(url, { cache: 'no-store' })
    if (!response.ok) return null

    const blob = await response.blob()
    if (!blob.type.startsWith('image/')) return null
    if (blob.size > MAX_INLINE_IMAGE_BYTES || blob.size > remainingBytes) return null

    const dataUrl = await blobToDataUrl(blob)
    return { dataUrl, size: blob.size }
  } catch (error) {
    console.warn('复制图片内联失败:', url, error)
    return null
  }
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(blob)
  })
}

function copyPlainTextBySelection(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'true')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '0'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()

  try {
    const ok = document.execCommand('copy')
    if (!ok) {
      throw new Error('浏览器拒绝复制')
    }
  } finally {
    document.body.removeChild(textarea)
  }
}

function openArticle() {
  if (!result.value?.article_id) return
  router.push({ name: 'Rewrite', query: { id: result.value.article_id } })
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

onMounted(loadData)
onUnmounted(stopPolling)

watch(() => appStore.selectedAccountId, (value) => {
  if (value && !activeTask.value?.id) {
    form.account_id = value
    selectDefaults()
  }
})

watch(currentAccount, () => {
  if (!activeTask.value?.id) {
    selectDefaults()
  }
})
</script>

<style scoped>
.content-flow-page {
  min-height: 100%;
}

.flow-panel {
  border-radius: 8px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.option-desc {
  color: #94a3b8;
  font-size: 12px;
  margin-left: 8px;
}

.run-button {
  width: 100%;
}

.task-actions {
  margin-top: 12px;
  display: flex;
  justify-content: center;
  gap: 10px;
}

.running-state {
  margin-top: 28px;
}

.failed-state {
  margin-top: 24px;
}

.result-layout {
  margin-top: 28px;
}

.result-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.result-title {
  min-width: 0;
}

.title-text {
  color: #111827;
  font-size: 18px;
  font-weight: 650;
  line-height: 1.5;
  word-break: break-word;
}

.title-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.result-buttons {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.module-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 16px;
}

.preview-shell {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}

.preview-header {
  height: 44px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #475569;
  font-size: 13px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.wechat-preview {
  max-height: 640px;
  overflow-y: auto;
  padding: 20px;
  line-height: 1.8;
  color: #1f2937;
}

.wechat-preview :deep(img) {
  max-width: 100%;
  height: auto;
}

.wechat-preview :deep(style) {
  display: none;
}
</style>
