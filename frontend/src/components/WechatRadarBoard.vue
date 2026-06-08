<template>
  <div class="wechat-radar-board">
    <el-card shadow="never" class="radar-summary-card">
      <div class="radar-summary-header">
        <div>
          <div class="radar-eyebrow">公众号雷达</div>
          <h3>扫码登录、关注公众号、拉取文章并同步到素材库</h3>
          <p>这条链路独立于 `AppID / Secret` 发布配置，适合登录公众号后台后采集关注号文章。</p>
        </div>
        <div class="radar-actions">
          <el-button @click="bootstrap" :loading="busy">
            <el-icon><Refresh /></el-icon>刷新状态
          </el-button>
          <el-button type="primary" @click="openLoginFlow" :loading="busy" :disabled="!accountId">
            扫码登录
          </el-button>
        </div>
      </div>

      <div class="radar-stat-grid">
        <div class="radar-stat-item">
          <span>当前账户</span>
          <strong>{{ accountName || accountId || '-' }}</strong>
        </div>
        <div class="radar-stat-item" :class="isLoggedIn ? 'ok' : 'warn'">
          <span>登录状态</span>
          <strong>{{ isLoggedIn ? '登录态有效' : '未登录' }}</strong>
        </div>
        <div class="radar-stat-item">
          <span>已关注公众号</span>
          <strong>{{ mpCount }}</strong>
        </div>
        <div class="radar-stat-item">
          <span>文章缓存数</span>
          <strong>{{ articleCount }}</strong>
        </div>
      </div>

      <div v-if="lastLoginAt" class="radar-tip">最近一次登录确认：{{ lastLoginAt }}，表示当前账户的公众号后台登录态可用于检索、关注和拉取。</div>
      <div v-if="message" class="radar-message">{{ message }}</div>
      <div v-if="errorMessage" class="radar-error">{{ errorMessage }}</div>
      <div v-if="runtimeBlockers.length" class="runtime-diagnostics">
        <div class="runtime-diagnostics-title">当前运行环境阻塞了扫码链路</div>
        <div
          v-for="blocker in runtimeBlockers"
          :key="blocker.key"
          class="runtime-diagnostics-item"
        >
          <strong>{{ blocker.label }}</strong>
          <span>{{ blocker.message }}</span>
        </div>
        <div v-if="missingModules.length" class="runtime-diagnostics-hint">
          缺少依赖：{{ missingModules.join(', ') }}
        </div>
        <div v-if="installHint" class="runtime-diagnostics-hint mono">建议安装：{{ installHint }}</div>
        <div v-if="browserInstallHint" class="runtime-diagnostics-hint mono">浏览器运行时：{{ browserInstallHint }}</div>
      </div>
    </el-card>

    <div class="radar-main-grid">
      <el-card shadow="never">
        <template #header>
          <div class="panel-header">公众号检索与关注</div>
        </template>
        <div class="panel-body">
          <div class="toolbar-row">
            <el-input
              v-model="keyword"
              placeholder="输入公众号关键词，例如 机器之心"
              clearable
              @keyup.enter="searchMp"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="searchMp" :loading="busy" :disabled="!keyword.trim() || !accountId">
              检索
            </el-button>
          </div>

          <div v-if="searchRows.length" class="list-stack">
            <div v-for="(row, index) in searchRows" :key="`${row.fakeid || row.nickname}-${index}`" class="search-card">
              <div class="search-card-main">
                <div class="search-card-title">{{ row.nickname || row.alias || '未知公众号' }}</div>
                <div class="search-card-subtitle">{{ row.signature || row.fakeid || '未返回签名' }}</div>
              </div>
              <el-button size="small" @click="addMpByPick(index + 1)" :loading="busy">
                关注 #{{ index + 1 }}
              </el-button>
            </div>
          </div>
          <el-empty v-else description="先检索公众号，再加入关注列表" />
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="panel-header">已关注公众号</div>
        </template>
        <div class="panel-body">
          <div class="toolbar-row">
            <el-select v-model="selectedMpId" placeholder="选择已关注公众号" style="width: 100%">
              <el-option
                v-for="item in mpList"
                :key="item.id"
                :label="item.name || item.id"
                :value="String(item.id || '')"
              />
            </el-select>
            <el-button @click="reloadMpList" :loading="busy" :disabled="!accountId">
              刷新
            </el-button>
          </div>

          <div v-if="mpList.length" class="list-stack compact">
            <div v-for="item in mpList" :key="item.id" class="info-card">
              <div class="info-card-title">{{ item.name || item.id }}</div>
              <div class="info-card-subtitle">ID: {{ item.id || '-' }}</div>
            </div>
          </div>
          <el-empty v-else description="当前账户还没有关注公众号" />
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="panel-header">拉取与同步</div>
        </template>
        <div class="panel-body">
          <div class="settings-grid">
            <div class="setting-item">
              <span>拉取页数</span>
              <el-input-number v-model="pages" :min="1" :max="10" />
            </div>
            <div class="setting-item">
              <span>正文抓取上限</span>
              <el-input-number v-model="contentLimit" :min="1" :max="200" />
            </div>
            <div class="setting-item">
              <span>素材同步上限</span>
              <el-input-number v-model="syncLimit" :min="1" :max="200" />
            </div>
          </div>

          <div class="checkbox-row">
            <el-checkbox v-model="withContent">拉取文章时同时抓取正文缓存</el-checkbox>
          </div>

          <div class="stack-actions">
            <el-button @click="pullArticlesAction" :loading="busy" :disabled="!selectedMpId || !accountId">
              拉取文章列表
            </el-button>
            <el-button type="primary" @click="syncInspirationAction" :loading="busy" :disabled="!accountId">
              同步到素材库
            </el-button>
            <el-button type="success" @click="fullFlowAction" :loading="busy" :disabled="!accountId">
              一键全流程
            </el-button>
          </div>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="panel-header">文章缓存预览</div>
        </template>
        <div class="panel-body">
          <div v-if="articleRows.length" class="list-stack">
            <div v-for="(item, index) in articleRows" :key="item.id || item.url || index" class="info-card article-card">
              <div class="article-card-main">
                <div class="info-card-title">{{ item.title || '未命名文章' }}</div>
                <div class="info-card-subtitle">{{ item.publish_time_str || item.publish_time || '无时间信息' }}</div>
              </div>
              <div class="article-card-actions">
                <el-button
                  v-if="item.has_content"
                  link
                  type="primary"
                  class="article-link-button"
                  @click="openArticlePreview(item)"
                >
                  查看缓存
                </el-button>
                <el-button
                  v-if="validHttpUrl(item.url)"
                  link
                  type="primary"
                  class="article-link-button"
                  @click="openOriginal(item.url)"
                >
                  打开原文
                </el-button>
              </div>
            </div>
          </div>
          <el-empty v-else description="选择公众号后可以查看拉取到的文章缓存" />
        </div>
      </el-card>
    </div>

    <el-dialog v-model="loginDialogVisible" title="扫码登录公众号后台" width="560px" destroy-on-close>
      <div class="login-dialog-body">
        <div class="qr-preview-box">
          <div v-if="runtimeBlockers.length" class="qr-blocked-box">
            <div class="qr-blocked-title">二维码无法生成</div>
            <div class="qr-blocked-body">
              当前登录态 runtime 未就绪，缺少依赖：{{ missingModules.join(', ') || 'unknown' }}
            </div>
            <div v-if="installHint" class="qr-blocked-hint mono">{{ installHint }}</div>
            <div v-if="browserInstallHint" class="qr-blocked-hint mono">{{ browserInstallHint }}</div>
          </div>
          <img
            v-else-if="qrImageUrl"
            :src="qrImageUrl"
            alt="微信扫码二维码"
            class="qr-preview-image"
            @load="qrImageReady = true"
            @error="handleQrError"
          />
          <el-empty v-else description="二维码准备中" />
        </div>
        <div class="login-guide">
          <div class="guide-row">
            <span>步骤 1</span>
            <strong>点击“扫码登录”后等待二维码生成</strong>
          </div>
          <div class="guide-row">
            <span>步骤 2</span>
            <strong>使用微信扫码，并在手机端确认登录</strong>
          </div>
          <div class="guide-row">
            <span>步骤 3</span>
            <strong>点击“检查状态”确认当前账户已登录</strong>
          </div>
          <div class="guide-row">
            <span>后台进程</span>
            <strong>{{ loginJobId || '-' }}</strong>
          </div>
          <div class="guide-row">
            <span>轮询状态</span>
            <strong>{{ loginPolling ? '进行中' : '未轮询' }}</strong>
          </div>
        </div>
        <div v-if="runtimeBlockers.length" class="radar-error compact">
          {{ runtimeSummary }}
        </div>
        <div v-else-if="qrImageError" class="radar-error compact">{{ qrImageError }}</div>
        <div v-else-if="qrImageUrl && !qrImageReady" class="radar-tip compact">二维码文件已生成，等待浏览器完成加载。</div>
      </div>
      <template #footer>
        <el-button @click="refreshQrImage" :loading="busy">刷新二维码</el-button>
        <el-button @click="refreshLoginStatus" :loading="busy">检查状态</el-button>
        <el-button type="primary" @click="closeLoginDialog">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewDialogVisible" title="正文缓存预览" width="860px" destroy-on-close>
      <div class="article-preview-dialog">
        <div class="article-preview-header">
          <h3>{{ previewArticle?.title || '未命名文章' }}</h3>
          <div class="article-preview-meta">
            <span>{{ previewArticle?.publish_time_str || previewArticle?.publish_time || '无时间信息' }}</span>
            <span v-if="previewArticle?.author">{{ previewArticle.author }}</span>
          </div>
        </div>
        <div v-if="previewBusy" class="article-preview-loading">正在加载正文缓存...</div>
        <el-empty v-else-if="!previewArticle?.content_html" description="当前文章还没有正文缓存，请勾选“拉取文章时同时抓取正文缓存”后重新拉取。" />
        <div v-else class="article-preview-content" v-html="previewArticle.content_html"></div>
      </div>
      <template #footer>
        <el-button v-if="validHttpUrl(previewArticle?.url)" @click="openOriginal(previewArticle.url)">打开原文</el-button>
        <el-button type="primary" @click="previewDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import api from '../api'

