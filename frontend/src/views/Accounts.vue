<template>
  <div class="accounts-page">
    <el-card shadow="never">
      <template #header>
        <div class="accounts-toolbar">
          <div class="accounts-toolbar-main">
            <div class="accounts-toolbar-title-row">
              <span class="accounts-toolbar-title">账户列表</span>
              <span class="accounts-toolbar-badge">{{ accountStore.accounts.length }} 个账户</span>
            </div>
            <div class="accounts-toolbar-subtitle">
              当前账户：
              <span class="accounts-toolbar-current">
                {{ selectedAccountLabel }}
              </span>
            </div>
          </div>
          <el-button type="primary" class="accounts-create-button" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>
            <span>新建账户</span>
          </el-button>
        </div>
      </template>

      <el-table :data="accountStore.accounts" v-loading="loading" stripe>
        <el-table-column label="账户名称" prop="name" min-width="140" />
        <el-table-column label="账户ID" prop="account_id" min-width="140" />
        <el-table-column label="作者" min-width="120">
          <template #default="{ row }">
            {{ row.wechat_author || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="广告位" min-width="220">
          <template #default="{ row }">
            <div class="ad-cell">
              <div class="tag-list">
                <el-tag v-if="row.ad_header_html" size="small" type="success">头部</el-tag>
                <el-tag v-if="row.ad_footer_html" size="small" type="warning">底部</el-tag>
                <span v-if="!row.ad_header_html && !row.ad_footer_html" class="text-gray-400">未配置</span>
              </div>
              <el-button size="small" link type="primary" @click="openAdDialog(row)">
                配置广告位
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="默认风格" width="150">
          <template #default="{ row }">
            {{ row.pipeline_role }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button
                v-if="appStore.selectedAccountId !== row.account_id"
                size="small"
                type="primary"
                @click="switchAccount(row.account_id)"
              >
                切换
              </el-button>
              <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑账户' : '新建账户'"
      width="720px"
      destroy-on-close
    >
      <div class="account-guide">
        <div class="account-guide-title">配置说明</div>
        <div class="account-guide-text">
          发布到公众号至少需要补齐微信 `AppID` 和 `密钥`。可在微信公众平台的“开发 / 基本配置”里获取；
          “默认作者”和“默认改写风格”会作为文章发布与改写时的默认值使用。
        </div>
      </div>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="账户名称" prop="name">
              <el-input v-model="form.name" placeholder="例如：主账号" />
              <span class="form-tip">用于后台区分账号，例如品牌号、个人号、测试号。</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="账户ID" prop="account_id" v-if="!isEdit">
              <el-input
                :model-value="form.account_id"
                placeholder="根据账户名称自动生成"
                disabled
              />
              <span class="form-tip">系统会根据账户名称自动生成唯一标识，创建后固定不可变。</span>
            </el-form-item>
            <el-form-item label="账户ID" v-else>
              <el-input :model-value="form.account_id" disabled />
              <span class="form-tip">账户ID 作为系统内主键使用，创建后固定不可变。</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="微信AppID">
              <el-input v-model="form.wechat_appid" placeholder="可选" />
              <span class="form-tip">实际发布公众号草稿时必填，可在微信公众平台“开发 / 基本配置”查看。</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="微信密钥">
              <el-input v-model="form.wechat_secret" type="password" placeholder="可选" show-password />
              <span class="form-tip">与 AppID 配套使用，仅在发布到公众号时需要填写。</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="默认作者">
              <el-input v-model="form.wechat_author" placeholder="发布时显示的作者名" />
              <span class="form-tip">不填时文章会优先使用文章自身作者；这里适合作为账号级兜底作者名。</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="默认改写风格">
              <el-select v-model="form.pipeline_role" placeholder="选择默认风格" style="width: 100%">
                <el-option label="科技专家" value="tech_expert" />
                <el-option label="商业分析师" value="business_analyst" />
                <el-option label="故事讲述者" value="storyteller" />
                <el-option label="科普作家" value="popular_science" />
                <el-option label="观点领袖" value="opinion_leader" />
                <el-option label="趋势观察者" value="trend_observer" />
                <el-option label="实战派" value="practitioner" />
                <el-option label="娱乐向" value="entertainment" />
              </el-select>
              <span class="form-tip">新采集或新建文章在未单独指定风格时，会默认使用这里的改写风格。</span>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="adDialogVisible"
      title="广告位配置"
      width="960px"
      destroy-on-close
    >
      <div class="ad-dialog-header">
        <div>
          <div class="ad-dialog-title">{{ adDialogAccount?.name }}</div>
          <div class="ad-dialog-subtitle">{{ adDialogAccount?.account_id }}</div>
        </div>
      </div>

      <el-tabs v-model="activeAdTab">
        <el-tab-pane label="头部广告位" name="header">
          <div class="ad-layout">
            <div class="ad-form-panel">
              <el-form label-width="100px">
                <el-form-item label="标题">
                  <el-input v-model="adForm.header.title" placeholder="例如：推荐阅读 / 限时活动" />
                </el-form-item>
                <el-form-item label="说明">
                  <el-input
                    v-model="adForm.header.description"
                    type="textarea"
                    :rows="4"
                    placeholder="输入广告说明文案"
                  />
                </el-form-item>
                <el-form-item label="图片地址">
                  <div class="image-field">
                    <el-input v-model="adForm.header.image_url" placeholder="输入图片 URL 或直接上传" />
                    <el-upload
                      :show-file-list="false"
                      :auto-upload="false"
                      accept="image/*"
                      :before-upload="(file) => handleAdImageSelect(file, 'header')"
                    >
                      <el-button>上传图片</el-button>
                    </el-upload>
                  </div>
                </el-form-item>
                <el-form-item label="按钮文案">
                  <el-input v-model="adForm.header.button_text" placeholder="例如：立即查看" />
                </el-form-item>
                <el-form-item label="跳转链接">
                  <el-input v-model="adForm.header.button_url" placeholder="例如：https://example.com" />
                </el-form-item>
              </el-form>
            </div>
            <div class="ad-preview-panel">
              <div class="ad-preview-title">预览</div>
              <div v-if="headerPreviewHtml" class="ad-preview-card" v-html="headerPreviewHtml" />
              <el-empty v-else description="未配置头部广告位" :image-size="80" />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="底部广告位" name="footer">
          <div class="ad-layout">
            <div class="ad-form-panel">
              <el-form label-width="100px">
                <el-form-item label="标题">
                  <el-input v-model="adForm.footer.title" placeholder="例如：延伸阅读 / 关注引导" />
                </el-form-item>
                <el-form-item label="说明">
                  <el-input
                    v-model="adForm.footer.description"
                    type="textarea"
                    :rows="4"
                    placeholder="输入广告说明文案"
                  />
                </el-form-item>
                <el-form-item label="图片地址">
                  <div class="image-field">
                    <el-input v-model="adForm.footer.image_url" placeholder="输入图片 URL 或直接上传" />
                    <el-upload
                      :show-file-list="false"
                      :auto-upload="false"
                      accept="image/*"
                      :before-upload="(file) => handleAdImageSelect(file, 'footer')"
                    >
                      <el-button>上传图片</el-button>
                    </el-upload>
                  </div>
                </el-form-item>
                <el-form-item label="按钮文案">
                  <el-input v-model="adForm.footer.button_text" placeholder="例如：点击了解" />
                </el-form-item>
                <el-form-item label="跳转链接">
                  <el-input v-model="adForm.footer.button_url" placeholder="例如：https://example.com" />
                </el-form-item>
              </el-form>
            </div>
            <div class="ad-preview-panel">
              <div class="ad-preview-title">预览</div>
              <div v-if="footerPreviewHtml" class="ad-preview-card" v-html="footerPreviewHtml" />
              <el-empty v-else description="未配置底部广告位" :image-size="80" />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="resetActiveAdTab">清空当前广告位</el-button>
        <el-button @click="adDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAdConfig" :loading="savingAds">
          保存广告位
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAccountStore, useAppStore } from '../stores'

const accountStore = useAccountStore()
const appStore = useAppStore()
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const adDialogVisible = ref(false)
const savingAds = ref(false)
const activeAdTab = ref('header')
const adDialogAccount = ref(null)

const createEmptyForm = () => ({
  name: '',
  account_id: '',
  wechat_appid: '',
  wechat_secret: '',
  wechat_author: '',
  pipeline_role: 'tech_expert'
})

const createEmptyAdSlot = () => ({
  title: '',
  description: '',
  image_url: '',
  button_text: '',
  button_url: ''
})

const form = ref(createEmptyForm())
const adForm = ref({
  header: createEmptyAdSlot(),
  footer: createEmptyAdSlot()
})

const rules = {
  name: [{ required: true, message: '请输入账户名称', trigger: 'blur' }],
  account_id: [{ required: true, message: '请输入账户ID', trigger: 'blur' }]
}

const headerPreviewHtml = computed(() => buildAdHtml(adForm.value.header))
const footerPreviewHtml = computed(() => buildAdHtml(adForm.value.footer))
const selectedAccountLabel = computed(() => {
  const selected = accountStore.accounts.find(account => account.account_id === appStore.selectedAccountId)
  if (!selected) return '未选择账户'
  return `${selected.name} (${selected.account_id})`
})

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function escapeHtml(value) {
  return (value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function buildAdHtml(slot) {
  if (!slot) return ''
  const hasContent = slot.title || slot.description || slot.image_url || slot.button_text
  if (!hasContent) return ''

  const imageHtml = slot.image_url
    ? `<img src="${escapeHtml(slot.image_url)}" alt="${escapeHtml(slot.title || '广告图')}" style="display:block;width:100%;max-width:100%;height:auto;border-radius:10px;margin-bottom:12px;" />`
    : ''

  const titleHtml = slot.title
    ? `<div style="font-size:18px;font-weight:700;color:#0f172a;line-height:1.5;margin-bottom:8px;">${escapeHtml(slot.title)}</div>`
    : ''

  const descHtml = slot.description
    ? `<div style="font-size:14px;color:#475569;line-height:1.7;white-space:pre-wrap;margin-bottom:${slot.button_text ? '14px' : '0'};">${escapeHtml(slot.description)}</div>`
    : ''

  let buttonHtml = ''
  if (slot.button_text) {
    const tag = slot.button_url ? 'a' : 'span'
    const href = slot.button_url ? ` href="${escapeHtml(slot.button_url)}"` : ''
    buttonHtml = `<${tag}${href} style="display:inline-block;padding:8px 14px;border-radius:999px;background:#2563eb;color:#ffffff;font-size:13px;font-weight:600;text-decoration:none;">${escapeHtml(slot.button_text)}</${tag}>`
  }

  return `
    <section style="padding:16px;border-radius:14px;background:#f8fafc;border:1px solid #dbeafe;">
      ${imageHtml}
      ${titleHtml}
      ${descHtml}
      ${buttonHtml}
    </section>
  `
}

function parseAdSlots(account) {
  const slots = account?.metadata?.ad_slots || {}
  return {
    header: { ...createEmptyAdSlot(), ...(slots.header || {}) },
    footer: { ...createEmptyAdSlot(), ...(slots.footer || {}) }
  }
}

function hashString(value) {
  let hash = 0
  for (const char of value) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  }
  return hash.toString(36)
}

function generateAccountId(name) {
  const normalizedName = (name || '')
    .trim()
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .replace(/_+/g, '_')
    .slice(0, 24)

  const baseId = normalizedName || `acc_${hashString((name || '').trim() || 'account')}`
  const usedIds = new Set(accountStore.accounts.map(account => account.account_id))

  if (!usedIds.has(baseId)) {
    return baseId
  }

  let suffix = 2
  let candidate = `${baseId}_${suffix}`
  while (usedIds.has(candidate)) {
    suffix += 1
    candidate = `${baseId}_${suffix}`
  }
  return candidate
}

function handleAdImageSelect(file, slotKey) {
  const reader = new FileReader()
  reader.onload = (event) => {
    adForm.value[slotKey].image_url = event.target?.result || ''
  }
  reader.readAsDataURL(file)
  return false
}

async function loadData() {
  loading.value = true
  const accounts = await accountStore.fetchAccounts().finally(() => {
    loading.value = false
  })

  if (accounts.length && !accounts.some(acc => acc.account_id === appStore.selectedAccountId)) {
    appStore.setSelectedAccount(accounts[0].account_id)
  }
}

function openCreateDialog() {
  isEdit.value = false
  form.value = createEmptyForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  form.value = {
    name: row.name,
    account_id: row.account_id,
    wechat_appid: row.wechat_appid || '',
    wechat_secret: row.wechat_secret || '',
    wechat_author: row.wechat_author || '',
    pipeline_role: row.pipeline_role || 'tech_expert'
  }
  dialogVisible.value = true
}

function openAdDialog(row) {
  adDialogAccount.value = row
  adForm.value = parseAdSlots(row)
  activeAdTab.value = 'header'
  adDialogVisible.value = true
}

function resetActiveAdTab() {
  adForm.value[activeAdTab.value] = createEmptyAdSlot()
}

async function handleSubmit() {
  if (!isEdit.value && !form.value.account_id) {
    form.value.account_id = generateAccountId(form.value.name)
  }

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = {
      name: form.value.name,
      account_id: form.value.account_id,
      wechat_appid: form.value.wechat_appid,
      wechat_secret: form.value.wechat_secret,
      wechat_author: form.value.wechat_author,
      pipeline_role: form.value.pipeline_role
    }

    if (isEdit.value) {
      await accountStore.updateAccount(form.value.account_id, payload)
      ElMessage.success('更新成功')
    } else {
      await accountStore.createAccount(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function saveAdConfig() {
  if (!adDialogAccount.value) return

  savingAds.value = true
  try {
    const metadata = {
      ...(adDialogAccount.value.metadata || {}),
      ad_slots: {
        header: { ...adForm.value.header },
        footer: { ...adForm.value.footer }
      }
    }

    await accountStore.updateAccount(adDialogAccount.value.account_id, {
      ad_header_html: buildAdHtml(adForm.value.header),
      ad_footer_html: buildAdHtml(adForm.value.footer),
      metadata
    })

    ElMessage.success('广告位已更新')
    adDialogVisible.value = false
    await loadData()
  } catch (error) {
    ElMessage.error(error.message || '保存广告位失败')
  } finally {
    savingAds.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除账户 "${row.name}" 吗？此操作不可恢复。`,
      '确认删除',
      { type: 'warning' }
    )
    await accountStore.deleteAccount(row.account_id)
    await loadData()
    const remaining = accountStore.accounts
    if (!remaining.length) {
      appStore.setSelectedAccount('')
    } else if (appStore.selectedAccountId === row.account_id) {
      appStore.setSelectedAccount(remaining[0].account_id)
    }
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

function switchAccount(accountId) {
  appStore.setSelectedAccount(accountId)
  ElMessage.success(`已切换到账户：${accountId}`)
}

onMounted(() => {
  loadData()
})

watch(
  () => form.value.name,
  (name) => {
    if (isEdit.value) return
    form.value.account_id = name ? generateAccountId(name) : ''
  }
)
</script>

<style scoped>
.accounts-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.accounts-toolbar-main {
  min-width: 0;
}

.accounts-toolbar-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.accounts-toolbar-title {
  font-size: 18px;
  line-height: 1.3;
  font-weight: 600;
  color: #0f172a;
}

.accounts-toolbar-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
}

.accounts-toolbar-subtitle {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.accounts-toolbar-current {
  color: #334155;
  font-weight: 500;
}

.accounts-create-button {
  min-width: 116px;
}

.text-gray-400 {
  color: #94a3b8;
}

.ad-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tag-list {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.ad-dialog-header {
  margin-bottom: 12px;
}

.ad-dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.account-guide {
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fbff;
}

.account-guide-title {
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1e3a8a;
}

.account-guide-text {
  font-size: 13px;
  line-height: 1.7;
  color: #475569;
}

.form-tip {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.ad-dialog-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.ad-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: 20px;
}

.ad-form-panel,
.ad-preview-panel {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}

.ad-preview-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 12px;
}

.ad-preview-card {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  min-height: 180px;
}

.image-field {
  display: flex;
  gap: 12px;
}

.image-field .el-input {
  flex: 1;
}

@media (max-width: 768px) {
  .accounts-create-button {
    width: 100%;
  }
}
</style>
