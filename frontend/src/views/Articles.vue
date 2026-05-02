<template>
  <div class="articles-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="toolbar-left">
            <el-radio-group v-model="filterStatus" size="small">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="pending">草稿</el-radio-button>
              <el-radio-button label="rewriting">改写中</el-radio-button>
              <el-radio-button label="rewritten">已完成</el-radio-button>
              <el-radio-button label="failed">失败</el-radio-button>
              <el-radio-button label="published">已发布</el-radio-button>
            </el-radio-group>
          </div>
          <div class="toolbar-right">
            <el-button @click="loadData">
              <el-icon><Refresh /></el-icon>刷新
            </el-button>
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon>新建文章
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredArticles" v-loading="loading" stripe>
        <el-table-column label="标题" min-width="300">
          <template #default="{ row }">
            <div class="article-title" :title="row.source_title">
              {{ row.source_title || '无标题' }}
            </div>
            <div class="article-tags">
              <el-tag v-if="row.metadata?.manual_created" size="small" type="success">后台创作</el-tag>
              <el-tag v-if="row.metadata?.ad_header_enabled || row.metadata?.ad_footer_enabled" size="small" type="warning">
                含广告位
              </el-tag>
            </div>
            <div class="article-substate">
              <span v-if="row.status === 'rewriting'" class="substate pending">AI 正在改写，列表会自动刷新</span>
              <span v-else-if="row.status === 'rewritten'" class="substate success">改写已完成，可直接查看成稿</span>
              <span v-else-if="row.status === 'failed'" class="substate error">
                {{ row.error_message || '改写失败，请重试' }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="账户" width="140">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.account_id || '-' }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="来源" width="120">
          <template #default="{ row }">
            {{ row.source_author || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="改写风格" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.rewrite_style" type="info" size="small">
              {{ row.rewrite_style }}
            </el-tag>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button
                v-if="canEdit(row.status)"
                size="small"
                @click="openEditDialog(row)"
              >
                编辑
              </el-button>
              <el-button
                v-if="canRewrite(row.status)"
                size="small"
                type="primary"
                @click="goRewrite(row.id)"
              >
                改写
              </el-button>
              <el-button
                v-if="row.status === 'rewritten'"
                size="small"
                type="info"
                plain
                @click="openResultDialog(row)"
              >
                成稿
              </el-button>
              <el-button
                v-if="row.status === 'rewritten'"
                size="small"
                @click="goRewrite(row.id)"
              >
                去改写页
              </el-button>
              <el-button
                v-if="canPublish(row.status)"
                size="small"
                type="success"
                @click="openPublishDialog(row.id)"
              >
                发布
              </el-button>
              <el-button
                v-if="row.status === 'published'"
                size="small"
                @click="viewDraft(row.wechat_draft_id)"
              >
                查看
              </el-button>
              <el-button
                v-if="row.status === 'failed'"
                size="small"
                plain
                @click="openResultDialog(row)"
              >
                详情
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <el-dialog
        v-model="editorDialogVisible"
        :title="editorMode === 'create' ? '新建文章' : '编辑文章'"
        width="1080px"
        destroy-on-close
      >
        <el-row :gutter="20">
          <el-col :span="13">
              <el-form :model="editorForm" :rules="editorRules" ref="editorFormRef" label-width="100px">
              <div class="editor-context-card">
                <div class="editor-context-header">
                  <div class="editor-context-title">当前编辑对象</div>
                  <el-radio-group v-model="editorContentSource" size="small" @change="handleEditorContentSourceChange">
                    <el-radio-button label="original">原文底稿</el-radio-button>
                    <el-radio-button label="rewritten" :disabled="!editorSourceDrafts.rewritten">AI 成稿</el-radio-button>
                  </el-radio-group>
                </div>
                <div class="editor-context-desc">
                  {{ editorContentSourceDescription }}
                </div>
              </div>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="文章标题" prop="source_title">
                    <el-input v-model="editorForm.source_title" placeholder="输入文章标题" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="作者">
                    <el-input v-model="editorForm.source_author" placeholder="例如：运营团队" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="所属账户">
                    <el-select v-model="editorForm.account_id" style="width: 100%" :disabled="editorMode === 'edit'">
                      <el-option label="default" value="default" />
                      <el-option
                        v-for="acc in accountStore.accounts"
                        :key="acc.account_id"
                        :label="`${acc.name} (${acc.account_id})`"
                        :value="acc.account_id"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="来源链接">
                    <el-input v-model="editorForm.source_url" placeholder="可选，不填则自动生成 manual:// 链接" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="封面图">
                <div class="cover-field">
                  <el-input v-model="editorForm.cover_image" placeholder="可选，可直接填写图片 URL 或从素材库选择" />
                  <div class="cover-field-actions">
                    <el-button @click="openCoverPicker">选择素材库</el-button>
                    <el-button @click="goImageLibrary">管理图片素材</el-button>
                    <el-button v-if="bodyImageCandidates.length" @click="openBodyImagePicker">正文选图</el-button>
                    <el-button v-if="editorForm.cover_image" type="danger" plain @click="clearCoverImage">清空封面</el-button>
                  </div>
                  <div v-if="editorForm.cover_image" class="cover-preview-card">
                    <img :src="editorForm.cover_image" alt="封面预览" class="cover-preview-image">
                  </div>
                  <div v-else-if="bodyImageCandidates.length" class="cover-default-hint">
                    当前未单独设置封面，发布预览会自动使用正文首图。
                  </div>
                </div>
              </el-form-item>

              <el-form-item label="正文内容" prop="content">
                <div class="editor-content-shell">
                  <div class="editor-content-toolbar">
                    <el-radio-group v-model="editorContentMode" size="small">
                      <el-radio-button label="rich">富文本</el-radio-button>
                      <el-radio-button label="html">HTML</el-radio-button>
                    </el-radio-group>
                    <div v-if="editorContentMode === 'rich'" class="rich-toolbar-buttons">
                      <el-button size="small" @click="formatRichBlock('p')">正文</el-button>
                      <el-button size="small" @click="formatRichBlock('h2')">H2</el-button>
                      <el-button size="small" @click="formatRichBlock('h3')">H3</el-button>
                      <el-button size="small" @click="execRichCommand('bold')">加粗</el-button>
                      <el-button size="small" @click="execRichCommand('italic')">斜体</el-button>
                      <el-button size="small" @click="execRichCommand('insertUnorderedList')">列表</el-button>
                      <el-button size="small" @click="formatRichBlock('blockquote')">引用</el-button>
                    </div>
                  </div>
                  <div
                    v-if="editorContentMode === 'rich'"
                    ref="richEditorRef"
                    class="rich-editor"
                    contenteditable="true"
                    @input="handleRichEditorInput"
                  />
                  <el-input
                    v-else
                    v-model="editorForm.content"
                    type="textarea"
                    :rows="16"
                    placeholder="支持直接写纯文本，也支持粘贴 HTML。"
                  />
                  <div class="editor-content-help">
                    富文本模式会与右侧手机预览实时联动；HTML 模式适合直接精修标签结构。
                  </div>
                </div>
              </el-form-item>

              <el-form-item label="保存方式">
                <el-radio-group v-model="editorForm.publish_ready">
                  <el-radio :label="false">保存草稿</el-radio>
                  <el-radio :label="true">保存为可发布成稿</el-radio>
                </el-radio-group>
              </el-form-item>
            </el-form>
          </el-col>

          <el-col :span="11">
            <div class="editor-preview-panel">
              <div class="preview-toolbar">
                <div>
                  <div class="preview-title">手机阅读预览</div>
                  <div class="preview-subtitle">预览会带上当前账户的头部 / 底部广告位</div>
                </div>
                <div class="preview-actions">
                  <el-select v-model="previewTemplate" size="small" style="width: 140px">
                    <el-option
                      v-for="(tpl, key) in templates"
                      :key="key"
                      :label="tpl.name"
                      :value="key"
                    />
                  </el-select>
                  <el-button size="small" @click="refreshEditorPreview" :loading="previewLoading">
                    刷新预览
                  </el-button>
                </div>
              </div>

              <div class="preview-meta">
                <el-tag size="small" type="info">{{ currentEditorAccount?.name || editorForm.account_id || 'default' }}</el-tag>
                <el-tag v-if="currentEditorAccount?.ad_header_html" size="small" type="success">头部广告已启用</el-tag>
                <el-tag v-if="currentEditorAccount?.ad_footer_html" size="small" type="warning">底部广告已启用</el-tag>
              </div>

              <div class="mobile-preview-shell">
                <div class="mobile-preview-screen">
                  <div v-if="previewLoading" class="preview-loading">
                    <el-skeleton :rows="8" animated />
                  </div>
                  <div v-else-if="editorPreviewHtml" class="mobile-preview-content" v-html="editorPreviewHtml" />
                  <el-empty v-else description="输入标题和正文后可预览" />
                </div>
              </div>
            </div>
          </el-col>
        </el-row>

        <template #footer>
          <el-button @click="editorDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitArticle" :loading="savingArticle">
            保存
          </el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="publishDialogVisible" title="选择发布模板" width="500px">
        <div class="publish-summary" v-if="publishTargetArticle">
          <div class="publish-title">{{ publishTargetArticle.source_title || '未命名文章' }}</div>
          <div class="publish-tags">
            <el-tag size="small" type="info">{{ publishTargetArticle.account_id || 'default' }}</el-tag>
            <el-tag v-if="publishAccount?.ad_header_html" size="small" type="success">将注入头部广告</el-tag>
            <el-tag v-if="publishAccount?.ad_footer_html" size="small" type="warning">将注入底部广告</el-tag>
          </div>
        </div>

        <div class="template-grid">
          <div
            v-for="(tpl, key) in templates"
            :key="key"
            class="template-item"
            :class="{ active: selectedTemplate === key }"
            @click="selectedTemplate = key"
          >
            <el-icon :size="32" class="mb-2"><Document /></el-icon>
            <div class="name">{{ tpl.name }}</div>
            <div class="desc">{{ tpl.description }}</div>
          </div>
        </div>
        <template #footer>
          <el-button @click="publishDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmPublish" :loading="publishing">
            确认发布
          </el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="imagePickerVisible" title="选择头图素材" width="860px">
        <div class="picker-toolbar">
          <div class="picker-toolbar-text">
            当前账户图片素材：{{ currentEditorAccount?.name || editorForm.account_id || 'default' }}
          </div>
          <div class="picker-toolbar-actions">
            <el-button @click="loadCoverAssets">刷新</el-button>
            <el-button @click="goImageLibrary">去图片素材库</el-button>
          </div>
        </div>

        <div v-if="coverAssets.length" class="cover-asset-grid">
          <div
            v-for="asset in coverAssets"
            :key="asset.id"
            class="cover-asset-card"
            :class="{ active: editorForm.cover_image === asset.image_url }"
            @click="selectCoverAsset(asset)"
          >
            <div class="cover-asset-image-wrap">
              <img :src="asset.image_url" :alt="asset.title || '封面素材'" class="cover-asset-image">
            </div>
            <div class="cover-asset-title">{{ asset.title || '未命名图片' }}</div>
            <div v-if="asset.prompt" class="cover-asset-prompt">{{ asset.prompt }}</div>
          </div>
        </div>
        <el-empty v-else description="当前账户还没有图片素材" />
      </el-dialog>

      <el-dialog v-model="bodyImagePickerVisible" title="从正文图片中选择封面" width="820px">
        <div class="body-cover-section dialog-mode">
          <div class="body-cover-header">
            <span>正文内可选图片</span>
            <span class="body-cover-tip">未手动设置时，默认使用正文首图作为封面</span>
          </div>
          <div v-if="bodyImageCandidates.length" class="body-cover-grid">
            <button
              v-for="candidate in bodyImageCandidates"
              :key="candidate.src"
              type="button"
              class="body-cover-card"
              :class="{ active: effectiveCoverImage === candidate.src }"
              @click="selectBodyImageAsCover(candidate.src)"
            >
              <img :src="candidate.src" :alt="candidate.alt || '正文图片'" class="body-cover-image">
              <span class="body-cover-label">{{ candidate.alt || candidate.label }}</span>
            </button>
          </div>
          <el-empty v-else description="正文里还没有可用图片" />
        </div>
        <template #footer>
          <el-button @click="bodyImagePickerVisible = false">关闭</el-button>
          <el-button v-if="bodyImageCandidates.length" @click="applyFirstBodyImageAsCover">恢复正文首图</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="resultDialogVisible" title="文章状态详情" width="860px">
        <div v-if="resultDialogArticle" class="result-dialog">
          <div class="result-dialog-header">
            <div>
              <div class="result-dialog-title">{{ resultDialogArticle.source_title || '未命名文章' }}</div>
              <div class="result-dialog-meta">
                <el-tag :type="getStatusType(resultDialogArticle.status)" size="small">
                  {{ getStatusLabel(resultDialogArticle.status) }}
                </el-tag>
                <el-tag v-if="resultDialogArticle.rewrite_style" size="small" type="info">
                  {{ resultDialogArticle.rewrite_style }}
                </el-tag>
                <span class="result-dialog-time">创建于 {{ formatDate(resultDialogArticle.created_at) }}</span>
              </div>
            </div>
            <div class="result-dialog-actions">
              <el-button v-if="resultDialogArticle.status === 'rewritten'" size="small" @click="goRewrite(resultDialogArticle.id)">
                去改写页
              </el-button>
              <el-button
                v-if="resultDialogArticle.status === 'rewritten'"
                size="small"
                type="success"
                @click="openPublishDialog(resultDialogArticle.id)"
              >
                发布
              </el-button>
              <el-button
                v-if="resultDialogArticle.status === 'failed'"
                size="small"
                type="primary"
                @click="retryRewrite(resultDialogArticle)"
              >
                重新改写
              </el-button>
            </div>
          </div>

          <div v-if="resultDialogArticle.status === 'failed'" class="result-error-box">
            {{ resultDialogArticle.error_message || '当前文章改写失败，请重试。' }}
          </div>

          <div v-else-if="resultDialogArticle.status === 'rewriting'" class="result-running-box">
            AI 正在处理中，列表会自动刷新。你也可以稍后回到这里查看结果。
          </div>

          <div
            v-if="resultDialogArticle.status === 'rewritten' && resultDialogArticle.rewritten_html"
            class="result-preview-panel"
          >
            <div class="result-preview-toolbar">
              <div>
                <div class="preview-title">成稿预览</div>
                <div class="preview-subtitle">按模板和账户广告位展示最终阅读效果</div>
              </div>
              <div class="preview-actions">
                <el-select v-model="resultPreviewTemplate" size="small" style="width: 140px" @change="refreshResultPreview">
                  <el-option
                    v-for="(tpl, key) in templates"
                    :key="key"
                    :label="tpl.name"
                    :value="key"
                  />
                </el-select>
                <el-button size="small" @click="refreshResultPreview" :loading="resultPreviewLoading">
                  刷新预览
                </el-button>
              </div>
            </div>

            <div class="preview-meta">
              <el-tag size="small" type="info">{{ resultPreviewAccount?.name || resultDialogArticle.account_id || 'default' }}</el-tag>
              <el-tag v-if="resultPreviewAccount?.ad_header_html" size="small" type="success">头部广告已启用</el-tag>
              <el-tag v-if="resultPreviewAccount?.ad_footer_html" size="small" type="warning">底部广告已启用</el-tag>
            </div>

            <div class="mobile-preview-shell result-mobile-preview-shell">
              <div class="mobile-preview-screen result-mobile-preview-screen">
                <div v-if="resultPreviewLoading" class="preview-loading">
                  <el-skeleton :rows="8" animated />
                </div>
                <div v-else-if="resultPreviewHtml" class="mobile-preview-content" v-html="resultPreviewHtml" />
                <el-empty v-else description="当前还没有可预览的成稿" />
              </div>
            </div>
          </div>
          <el-empty
            v-else-if="resultDialogArticle.status !== 'failed' && resultDialogArticle.status !== 'rewriting'"
            description="当前还没有改写内容"
          />
        </div>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Document, Plus } from '@element-plus/icons-vue'
import api from '../api'
import { useAccountStore, useArticleStore, useAppStore, useImageAssetStore } from '../stores'

const router = useRouter()
const route = useRoute()
const articleStore = useArticleStore()
const accountStore = useAccountStore()
const appStore = useAppStore()
const imageAssetStore = useImageAssetStore()

const loading = ref(false)
const filterStatus = ref('')
const publishDialogVisible = ref(false)
const publishArticleId = ref('')
const templates = ref({})
const selectedTemplate = ref('default')
const publishing = ref(false)

const editorDialogVisible = ref(false)
const editorMode = ref('create')
const savingArticle = ref(false)
const editorFormRef = ref(null)
const editorTargetId = ref('')
const previewTemplate = ref('default')
const editorPreviewHtml = ref('')
const previewLoading = ref(false)
const previewTimer = ref(null)
const richEditorRef = ref(null)
const editorContentMode = ref('rich')
const editorContentSource = ref('original')
const editorSourceDrafts = ref({ original: '', rewritten: '' })
const imagePickerVisible = ref(false)
const bodyImagePickerVisible = ref(false)
const resultDialogVisible = ref(false)
const resultDialogArticle = ref(null)
const resultPreviewHtml = ref('')
const resultPreviewLoading = ref(false)
const resultPreviewTemplate = ref('default')
const listRefreshTimer = ref(null)

const createEmptyForm = () => ({
  source_title: '',
  source_author: '',
  account_id: appStore.selectedAccountId || accountStore.accounts[0]?.account_id || 'default',
  source_url: '',
  cover_image: '',
  content: '',
  publish_ready: false
})

const editorForm = ref(createEmptyForm())
const editorRules = {
  source_title: [{ required: true, message: '请输入文章标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入正文内容', trigger: 'blur' }]
}

const filteredArticles = computed(() => {
  if (!filterStatus.value) return articleStore.articles
  return articleStore.articles.filter(a => a.status === filterStatus.value)
})

const currentEditorAccount = computed(() => {
  return accountStore.accounts.find(acc => acc.account_id === editorForm.value.account_id) || null
})

const editorContentSourceDescription = computed(() => {
  if (editorMode.value === 'create') {
    return '新建文章默认编辑原文底稿。保存为可发布成稿后，这份内容会直接作为当前发布版本。'
  }
  if (editorContentSource.value === 'rewritten') {
    return '你当前编辑的是 AI 改写后的成稿内容，右侧预览展示的也是这份成稿。'
  }
  return '你当前编辑的是原文底稿内容。若后续重新 AI 改写，将以这份底稿为输入。'
})

const publishTargetArticle = computed(() => {
  return articleStore.articles.find(article => article.id === publishArticleId.value) || null
})

const publishAccount = computed(() => {
  if (!publishTargetArticle.value) return null
  return accountStore.accounts.find(acc => acc.account_id === publishTargetArticle.value.account_id) || null
})

const resultPreviewAccount = computed(() => {
  if (!resultDialogArticle.value) return null
  return accountStore.accounts.find(acc => acc.account_id === resultDialogArticle.value.account_id) || null
})

const coverAssets = computed(() => {
  return imageAssetStore.imageAssets.filter(asset => asset.account_id === (editorForm.value.account_id || 'default'))
})

const bodyImageCandidates = computed(() => {
  const seen = new Set()
  const candidates = []
  const parser = typeof DOMParser !== 'undefined' ? new DOMParser() : null
  const html = editorForm.value.content || ''

  if (parser && html) {
    const doc = parser.parseFromString(normalizeContentForPreview(html), 'text/html')
    doc.querySelectorAll('img').forEach((img, index) => {
      const src = (img.getAttribute('src') || img.getAttribute('data-src') || '').trim()
      if (!src || seen.has(src)) return
      seen.add(src)
      candidates.push({
        src,
        alt: (img.getAttribute('alt') || '').trim(),
        label: `正文图片 ${index + 1}`
      })
    })
  }

  const currentArticle = articleStore.currentArticle
  ;(currentArticle?.images || []).forEach((src, index) => {
    const cleanSrc = (src || '').trim()
    if (!cleanSrc || seen.has(cleanSrc)) return
    seen.add(cleanSrc)
    candidates.push({
      src: cleanSrc,
      alt: '',
      label: `正文图片 ${candidates.length + 1 || index + 1}`
    })
  })

  return candidates
})

const effectiveCoverImage = computed(() => {
  return editorForm.value.cover_image || bodyImageCandidates.value[0]?.src || ''
})

const statusMap = {
  pending: { label: '草稿', type: 'warning' },
  rewriting: { label: '改写中', type: 'primary' },
  rewritten: { label: '已完成', type: 'success' },
  publishing: { label: '发布中', type: 'primary' },
  published: { label: '已发布', type: 'success' },
  failed: { label: '失败', type: 'danger' }
}

function getStatusLabel(status) {
  return statusMap[status]?.label || status
}

function getStatusType(status) {
  return statusMap[status]?.type || 'info'
}

function canRewrite(status) {
  return status === 'pending' || status === 'failed'
}

function canEdit(status) {
  return status !== 'published' && status !== 'publishing'
}

function canPublish(status) {
  return status === 'rewritten'
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function normalizeContentForPreview(content) {
  const raw = (content || '').trim()
  if (!raw) return ''
  if (/<\/?[a-z][\s\S]*>/i.test(raw)) return raw
  return raw
    .split(/\n\s*\n/)
    .map(block => block.trim())
    .filter(Boolean)
    .map(block => `<p>${block.replace(/\n/g, '<br>')}</p>`)
    .join('')
}

function setRichEditorHtml(content) {
  if (!richEditorRef.value) return
  richEditorRef.value.innerHTML = normalizeContentForPreview(content || '')
}

function syncRichEditorFromForm() {
  nextTick(() => {
    if (editorContentMode.value === 'rich') {
      setRichEditorHtml(editorForm.value.content)
    }
  })
}

function applyContentSource(source) {
  const targetContent = source === 'rewritten'
    ? (editorSourceDrafts.value.rewritten || editorSourceDrafts.value.original || '')
    : (editorSourceDrafts.value.original || editorSourceDrafts.value.rewritten || '')
  editorForm.value.content = targetContent
  syncRichEditorFromForm()
}

function handleEditorContentSourceChange(value) {
  if (value === 'rewritten' && !editorSourceDrafts.value.rewritten) {
    editorContentSource.value = 'original'
    return
  }
  applyContentSource(value)
}

function handleRichEditorInput(event) {
  editorForm.value.content = event.target.innerHTML
}

function focusRichEditor() {
  if (!richEditorRef.value) return
  richEditorRef.value.focus()
}

function execRichCommand(command, value = null) {
  focusRichEditor()
  document.execCommand(command, false, value)
  if (richEditorRef.value) {
    editorForm.value.content = richEditorRef.value.innerHTML
  }
}

function formatRichBlock(tagName) {
  execRichCommand('formatBlock', tagName)
}

function extractPreviewFragment(html) {
  if (!html) return ''
  const styleMatch = html.match(/<style[\s\S]*?<\/style>/i)
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i)
  if (!styleMatch && !bodyMatch) return html
  return `${styleMatch?.[0] || ''}${bodyMatch?.[1] || ''}`
}

async function loadData() {
  loading.value = true
  const params = appStore.selectedAccountId
    ? { account_id: appStore.selectedAccountId }
    : undefined
  await Promise.all([
    articleStore.fetchArticles(params),
    accountStore.fetchAccounts(),
    loadTemplates()
  ]).finally(() => {
    loading.value = false
    ensureListAutoRefresh()
  })
}

function hasActiveArticleJobs() {
  return articleStore.articles.some(article => ['rewriting', 'publishing'].includes(article.status))
}

function clearListRefreshTimer() {
  if (listRefreshTimer.value) {
    clearInterval(listRefreshTimer.value)
    listRefreshTimer.value = null
  }
}

function ensureListAutoRefresh() {
  if (hasActiveArticleJobs()) {
    if (!listRefreshTimer.value) {
      listRefreshTimer.value = setInterval(() => {
        loadData()
      }, 5000)
    }
    return
  }
  clearListRefreshTimer()
}

async function loadCoverAssets() {
  const accountId = editorForm.value.account_id || appStore.selectedAccountId || 'default'
  await imageAssetStore.fetchImageAssets({ account_id: accountId })
}

async function loadTemplates() {
  const data = await api.templates.list()
  templates.value = data
  return data
}

function goRewrite(id) {
  router.push({ name: 'Rewrite', query: { id } })
}

async function openResultDialog(row) {
  resultDialogArticle.value = row
  resultPreviewTemplate.value = row.metadata?.template || 'default'
  resultPreviewHtml.value = ''
  resultDialogVisible.value = true
  if (row.status === 'rewritten' && row.rewritten_html) {
    await refreshResultPreview()
  }
}

function openCreateDialog() {
  editorMode.value = 'create'
  editorTargetId.value = ''
  articleStore.currentArticle = null
  editorForm.value = createEmptyForm()
  editorSourceDrafts.value = { original: '', rewritten: '' }
  editorContentSource.value = 'original'
  editorContentMode.value = 'rich'
  previewTemplate.value = 'default'
  editorPreviewHtml.value = ''
  editorDialogVisible.value = true
  loadCoverAssets()
  syncRichEditorFromForm()
  scheduleEditorPreview()
}

async function openEditDialog(row) {
  try {
    editorMode.value = 'edit'
    editorTargetId.value = row.id
    const detail = await articleStore.getArticle(row.id)
    const originalDraft = detail.original_html || detail.original_content || ''
    const rewrittenDraft = detail.rewritten_html || ''
    editorSourceDrafts.value = {
      original: originalDraft,
      rewritten: rewrittenDraft
    }
    editorContentSource.value = rewrittenDraft ? 'rewritten' : 'original'
    editorContentMode.value = 'rich'
    editorForm.value = {
      source_title: detail.source_title || '',
      source_author: detail.source_author || '',
      account_id: detail.account_id || 'default',
      source_url: detail.source_url || '',
      cover_image: detail.cover_image || '',
      content: rewrittenDraft || originalDraft,
      publish_ready: detail.status === 'rewritten'
    }
    previewTemplate.value = detail.metadata?.template || 'default'
    editorPreviewHtml.value = ''
    editorDialogVisible.value = true
    await loadCoverAssets()
    syncRichEditorFromForm()
    scheduleEditorPreview()
  } catch (error) {
    ElMessage.error(error.message || '加载文章详情失败')
  }
}

function openCoverPicker() {
  imagePickerVisible.value = true
  loadCoverAssets()
}

function openBodyImagePicker() {
  bodyImagePickerVisible.value = true
}

function selectCoverAsset(asset) {
  editorForm.value.cover_image = asset.image_url
  imagePickerVisible.value = false
}

function selectBodyImageAsCover(src) {
  editorForm.value.cover_image = src
  bodyImagePickerVisible.value = false
}

function applyFirstBodyImageAsCover() {
  if (!bodyImageCandidates.value.length) return
  editorForm.value.cover_image = bodyImageCandidates.value[0].src
  bodyImagePickerVisible.value = false
}

function clearCoverImage() {
  editorForm.value.cover_image = ''
}

function goImageLibrary() {
  imagePickerVisible.value = false
  router.push({ name: 'Inspirations', query: { tab: 'images' } })
}

function clearPreviewTimer() {
  if (previewTimer.value) {
    clearTimeout(previewTimer.value)
    previewTimer.value = null
  }
}

function scheduleEditorPreview() {
  if (!editorDialogVisible.value) return
  clearPreviewTimer()
  previewTimer.value = setTimeout(() => {
    refreshEditorPreview()
  }, 300)
}

async function refreshEditorPreview() {
  const content = normalizeContentForPreview(editorForm.value.content)
  if (!editorForm.value.source_title || !content) {
    editorPreviewHtml.value = ''
    return
  }
  previewLoading.value = true
  try {
    const result = await api.templates.preview(previewTemplate.value, {
      title: editorForm.value.source_title,
      content,
      author: editorForm.value.source_author || currentEditorAccount.value?.wechat_author || '',
      cover_image: effectiveCoverImage.value || '',
      ad_header_html: currentEditorAccount.value?.ad_header_html || '',
      ad_footer_html: currentEditorAccount.value?.ad_footer_html || ''
    })
    editorPreviewHtml.value = extractPreviewFragment(result.html)
  } catch {
    editorPreviewHtml.value = ''
  } finally {
    previewLoading.value = false
  }
}

async function refreshResultPreview() {
  if (!resultDialogArticle.value?.rewritten_html) {
    resultPreviewHtml.value = ''
    return
  }

  resultPreviewLoading.value = true
  try {
    const article = resultDialogArticle.value
    const result = await api.templates.preview(resultPreviewTemplate.value, {
      title: article.source_title || '未命名文章',
      content: normalizeContentForPreview(article.rewritten_html),
      author: article.source_author || resultPreviewAccount.value?.wechat_author || '',
      cover_image: article.cover_image || '',
      ad_header_html: resultPreviewAccount.value?.ad_header_html || '',
      ad_footer_html: resultPreviewAccount.value?.ad_footer_html || ''
    })
    resultPreviewHtml.value = extractPreviewFragment(result.html)
  } catch {
    resultPreviewHtml.value = ''
  } finally {
    resultPreviewLoading.value = false
  }
}

async function submitArticle() {
  const valid = await editorFormRef.value.validate().catch(() => false)
  if (!valid) return

  savingArticle.value = true
  try {
    if (editorMode.value === 'create') {
      const payload = {
        ...editorForm.value,
        cover_image: effectiveCoverImage.value || ''
      }
      const article = await articleStore.createArticle(payload)
      ElMessage.success(editorForm.value.publish_ready ? '文章已保存为可发布成稿' : '文章草稿已创建')
      editorDialogVisible.value = false
      await loadData()
      if (editorForm.value.publish_ready) {
        openPublishDialog(article.id)
      }
    } else {
      const payload = {
        ...editorForm.value,
        cover_image: effectiveCoverImage.value || '',
        editing_target: editorContentSource.value
      }
      const article = await articleStore.updateArticle(editorTargetId.value, payload)
      ElMessage.success('文章已更新')
      editorDialogVisible.value = false
      await loadData()
      if (editorForm.value.publish_ready) {
        openPublishDialog(article.id)
      }
    }
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    savingArticle.value = false
  }
}

async function openPublishDialog(id) {
  publishArticleId.value = id
  try {
    await loadTemplates()
    selectedTemplate.value = publishTargetArticle.value?.metadata?.template || 'default'
    publishDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载模板失败')
  }
}

async function confirmPublish() {
  publishing.value = true
  try {
    const result = await articleStore.publish(publishArticleId.value, selectedTemplate.value)
    ElMessage.success(`发布任务已创建: ${result.task_id?.slice(0, 8)}...`)
    publishDialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.message || '发布失败')
  } finally {
    publishing.value = false
  }
}