const props = defineProps({
  accountId: { type: String, default: '' },
  accountName: { type: String, default: '' }
})

const emit = defineEmits(['refresh'])

const busy = ref(false)
const message = ref('')
const errorMessage = ref('')
const statusInfo = ref(null)
const mpList = ref([])
const searchRows = ref([])
const articleRows = ref([])
const keyword = ref('')
const selectedMpId = ref('')
const pages = ref(1)
const withContent = ref(false)
const syncLimit = ref(20)
const contentLimit = ref(10)
const loginDialogVisible = ref(false)
const loginJobId = ref('')
const loginPolling = ref(false)
const qrImageUrl = ref('')
const qrImageReady = ref(false)
const qrImageError = ref('')
const lastLoginAt = ref('')
const persistedLogin = ref(false)
const previewDialogVisible = ref(false)
const previewBusy = ref(false)
const previewArticle = ref(null)

let loginPollTimer = null

const accountId = computed(() => props.accountId || '')
const loginMemoryKey = computed(() => `autoplatform:wechat-login:${accountId.value || 'default'}`)

const isLoggedIn = computed(() => {
  return Boolean(statusInfo.value?.runtime?.login_status) || persistedLogin.value
})

const mpCount = computed(() => Number(statusInfo.value?.state?.mp_count || mpList.value.length || 0))
const articleCount = computed(() => Number(statusInfo.value?.state?.article_count || articleRows.value.length || 0))
const diagnostics = computed(() => statusInfo.value?.diagnostics || {})
const runtimeBlockers = computed(() => diagnostics.value.blockers || [])
const missingModules = computed(() => diagnostics.value.missing_modules || [])
const runtimeSummary = computed(() => diagnostics.value.summary || '')
const installHint = computed(() => statusInfo.value?.install_hint || diagnostics.value.install_hint || '')
const browserInstallHint = computed(() => statusInfo.value?.browser_install_hint || diagnostics.value.browser_install_hint || '')

