<template>
  <div class="inspirations-page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="文章素材" name="articles">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <el-input
                v-model="searchQuery"
                placeholder="搜索素材..."
                :prefix-icon="Search"
                style="width: 300px"
                clearable
              />
              <el-button type="primary" @click="openCollectDialog">
                <el-icon><Plus /></el-icon>采集素材
              </el-button>
            </div>
          </template>

          <el-table :data="filteredInspirations" v-loading="loading" stripe>
            <el-table-column label="标题" min-width="250">
              <template #default="{ row }">
                <div class="inspiration-title">{{ row.title || '无标题' }}</div>
                <div class="inspiration-tags">
                  <el-tag v-if="row.source_type === 'wechat_login_state'" size="small" type="success">公众号雷达</el-tag>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="来源" width="120" prop="source_account" />

            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === '已采集' ? 'success' : 'warning'">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="采集时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.collected_at) }}
              </template>
            </el-table-column>

            <el-table-column label="操作" width="340" fixed="right">
              <template #default="{ row }">
                <el-button-group>
                  <el-button size="small" type="primary" @click="createArticle(row.id)">
                    改写
                  </el-button>
                  <el-button size="small" @click="viewDetail(row)">
                    查看
                  </el-button>
                  <el-button size="small" @click="openOriginal(row.source_url)">
                    原文
                  </el-button>
                  <el-button size="small" type="danger" @click="handleDelete(row)">
                    删除
                  </el-button>
                </el-button-group>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

    <el-tab-pane label="图片素材库" name="images">
        <el-card shadow="never">
          <template #header>
            <div class="card-header image-header">
              <div class="toolbar-left">
                <el-input
                  v-model="imageSearchQuery"
                  placeholder="搜索图片标题或提示词..."
                  style="width: 320px"
                  clearable
                />
                <div class="image-toolbar-tip">
                  可上传头图，或用 AI 生成后在文章编辑里直接选择。
                </div>
              </div>
              <div class="toolbar-right">
                <el-button @click="loadImageAssets">
                  <el-icon><Refresh /></el-icon>刷新
                </el-button>
                <el-button @click="openGenerateDialog">AI 生成</el-button>
                <el-button type="primary" @click="openUploadDialog">上传图片</el-button>
              </div>
            </div>
          </template>

          <div v-if="filteredImageAssets.length" class="image-grid">
            <div v-for="asset in filteredImageAssets" :key="asset.id" class="image-card">
              <div class="image-card-preview">
                <img :src="asset.image_url" :alt="asset.title || '图片素材'" />
              </div>
              <div class="image-card-body">
                <div class="image-card-title">{{ asset.title || '未命名图片' }}</div>
                <div class="image-card-meta">
                  <el-tag size="small" :type="asset.source_type === 'ai' ? 'warning' : 'info'">
                    {{ asset.source_type === 'ai' ? 'AI 生成' : '上传' }}
                  </el-tag>
                  <span>{{ formatDate(asset.created_at) }}</span>
                </div>
                <div v-if="asset.prompt" class="image-card-prompt">
                  {{ asset.prompt }}
                </div>
                <div class="image-card-actions">
                  <el-button size="small" @click="copyImageUrl(asset)">复制地址</el-button>
                  <el-button size="small" type="danger" @click="deleteImageAsset(asset)">
                    删除
                  </el-button>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="当前账户还没有图片素材" />
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="公众号雷达" name="wechat">
        <WechatRadarBoard
          :account-id="currentAccount?.account_id || ''"
          :account-name="currentAccount?.name || ''"
          @refresh="loadData"
        />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showCollectDialog" title="采集素材" width="500px">
      <el-form :model="collectForm" label-width="100px">
        <el-form-item label="文章链接">
          <el-input
            v-model="collectForm.url"
            placeholder="输入微信公众号文章链接..."
          />
        </el-form-item>
        <el-form-item label="账户">
          <el-select v-model="collectForm.account_id" style="width: 100%">
            <el-option
              v-for="acc in accountStore.accounts"
              :key="acc.account_id"
              :label="acc.name"
              :value="acc.account_id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCollectDialog = false">取消</el-button>
        <el-button type="primary" @click="collect" :loading="collecting">
          开始采集
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showUploadDialog" title="上传图片素材" width="520px">
      <el-form :model="uploadForm" label-width="90px">
        <el-form-item label="素材标题">
          <el-input v-model="uploadForm.title" placeholder="例如：产品封面图" />
        </el-form-item>
        <el-form-item label="所属账户">
          <el-select v-model="uploadForm.account_id" style="width: 100%">
            <el-option
              v-for="acc in accountStore.accounts"
              :key="acc.account_id"
              :label="`${acc.name} (${acc.account_id})`"
              :value="acc.account_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="图片文件">
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept="image/*"
            :show-file-list="true"
            :on-change="handleUploadChange"
            :on-remove="handleUploadRemove"
          >
            <el-button>选择图片</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">
          上传
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showGenerateDialog" title="AI 生成图片素材" width="560px">
      <el-form :model="generateForm" label-width="90px">
        <el-form-item label="素材标题">
          <el-input v-model="generateForm.title" placeholder="例如：AI 科技头图" />
        </el-form-item>
        <el-form-item label="所属账户">
          <el-select v-model="generateForm.account_id" style="width: 100%">
            <el-option
              v-for="acc in accountStore.accounts"
              :key="acc.account_id"
              :label="`${acc.name} (${acc.account_id})`"
              :value="acc.account_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="提示词">
          <el-input
            v-model="generateForm.prompt"
            type="textarea"
            :rows="5"
            placeholder="例如：科技感蓝色光影背景，AI 芯片主题，适合微信公众号文章头图，16:9 横图"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerateDialog = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="submitGenerate">
          开始生成
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDetailDialog" title="素材详情" width="920px" class="detail-dialog">
      <div v-if="selectedInspiration" class="detail-layout">
        <div class="detail-meta-panel">
          <div class="detail-meta-eyebrow">文章阅读预览</div>
          <h3 class="detail-title">{{ selectedInspiration.title }}</h3>
          <div class="detail-meta-row">
            <div class="detail-meta-item">
              <span class="detail-meta-label">来源</span>
              <span class="detail-meta-value">{{ selectedInspiration.source_account || '未标注' }}</span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">作者</span>
              <span class="detail-meta-value">{{ selectedInspiration.author || '未知作者' }}</span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">采集时间</span>
              <span class="detail-meta-value">{{ formatDate(selectedInspiration.collected_at) }}</span>
            </div>
          </div>
          <div class="detail-source-actions">
            <el-button type="primary" plain @click="openOriginal(selectedInspiration.source_url)">
              查看原文
            </el-button>
          </div>
        </div>

        <div class="detail-preview-shell">
          <div class="detail-preview-device">
            <div class="detail-preview-header">
              <div class="detail-preview-dots">
                <span />
                <span />
                <span />
              </div>
              <div class="detail-preview-caption">公众号文章预览</div>
            </div>
            <div class="detail-article">
              <header class="detail-article-header">
                <h1>{{ selectedInspiration.title }}</h1>
              </header>
              <div ref="contentRef" class="content-box article-content" v-html="displayContentHtml" />
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { useInspirationStore, useAccountStore, useAppStore, useImageAssetStore } from '../stores'
import WechatRadarBoard from '../components/WechatRadarBoard.vue'

