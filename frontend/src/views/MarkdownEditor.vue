<template>
  <div class="markdown-editor">
    <!-- 顶部工具栏 -->
    <MdToolbar
      :theme="currentTheme"
      :formatting="formatting"
      :saving="saving"
      @insert="insertText"
      @heading="insertHeading"
      @insert-link="insertLink"
      @insert-image="insertImage"
      @upload-image="handleImageUpload"
      @format="handleFormat"
      @save="handleSave"
      @update:theme="switchTheme"
    />

    <!-- 主编辑区 -->
    <div class="editor-main">
      <!-- 左侧：编辑区 -->
      <div class="editor-pane">
        <div class="pane-header">
          <span>Markdown 编辑</span>
          <span class="char-count">{{ markdownContent.length }} 字符</span>
        </div>
        <textarea
          ref="editorRef"
          v-model="markdownContent"
          class="editor-textarea"
          placeholder="# 开始写作...

输入 Markdown 文本，右侧实时预览微信排版效果。

## 支持的语法
- **加粗**、*斜体*、~~删除线~~
- [链接](https://example.com)
- ![图片](https://example.com/img.png)
- > 引用文本
- 代码块、表格、列表等
"
          @input="onInput"
          @keydown.tab.prevent="insertTab"
          @contextmenu.prevent="openContextMenu"
        ></textarea>
      </div>

      <!-- 分隔条 -->
      <div class="resize-handle" @mousedown="startResize"></div>

      <!-- 右侧：预览区 -->
      <div class="preview-pane" :style="{ flex: `0 0 ${previewWidth}px` }">
        <MdPreview :html="renderedHtml" :css="themeCSS" />
      </div>
    </div>

    <!-- AI 助手面板 -->
    <el-drawer
      v-model="aiDrawerVisible"
      title="AI 写作助手"
      direction="rtl"
      size="420px"
    >
      <div class="ai-panel">
        <div class="ai-actions">
          <el-button @click="aiAction('续写')" :loading="aiLoading === '续写'">
            <el-icon><EditPen /></el-icon> 续写
          </el-button>
          <el-button @click="aiAction('润色')" :loading="aiLoading === '润色'">
            <el-icon><Brush /></el-icon> 润色
          </el-button>
          <el-button @click="aiAction('摘要')" :loading="aiLoading === '摘要'">
            <el-icon><Document /></el-icon> 摘要
          </el-button>
          <el-button @click="aiAction('扩写')" :loading="aiLoading === '扩写'">
            <el-icon><FullScreen /></el-icon> 扩写
          </el-button>
        </div>

        <el-input
          v-model="aiInstruction"
          type="textarea"
          :rows="3"
          placeholder="自定义指令（可选）..."
          style="margin-top: 12px"
        />

        <div v-if="aiResult" class="ai-result">
          <div class="ai-result-header">
            <span>AI 生成结果</span>
            <el-button size="small" text @click="applyAIResult">应用</el-button>
          </div>
          <div class="ai-result-content" v-html="aiResultPreview"></div>
        </div>
      </div>
    </el-drawer>

    <!-- 右键菜单 -->
    <EditorContextMenu
      :visible="ctxMenu.visible"
      :x="ctxMenu.x"
      :y="ctxMenu.y"
      @close="closeContextMenu"
      @insert="(text) => { insertText(text); closeContextMenu() }"
      @heading="(level) => { insertHeading(level); closeContextMenu() }"
      @insert-image="() => { insertImage(); closeContextMenu() }"
      @upload-image="() => { handleImageUpload(); closeContextMenu() }"
      @insert-link="() => { insertLink(); closeContextMenu() }"
      @format="() => { handleFormat(); closeContextMenu() }"
      @export-md="() => { exportMarkdown(); closeContextMenu() }"
      @clear="() => { clearContent(); closeContextMenu() }"
      @component="() => { showComponentDialog = true; closeContextMenu() }"
    />

    <!-- 组件对话框 -->
    <ComponentDialog v-model:visible="showComponentDialog" @insert="insertComponentHtml" />

    <!-- 底部状态栏 -->
    <div class="editor-footer">
      <span>{{ currentTheme === 'default' ? '经典' : currentTheme === 'grace' ? '优雅' : '极简' }}主题</span>
      <el-button size="small" text @click="aiDrawerVisible = true">
        <el-icon><MagicStick /></el-icon> AI 助手
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import MdToolbar from '../components/editor/MdToolbar.vue'
import MdPreview from '../components/editor/MdPreview.vue'
import EditorContextMenu from '../components/editor/EditorContextMenu.vue'
import ComponentDialog from '../components/editor/ComponentDialog.vue'
import { renderMarkdown, getThemeCSS, htmlToMarkdown, escapeHtml } from '../composables/useMarkdownRender'
import { formatMarkdown } from '../composables/useMdFormat'
import api from '../api'
import { useAppStore } from '../stores'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

// 右键菜单
const ctxMenu = ref({ visible: false, x: 0, y: 0 })
function openContextMenu(e) {
  ctxMenu.value = { visible: true, x: e.clientX, y: e.clientY }
}
function closeContextMenu() {
  ctxMenu.value.visible = false
}

// 导出 MD
function exportMarkdown() {
  const blob = new Blob([markdownContent.value], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'article.md'
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出 Markdown 文件')
}

// 组件对话框
const showComponentDialog = ref(false)
function insertComponentHtml(html) {
  insertText('\n' + html + '\n')
}

// 清空
function clearContent() {
  markdownContent.value = ''
  ElMessage.success('内容已清空')
}

// 状态
const markdownContent = ref('')
const currentTheme = ref('default')
const themeCSS = ref('')
const formatting = ref(false)
const saving = ref(false)
const editorRef = ref(null)
const previewWidth = ref(400)

// AI 面板
const aiDrawerVisible = ref(false)
const aiLoading = ref(null)
const aiInstruction = ref('')
const aiResult = ref('')
const aiResultPreview = computed(() => renderMarkdown(aiResult.value))

// 渲染
const renderedHtml = computed(() => renderMarkdown(markdownContent.value))

// 加载主题 CSS
async function switchTheme(name) {
  currentTheme.value = name
  themeCSS.value = await getThemeCSS(name)
}

// 防抖渲染
let debounceTimer = null
function onInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    // 触发响应式更新
  }, 150)
}