function setMessage(text = '') {
  message.value = text
  errorMessage.value = ''
}

function setError(error) {
  errorMessage.value = error?.message || String(error || '操作失败')
}

function readLoginMemory() {
  try {
    persistedLogin.value = window.localStorage.getItem(loginMemoryKey.value) === '1'
    lastLoginAt.value = window.localStorage.getItem(`${loginMemoryKey.value}:at`) || ''
  } catch {
    persistedLogin.value = false
    lastLoginAt.value = ''
  }
}

function markLoginConfirmed() {
  const now = new Date().toLocaleString('zh-CN')
  persistedLogin.value = true
  lastLoginAt.value = now
  try {
    window.localStorage.setItem(loginMemoryKey.value, '1')
    window.localStorage.setItem(`${loginMemoryKey.value}:at`, now)
  } catch {
    // ignore storage failure
  }
}

function stopLoginPolling() {
  loginPolling.value = false
  if (loginPollTimer) {
    clearInterval(loginPollTimer)
    loginPollTimer = null
  }
}

function updateQrPreviewFromStatus() {
  if (runtimeBlockers.value.length) {
    qrImageUrl.value = ''
    qrImageReady.value = false
    qrImageError.value = runtimeSummary.value || '运行环境未就绪，二维码无法生成。'
    return false
  }
  const state = statusInfo.value?.state || {}
  const hasQr = Boolean(state.qr_image_exists || state.qr_image_path || statusInfo.value?.qr_image_path)
  if (!hasQr || !accountId.value) {
    qrImageUrl.value = ''
    return false
  }
  qrImageReady.value = false
  qrImageError.value = ''
  qrImageUrl.value = `${api.wechatIngest.qrImageUrl(accountId.value)}&t=${Date.now()}`
  return true
}