const route = useRoute()
const router = useRouter()
const inspirationStore = useInspirationStore()
const accountStore = useAccountStore()
const appStore = useAppStore()
const imageAssetStore = useImageAssetStore()

const loading = ref(false)
const searchQuery = ref('')
const imageSearchQuery = ref('')
const activeTab = ref(['articles', 'images', 'wechat'].includes(route.query.tab) ? route.query.tab : 'articles')

const showCollectDialog = ref(false)
const showDetailDialog = ref(false)
const selectedInspiration = ref(null)
const collecting = ref(false)
const contentRef = ref(null)

const showUploadDialog = ref(false)
const showGenerateDialog = ref(false)
const uploading = ref(false)
const generating = ref(false)
const uploadFile = ref(null)

const collectForm = ref({
  url: '',
  account_id: ''
})

const uploadForm = ref({
  title: '',
  account_id: ''
})

const generateForm = ref({
  title: '',
  prompt: '',
  account_id: ''
})

const filteredInspirations = computed(() => {
  if (!searchQuery.value) return inspirationStore.inspirations
  const search = searchQuery.value.toLowerCase()
  return inspirationStore.inspirations.filter(i =>
    i.title?.toLowerCase().includes(search) ||
    i.content?.toLowerCase().includes(search)
  )
})

