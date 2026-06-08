<template>
  <div class="sticker-post-page">
    <div class="work-area">
      <!-- 左侧：上传 + 编辑 -->
      <div class="edit-panel">
        <el-card shadow="never">
          <template #header><span>贴图信息</span></template>
          <el-form :model="form" label-position="top">
            <el-form-item label="标题">
              <el-input v-model="form.title" placeholder="输入贴图标题（最多 20 字）" maxlength="20" show-word-limit />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="3"
                placeholder="简短描述（最多 200 字）" maxlength="200" show-word-limit />
            </el-form-item>
            <el-form-item label="账户">
              <el-select v-model="form.account_id" style="width: 100%">
                <el-option v-for="acc in accountStore.accounts" :key="acc.account_id"
                  :label="`${acc.name} (${acc.account_id})`" :value="acc.account_id" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 图片上传区 -->
        <el-card shadow="never" class="upload-card">
          <template #header>
            <div class="card-header">
              <span>图片 ({{ images.length }})</span>
              <span class="card-tip">拖拽排序，点击删除</span>
            </div>
          </template>

          <!-- 上传按钮 -->
          <div class="upload-zone" @click="triggerUpload" @paste="handlePaste" tabindex="0">
            <input ref="fileInput" type="file" accept="image/*" multiple
              @change="handleFileSelect" style="display:none" />
            <el-icon :size="36"><Plus /></el-icon>
            <span>点击上传或 Ctrl+V 粘贴</span>
          </div>

          <!-- 图片网格 -->
          <div v-if="images.length" class="image-grid">
            <div v-for="(img, i) in images" :key="i" class="image-item" draggable="true"
              @dragstart="onDragStart(i)" @dragover.prevent @drop="onDrop(i)">
              <img :src="img.preview" :alt="img.name" />
              <div class="image-overlay">
                <span class="image-index">{{ i + 1 }}</span>
                <el-button size="small" type="danger" circle :icon="'Close'"
                  @click.stop="removeImage(i)" />
              </div>
            </div>
          </div>
        </el-card>

        <!-- 操作按钮 -->
        <div class="action-bar">
          <el-button type="primary" size="large" @click="handlePublish" :loading="publishing"
            :disabled="!canSubmit">
            <el-icon><Promotion /></el-icon>保存并发布
          </el-button>
          <el-button size="large" @click="handleSaveDraft" :loading="saving"
            :disabled="!canSubmit">
            <el-icon><Document /></el-icon>仅保存草稿
          </el-button>
        </div>
      </div>

      <!-- 右侧：预览 -->
      <div class="preview-panel">
        <div class="preview-header">
          <span>手机预览</span>
        </div>
        <div class="preview-phone">
          <div class="phone-screen">
            <div class="phone-status-bar">
              <span>12:00</span>
              <span>📶 🔋</span>
            </div>
            <div v-if="form.title" class="preview-article">
              <h1 class="preview-title">{{ form.title }}</h1>
              <p v-if="form.description" class="preview-desc">{{ form.description }}</p>
              <div v-if="images.length" class="preview-images">
                <img v-for="(img, i) in images" :key="i" :src="img.preview" :alt="img.name" />
              </div>
              <div v-if="!images.length" class="preview-empty">
                <el-empty description="上传图片后可预览" :image-size="80" />
              </div>
            </div>
            <div v-else class="preview-empty">
              <el-empty description="输入标题和图片后预览" :image-size="80" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Close, Document, Plus, Promotion } from '@element-plus/icons-vue'
import { useAccountStore, useAppStore } from '../stores'
import api from '../api'

const accountStore = useAccountStore()
const appStore = useAppStore()

const form = reactive({ title: '', description: '', account_id: '' })
const images = ref([])
const publishing = ref(false)
const saving = ref(false)
const fileInput = ref(null)
const dragIndex = ref(null)

const canSubmit = computed(() => form.title.trim() && images.value.length > 0)

function triggerUpload() { fileInput.value?.click() }

async function handleFileSelect(e) {
  for (const file of e.target.files) {
    await addImage(file)
  }
  e.target.value = ''
}

async function handlePaste(e) {
  const items = e.clipboardData?.items || []
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      await addImage(item.getAsFile())
    }
  }
}

async function addImage(file) {
  if (!file) return
  const preview = URL.createObjectURL(file)
  images.value.push({ file, preview, name: file.name || 'image' })
}

function removeImage(i) { images.value.splice(i, 1) }

function onDragStart(i) { dragIndex.value = i }
function onDrop(i) {
  if (dragIndex.value === null || dragIndex.value === i) return
  const items = [...images.value]
  const [moved] = items.splice(dragIndex.value, 1)
  items.splice(i, 0, moved)
  images.value = items
  dragIndex.value = null
}

