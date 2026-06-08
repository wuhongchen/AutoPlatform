<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { dashboardApi } from '../lib/api'

const props = defineProps({
  activeAccount: { type: Object, default: () => ({}) },
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
const syncLimit = ref(50)
const contentLimit = ref(10)

const loginDialogVisible = ref(false)
const loginJobId = ref('')
const loginPolling = ref(false)
const lastLoginAt = ref('')
const persistedLogin = ref(false)
const qrImageUrl = ref('')
const qrImageReady = ref(false)
const qrImageError = ref('')

let loginPollTimer = null

const activeAccount = computed(() => props.activeAccount || {})
const accountId = computed(() => activeAccount.value?.id || '')
const loginMemoryKey = computed(() => `wechat_login_confirmed_${accountId.value || 'default'}`)

const isLoggedIn = computed(() => {
  return Boolean(statusInfo.value?.runtime?.login_status) || persistedLogin.value
})

const mpCount = computed(() => {
  return Number(statusInfo.value?.state?.mp_count || mpList.value.length || 0)
})

const articleCount = computed(() => {
  return Number(statusInfo.value?.state?.article_count || 0)
})

function setInfo(text) {
  message.value = text || ''
  errorMessage.value = ''
}

function setError(err) {
  errorMessage.value = err?.message || String(err || '操作失败')
}

function readLoginMemory() {
  try {
    persistedLogin.value = localStorage.getItem(loginMemoryKey.value) === '1'
    lastLoginAt.value = localStorage.getItem(`${loginMemoryKey.value}_at`) || ''
  } catch {
    persistedLogin.value = false
    lastLoginAt.value = ''
  }
}

function markLoginConfirmed() {
  persistedLogin.value = true
  const now = new Date().toLocaleString()
  lastLoginAt.value = now
  try {
    localStorage.setItem(loginMemoryKey.value, '1')
    localStorage.setItem(`${loginMemoryKey.value}_at`, now)
  } catch {
    // ignore localStorage failures
  }
}

function clearLoginMemory() {
  persistedLogin.value = false
  lastLoginAt.value = ''
  try {
    localStorage.removeItem(loginMemoryKey.value)
    localStorage.removeItem(`${loginMemoryKey.value}_at`)
  } catch {
    // ignore localStorage failures
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
  const status = statusInfo.value || {}
  const state = status.state || {}
  const hasQr = Boolean(status.qr_image_url || state.qr_image_exists || state.qr_image_path)
  if (hasQr) {
    qrImageReady.value = false
    qrImageUrl.value =
      status.qr_image_url ||
      `/api/wechat/qr-image?account_id=${encodeURIComponent(accountId.value || '')}&t=${Date.now()}`
    qrImageError.value = ''
  }
  return hasQr
}

function startLoginPolling() {
  stopLoginPolling()
  loginPolling.value = true
  loginPollTimer = setInterval(async () => {
    try {
      await reloadStatus()
      updateQrPreviewFromStatus()
      if (statusInfo.value?.runtime?.login_status) {
        markLoginConfirmed()
        stopLoginPolling()
        setInfo('扫码登录成功，当前账户登录状态已确认。')
      }
    } catch {
      // keep polling silently
    }
  }, 3000)
}

async function withBusy(fn) {
  busy.value = true
  errorMessage.value = ''
  try {
    await fn()
  } catch (err) {
    setError(err)
  } finally {
    busy.value = false
  }
}

async function reloadStatus() {
  if (!accountId.value) return
  statusInfo.value = await dashboardApi.wechatStatus(accountId.value)
  updateQrPreviewFromStatus()
  if (statusInfo.value?.runtime?.login_status) {
    markLoginConfirmed()
  }
}

async function reloadMpList() {
  if (!accountId.value) return
  const data = await dashboardApi.wechatListMp(accountId.value)
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
  const data = await dashboardApi.wechatListArticles(accountId.value, selectedMpId.value)
  articleRows.value = data.items || []
}

async function bootstrap() {
  await withBusy(async () => {
    readLoginMemory()
    const settled = await Promise.allSettled([reloadStatus(), reloadMpList()])
    const allFailed = settled.every((it) => it.status === 'rejected')
    if (allFailed) {
      throw (settled.find((it) => it.status === 'rejected') || {}).reason || new Error('刷新失败')
    }
    await reloadArticles()
    setInfo('雷达舱已刷新：可继续登录、关注、拉取和批次投递。')
  })
}

async function openLoginFlow() {
  if (!accountId.value) return
  loginDialogVisible.value = true
  await withBusy(async () => {
    qrImageReady.value = false
    qrImageError.value = ''
    qrImageUrl.value = ''
    const data = await dashboardApi.wechatLogin({
      account_id: accountId.value,
      wait: false,
      qr_display: 'none',
      timeout: 60,
      token_wait_timeout: 20,
      thread_join_timeout: 8,
    })
    loginJobId.value = data.job_id || `rc:${String(data.login_return_code ?? '-')}`
    statusInfo.value = data
    updateQrPreviewFromStatus()
    startLoginPolling()
    if (data?.error) {
      setInfo(`登录流程已触发，但返回提示：${data.error}`)
    } else {
      setInfo('已触发二维码登录，请在弹窗二维码区域完成扫码。')
    }
    emit('refresh')
  })
}

async function refreshLoginStatus() {
  await withBusy(async () => {
    await reloadStatus()
    if (statusInfo.value?.runtime?.login_status) {
      markLoginConfirmed()
      stopLoginPolling()
      setInfo('登录状态确认成功。')
    } else {
      setInfo('当前仍未检测到登录成功，请继续扫码后重试。')
    }
  })
}

async function searchMp() {
  if (!accountId.value || !keyword.value.trim()) return
  await withBusy(async () => {
    const data = await dashboardApi.wechatSearchMp({ account_id: accountId.value, keyword: keyword.value.trim(), limit: 8 })
    searchRows.value = data.items || []
    setInfo(`检索完成，候选 ${searchRows.value.length} 条。`)
  })
}

async function addMpByPick(pickIndex) {
  if (!accountId.value || !keyword.value.trim()) return
  await withBusy(async () => {
    await dashboardApi.wechatAddMp({
      account_id: accountId.value,
      keyword: keyword.value.trim(),
      pick: pickIndex,
      limit: 8,
    })
    await reloadMpList()
    await reloadArticles()
    setInfo(`已关注候选 #${pickIndex}。`)
    emit('refresh')
  })
}

async function pullArticlesAction() {
  if (!accountId.value || !selectedMpId.value) return
  await withBusy(async () => {
    const data = await dashboardApi.wechatPullArticles({
      account_id: accountId.value,
      mp_id: selectedMpId.value,
      pages: Number(pages.value || 1),
      mode: 'api',
      with_content: Boolean(withContent.value),
    })
    articleRows.value = data.items || []
    setInfo(`文章拉取完成，缓存 ${Number(data.count || 0)} 条。`)
    emit('refresh')
  })
}

async function syncInspirationAction() {
  if (!accountId.value) return
  await withBusy(async () => {
    const data = await dashboardApi.wechatSyncInspiration({
      account_id: accountId.value,
      mp_id: selectedMpId.value,
      limit: Number(syncLimit.value || 50),
    })
    setInfo(`日批次投递完成：新增 ${Number(data.inserted || 0)} 条。`)
    emit('refresh')
  })
}

async function fullFlowAction() {
  if (!accountId.value) return
  if (!selectedMpId.value && !keyword.value.trim()) {
    setError(new Error('请先选择已关注公众号，或先输入关键词检索。'))
    return
  }
  await withBusy(async () => {
    const data = await dashboardApi.wechatFullFlow({
      account_id: accountId.value,
      mp_id: selectedMpId.value,
      keyword: keyword.value.trim(),
      pick: 1,
      pages: Number(pages.value || 1),
      mode: 'api',
      with_content: Boolean(withContent.value),
      content_limit: Number(contentLimit.value || 10),
      sync_limit: Number(syncLimit.value || 50),
    })
    const pulled = Number(data?.pull?.count || 0)
    const synced = Number(data?.sync?.inserted || 0)
    setInfo(`全流程执行完成：文章缓存 ${pulled} 条，入库新增 ${synced} 条。`)
    await reloadMpList()
    await reloadArticles()
    emit('refresh')
  })
}

function closeLoginDialog() {
  loginDialogVisible.value = false
  stopLoginPolling()
}

function validHttpUrl(url) {
  return /^https?:\/\//.test(String(url || '').trim())
}

function onQrImageLoad() {
  qrImageReady.value = true
  qrImageError.value = ''
}

function onQrImageError() {
  qrImageReady.value = false
  qrImageError.value = '二维码暂未生成，请稍后点击“刷新二维码”。'
}

async function refreshQrImage() {
  await withBusy(async () => {
    await reloadStatus()
    const hasQr = updateQrPreviewFromStatus()
    if (!hasQr) {
      qrImageError.value = '二维码暂未生成，请稍后再试。'
    } else {
      qrImageReady.value = false
    }
  })
}

onMounted(() => {
  readLoginMemory()
  bootstrap()
})

onBeforeUnmount(() => {
  stopLoginPolling()
})

watch(
  () => accountId.value,
  () => {
    searchRows.value = []
    articleRows.value = []
    stopLoginPolling()
    readLoginMemory()
    qrImageUrl.value = ''
    qrImageReady.value = false
    qrImageError.value = ''
    bootstrap()
  }
)

watch(
  () => selectedMpId.value,
  () => {
    reloadArticles().catch(() => {
      // do not break main flow when article list not ready
    })
  }
)
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>雷达舱</h1>
        <p>独立负责扫码登录、关注同步、文章拉取和每日批次投递，不与灵感库视图混排。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" :disabled="busy" @click="bootstrap">刷新雷达舱</button>
        <button class="primary-btn" :disabled="busy || !accountId" @click="openLoginFlow">扫码登录</button>
      </div>
    </div>

    <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
    <div v-if="message" class="global-info">{{ message }}</div>

    <div class="panel-card panel-soft">
      <div class="inspiration-status-bar">
        <div class="status-chip-block">
          <span class="status-label">当前账户</span>
          <strong>{{ activeAccount?.name || activeAccount?.id || '-' }}</strong>
        </div>
        <div class="status-chip-block" :class="isLoggedIn ? 'ok' : 'warn'">
          <span class="status-label">扫码登录状态</span>
          <strong>{{ isLoggedIn ? '已确认登录' : '未登录' }}</strong>
        </div>
        <div class="status-chip-block">
          <span class="status-label">关注号数量</span>
          <strong>{{ mpCount }}</strong>
        </div>
        <div class="status-chip-block">
          <span class="status-label">文章缓存数量</span>
          <strong>{{ articleCount }}</strong>
        </div>
      </div>
      <p v-if="lastLoginAt" class="panel-tip">最近一次登录确认：{{ lastLoginAt }}</p>
      <div class="action-row">
        <button class="ghost-btn" :disabled="busy || !accountId" @click="refreshLoginStatus">检查登录状态</button>
        <button class="ghost-btn" :disabled="busy" @click="clearLoginMemory">清除登录记忆</button>
      </div>
    </div>

    <div class="inspiration-grid radar-grid">
      <div class="panel-card">
        <h3 class="section-title">公众号检索与关注</h3>
        <div class="form-row">
          <input v-model="keyword" type="text" placeholder="输入关键词检索公众号，例如 机器之心" />
          <button class="ghost-btn" :disabled="busy || !keyword.trim()" @click="searchMp">检索公众号</button>
        </div>
        <div class="search-list">
          <div v-for="(row, idx) in searchRows" :key="idx" class="search-item">
            <div>
              <strong>{{ row.nickname || row.alias || '未知公众号' }}</strong>
              <p>{{ row.signature || row.fakeid || '' }}</p>
            </div>
            <button class="ghost-btn" :disabled="busy" @click="addMpByPick(idx + 1)">关注 #{{ idx + 1 }}</button>
          </div>
          <div v-if="!searchRows.length" class="empty-block">先检索并关注公众号，再拉取文章列表。</div>
        </div>
      </div>

      <div class="panel-card">
        <h3 class="section-title">已关注公众号</h3>
        <div class="form-row">
          <select v-model="selectedMpId">
            <option value="">选择已关注公众号</option>
            <option v-for="item in mpList" :key="item.id" :value="item.id">{{ item.name || item.id }}</option>
          </select>
          <button class="ghost-btn" :disabled="busy" @click="reloadMpList">刷新列表</button>
        </div>
        <div class="article-list">
          <div v-for="item in mpList" :key="item.id" class="article-item">
            <strong>{{ item.name || item.id }}</strong>
            <p>ID: {{ item.id || '-' }}</p>
          </div>
          <div v-if="!mpList.length" class="empty-block">当前账户还没有关注公众号。</div>
        </div>
      </div>

      <div class="panel-card">
        <h3 class="section-title">拉取与批次投递</h3>
        <div class="form-grid-3">
          <label>
            拉取页数
            <input v-model.number="pages" type="number" min="1" max="10" />
          </label>
          <label>
            日批次投递上限
            <input v-model.number="syncLimit" type="number" min="1" max="200" />
          </label>
          <label>
            正文抓取上限
            <input v-model.number="contentLimit" type="number" min="1" max="200" />
          </label>
        </div>
        <div class="action-row">
          <label class="checkbox-inline"><input v-model="withContent" type="checkbox" />拉取时附带正文抓取</label>
        </div>
        <div class="action-row">
          <button class="ghost-btn" :disabled="busy || !selectedMpId" @click="pullArticlesAction">拉取文章列表</button>
          <button class="primary-btn" :disabled="busy" @click="syncInspirationAction">执行日批次投递</button>
          <button class="soft-btn" :disabled="busy" @click="fullFlowAction">一键全流程采集</button>
        </div>
      </div>

      <div class="panel-card">
        <h3 class="section-title">文章缓存预览</h3>
        <div class="article-list">
          <div v-for="(item, idx) in articleRows" :key="item.id || item.url || idx" class="article-item">
            <strong>{{ item.title || '未命名文章' }}</strong>
            <p>{{ item.publish_time || item.publish_time_str || '' }}</p>
            <a v-if="validHttpUrl(item.url)" :href="item.url" target="_blank" rel="noreferrer">打开链接</a>
          </div>
          <div v-if="!articleRows.length" class="empty-block">请先选择公众号并拉取文章。</div>
        </div>
      </div>
    </div>

    <div v-if="loginDialogVisible" class="modal-mask" @click.self="closeLoginDialog">
      <div class="modal-card">
        <h3>扫码登录流程</h3>
        <div class="radar-qr-box">
          <img
            v-if="qrImageUrl"
            class="radar-qr-image"
            :src="qrImageUrl"
            alt="微信扫码二维码"
            @load="onQrImageLoad"
            @error="onQrImageError"
          />
          <div v-else class="empty-block">二维码准备中...</div>
          <p v-if="qrImageError" class="panel-tip">{{ qrImageError }}</p>
          <p v-else-if="!qrImageReady" class="panel-tip">正在检测二维码文件，请稍候。</p>
        </div>
        <div class="kv-list">
          <div><span>步骤 1</span><strong>系统已生成二维码预览</strong></div>
          <div><span>步骤 2</span><strong>请用微信扫码并在手机端确认</strong></div>
          <div><span>步骤 3</span><strong>点击“检查登录状态”确认成功</strong></div>
          <div><span>登录返回</span><strong>{{ loginJobId || '-' }}</strong></div>
          <div><span>自动轮询</span><strong>{{ loginPolling ? '进行中' : '已停止' }}</strong></div>
          <div><span>当前状态</span><strong>{{ isLoggedIn ? '已确认登录' : '等待扫码确认' }}</strong></div>
        </div>
        <div class="detail-actions">
          <button class="ghost-btn" :disabled="busy" @click="refreshQrImage">刷新二维码</button>
          <button class="ghost-btn" :disabled="busy" @click="refreshLoginStatus">检查登录状态</button>
          <button class="primary-btn" @click="closeLoginDialog">我知道了</button>
        </div>
      </div>
    </div>
  </section>
</template>