// 插入文本
function insertText(text) {
  const el = editorRef.value
  if (!el) return
  const start = el.selectionStart
  const end = el.selectionEnd
  markdownContent.value = markdownContent.value.slice(0, start) + text + markdownContent.value.slice(end)
  nextTick(() => {
    el.focus()
    el.selectionStart = el.selectionEnd = start + text.length
  })
}

// 插入标题
function insertHeading(level) {
  const prefix = '#'.repeat(level) + ' '
  insertAtLineStart(prefix)
}

// 插入链接
function insertLink() {
  const el = editorRef.value
  const selection = el ? markdownContent.value.slice(el.selectionStart, el.selectionEnd) : ''
  const text = selection || '链接文本'
  insertText(`[${text}](url)`)
}

// 插入图片（从URL）
function insertImage() {
  insertText('![图片描述](图片URL)')
}

// 上传图片到图床
const uploadingImage = ref(false)
const imageUploadInput = ref(null)

function handleImageUpload() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/png,image/jpeg,image/gif,image/webp,image/svg+xml,image/bmp'
  input.onchange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > 10 * 1024 * 1024) {
      ElMessage.warning('图片不能超过 10 MB')
      return
    }

    uploadingImage.value = true
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('provider', 'local')

      const resp = await fetch('/api/image-hosting/upload', {
        method: 'POST',
        body: formData,
      })

      if (resp.ok) {
        const data = await resp.json()
        const altText = file.name.replace(/\.[^.]+$/, '')
        insertText(`![${altText}](${data.url})`)
        ElMessage.success('图片已上传到图床')
      } else {
        const err = await resp.json()
        ElMessage.error(err.error || '上传失败')
      }
    } catch (e) {
      ElMessage.error('上传失败: ' + e.message)
    } finally {
      uploadingImage.value = false
    }
  }
  input.click()
}

// Tab 缩进
function insertTab() {
  insertText('  ')
}

// 在行首插入
function insertAtLineStart(prefix) {
  const el = editorRef.value
  if (!el) return
  const start = el.selectionStart
  const beforeCursor = markdownContent.value.slice(0, start)
  const lastNewline = beforeCursor.lastIndexOf('\n')
  const lineStart = lastNewline + 1
  markdownContent.value = markdownContent.value.slice(0, lineStart) + prefix + markdownContent.value.slice(lineStart)
  nextTick(() => {
    el.focus()
    el.selectionStart = el.selectionEnd = lineStart + prefix.length
  })
}

// 调整面板宽度
let resizeStart = 0
let resizeWidth = 0

function startResize(e) {
  resizeStart = e.clientX
  resizeWidth = previewWidth.value
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
}

function onResize(e) {
  const delta = resizeStart - e.clientX
  previewWidth.value = Math.max(280, Math.min(700, resizeWidth + delta))
}