async function retryRewrite(row) {
  try {
    const result = await articleStore.rewrite(row.id, {
      style: row.rewrite_style || 'tech_expert',
      use_references: true
    })
    ElMessage.success(`改写任务已重新创建: ${result.task_id?.slice(0, 8)}...`)
    resultDialogVisible.value = false
    await loadData()
  } catch (error) {
    ElMessage.error(error.message || '重新改写失败')
  }
}

function viewDraft(draftId) {
  if (!draftId) {
    ElMessage.warning('该文章暂无草稿 ID')
    return
  }
  ElMessage.info(`草稿 ID: ${draftId}`)
}

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  clearPreviewTimer()
  clearListRefreshTimer()
})

watch(() => appStore.selectedAccountId, () => {
  loadData()
})

watch(
  () => route.query.publish,
  async (publishId) => {
    if (!publishId) return
    if (!articleStore.articles.length) {
      await loadData()
    }
    await openPublishDialog(publishId)
    router.replace({ name: 'Articles', query: { ...route.query, publish: undefined } })
  },
  { immediate: true }
)

watch(
  () => editorForm.value.account_id,
  () => {
    if (editorDialogVisible.value) {
      loadCoverAssets()
    }
  }
)

watch(
  () => [
    editorDialogVisible.value,
    editorForm.value.source_title,
    editorForm.value.source_author,
    editorForm.value.account_id,
    editorForm.value.content,
    editorForm.value.cover_image,
    previewTemplate.value
  ],
  () => {
    scheduleEditorPreview()
  }
)

