<template>
  <div class="wechat-radar-board">
    <!-- 顶部概览 -->
    <div class="radar-header">
      <div class="radar-header-main">
        <div class="radar-title-row">
          <h2>公众号雷达</h2>
          <el-tag v-if="isLoggedIn" type="success" effect="light">已登录</el-tag>
          <el-tag v-else type="info" effect="light">未登录</el-tag>
        </div>
        <p class="radar-desc">登录公众号后台，检索并关注目标公众号，拉取文章缓存后同步到素材库。</p>
      </div>
      <div class="radar-header-actions">
        <el-button @click="bootstrap" :loading="busy">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
        <el-button type="primary" @click="openLoginFlow" :loading="busy" :disabled="!accountId">
          扫码登录
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-bar">
      <div class="stat-item">
        <el-icon class="stat-icon" :size="20"><UserFilled /></el-icon>
        <div class="stat-body">
          <span class="stat-label">当前账户</span>
          <span class="stat-value">{{ accountName || accountId || '-' }}</span>
        </div>
      </div>
      <div class="stat-item" :class="isLoggedIn ? 'ok' : 'warn'">
        <el-icon class="stat-icon" :size="20"><CircleCheck v-if="isLoggedIn" /><CircleClose v-else /></el-icon>
        <div class="stat-body">
          <span class="stat-label">登录状态</span>
          <span class="stat-value">{{ isLoggedIn ? '有效' : '未登录' }}</span>
        </div>
      </div>
      <div class="stat-item">
        <el-icon class="stat-icon" :size="20"><Collection /></el-icon>
        <div class="stat-body">
          <span class="stat-label">已关注公众号</span>
          <span class="stat-value">{{ mpCount }}</span>
        </div>
      </div>
      <div class="stat-item">
        <el-icon class="stat-icon" :size="20"><Document /></el-icon>
        <div class="stat-body">
          <span class="stat-label">文章缓存</span>
          <span class="stat-value">{{ articleCount }}</span>
        </div>
      </div>
    </div>

    <!-- 消息提示 -->
    <div v-if="message" class="banner-message">{{ message }}</div>
    <div v-if="errorMessage" class="banner-error">{{ errorMessage }}</div>
    <div v-if="runtimeBlockers.length" class="banner-error">
      <strong>运行环境异常：</strong>{{ runtimeSummary }}
      <div v-if="missingModules.length" class="mt-4">缺少依赖：{{ missingModules.join(', ') }}</div>
    </div>

    <!-- 主体内容区 -->
    <div class="radar-body">
      <!-- 左侧栏 -->
      <div class="radar-sidebar">
        <!-- 登录面板 -->
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="panel-title">
              <el-icon><Lock /></el-icon>
              <span>登录状态</span>
            </div>
          </template>
          <div class="login-panel-body">
            <div class="login-indicator" :class="isLoggedIn ? 'online' : 'offline'">
              <span class="login-dot" />
              <span class="login-text">{{ isLoggedIn ? '登录态有效' : '尚未登录' }}</span>
            </div>
            <div v-if="lastLoginAt" class="login-meta">最近确认：{{ lastLoginAt }}</div>
            <div v-if="!isLoggedIn" class="login-hint">需先扫码登录公众号后台，才能检索和拉取文章。</div>
            <el-button
              v-if="!isLoggedIn"
              type="primary"
              style="width: 100%; margin-top: 12px"
              @click="openLoginFlow"
              :loading="busy"
              :disabled="!accountId"
            >
              扫码登录
            </el-button>
            <el-button
              v-else
              style="width: 100%; margin-top: 12px"
              @click="openLoginFlow"
              :loading="busy"
            >
              重新登录
            </el-button>
          </div>
        </el-card>

        <!-- 公众号检索 -->
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="panel-title">
              <el-icon><Search /></el-icon>
              <span>检索公众号</span>
            </div>
          </template>
          <div class="search-panel-body">
            <el-input
              v-model="keyword"
              placeholder="输入公众号关键词，如：机器之心"
              clearable
              @keyup.enter="searchMp"
            >
              <template #append>
                <el-button @click="searchMp" :loading="busy" :disabled="!keyword.trim() || !accountId">
                  <el-icon><Search /></el-icon>
                </el-button>
              </template>
            </el-input>

            <div v-if="searchRows.length" class="search-results">
              <div
                v-for="(row, index) in searchRows"
                :key="`${row.fakeid || row.nickname}-${index}`"
                class="search-result-item"
              >
                <div class="search-result-info">
                  <div class="search-result-name">{{ row.nickname || row.alias || '未知公众号' }}</div>
                  <div class="search-result-desc">{{ row.signature || '未返回签名' }}</div>
                </div>
                <el-button size="small" type="primary" plain @click="addMpByPick(index + 1)" :loading="busy">
                  关注
                </el-button>
              </div>
            </div>
            <el-empty v-else description="输入关键词检索公众号" :image-size="60" />
          </div>
        </el-card>

        <!-- 已关注公众号 -->
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="panel-title">
              <el-icon><Collection /></el-icon>
              <span>已关注公众号</span>
              <el-tag size="small" type="info">{{ mpList.length }}</el-tag>
            </div>
          </template>
          <div class="mp-panel-body">
            <el-select
              v-model="selectedMpId"
              placeholder="选择公众号"
              style="width: 100%"
              v-if="mpList.length"
            >
              <el-option
                v-for="item in mpList"
                :key="item.id"
                :label="item.name || item.id"
                :value="String(item.id || '')"
              />
            </el-select>
            <div v-if="mpList.length" class="mp-list">
              <div
                v-for="item in mpList"
                :key="item.id"
                class="mp-list-item"
                :class="{ active: selectedMpId === String(item.id || '') }"
                @click="selectedMpId = String(item.id || '')"
              >
                <el-icon><ChatDotRound /></el-icon>
                <span class="mp-name">{{ item.name || item.id }}</span>
              </div>
            </div>
            <el-empty v-else description="还没有关注公众号" :image-size="60" />
          </div>
        </el-card>
      </div>

      <!-- 右侧主区域 -->
      <div class="radar-main">
        <!-- 操作工具栏 -->
        <el-card shadow="never" class="toolbar-card">
          <div class="toolbar-content">
            <div class="toolbar-settings">
              <div class="setting-field">
                <label>拉取页数</label>
                <el-input-number v-model="pages" :min="1" :max="10" size="small" />
              </div>
              <div class="setting-field">
                <label>正文上限</label>
                <el-input-number v-model="contentLimit" :min="1" :max="200" size="small" />
              </div>
              <div class="setting-field">
                <label>同步上限</label>
                <el-input-number v-model="syncLimit" :min="1" :max="200" size="small" />
              </div>
              <el-checkbox v-model="withContent">同时抓取正文</el-checkbox>
            </div>
            <div class="toolbar-actions">
              <el-button @click="pullArticlesAction" :loading="busy" :disabled="!selectedMpId || !accountId">
                拉取文章
              </el-button>
              <el-button type="primary" @click="syncInspirationAction" :loading="busy" :disabled="!accountId">
                同步素材库
              </el-button>
              <el-button type="success" @click="fullFlowAction" :loading="busy" :disabled="!accountId">
                一键全流程
              </el-button>
            </div>
          </div>
        </el-card>

        <!-- 文章列表 -->
        <el-card shadow="never" class="articles-card">
          <template #header>
            <div class="panel-title">
              <el-icon><Document /></el-icon>
              <span>文章缓存</span>
              <el-tag size="small" type="info" v-if="articleRows.length">{{ articleRows.length }} 条</el-tag>
            </div>
          </template>
          <div class="articles-body">
            <div v-if="articleRows.length" class="article-list">
              <div
                v-for="(item, index) in articleRows"
                :key="item.id || item.url || index"
                class="article-item"
              >
                <div class="article-main">
                  <div class="article-title">{{ item.title || '未命名文章' }}</div>
                  <div class="article-meta">
                    <el-icon v-if="item.has_content" class="meta-icon" title="已有正文缓存"><DocumentChecked /></el-icon>
                    <el-icon v-else class="meta-icon muted" title="暂无正文缓存"><Document /></el-icon>
                    <span>{{ item.publish_time_str || item.publish_time || '无时间' }}</span>
                  </div>
                </div>
                <div class="article-actions">
                  <el-button
                    v-if="item.has_content"
                    link
                    type="primary"
                    size="small"
                    @click="openArticlePreview(item)"
                  >
                    查看缓存
                  </el-button>
                  <el-button
                    v-if="validHttpUrl(item.url)"
                    link
                    type="info"
                    size="small"
                    @click="openOriginal(item.url)"
                  >
                    原文
                  </el-button>
                </div>
              </div>
            </div>
            <el-empty v-else :description="selectedMpId ? '当前公众号暂无文章缓存' : '选择公众号后查看文章'" :image-size="80" />
          </div>
        </el-card>
      </div>
    </div>

    <!-- 登录弹窗 -->
    <el-dialog v-model="loginDialogVisible" title="扫码登录公众号后台" width="520px" destroy-on-close>
      <div class="login-dialog-body">
        <div class="qr-box">
          <div v-if="runtimeBlockers.length" class="qr-error">
            <el-icon :size="32" color="#f56c6c"><Warning /></el-icon>
            <div class="qr-error-title">二维码无法生成</div>
            <div class="qr-error-text">
              缺少依赖：{{ missingModules.join(', ') || 'unknown' }}
            </div>
          </div>
          <img
            v-else-if="qrImageUrl"
            :src="qrImageUrl"
            alt="微信扫码二维码"
            class="qr-image"
            @load="qrImageReady = true"
            @error="handleQrError"
          />
          <el-empty v-else description="二维码准备中" :image-size="80" />
        </div>
        <div class="login-steps">
          <div class="step">
            <span class="step-num">1</span>
            <span>等待二维码生成</span>
          </div>
          <div class="step">
            <span class="step-num">2</span>
            <span>微信扫码并确认登录</span>
          </div>
          <div class="step">
            <span class="step-num">3</span>
            <span>点击"检查状态"确认</span>
          </div>
        </div>
        <div v-if="qrImageError" class="dialog-error">{{ qrImageError }}</div>
        <div v-else-if="qrImageUrl && !qrImageReady" class="dialog-tip">二维码加载中...</div>
      </div>
      <template #footer>
        <el-button @click="refreshQrImage" :loading="busy">刷新二维码</el-button>
        <el-button @click="refreshLoginStatus" :loading="busy">检查状态</el-button>
        <el-button type="primary" @click="closeLoginDialog">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 文章预览弹窗 -->
    <el-dialog v-model="previewDialogVisible" title="正文缓存预览" width="860px" destroy-on-close>
      <div class="preview-body">
        <div class="preview-header">
          <h3>{{ previewArticle?.title || '未命名文章' }}</h3>
          <div class="preview-meta">
            <span>{{ previewArticle?.publish_time_str || previewArticle?.publish_time || '无时间信息' }}</span>
            <span v-if="previewArticle?.author">{{ previewArticle.author }}</span>
          </div>
        </div>
        <div v-if="previewBusy" class="preview-loading">正在加载正文缓存...</div>
        <el-empty v-else-if="!previewArticle?.content_html" description="当前文章还没有正文缓存" :image-size="80" />
        <div v-else class="preview-content" v-html="previewArticle.content_html" />
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
import {
  Refresh, Search, Lock, Collection, Document,
  UserFilled, CircleCheck, CircleClose, ChatDotRound,
  DocumentChecked, Warning
} from '@element-plus/icons-vue'
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
  try {
    const data = await api.wechatIngest.status(accountId.value)
    statusInfo.value = data
    if (data?.runtime?.login_status) {
      markLoginConfirmed()
    }
  } catch {
    statusInfo.value = null
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
  try {
    const data = await api.wechatIngest.listMps(accountId.value)
    mpList.value = data.items || []
    if (!selectedMpId.value && mpList.value.length) {
      selectedMpId.value = String(mpList.value[0].id || '')
    }
  } catch {
    mpList.value = []
  }
}

