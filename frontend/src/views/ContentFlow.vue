<template>
  <div class="content-flow-page">
    <el-row :gutter="24">
      <!-- 左侧：配置 -->
      <el-col :span="8">
        <div class="config-panel">
          <div class="panel-header">
            <h3>链接成稿</h3>
            <el-tag v-if="activeTask" :type="taskStatusType" size="small" effect="dark">
              {{ taskStatusLabel }}
            </el-tag>
          </div>

          <el-form :model="form" label-position="top" class="flow-form">
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

            <el-form-item label="改写风格">
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

            <el-form-item label="排版模板">
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
                placeholder="可选：增加数据支撑、语气更口语化..."
              />
            </el-form-item>
          </el-form>

          <button
            class="run-btn"
            :class="{ loading: running }"
            :disabled="!canRun || running"
            @click="startFlow"
          >
            <span v-if="running" class="run-btn-spinner"/>
            <el-icon v-else><MagicStick /></el-icon>
            {{ running ? '处理中...' : '一次性生成' }}
          </button>

          <div v-if="activeTask?.id" class="task-links">
            <el-button text @click="router.push('/tasks')">任务看板</el-button>
            <el-button v-if="result?.article_id" text type="primary" @click="openArticle">文章详情</el-button>
          </div>
        </div>
      </el-col>

      <!-- 右侧：结果 -->
      <el-col :span="16">
        <div class="result-panel">
          <div class="panel-header">
            <h3>流程状态</h3>
            <el-button :icon="Refresh" size="small" text @click="refreshCurrentTask" :disabled="!activeTask?.id">
              刷新
            </el-button>
          </div>

          <el-steps :active="stepActive" finish-status="success" align-center class="flow-steps">
            <el-step title="采集" />
            <el-step title="文章" />
            <el-step title="改写" />
            <el-step title="排版" />
          </el-steps>

          <div v-if="activeTask && !isTaskDone" class="loading-state">
            <el-skeleton :rows="8" animated />
          </div>

          <div v-else-if="activeTask?.status === 'failed'" class="error-state">
            <el-result icon="error" title="任务失败" :sub-title="activeTask.error_message || '请查看任务看板中的错误信息'" />
          </div>

          <el-empty v-else-if="!result" description="输入链接后点击「一次性生成」" />

          <div v-else class="result-body">
            <!-- 工具栏 -->
            <div class="result-bar">
              <div class="result-meta">
                <div class="result-title">{{ result.title || currentArticle?.source_title || '无标题' }}</div>
                <div class="result-tags">
                  <el-tag size="small" type="success" effect="dark">已改写</el-tag>
                  <el-tag size="small" type="info">{{ result.style }}</el-tag>
                  <el-tag size="small" type="warning">{{ result.template }}</el-tag>
                </div>
              </div>
              <div class="result-actions">
                <el-button @click="refreshWechatCopy" :loading="formatting" size="small">
                  <el-icon><Refresh /></el-icon>重排版
                </el-button>
                <el-button
                  type="primary"
                  size="small"
                  @click="copyWechatHtml"
                  :loading="copying || clipboardPreparing"
                  :disabled="!wechatHtml || copying"
                >
                  <el-icon><CopyDocument /></el-icon>复制公众号格式
                </el-button>
              </div>
            </div>

            <!-- 关联链接 -->
            <div class="related-links">
              <el-button size="small" text @click="router.push('/inspirations')">
                <el-icon><Collection /></el-icon>素材库
              </el-button>
              <el-button size="small" text @click="router.push('/articles')">
                <el-icon><Document /></el-icon>我的文章
              </el-button>
              <el-button size="small" text @click="router.push({ name: 'Rewrite', query: { id: result.article_id } })">
                <el-icon><MagicStick /></el-icon>AI 改写
              </el-button>
            </div>

            <!-- 预览 -->
            <div class="preview-shell">
              <div class="preview-topbar">
                <span>微信公众号格式预览</span>
                <span class="preview-count">{{ copyTextLength }} 字</span>
              </div>
              <div class="preview-content" v-html="previewHtml" />
            </div>
          </div>
        </div>
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
  pollTimer.value = setInterval(async () => { await pollTask(taskId) }, 2000)
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
    if (showMessage) ElMessage.success('排版已更新')
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
  container.style.cssText = 'position:fixed;left:-9999px;top:0;width:1px;height:1px;overflow:hidden'
  container.innerHTML = html
  document.body.appendChild(container)
  const selection = window.getSelection()
  const range = document.createRange()
  range.selectNodeContents(container)
  selection.removeAllRanges()
  selection.addRange(range)
  container.focus()
  try {
    if (!document.execCommand('copy')) throw new Error('浏览器拒绝复制')
  } finally {
    selection.removeAllRanges()
    document.body.removeChild(container)
  }
}