watch(
  () => editorContentMode.value,
  () => {
    syncRichEditorFromForm()
  }
)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.article-title {
  font-weight: 600;
  color: #1e293b;
}

.article-tags {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.article-substate {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
}

.substate {
  display: block;
}

.substate.pending {
  color: #2563eb;
}

.substate.success {
  color: #059669;
}

.substate.error {
  color: #dc2626;
}

.text-gray-400 {
  color: #94a3b8;
}

.editor-context-card {
  margin-bottom: 18px;
  padding: 14px 16px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fbff;
}

.editor-context-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.editor-context-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.editor-context-desc {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #475569;
}

.cover-field {
  width: 100%;
}

.cover-field-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.body-cover-section {
  margin-top: 14px;
}

.body-cover-section.dialog-mode {
  margin-top: 0;
}

.body-cover-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #475569;
}

.body-cover-tip {
  color: #64748b;
}

.body-cover-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.body-cover-card {
  padding: 0;
  border: 1px solid #dbe3f0;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.body-cover-card:hover,
.body-cover-card.active {
  border-color: #2563eb;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.12);
}

.body-cover-image {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  background: #f8fafc;
}

.body-cover-label {
  display: block;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.5;
  color: #334155;
  word-break: break-all;
}

.cover-preview-card {
  margin-top: 12px;
  width: 220px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

.cover-preview-image {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
}

.cover-default-hint {
  margin-top: 12px;
  font-size: 12px;
  color: #64748b;
}

.editor-content-shell {
  width: 100%;
}

.editor-content-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.rich-toolbar-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.rich-editor {
  height: 420px;
  padding: 14px 16px;
  border: 1px solid #d1d9e6;
  border-radius: 10px;
  background: #fff;
  color: #0f172a;
  line-height: 1.8;
  overflow-y: auto;
}

.rich-editor:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.rich-editor :deep(h2) {
  margin: 18px 0 10px;
  font-size: 22px;
  line-height: 1.45;
}

.rich-editor :deep(h3) {
  margin: 16px 0 8px;
  font-size: 18px;
  line-height: 1.5;
}

.rich-editor :deep(p),
.rich-editor :deep(li),
.rich-editor :deep(blockquote) {
  margin: 0 0 12px;
}

.rich-editor :deep(img) {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 12px auto;
  border-radius: 8px;
}

.editor-content-help {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
}

.editor-preview-panel {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
}

.preview-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.preview-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.preview-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.preview-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.preview-meta {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.mobile-preview-shell {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.mobile-preview-screen {
  width: 390px;
  max-width: 100%;
  min-height: 620px;
  background: #fff;
  border: 10px solid #0f172a;
  border-radius: 28px;
  overflow: hidden;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.12);
}

.mobile-preview-content {
  max-height: 620px;
  overflow-y: auto;
  background: #fff;
}

.preview-loading {
  padding: 16px;
}

.publish-summary {
  margin-bottom: 16px;
  padding: 14px 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.publish-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.publish-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.template-item {
  padding: 24px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.template-item:hover {
  border-color: #4f46e5;
}

.template-item.active {
  border-color: #4f46e5;
  background: #eef2ff;
}

.template-item .name {
  font-weight: 500;
  margin-bottom: 4px;
}

.template-item .desc {
  font-size: 12px;
  color: #64748b;
}

.picker-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.picker-toolbar-text {
  font-size: 13px;
  color: #64748b;
}

.picker-toolbar-actions {
  display: flex;
  gap: 8px;
}

.cover-asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.cover-asset-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  background: #fff;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.cover-asset-card:hover,
.cover-asset-card.active {
  border-color: #4f46e5;
  box-shadow: 0 10px 24px rgba(79, 70, 229, 0.12);
}

.cover-asset-image-wrap {
  background: #f8fafc;
}

.cover-asset-image {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
}

.cover-asset-title {
  padding: 12px 12px 4px;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.cover-asset-prompt {
  padding: 0 12px 12px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.result-dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.result-dialog-title {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}

.result-dialog-meta {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.result-dialog-time {
  font-size: 12px;
  color: #64748b;
}

.result-dialog-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.result-error-box,
.result-running-box {
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.6;
}

.result-error-box {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.result-running-box {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.result-content {
  margin-top: 16px;
  max-height: 68vh;
  overflow: auto;
  padding-right: 8px;
  line-height: 1.8;
  color: #1e293b;
}

.result-content :deep(h2) {
  margin: 24px 0 12px;
  font-size: 24px;
  line-height: 1.35;
  color: #0f172a;
}

.result-content :deep(h3) {
  margin: 18px 0 10px;
  font-size: 18px;
  line-height: 1.45;
  color: #1e293b;
}

.result-content :deep(p),
.result-content :deep(li),
.result-content :deep(blockquote) {
  font-size: 15px;
}

.result-preview-panel {
  margin-top: 18px;
}

.result-preview-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.result-mobile-preview-shell {
  margin-top: 14px;
}

.result-mobile-preview-screen {
  min-height: 680px;
}
</style>