async function withBusy(fn) {
  busy.value = true
  try {
    await fn()
  } catch (error) {
    setError(error)
    ElMessage.error(error?.message || '操作失败')
  } finally {
    busy.value = false
  }
}

async function reloadStatus() {
  if (!accountId.value) return
  statusInfo.value = await api.wechatIngest.status(accountId.value)
  if (statusInfo.value?.runtime?.login_status) {
    markLoginConfirmed()
  }
  updateQrPreviewFromStatus()
}

function applyRuntimeFeedback() {
  if (!runtimeBlockers.value.length) return false
  stopLoginPolling()
  setError(runtimeSummary.value || '运行环境未就绪，二维码无法生成')
  qrImageError.value = runtimeSummary.value || '运行环境未就绪，二维码无法生成'
  return true
}

async function reloadMpList() {
  if (!accountId.value) return
  const data = await api.wechatIngest.listMps(accountId.value)
  mpList.value = data.items || []
  if (!selectedMpId.value && mpList.value.length) {
    selectedMpId.value = String(mpList.value[0].id || '')
  }
}

async function reloadArticles() {
  if (!accountId.value || !selectedMpId.value) {
    articleRows.value = []
    return
  }
  const data = await api.wechatIngest.listArticles({
    account_id: accountId.value,
    mp_id: selectedMpId.value,
    limit: 50
  })
  articleRows.value = data.items || []
}

async function bootstrap() {
  if (!accountId.value) return
  await withBusy(async () => {
    readLoginMemory()
    const settled = await Promise.allSettled([reloadStatus(), reloadMpList()])
    if (settled.every(item => item.status === 'rejected')) {
      throw settled.find(item => item.status === 'rejected')?.reason || new Error('刷新失败')
    }
    await reloadArticles()
    if (!applyRuntimeFeedback()) {
      setMessage('登录态、关注列表和文章缓存已刷新。')
    }
  })
}

function startLoginPolling() {
  stopLoginPolling()
  loginPolling.value = true
  loginPollTimer = window.setInterval(async () => {
    try {
      await reloadStatus()
      if (applyRuntimeFeedback()) {
        return
      }
      if (statusInfo.value?.runtime?.login_status) {
        markLoginConfirmed()
        stopLoginPolling()
        setMessage('扫码登录成功，当前账户已确认登录。')
      }
    } catch {
      // keep polling
    }
  }, 3000)
}

async function openLoginFlow() {
  if (!accountId.value) return
  loginDialogVisible.value = true
  await withBusy(async () => {
    const data = await api.wechatIngest.login({
      account_id: accountId.value,
      wait: false,
      qr_display: 'none',
      timeout: 60,
      token_wait_timeout: 20,
      thread_join_timeout: 8
    })
    statusInfo.value = data
    loginJobId.value = String(data.login_daemon_pid || data.login_return_code || '-')
    updateQrPreviewFromStatus()
    if (runtimeBlockers.value.length || data.login_mode === 'blocked') {
      applyRuntimeFeedback()
      return
    }
    startLoginPolling()
    setMessage(data.error || '已触发二维码登录，请扫码并确认。')
  })
}

async function refreshLoginStatus() {
  await withBusy(async () => {
    await reloadStatus()
    if (applyRuntimeFeedback()) {
      return
    }
    if (statusInfo.value?.runtime?.login_status) {
      markLoginConfirmed()
      stopLoginPolling()
      setMessage('登录状态已确认。')
    } else {
      setMessage('当前还未检测到登录成功，请继续扫码后再检查。')
    }
  })
}

async function searchMp() {
  if (!accountId.value || !keyword.value.trim()) return
  await withBusy(async () => {
    const data = await api.wechatIngest.searchMp({
      account_id: accountId.value,
      keyword: keyword.value.trim(),
      limit: 8,
      offset: 0
    })
    searchRows.value = data.items || []
    setMessage(`检索完成，返回 ${searchRows.value.length} 个候选公众号。`)
  })
}