const filteredImageAssets = computed(() => {
  if (!imageSearchQuery.value) return imageAssetStore.imageAssets
  const search = imageSearchQuery.value.toLowerCase()
  return imageAssetStore.imageAssets.filter(asset =>
    asset.title?.toLowerCase().includes(search) ||
    asset.prompt?.toLowerCase().includes(search)
  )
})

const currentAccount = computed(() => {
  const selectedId = appStore.selectedAccountId
  return (
    accountStore.accounts.find(acc => acc.account_id === selectedId) ||
    accountStore.accounts[0] ||
    null
  )
})

const displayContentHtml = computed(() => {
  if (!selectedInspiration.value) return ''
  return sanitizeInspirationHtml(
    selectedInspiration.value.content_html || selectedInspiration.value.content || ''
  )
})

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function loadImageAssets() {
  const params = appStore.selectedAccountId
    ? { account_id: appStore.selectedAccountId }
    : undefined
  await imageAssetStore.fetchImageAssets(params)
}

async function loadData() {
  loading.value = true
  const params = appStore.selectedAccountId
    ? { account_id: appStore.selectedAccountId }
    : undefined
  await Promise.all([
    inspirationStore.fetchInspirations(params),
    imageAssetStore.fetchImageAssets(params),
    accountStore.fetchAccounts()
  ]).finally(() => {
    loading.value = false
  })
}

function preferredAccountId() {
  return appStore.selectedAccountId || accountStore.accounts[0]?.account_id || 'default'
}

function openCollectDialog() {
  collectForm.value.account_id = preferredAccountId()
  showCollectDialog.value = true
}

function openUploadDialog() {
  uploadForm.value = {
    title: '',
    account_id: preferredAccountId()
  }
  uploadFile.value = null
  showUploadDialog.value = true
}

function openGenerateDialog() {
  generateForm.value = {
    title: '',
    prompt: '',
    account_id: preferredAccountId()
  }
  showGenerateDialog.value = true
}

function handleUploadChange(file) {
  uploadFile.value = file.raw || null
}

function handleUploadRemove() {
  uploadFile.value = null
}