async function uploadAllImages() {
  const urls = []
  for (const img of images.value) {
    const formData = new FormData()
    formData.append('file', img.file)
    try {
      const result = await api.imageHosting.upload(formData)
      urls.push(result.url || result.image_url)
    } catch (e) {
      ElMessage.error(`图片 ${img.name} 上传失败: ${e.message}`)
    }
  }
  return urls
}

async function handlePublish() {
  if (!canSubmit.value) return
  publishing.value = true
  try {
    const imageUrls = await uploadAllImages()
    if (!imageUrls.length) { ElMessage.error('没有成功上传的图片'); return }
    const result = await api.stickers.create({
      title: form.title,
      description: form.description,
      account_id: form.account_id || 'default',
      images: imageUrls,
      publish: true,
    })
    ElMessage.success(result.task_id
      ? `发布任务已创建: ${result.task_id.slice(0, 8)}`
      : '已保存并发布')
    resetForm()
  } catch (e) {
    ElMessage.error(e.message || '发布失败')
  } finally { publishing.value = false }
}

async function handleSaveDraft() {
  if (!canSubmit.value) return
  saving.value = true
  try {
    const imageUrls = await uploadAllImages()
    if (!imageUrls.length) { ElMessage.error('没有成功上传的图片'); return }
    const result = await api.stickers.create({
      title: form.title,
      description: form.description,
      account_id: form.account_id || 'default',
      images: imageUrls,
      publish: false,
    })
    ElMessage.success('草稿已保存')
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally { saving.value = false }
}

function resetForm() {
  form.title = ''; form.description = ''
  images.value = []
}

onMounted(async () => {
  await accountStore.fetchAccounts()
  form.account_id = appStore.selectedAccountId || accountStore.accounts[0]?.account_id || ''
})
</script>

<style scoped>
.sticker-post-page { min-height: 100%; }
.work-area { display: flex; gap: 20px; align-items: flex-start; }

/* 左侧 */
.edit-panel { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 16px; }
.upload-card { margin-top: 0; }

.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-tip { font-size: 12px; color: var(--text-muted); }

/* 上传区 */
.upload-zone {
  border: 2px dashed var(--border); border-radius: var(--radius); padding: 28px;
  text-align: center; color: var(--text-muted); cursor: pointer; transition: all 0.2s;
  display: flex; flex-direction: column; align-items: center; gap: 8px; margin-bottom: 16px;
}
.upload-zone:hover { border-color: var(--accent); color: var(--accent); background: #fafbff; }

/* 图片网格 */
.image-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.image-item {
  position: relative; aspect-ratio: 4/3; border-radius: var(--radius-sm); overflow: hidden;
  cursor: grab; border: 2px solid transparent; transition: border-color 0.2s;
}
.image-item:hover { border-color: var(--accent); }
.image-item img { width: 100%; height: 100%; object-fit: cover; display: block; }
.image-overlay {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0); transition: background 0.2s;
  display: flex; align-items: flex-start; justify-content: space-between; padding: 6px;
}
.image-item:hover .image-overlay { background: rgba(0,0,0,0.3); }
.image-index {
  width: 22px; height: 22px; border-radius: 50%; background: var(--accent);
  color: #fff; font-size: 12px; display: flex; align-items: center; justify-content: center;
}

/* 操作 */
.action-bar { display: flex; gap: 12px; padding-top: 4px; }

/* 右侧预览 */
.preview-panel { flex: 0 0 340px; position: sticky; top: 24px; }
.preview-header {
  font-size: 13px; font-weight: 600; color: var(--text-secondary);
  text-align: center; margin-bottom: 12px;
}
.preview-phone {
  background: #1a1a2e; border-radius: 28px; padding: 12px;
  box-shadow: 0 16px 40px rgba(0,0,0,0.15);
}
.phone-screen {
  background: #fff; border-radius: 18px; overflow: hidden; min-height: 500px;
}
.phone-status-bar {
  display: flex; justify-content: space-between; padding: 8px 16px;
  font-size: 11px; color: #1a1a2e; background: #f8f8f8; font-weight: 600;
}
.preview-article { padding: 20px 16px; }
.preview-title { font-size: 18px; font-weight: 700; color: #111; margin-bottom: 8px; text-align: center; }
.preview-desc { font-size: 14px; color: #666; text-align: center; line-height: 1.7; margin-bottom: 16px; }
.preview-images img { display: block; width: 100%; height: auto; margin-bottom: 0; }
.preview-empty { padding: 60px 0; }

@media (max-width: 900px) { .work-area { flex-direction: column; } .preview-panel { flex: 1; width: 100%; } }
</style>