async function reloadArticles() {
  if (!accountId.value || !selectedMpId.value) {
    articleRows.value = []
    return
  }
  try {
    const data = await api.wechatIngest.listArticles({
      account_id: accountId.value,
      mp_id: selectedMpId.value,
      limit: 50
    })
    articleRows.value = data.items || []
  } catch {
    articleRows.value = []
  }
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
  statusInfo.value = null
  message.value = ''
  errorMessage.value = ''
  stopLoginPolling()
  readLoginMemory()
  bootstrap()
})

watch(selectedMpId, () => {
  reloadArticles().catch(() => {})
})
</script>

<style scoped>
/* ========== 根容器 ========== */
.wechat-radar-board {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px;
}

/* ========== 顶部标题栏 ========== */
.radar-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.radar-header-main {
  flex: 1;
  min-width: 0;
}

.radar-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.radar-title-row h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.3;
}

.radar-desc {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
}

.radar-header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* ========== 统计栏 ========== */
.stat-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  transition: all 0.2s;
}

.stat-item.ok {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.stat-item.ok .stat-icon {
  color: #16a34a;
}

.stat-item.warn {
  background: #fff7ed;
  border-color: #fed7aa;
}

.stat-item.warn .stat-icon {
  color: #ea580c;
}

.stat-icon {
  color: #64748b;
  flex-shrink: 0;
}

.stat-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

/* ========== 消息横幅 ========== */
.banner-message,
.banner-error {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
}

.banner-message {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.banner-error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.mt-4 {
  margin-top: 4px;
}

/* ========== 主体布局 ========== */
.radar-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  align-items: start;
}

/* ========== 左侧边栏 ========== */
.radar-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-card {
  border-radius: 10px;
}

.panel-card :deep(.el-card__header) {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.panel-title .el-tag {
  margin-left: auto;
}

/* 登录面板 */
.login-panel-body {
  padding: 4px 0;
}

.login-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
}

.login-indicator.online {
  background: #f0fdf4;
  color: #15803d;
}

.login-indicator.offline {
  background: #f8fafc;
  color: #64748b;
}

.login-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.login-indicator.online .login-dot {
  background: #22c55e;
  box-shadow: 0 0 0 3px #bbf7d0;
}

.login-indicator.offline .login-dot {
  background: #94a3b8;
}

.login-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
  padding-left: 22px;
}

