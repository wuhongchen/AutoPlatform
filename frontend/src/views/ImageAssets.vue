<template>
  <div class="image-assets-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="toolbar-left">
            <el-input
              v-model="searchQuery"
              placeholder="搜索图片素材..."
              :prefix-icon="Search"
              style="width: 280px"
              clearable
            />
            <span class="toolbar-tip">共 {{ imageAssetStore.imageAssets.length }} 张</span>
          </div>
          <div class="toolbar-right">
            <el-button @click="loadAssets">
              <el-icon><Refresh /></el-icon>刷新
            </el-button>
            <el-button type="primary" @click="openUpload">
              <el-icon><Plus /></el-icon>上传图片
            </el-button>
            <el-button @click="openGenerate">
              <el-icon><MagicStick /></el-icon>AI 生成
            </el-button>
          </div>
        </div>
      </template>

      <div v-if="filteredAssets.length" class="image-grid">
        <div v-for="asset in filteredAssets" :key="asset.id" class="image-card">
          <div class="image-card-preview">
            <img :src="asset.image_url" :alt="asset.title || '图片素材'" />
          </div>
          <div class="image-card-body">
            <div class="image-card-title">{{ asset.title || '未命名' }}</div>
            <div class="image-card-meta">
              <el-tag :type="asset.source_type === 'ai' ? 'warning' : 'info'" size="small">
                {{ asset.source_type === 'ai' ? 'AI 生成' : '上传' }}
              </el-tag>
              <span>{{ formatDate(asset.created_at) }}</span>
            </div>
            <div v-if="asset.prompt" class="image-card-prompt">{{ asset.prompt }}</div>
            <div class="image-card-actions">
              <el-button size="small" @click="copyUrl(asset.image_url)">复制链接</el-button>
              <el-button size="small" type="danger" @click="handleDelete(asset)">删除</el-button>
            </div>
          </div>
        </div>
      </div>

      <el-empty v-else description="暂无图片素材" />
    </el-card>

    <!-- 上传 -->
    <el-dialog v-model="uploadVisible" title="上传图片" width="480px">
      <el-upload
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        accept="image/*"
        :limit="1"
      >
        <el-icon :size="48"><UploadFilled /></el-icon>
        <div class="upload-text">拖拽或点击上传</div>
      </el-upload>
      <el-form-item label="图片名称" style="margin-top: 16px">
        <el-input v-model="uploadForm.title" placeholder="可选" />
      </el-form-item>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" @click="doUpload" :loading="uploading" :disabled="!uploadFile">
          上传
        </el-button>
      </template>
    </el-dialog>

    <!-- AI 生成 -->
    <el-dialog v-model="generateVisible" title="AI 生成图片" width="480px">
      <el-form :model="generateForm" label-width="80px">
        <el-form-item label="提示词">
          <el-input v-model="generateForm.prompt" type="textarea" :rows="4"
            placeholder="描述你想要的图片..." />
        </el-form-item>
        <el-form-item label="尺寸">
          <el-select v-model="generateForm.size" style="width: 100%">
            <el-option label="1280x720 (横屏)" value="1280x720" />
            <el-option label="720x1280 (竖屏)" value="720x1280" />
            <el-option label="1024x1024 (方形)" value="1024x1024" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateVisible = false">取消</el-button>
        <el-button type="primary" @click="doGenerate" :loading="generating" :disabled="!generateForm.prompt">
          生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, Plus, Refresh, Search, UploadFilled } from '@element-plus/icons-vue'
import { useAppStore, useImageAssetStore } from '../stores'

const appStore = useAppStore()
const imageAssetStore = useImageAssetStore()

const searchQuery = ref('')
const uploadVisible = ref(false)
const generateVisible = ref(false)
const uploading = ref(false)
const generating = ref(false)
const uploadFile = ref(null)
const uploadForm = reactive({ title: '' })
const generateForm = reactive({ prompt: '', size: '1280x720' })

const filteredAssets = computed(() => {
  if (!searchQuery.value) return imageAssetStore.imageAssets
  const s = searchQuery.value.toLowerCase()
  return imageAssetStore.imageAssets.filter(a =>
    (a.title || '').toLowerCase().includes(s) ||
    (a.prompt || '').toLowerCase().includes(s)
  )
})

async function loadAssets() {
  const params = appStore.selectedAccountId
    ? { account_id: appStore.selectedAccountId }
    : undefined
  await imageAssetStore.fetchImageAssets(params)
}

function openUpload() { uploadVisible.value = true; uploadFile.value = null; uploadForm.title = '' }
function openGenerate() { generateVisible.value = true }

function handleFileChange(file) { uploadFile.value = file }

async function doUpload() {
  if (!uploadFile.value) return
  uploading.value = true
  try {
    await imageAssetStore.uploadImageAsset({
      file: uploadFile.value.raw,
      title: uploadForm.title,
      account_id: appStore.selectedAccountId || 'default',
    })
    ElMessage.success('上传成功')
    uploadVisible.value = false
    loadAssets()
  } catch (e) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function doGenerate() {
  generating.value = true
  try {
    await imageAssetStore.generateImageAsset({
      prompt: generateForm.prompt,
      size: generateForm.size,
      account_id: appStore.selectedAccountId || 'default',
    })
    ElMessage.success('生成成功')
    generateVisible.value = false
    loadAssets()
  } catch (e) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    generating.value = false
  }
}

async function copyUrl(url) {
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('链接已复制')
  } catch { ElMessage.info(url) }
}

async function handleDelete(asset) {
  try {
    await ElMessageBox.confirm('确定删除这张图片？', '确认', { type: 'warning' })
    await imageAssetStore.deleteImageAsset(asset.id)
    ElMessage.success('已删除')
    loadAssets()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.message || '删除失败')
  }
}

function formatDate(val) {
  if (!val) return '-'
  try { return new Date(val).toLocaleDateString('zh-CN') } catch { return val }
}

onMounted(loadAssets)
watch(() => appStore.selectedAccountId, loadAssets)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.toolbar-left, .toolbar-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.toolbar-tip { font-size: 13px; color: var(--text-secondary); }

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.image-card {
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: #fff;
}
.image-card-preview { aspect-ratio: 16 / 10; background: #f8fafc; }
.image-card-preview img { display: block; width: 100%; height: 100%; object-fit: cover; }
.image-card-body { padding: 12px; }
.image-card-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.image-card-meta { margin-top: 8px; display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: var(--text-secondary); }
.image-card-prompt { margin-top: 8px; font-size: 12px; line-height: 1.6; color: var(--text-secondary); }
.image-card-actions { display: flex; gap: 8px; margin-top: 12px; }
.upload-text { margin-top: 8px; color: var(--text-secondary); }
</style>
