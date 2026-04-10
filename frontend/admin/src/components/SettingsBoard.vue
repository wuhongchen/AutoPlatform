<script setup>
import { ref } from 'vue'
import { dashboardApi } from '../lib/api'

const props = defineProps({
  health: { type: Object, default: null },
  activeAccountId: { type: String, default: '' },
  activeAccount: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['refresh'])

const busy = ref(false)
const errorMessage = ref('')
const message = ref('')
const wechatCheck = ref(null)

function setInfo(text) {
  message.value = text || ''
  errorMessage.value = ''
}

function setError(err) {
  errorMessage.value = err?.message || String(err || '操作失败')
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

async function runScan() {
  if (!props.activeAccountId) return
  await withBusy(async () => {
    const data = await dashboardApi.runInspirationScan(props.activeAccountId)
    setInfo(`已提交灵感扫描任务：${data.job_id}`)
    emit('refresh')
  })
}

async function checkWechatStatus() {
  if (!props.activeAccountId) return
  await withBusy(async () => {
    wechatCheck.value = await dashboardApi.wechatStatus(props.activeAccountId)
    setInfo('微信采集状态已刷新。')
  })
}
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>设置</h1>
        <p>系统信息与快捷操作。</p>
      </div>
    </div>

    <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
    <div v-if="message" class="global-info">{{ message }}</div>

    <div class="settings-grid">
      <!-- 系统状态 -->
      <div class="panel-card">
        <h3>系统状态</h3>
        <div class="kv-list">
          <div><span>当前账户</span><strong>{{ activeAccount?.name || activeAccount?.id || '-' }}</strong></div>
          <div><span>Python</span><strong>{{ health?.python || '-' }}</strong></div>
          <div><span>默认模型</span><strong>{{ health?.defaults?.model || '-' }}</strong></div>
          <div><span>默认角色</span><strong>{{ health?.defaults?.role || '-' }}</strong></div>
          <div><span>更新时间</span><strong>{{ health?.time || '-' }}</strong></div>
        </div>
      </div>

      <!-- 快捷操作 -->
      <div class="panel-card">
        <h3>快捷操作</h3>
        <div class="action-row">
          <button class="ghost-btn" :disabled="busy || !activeAccountId" @click="runScan">灵感库扫描</button>
          <button class="primary-btn" :disabled="busy || !activeAccountId" @click="checkWechatStatus">检查微信采集状态</button>
        </div>
        <div class="kv-list" v-if="wechatCheck">
          <div><span>登录状态</span><strong>{{ wechatCheck?.runtime?.login_status ? '已登录' : '未登录' }}</strong></div>
          <div><span>关注号数</span><strong>{{ wechatCheck?.state?.mp_count || 0 }}</strong></div>
          <div><span>文章缓存</span><strong>{{ wechatCheck?.state?.article_count || 0 }}</strong></div>
        </div>
      </div>

      <!-- 帮助链接 -->
      <div class="panel-card">
        <h3>帮助</h3>
        <p class="panel-tip">微信公众号 AppID / AppSecret 可在微信公众平台开发者中心获取。</p>
        <a class="primary-btn inline-btn" href="https://developers.weixin.qq.com/platform" target="_blank" rel="noreferrer">
          打开微信开发者平台
        </a>
      </div>
    </div>
  </section>
</template>