async function addMpByPick(pick) {
  if (!accountId.value || !keyword.value.trim()) return
  await withBusy(async () => {
    await api.wechatIngest.addMp({
      account_id: accountId.value,
      keyword: keyword.value.trim(),
      pick,
      limit: 8,
      offset: 0
    })
    await reloadMpList()
    await reloadArticles()
    emit('refresh')
    setMessage(`已加入候选 #${pick}。`)
  })
}

async function pullArticlesAction() {
  if (!accountId.value || !selectedMpId.value) return
  await withBusy(async () => {
    const data = await api.wechatIngest.pullArticles({
      account_id: accountId.value,
      mp_id: selectedMpId.value,
      pages: Number(pages.value || 1),
      mode: 'api',
      with_content: Boolean(withContent.value)
    })
    articleRows.value = data.items || []
    setMessage(`文章拉取完成，当前缓存 ${Number(data.count || 0)} 条。`)
  })
}

async function syncInspirationAction() {
  if (!accountId.value) return
  await withBusy(async () => {
    const data = await api.wechatIngest.syncInspirations({
      account_id: accountId.value,
      mp_id: selectedMpId.value,
      limit: Number(syncLimit.value || 20)
    })
    emit('refresh')
    setMessage(`素材同步完成，新增 ${Number(data.inserted || 0)} 条。`)
  })
}

async function fullFlowAction() {
  if (!accountId.value) return
  await withBusy(async () => {
    const data = await api.wechatIngest.fullFlow({
      account_id: accountId.value,
      mp_id: selectedMpId.value,
      keyword: keyword.value.trim(),
      pick: 1,
      pages: Number(pages.value || 1),
      mode: 'api',
      with_content: Boolean(withContent.value),
      content_limit: Number(contentLimit.value || 10),
      sync_limit: Number(syncLimit.value || 20)
    })
    await reloadMpList()
    await reloadArticles()
    emit('refresh')
    setMessage(`全流程完成：缓存 ${Number(data.pull?.count || 0)} 条，新增 ${Number(data.sync?.inserted || 0)} 条。`)
  })
}

function validHttpUrl(url) {
  return /^https?:\/\//.test(String(url || '').trim())
}

function openOriginal(url) {
  const targetUrl = String(url || '').trim()
  if (!validHttpUrl(targetUrl)) {
    ElMessage.error('原文链接无效')
    return
  }
  window.location.assign(targetUrl)
}

async function openArticlePreview(item) {
  if (!accountId.value || !selectedMpId.value || !item?.id) return
  previewDialogVisible.value = true
  previewBusy.value = true
  previewArticle.value = {
    ...item,
    content_html: '',
    content_text: ''
  }
  try {
    const data = await api.wechatIngest.articlePreview({
      account_id: accountId.value,
      mp_id: selectedMpId.value,
      article_id: item.id
    })
    previewArticle.value = data.item || previewArticle.value
  } catch (error) {
    ElMessage.error(error?.message || '正文缓存加载失败')
  } finally {
    previewBusy.value = false
  }
}

function handleQrError() {
  qrImageReady.value = false
  qrImageError.value = '二维码加载失败，请刷新二维码后重试。'
}

async function refreshQrImage() {
  await withBusy(async () => {
    await reloadStatus()
    if (applyRuntimeFeedback()) {
      return
    }
    const hasQr = updateQrPreviewFromStatus()
    if (!hasQr) {
      qrImageError.value = '二维码尚未生成，请稍后重试。'
    }
  })
}

function closeLoginDialog() {
  loginDialogVisible.value = false
  stopLoginPolling()
}

onMounted(() => {
  readLoginMemory()
  bootstrap()
})

onBeforeUnmount(() => {
  stopLoginPolling()
})

watch(accountId, () => {
  searchRows.value = []
  articleRows.value = []
  mpList.value = []
  selectedMpId.value = ''
  qrImageUrl.value = ''
  qrImageReady.value = false
  qrImageError.value = ''
  stopLoginPolling()
  readLoginMemory()
  bootstrap()
})

watch(selectedMpId, () => {
  reloadArticles().catch(() => {})
})
</script>

<style scoped>
.wechat-radar-board {
  display: grid;
  gap: 16px;
}

.radar-summary-card {
  border-radius: 12px;
}

.radar-summary-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.radar-eyebrow {
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
}