async function submitUpload() {
  if (!uploadFile.value) {
    ElMessage.warning('请选择图片文件')
    return
  }
  uploading.value = true
  try {
    await imageAssetStore.uploadImageAsset({
      file: uploadFile.value,
      account_id: uploadForm.value.account_id || preferredAccountId(),
      title: uploadForm.value.title
    })
    ElMessage.success('图片素材已上传')
    showUploadDialog.value = false
    await loadImageAssets()
  } catch (error) {
    ElMessage.error(error.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function submitGenerate() {
  if (!generateForm.value.prompt.trim()) {
    ElMessage.warning('请输入图片提示词')
    return
  }
  generating.value = true
  try {
    await imageAssetStore.generateImageAsset({
      title: generateForm.value.title,
      prompt: generateForm.value.prompt,
      account_id: generateForm.value.account_id || preferredAccountId()
    })
    ElMessage.success('图片素材已生成')
    showGenerateDialog.value = false
    await loadImageAssets()
  } catch (error) {
    ElMessage.error(error.message || '生成失败')
  } finally {
    generating.value = false
  }
}

async function collect() {
  if (!collectForm.value.url) {
    ElMessage.warning('请输入链接')
    return
  }
  collecting.value = true
  try {
    await inspirationStore.collect(collectForm.value.url, collectForm.value.account_id || preferredAccountId())
    ElMessage.success('采集任务已创建，3 秒后自动刷新列表')
    showCollectDialog.value = false
    collectForm.value = { url: '', account_id: '' }
    setTimeout(() => {
      loadData()
    }, 3000)
  } catch (error) {
    ElMessage.error(error.message || '采集失败')
  } finally {
    collecting.value = false
  }
}

async function createArticle(id) {
  try {
    const article = await inspirationStore.createArticle(id)
    ElMessage.success('已创建文章，前往改写')
    router.push({ name: 'Rewrite', query: { id: article.id } })
  } catch (error) {
    ElMessage.error(error.message || '创建文章失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除这条素材吗？"${row.title || '无标题'}"`,
      '确认删除',
      { type: 'warning' }
    )
    await inspirationStore.deleteInspiration(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

async function deleteImageAsset(asset) {
  try {
    await ElMessageBox.confirm(
      `确定要删除图片素材 "${asset.title || '未命名图片'}" 吗？`,
      '确认删除',
      { type: 'warning' }
    )
    await imageAssetStore.deleteImageAsset(asset.id)
    ElMessage.success('图片素材已删除')
    await loadImageAssets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

async function copyImageUrl(asset) {
  const fullUrl = `${window.location.origin}${asset.image_url}`
  try {
    await navigator.clipboard.writeText(fullUrl)
    ElMessage.success('图片地址已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

function openOriginal(url) {
  if (!url) {
    ElMessage.warning('当前素材没有原文链接')
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

function viewDetail(row) {
  openInspirationDetail(row.id)
}

function sanitizeInspirationHtml(html) {
  if (!html) return ''
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')
  doc.body.querySelectorAll('img').forEach((node) => {
    const dataSrc = node.getAttribute('data-src') || ''
    if (dataSrc && !node.getAttribute('src')) {
      node.setAttribute('src', dataSrc)
    }
    node.setAttribute('referrerpolicy', 'no-referrer')
    node.setAttribute('loading', 'lazy')
  })
  doc.body.querySelectorAll('[style]').forEach((node) => {
    const style = node.getAttribute('style') || ''
    const declarations = style
      .split(';')
      .map(item => item.trim())
      .filter(Boolean)
      .filter(item => !/^visibility\s*:\s*hidden$/i.test(item))
      .filter(item => !/^opacity\s*:\s*0(?:\.0+)?$/i.test(item))
    if (declarations.length) {
      node.setAttribute('style', declarations.join('; '))
    } else {
      node.removeAttribute('style')
    }
  })
  doc.body.querySelectorAll('section, p, div').forEach((node) => {
    const text = (node.textContent || '').replace(/\s+/g, ' ').trim()
    const onlyBreaks = Array.from(node.childNodes).every((child) => {
      if (child.nodeType === Node.TEXT_NODE) {
        return !(child.textContent || '').trim()
      }
      return child.nodeName === 'BR'
    })
    if (onlyBreaks) {
      node.remove()
      return
    }
    if (/^编辑[｜丨:：]\s*\S+/i.test(text) && text.length <= 24) {
      node.remove()
    }
  })
  return doc.body.innerHTML
}

async function openInspirationDetail(id) {
  try {
    selectedInspiration.value = await inspirationStore.getInspiration(id)
    showDetailDialog.value = true
    nextTick(() => {
      if (contentRef.value) {
        contentRef.value.querySelectorAll('img').forEach(img => {
          img.referrerPolicy = 'no-referrer'
        })
      }
    })
  } catch (error) {
    ElMessage.error(error.message || '加载素材详情失败')
  }
}

onMounted(() => {
  loadData()
})

watch(() => appStore.selectedAccountId, () => {
  loadData()
})

watch(() => route.query.tab, (tab) => {
  activeTab.value = ['articles', 'images', 'wechat'].includes(tab) ? tab : 'articles'
})

watch(activeTab, (tab) => {
  router.replace({
    query: {
      ...route.query,
      tab
    }
  })
})
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
  flex-wrap: wrap;
}

.image-header {
  align-items: flex-start;
}

.image-toolbar-tip {
  font-size: 13px;
  color: #64748b;
}

.inspiration-title {
  font-weight: 600;
  color: #1e293b;
}

.inspiration-tags {
  margin-top: 6px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.image-card {
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
}

.image-card-preview {
  aspect-ratio: 16 / 10;
  background: #f8fafc;
}

.image-card-preview img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-card-body {
  padding: 12px;
}

.image-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.5;
}

.image-card-meta {
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: #64748b;
}

.image-card-prompt {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #475569;
  min-height: 38px;
}

.image-card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.content-box {
  max-height: 70vh;
  overflow-y: auto;
  line-height: 1.8;
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

.detail-meta-panel {
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: linear-gradient(180deg, #f8fbff 0%, #f8fafc 100%);
  position: sticky;
  top: 0;
}

.detail-meta-eyebrow {
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
  letter-spacing: 0;
}

.detail-title {
  margin: 12px 0 0;
  font-size: 24px;
  line-height: 1.4;
  color: #0f172a;
}

.detail-meta-row {
  display: grid;
  gap: 12px;
  margin-top: 20px;
}

.detail-meta-item {
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #e2e8f0;
}

.detail-meta-label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.detail-meta-value {
  display: block;
  font-size: 14px;
  color: #0f172a;
  font-weight: 600;
}

.detail-source-actions {
  margin-top: 18px;
}

.detail-preview-shell {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #eef4ff 0%, #f8fafc 100%);
  border: 1px solid #dbeafe;
}

.detail-preview-device {
  max-width: 520px;
  margin: 0 auto;
  border-radius: 24px;
  background: #ffffff;
  border: 1px solid #dbe2ea;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
  overflow: hidden;
}

.detail-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid #eef2f7;
  background: #f8fafc;
}

.detail-preview-dots {
  display: flex;
  gap: 6px;
}

.detail-preview-dots span {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #cbd5e1;
  display: inline-block;
}

.detail-preview-caption {
  font-size: 12px;
  color: #64748b;
}

.detail-article {
  background: #fff;
}

.detail-article-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.detail-article-header h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.42;
  color: #111827;
  font-weight: 700;
}

.article-content {
  padding: 0 24px 28px;
  font-size: 17px;
  color: #1f2937;
  background: #fff;
}

.article-content :deep(section) {
  margin: 0 0 1.15em;
}

.article-content :deep(p) {
  margin: 0 0 1.15em;
  line-height: 1.95;
  color: #1f2937;
}

.article-content :deep(h1),
.article-content :deep(h2),
.article-content :deep(h3) {
  margin: 1.35em 0 0.75em;
  line-height: 1.45;
  color: #0f172a;
}

.article-content :deep(h2) {
  padding: 10px 14px 10px 16px;
  font-size: 21px;
  font-weight: 700;
  border-left: 4px solid #3b82f6;
  border-radius: 0 12px 12px 0;
  background: linear-gradient(90deg, #eff6ff 0%, #f8fbff 100%);
}

.article-content :deep(h3) {
  padding-left: 12px;
  font-size: 18px;
  font-weight: 700;
  border-left: 3px solid #cbd5e1;
}

.article-content :deep(img) {
  display: block;
  width: 100%;
  max-width: 100%;
  height: auto;
  border-radius: 12px;
  margin: 18px auto;
  background: #f8fafc;
}

.article-content :deep(blockquote) {
  margin: 1.4em 0;
  padding: 14px 16px;
  border-left: 4px solid #60a5fa;
  background: #f8fbff;
  color: #334155;
}

.article-content :deep(ul),
.article-content :deep(ol) {
  margin: 0 0 1.2em;
  padding-left: 1.4em;
}

.article-content :deep(li) {
  margin-bottom: 0.6em;
  line-height: 1.9;
}

.text-gray-500 {
  color: #64748b;
}

.mb-4 {
  margin-bottom: 16px;
}

@media (max-width: 960px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }

  .detail-meta-panel {
    position: static;
  }

  .detail-preview-device {
    max-width: 100%;
  }
}

@media (max-width: 640px) {
  .detail-preview-shell,
  .detail-meta-panel {
    padding: 14px;
  }

  .detail-title {
    font-size: 20px;
  }

  .detail-article-header {
    padding: 18px 18px 14px;
  }

  .detail-article-header h1 {
    font-size: 24px;
  }

  .article-content {
    padding: 0 18px 22px;
    font-size: 16px;
  }
}
</style>
