<script setup>
import { ref, watch } from 'vue'
import { dashboardApi } from '../lib/api'

const props = defineProps({
  scheduler: { type: Object, default: () => ({ running: false, minutes: 0, next_run_at: '' }) },
  health: { type: Object, default: null },
  activeAccountId: { type: String, default: '' },
  activeAccount: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['refresh'])

const busy = ref(false)
const errorMessage = ref('')
const message = ref('')
const schedulerMinutes = ref(30)
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

async function startScheduler() {
  await withBusy(async () => {
    const minutes = Number(schedulerMinutes.value || 30)
    await dashboardApi.startScheduler(minutes)
    setInfo(`已启动自动巡检，间隔 ${minutes} 分钟。`)
    emit('refresh')
  })
}

async function stopScheduler() {
  await withBusy(async () => {
    await dashboardApi.stopScheduler()
    setInfo('已停止自动巡检。')
    emit('refresh')
  })
}

async function runScan() {
  if (!props.activeAccountId) return
  await withBusy(async () => {
    const data = await dashboardApi.runInspirationScan(props.activeAccountId)
    setInfo(`已提交灵感扫描任务：${data.job_id}`)
    emit('refresh')
  })
}

async function runPipeline() {
  if (!props.activeAccountId) return
  await withBusy(async () => {
    const data = await dashboardApi.runPipeline(props.activeAccountId)
    setInfo(`已提交流水线巡检：${data.job_id}`)
    emit('refresh')
  })
}

async function runFullInspection() {
  if (!props.activeAccountId) return
  await withBusy(async () => {
    const data = await dashboardApi.runFullInspection(props.activeAccountId)
    setInfo(`已提交全流程单次巡检：${data.job_id}`)
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

watch(
  () => props.scheduler,
  (value) => {
    const minutes = Number(value?.minutes || 30)
    if (minutes > 0) schedulerMinutes.value = minutes
  },
  { immediate: true, deep: true }
)
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>设置</h1>
        <p>统一管理定时执行、系统健康检查与关键配置入口。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" :disabled="busy" @click="emit('refresh')">刷新状态</button>
      </div>
    </div>

    <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
    <div v-if="message" class="global-info">{{ message }}</div>

    <div class="settings-grid">
      <div class="panel-card panel-soft">
        <h3>定时执行</h3>
        <div class="settings-form-row">
          <label>
            间隔（分钟）
            <input v-model.number="schedulerMinutes" type="number" min="1" max="720" />
          </label>
          <button class="primary-btn" :disabled="busy" @click="startScheduler">启动</button>
          <button class="warn-btn" :disabled="busy" @click="stopScheduler">停止</button>
        </div>
        <div class="kv-list">
          <div><span>当前状态</span><strong>{{ scheduler?.running ? '运行中' : '已停止' }}</strong></div>
          <div><span>间隔</span><strong>{{ scheduler?.minutes || '-' }}</strong></div>
          <div><span>下次执行</span><strong>{{ scheduler?.next_run_at || '-' }}</strong></div>
        </div>
      </div>

      <div class="panel-card">
        <h3>系统健康</h3>
        <div class="kv-list">
          <div><span>当前账户</span><strong>{{ activeAccount?.name || activeAccount?.id || '-' }}</strong></div>
          <div><span>Python</span><strong>{{ health?.python || '-' }}</strong></div>
          <div><span>默认模型</span><strong>{{ health?.defaults?.model || '-' }}</strong></div>
          <div><span>默认角色</span><strong>{{ health?.defaults?.role || '-' }}</strong></div>
          <div><span>更新时间</span><strong>{{ health?.time || '-' }}</strong></div>
        </div>
      </div>

      <div class="panel-card">
        <h3>动作测试</h3>
        <div class="action-row">
          <button class="ghost-btn" :disabled="busy || !activeAccountId" @click="runScan">灵感库扫描</button>
          <button class="ghost-btn" :disabled="busy || !activeAccountId" @click="runPipeline">流水线巡检</button>
          <button class="ghost-btn" :disabled="busy || !activeAccountId" @click="runFullInspection">全流程单次巡检</button>
          <button class="primary-btn" :disabled="busy || !activeAccountId" @click="checkWechatStatus">检查微信采集状态</button>
        </div>
        <div class="kv-list" v-if="wechatCheck">
          <div><span>登录状态</span><strong>{{ wechatCheck?.runtime?.login_status ? '已登录' : '未登录' }}</strong></div>
          <div><span>关注号数</span><strong>{{ wechatCheck?.state?.mp_count || 0 }}</strong></div>
          <div><span>文章缓存</span><strong>{{ wechatCheck?.state?.article_count || 0 }}</strong></div>
        </div>
      </div>

      <div class="panel-card">
        <h3>参数获取辅助</h3>
        <p class="panel-tip">微信公众号 AppID / AppSecret 可在微信公众平台开发者中心获取。</p>
        <a class="primary-btn inline-btn" href="https://developers.weixin.qq.com/platform" target="_blank" rel="noreferrer">
          打开微信开发者平台
        </a>
      </div>
    </div>
  </section>
</template>