function copyPlainTextBySelection(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'true')
  textarea.style.cssText = 'position:fixed;left:-9999px;top:0'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()
  try {
    if (!document.execCommand('copy')) throw new Error('浏览器拒绝复制')
  } finally {
    document.body.removeChild(textarea)
  }
}

async function prepareClipboardHtml(rawHtml) {
  clipboardPreparing.value = true
  const container = document.createElement('div')
  try {
    container.innerHTML = rawHtml
    let inlinedBytes = 0
    for (const img of Array.from(container.querySelectorAll('img'))) {
      const source = (img.getAttribute('src') || img.getAttribute('data-src') || '').trim()
      if (!source) continue
      const absoluteUrl = normalizeImageUrl(source)
      if (!absoluteUrl) continue
      img.setAttribute('src', absoluteUrl)
      img.setAttribute('data-src', absoluteUrl)
      img.removeAttribute('loading')
      img.removeAttribute('referrerpolicy')
      if (!isLocalImageUrl(absoluteUrl) || inlinedBytes >= MAX_INLINE_TOTAL_IMAGE_BYTES) continue
      const inlined = await fetchImageAsDataUrl(absoluteUrl, MAX_INLINE_TOTAL_IMAGE_BYTES - inlinedBytes)
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
  try { return new URL(source, window.location.origin).href }
  catch { return source }
}

function isLocalImageUrl(source) {
  try {
    const url = new URL(source, window.location.origin)
    return url.origin === window.location.origin && url.pathname.startsWith('/local_images/')
  } catch { return false }
}

async function fetchImageAsDataUrl(url, remainingBytes) {
  try {
    const response = await fetch(url, { cache: 'no-store' })
    if (!response.ok) return null
    const blob = await response.blob()
    if (!blob.type.startsWith('image/') || blob.size > MAX_INLINE_IMAGE_BYTES || blob.size > remainingBytes) return null
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

function openArticle() {
  if (!result.value?.article_id) return
  router.push({ name: 'Rewrite', query: { id: result.value.article_id } })
}

function stopPolling() {
  if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }
}

onMounted(loadData)
onUnmounted(stopPolling)
watch(() => appStore.selectedAccountId, (value) => {
  if (value && !activeTask.value?.id) { form.account_id = value; selectDefaults() }
})
watch(currentAccount, () => { if (!activeTask.value?.id) selectDefaults() })
</script>

<style scoped>
.content-flow-page {
  min-height: 100%;
}

/* === 面板通用 === */
.config-panel, .result-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-light);
}
.panel-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
  color: var(--text-primary);
}

/* === 配置表单 === */
.flow-form {
  padding: 20px 24px;
}
.flow-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.option-desc {
  color: var(--text-muted);
  font-size: 12px;
  margin-left: 8px;
}

/* === 主按钮 === */
.run-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: calc(100% - 48px);
  margin: 0 24px 20px;
  padding: 14px 0;
  font-size: 16px;
  font-weight: 650;
  color: #fff;
  border: none;
  border-radius: var(--radius);
  background: var(--accent-gradient);
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.01em;
}
.run-btn:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(99,102,241,0.35);
  transform: translateY(-1px);
}
.run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.run-btn.loading {
  background: var(--accent);
}

.run-btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* === 任务链接 === */
.task-links {
  padding: 0 24px 16px;
  display: flex;
  gap: 8px;
  justify-content: center;
}

/* === 步骤条 === */
.flow-steps {
  padding: 24px 28px 8px;
}

/* === 状态区 === */
.loading-state, .error-state {
  padding: 24px 28px;
}

/* === 结果 === */
.result-body {
  padding: 0 24px 24px;
}

.result-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 20px 0 16px;
  border-bottom: 1px solid var(--border-light);
}

.result-title {
  font-size: 17px;
  font-weight: 650;
  color: var(--text-primary);
  line-height: 1.5;
  word-break: break-word;
}

.result-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.result-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* === 关联链接 === */
.related-links {
  display: flex;
  gap: 4px;
  padding: 12px 0;
}

/* === 预览壳 === */
.preview-shell {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: #fff;
  overflow: hidden;
}

.preview-topbar {
  height: 40px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
  background: #fafafa;
  border-bottom: 1px solid var(--border-light);
}

.preview-count {
  color: var(--text-muted);
}

.preview-content {
  max-height: 600px;
  overflow-y: auto;
  padding: 20px;
  line-height: 1.85;
  color: var(--text-primary);
}

.preview-content :deep(img) {
  max-width: 100%;
  height: auto;
}

.preview-content :deep(style) {
  display: none;
}
</style>