.radar-summary-header h3 {
  margin: 8px 0 6px;
  font-size: 22px;
  line-height: 1.4;
  color: #0f172a;
}

.radar-summary-header p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #64748b;
  max-width: 620px;
}

.radar-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.radar-stat-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.radar-stat-item {
  padding: 14px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.radar-stat-item.ok {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.radar-stat-item.warn {
  background: #fff7ed;
  border-color: #fed7aa;
}

.radar-stat-item span {
  display: block;
  font-size: 12px;
  color: #64748b;
}

.radar-stat-item strong {
  display: block;
  margin-top: 6px;
  font-size: 18px;
  color: #0f172a;
  line-height: 1.4;
}

.radar-tip,
.radar-message,
.radar-error {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.6;
}

.radar-tip,
.radar-message {
  background: #eff6ff;
  color: #1d4ed8;
}

.radar-error {
  background: #fef2f2;
  color: #b91c1c;
}

.radar-error.compact,
.radar-tip.compact {
  margin-top: 0;
}

.runtime-diagnostics {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #fecaca;
  border-radius: 12px;
  background: #fff7f7;
  display: grid;
  gap: 10px;
}

.runtime-diagnostics-title {
  font-size: 13px;
  font-weight: 600;
  color: #991b1b;
}

.runtime-diagnostics-item {
  display: grid;
  gap: 4px;
  font-size: 13px;
}

.runtime-diagnostics-item strong {
  color: #7f1d1d;
}

.runtime-diagnostics-item span,
.runtime-diagnostics-hint {
  color: #b91c1c;
  line-height: 1.6;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace;
}

.radar-main-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.panel-header {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.panel-body {
  display: grid;
  gap: 14px;
}

.toolbar-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.setting-item {
  display: grid;
  gap: 8px;
  font-size: 13px;
  color: #475569;
}

.checkbox-row {
  display: flex;
  align-items: center;
}

.stack-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.list-stack {
  display: grid;
  gap: 10px;
  max-height: 360px;
  overflow: auto;
  padding-right: 2px;
}

.list-stack.compact {
  max-height: 300px;
}

.search-card,
.info-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
}

.search-card-main,
.article-card-main {
  min-width: 0;
}

.search-card-title,
.info-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.5;
}

.search-card-subtitle,
.info-card-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
  word-break: break-word;
}

.article-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.article-link-button {
  white-space: nowrap;
}

.article-preview-dialog {
  display: grid;
  gap: 16px;
}

.article-preview-header h3 {
  margin: 0 0 8px;
  font-size: 28px;
  line-height: 1.35;
}

.article-preview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #64748b;
  font-size: 13px;
}

.article-preview-loading {
  padding: 48px 0;
  text-align: center;
  color: #64748b;
}

.article-preview-content {
  max-height: 70vh;
  overflow: auto;
  padding-right: 8px;
  color: #1e293b;
  line-height: 1.8;
}

.article-preview-content :deep(img) {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 16px auto;
}

.article-preview-content :deep(p) {
  margin: 0 0 14px;
}

.article-preview-content :deep(blockquote) {
  margin: 18px 0;
  padding: 12px 16px;
  border-left: 4px solid #93c5fd;
  background: #f8fbff;
}

.login-dialog-body {
  display: grid;
  gap: 16px;
}

.qr-preview-box {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  background: #f8fafc;
}

.qr-blocked-box {
  width: 100%;
  padding: 20px 16px;
  border-radius: 12px;
  background: #fff7f7;
  border: 1px solid #fecaca;
  display: grid;
  gap: 8px;
  text-align: left;
}

.qr-blocked-title {
  font-size: 15px;
  font-weight: 600;
  color: #991b1b;
}

.qr-blocked-body,
.qr-blocked-hint {
  font-size: 13px;
  line-height: 1.7;
  color: #b91c1c;
  word-break: break-word;
}

.qr-preview-image {
  width: 260px;
  max-width: 100%;
  height: auto;
  border-radius: 12px;
  background: #fff;
}

.login-guide {
  display: grid;
  gap: 10px;
}

.guide-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fafc;
}

.guide-row span {
  font-size: 12px;
  color: #64748b;
}

.guide-row strong {
  font-size: 13px;
  color: #0f172a;
  text-align: right;
}

@media (max-width: 1100px) {
  .radar-main-grid,
  .radar-stat-grid,
  .settings-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .radar-summary-header,
  .toolbar-row {
    flex-direction: column;
    align-items: stretch;
  }

  .search-card,
  .info-card,
  .guide-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