.login-hint {
  margin-top: 10px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 6px;
}

/* 检索面板 */
.search-panel-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 260px;
  overflow: auto;
  padding-right: 2px;
}

.search-result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  transition: background 0.15s;
}

.search-result-item:hover {
  background: #f8fafc;
}

.search-result-info {
  min-width: 0;
  flex: 1;
}

.search-result-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
}

.search-result-desc {
  margin-top: 2px;
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 公众号列表 */
.mp-panel-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mp-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 220px;
  overflow: auto;
  padding-right: 2px;
}

.mp-list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #475569;
  transition: all 0.15s;
}

.mp-list-item:hover {
  background: #f1f5f9;
}

.mp-list-item.active {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 500;
}

.mp-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ========== 右侧主区域 ========== */
.radar-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

/* 工具栏卡片 */
.toolbar-card :deep(.el-card__body) {
  padding: 12px 16px;
}

.toolbar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-settings {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.setting-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.setting-field label {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 文章列表卡片 */
.articles-card {
  flex: 1;
  border-radius: 10px;
}

.articles-card :deep(.el-card__body) {
  padding: 0;
}

.articles-body {
  padding: 12px 16px 16px;
}

.article-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.article-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  transition: background 0.15s;
}

.article-item:hover {
  background: #f8fafc;
}

.article-main {
  flex: 1;
  min-width: 0;
}

.article-title {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 12px;
  color: #94a3b8;
}

.meta-icon {
  font-size: 14px;
  color: #16a34a;
}

.meta-icon.muted {
  color: #cbd5e1;
}

.article-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

/* ========== 登录弹窗 ========== */
.login-dialog-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.qr-box {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 260px;
  height: 260px;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  background: #f8fafc;
  overflow: hidden;
}

.qr-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 12px;
}

