<script setup>
import { computed, onMounted, ref } from 'vue'
import SidebarNav from './components/SidebarNav.vue'
import TopToolbar from './components/TopToolbar.vue'
import OverviewBoard from './components/OverviewBoard.vue'
import PipelineBoard from './components/PipelineBoard.vue'
import InspirationBoard from './components/InspirationBoard.vue'
import WechatRadarBoard from './components/WechatRadarBoard.vue'
import FormatterBoard from './components/FormatterBoard.vue'
import AccountsBoard from './components/AccountsBoard.vue'
import PublishBoard from './components/PublishBoard.vue'
import TraceBoard from './components/TraceBoard.vue'
import SettingsBoard from './components/SettingsBoard.vue'
import { dashboardApi } from './lib/api'
import { NAV_ITEMS } from './lib/pipeline'

const navItems = NAV_ITEMS
const activeView = ref('overview')
const accounts = ref([])
const activeAccountId = ref('')
const overview = ref(null)
const jobs = ref([])
const pipelineRows = ref([])
const publishRows = ref([])
const scheduler = ref({ running: false, minutes: 0, next_run_at: '' })
const health = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const selectedPipelineId = ref('')
const selectedJobId = ref('')

const activeAccount = computed(() => accounts.value.find((item) => item.id === activeAccountId.value) || {})
const schedulerText = computed(() => {
  if (scheduler.value?.running) {
    return `自动巡检运行中 / ${scheduler.value.minutes || '-'} 分钟`
  }
  return '自动巡检未开启'
})

async function bootstrap(selectCurrent = false) {
  loading.value = true
  errorMessage.value = ''
  try {
    const [accountsData, schedulerData, jobsData, healthData] = await Promise.all([
      dashboardApi.accounts(),
      dashboardApi.scheduler(),
      dashboardApi.jobs(),
      dashboardApi.health(),
    ])
    accounts.value = accountsData.items || []
    if (!activeAccountId.value || selectCurrent) {
      activeAccountId.value = accountsData.active_account_id || accounts.value[0]?.id || ''
    }
    scheduler.value = schedulerData.scheduler || { running: false, minutes: 0, next_run_at: '' }
    jobs.value = jobsData.items || []
    health.value = healthData || null
    if (activeAccountId.value) {
      const [overviewData, pipelineData, publishData] = await Promise.all([
        dashboardApi.overview(activeAccountId.value),
        dashboardApi.pipelineList({ accountId: activeAccountId.value, limit: 500 }),
        dashboardApi.publishList({ accountId: activeAccountId.value, limit: 500 }),
      ])
      overview.value = overviewData
      pipelineRows.value = pipelineData.items || []
      publishRows.value = publishData.items || []
      selectedPipelineId.value = overview.value?.recent?.pipeline?.[0]?.record_id || ''
      if (!selectedPipelineId.value && pipelineRows.value.length) {
        selectedPipelineId.value = pipelineRows.value[0]?.record_id || ''
      }
      if (!selectedJobId.value && jobs.value.length) {
        selectedJobId.value = jobs.value[0]?.id || ''
      }
    } else {
      overview.value = null
      pipelineRows.value = []
      publishRows.value = []
    }
  } catch (error) {
    errorMessage.value = error.message || '后台数据加载失败'
  } finally {
    loading.value = false
  }
}

async function changeAccount(accountId) {
  if (!accountId) return
  await dashboardApi.activateAccount(accountId)
  activeAccountId.value = accountId
  await bootstrap()
}

async function runPipeline() {
  if (!activeAccountId.value) return
  const data = await dashboardApi.runPipeline(activeAccountId.value)
  selectedJobId.value = data?.job_id || selectedJobId.value
  await bootstrap()
}

async function runFullInspection() {
  if (!activeAccountId.value) return
  const data = await dashboardApi.runFullInspection(activeAccountId.value)
  selectedJobId.value = data?.job_id || selectedJobId.value
  await bootstrap()
}

async function runInspirationScan() {
  if (!activeAccountId.value) return
  const data = await dashboardApi.runInspirationScan(activeAccountId.value)
  selectedJobId.value = data?.job_id || selectedJobId.value
  await bootstrap()
}

async function rerunSelected(item) {
  if (!item) return
  const url = item.url || item.rewritten_doc || ''
  if (!url) {
    errorMessage.value = '当前记录缺少可用链接，建议先补齐原文或改后文档链接。'
    return
  }
  await dashboardApi.runSingleArticle({
    account_id: activeAccountId.value,
    url,
    role: overview.value?.account?.pipeline_role || 'tech_expert',
    model: overview.value?.account?.pipeline_model || 'auto',
  })
  await bootstrap()
}

function openPublishWithJob(jobId) {
  if (jobId) selectedJobId.value = jobId
  activeView.value = 'publish'
}

onMounted(() => {
  bootstrap(true)
})
</script>

<template>
  <div class="admin-shell">
    <SidebarNav :items="navItems" :active-view="activeView" @change="activeView = $event" />

    <main class="main-shell">
      <TopToolbar
        :accounts="accounts"
        :active-account-id="activeAccountId"
        :scheduler-text="schedulerText"
        :scheduler-running="scheduler.running"
        @change-account="changeAccount"
        @refresh="bootstrap()"
      />

      <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
      <div v-if="loading" class="loading-card">正在加载 Vue 管理后台数据...</div>

      <template v-else>
        <OverviewBoard
          v-if="activeView === 'overview'"
          :overview="overview"
          :jobs="jobs"
          @run-scan="runInspirationScan"
          @run-full="runFullInspection"
          @run-pipeline="runPipeline"
        />
        <InspirationBoard
          v-else-if="activeView === 'inspiration'"
          :active-account="activeAccount"
          @refresh="bootstrap()"
        />
        <WechatRadarBoard
          v-else-if="activeView === 'radar'"
          :active-account="activeAccount"
          @refresh="bootstrap()"
        />
        <FormatterBoard
          v-else-if="activeView === 'formatter'"
        />
        <PipelineBoard
          v-else-if="activeView === 'pipeline'"
          :pipeline-items="pipelineRows"
          :active-account="activeAccount"
          :selected-pipeline-id="selectedPipelineId"
          @select="selectedPipelineId = $event"
          @run-pipeline="runPipeline"
          @run-selected="rerunSelected"
          @refresh="bootstrap()"
        />
        <AccountsBoard
          v-else-if="activeView === 'accounts'"
          :accounts="accounts"
          :active-account-id="activeAccountId"
          @refresh="bootstrap(true)"
        />
        <PublishBoard
          v-else-if="activeView === 'publish'"
          :jobs="jobs"
          :publish-rows="publishRows"
          :accounts="accounts"
          :active-account-id="activeAccountId"
          :initial-job-id="selectedJobId"
          @refresh="bootstrap()"
        />
        <TraceBoard
          v-else-if="activeView === 'trace'"
          :pipeline-items="pipelineRows"
          :jobs="jobs"
          :active-account="activeAccount"
          :active-account-id="activeAccountId"
          @refresh="bootstrap()"
          @run-selected="rerunSelected"
          @run-pipeline="runPipeline"
          @open-job="openPublishWithJob"
        />
        <SettingsBoard
          v-else
          :scheduler="scheduler"
          :health="health"
          :active-account-id="activeAccountId"
          :active-account="activeAccount"
          @refresh="bootstrap()"
        />
      </template>
    </main>
  </div>
</template>