function stopResize() {
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

// 一键排版
async function handleFormat() {
  formatting.value = true
  try {
    markdownContent.value = await formatMarkdown(markdownContent.value)
    ElMessage.success('排版完成')
  } catch (e) {
    ElMessage.error('排版失败: ' + e.message)
  } finally {
    formatting.value = false
  }
}

// 保存文章
async function handleSave() {
  const content = markdownContent.value
  if (!content.trim()) {
    ElMessage.warning('请输入内容')
    return
  }

  saving.value = true
  try {
    const accountId = appStore.selectedAccountId || 'default'
    const html = renderedHtml.value

    // 检查是否有文章 ID（编辑已有文章）
    const articleId = route.query.articleId
    if (articleId) {
      await api.articles.update(articleId, { content: html, markdown_content: content })
      ElMessage.success('文章已更新')
    } else {
      // 创建新文章
      const firstLine = content.trim().split('\n')[0].replace(/^#+\s*/, '')
      const title = firstLine || '未命名文章'
      const result = await api.articles.create({
        account_id: accountId,
        source_title: title,
        content: html,
        markdown_content: content,
        publish_ready: false,
      })
      ElMessage.success('文章已保存')
      if (result?.id) {
        router.replace({ query: { articleId: result.id } })
      }
    }
  } catch (e) {
    ElMessage.error('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

// AI 操作
async function aiAction(action) {
  aiLoading.value = action
  aiResult.value = ''
  try {
    const instruction = aiInstruction.value
    const context = markdownContent.value.slice(-2000) // 取末尾 2000 字符作为上下文
    const prompt = instruction
      ? `${action}以下内容，${instruction}：\n\n${context}`
      : `请${action}以下 Markdown 内容，保持语言风格一致，直接输出结果：\n\n${context}`

    // 使用后端 AI 接口
    const accountId = appStore.selectedAccountId || 'default'
    const response = await fetch('/api/articles/dummy/rewrite', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        style: 'tech_expert',
        instructions: prompt,
        use_references: false,
      }),
    })

    if (response.ok) {
      const data = await response.json()
      // 因为是异步任务，轮询结果
      if (data.task_id) {
        const result = await pollTask(data.task_id)
        if (result?.result?.content) {
          aiResult.value = htmlToMarkdown(result.result.content)
        } else {
          ElMessage.warning('AI 任务已完成但无内容返回')
        }
      }
    } else {
      throw new Error('AI 请求失败')
    }
  } catch (e) {
    ElMessage.error(`AI ${action}失败: ` + e.message)
  } finally {
    aiLoading.value = null
  }
}

// 轮询任务
async function pollTask(taskId) {
  for (let i = 0; i < 120; i++) {
    const task = await api.tasks.get(taskId)
    if (task.status === 'completed' || task.status === 'failed') {
      return task
    }
    await new Promise(r => setTimeout(r, 2000))
  }
  throw new Error('任务超时')
}

// 应用 AI 结果
function applyAIResult() {
  if (aiResult.value) {
    markdownContent.value = markdownContent.value + '\n\n' + aiResult.value
    aiResult.value = ''
    ElMessage.success('已插入到编辑器末尾')
  }
}

// 加载已有文章
async function loadArticle(id) {
  try {
    const article = await api.articles.get(id)
    if (article) {
      if (article.markdown_content) {
        markdownContent.value = article.markdown_content
      } else if (article.content) {
        // 将 HTML 转为 Markdown
        markdownContent.value = htmlToMarkdown(article.content)
        if (!markdownContent.value.trim()) {
          markdownContent.value = article.content
        }
      }
    }
  } catch (e) {
    console.error('加载文章失败:', e)
  }
}

// 初始化
onMounted(async () => {
  await switchTheme('default')

  const articleId = route.query.articleId
  if (articleId) {
    await loadArticle(articleId)
  }

  // 聚焦编辑器
  nextTick(() => {
    editorRef.value?.focus()
  })
})
</script>

<style scoped>
.markdown-editor {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  background: #fff;
}

.editor-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 300px;
}

.pane-header {
  display: flex;
  justify-content: space-between;
  padding: 6px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e5e5e5;
  font-size: 13px;
  color: #666;
}

.char-count {
  color: #999;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  padding: 16px 20px;
  font-family: 'Fira Code', Menlo, Consolas, monospace;
  font-size: 14px;
  line-height: 1.7;
  color: #333;
  background: #fefefe;
}

.editor-textarea::placeholder {
  color: #ccc;
}

.resize-handle {
  width: 4px;
  cursor: col-resize;
  background: #e5e5e5;
  transition: background 0.2s;
}

.resize-handle:hover {
  background: var(--el-color-primary, #6366f1);
}

.preview-pane {
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 16px;
  background: #fafafa;
  border-top: 1px solid #e5e5e5;
  font-size: 12px;
  color: #999;
}

/* AI 面板 */
.ai-panel {
  padding: 0;
}

.ai-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ai-result {
  margin-top: 16px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  overflow: hidden;
}

.ai-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #fafafa;
  font-size: 13px;
  font-weight: 600;
}

.ai-result-content {
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
}
</style>