.qr-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  text-align: center;
}

.qr-error-title {
  font-size: 14px;
  font-weight: 600;
  color: #dc2626;
}

.qr-error-text {
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}

.login-steps {
  display: flex;
  gap: 8px;
  width: 100%;
}

.step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px;
  border-radius: 8px;
  background: #f8fafc;
  font-size: 12px;
  color: #475569;
  text-align: center;
}

.step-num {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #e2e8f0;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.dialog-error {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 13px;
}

.dialog-tip {
  font-size: 13px;
  color: #64748b;
}

/* ========== 文章预览弹窗 ========== */
.preview-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.preview-header h3 {
  margin: 0 0 8px;
  font-size: 22px;
  line-height: 1.4;
  color: #1e293b;
}

.preview-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #64748b;
}

.preview-loading {
  padding: 40px 0;
  text-align: center;
  color: #64748b;
}

.preview-content {
  max-height: 60vh;
  overflow: auto;
  padding-right: 8px;
  line-height: 1.8;
  color: #334155;
}

.preview-content :deep(img) {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 16px auto;
  border-radius: 8px;
}

.preview-content :deep(p) {
  margin: 0 0 14px;
}

.preview-content :deep(blockquote) {
  margin: 16px 0;
  padding: 12px 16px;
  border-left: 4px solid #93c5fd;
  background: #f8fbff;
}

.preview-content :deep(h2) {
  font-size: 18px;
  margin: 20px 0 12px;
}

.preview-content :deep(h3) {
  font-size: 16px;
  margin: 16px 0 10px;
}

/* ========== 响应式 ========== */
@media (max-width: 1100px) {
  .stat-bar {
    grid-template-columns: repeat(2, 1fr);
  }

  .radar-body {
    grid-template-columns: 280px 1fr;
  }
}

@media (max-width: 900px) {
  .radar-body {
    grid-template-columns: 1fr;
  }

  .radar-sidebar {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .radar-header {
    flex-direction: column;
  }

  .stat-bar {
    grid-template-columns: repeat(2, 1fr);
  }

  .radar-sidebar {
    grid-template-columns: 1fr;
  }

  .toolbar-content {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-settings {
    justify-content: space-between;
  }

  .toolbar-actions {
    justify-content: flex-end;
  }

  .article-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .article-actions {
    align-self: flex-end;
  }

  .login-steps {
    flex-direction: column;
  }
}
</style>
