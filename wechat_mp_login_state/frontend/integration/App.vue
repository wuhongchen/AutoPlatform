<script setup>
import { computed, onMounted, ref } from 'vue'
import SidebarNav from './components/SidebarNav.vue'
import TopToolbar from './components/TopToolbar.vue'
import OverviewBoard from './components/OverviewBoard.vue'
import InspirationBoard from './components/InspirationBoard.vue'
import WechatRadarBoard from './components/WechatRadarBoard.vue'
import FormatterBoard from './components/FormatterBoard.vue'
import AccountsBoard from './components/AccountsBoard.vue'
import PublishBoard from './components/PublishBoard.vue'
import TaskCenterBoard from './components/TaskCenterBoard.vue'
import SettingsBoard from './components/SettingsBoard.vue'
import { dashboardApi } from './lib/api'
import { NAV_ITEMS } from './lib/pipeline'

const navItems = NAV_ITEMS
const activeView = ref('overview')
const accounts = ref([])
const activeAccountId = ref('')
const overview = ref(null)
const jobs = ref([])
const publishRows = ref([])
const health = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const selectedJobId = ref('')

const activeAccount = computed(() => accounts.value.find((item) => item.id === activeAccountId.value) || {})

function syncSelectedJob() {
  const current = selectedJobId.value
  if (current && jobs.value.some((item) => item.id === current)) return
  selectedJobId.value = jobs.value[0]?.id || ''
}

async function refreshBaseData(selectCurrent = false) {
  const [accountsData, jobsData, healthData] = await Promise.all([
    dashboardApi.accounts(),
    dashboardApi.jobs(),
    dashboardApi.health(),
  ])
  accounts.value = accountsData.items || []
  if (!activeAccountId.value || selectCurrent) {
    activeAccountId.value = accountsData.active_account_id || accounts.value[0]?.id || ''
  }
  jobs.value = jobsData.items || []
  health.value = healthData || null
  syncSelectedJob()
}

async function refreshJobsData() {
  const jobsData = await dashboardApi.jobs()
  jobs.value = jobsData.items || []
  syncSelectedJob()
}

async function refreshOverviewData() {
  if (!activeAccountId.value) {
    overview.value = null
    return
  }
  overview.value = await dashboardApi.overview(activeAccountId.value)
}

async function refreshPublishData() {
  if (!activeAccountId.value) {
    publishRows.value = []
    return
  }
  const publishData = await dashboardApi.publishList({ accountId: activeAccountId.value, limit: 500 })
  publishRows.value = publishData.items || []
}

async function refreshWorkflowWorkspace() {
  errorMessage.value = ''
  try {
    await Promise.all([refreshOverviewData(), refreshPublishData()])
  } catch (error) {
    errorMessage.value = error.message || '数据刷新失败'
  }
}

async function refreshJobsAndWorkflow() {
  await Promise.all([refreshJobsData(), refreshWorkflowWorkspace()])
}

async function refreshDashboard(selectCurrent = false) {
  loading.value = true
  errorMessage.value = ''
  try {
    await refreshBaseData(selectCurrent)
    if (activeAccountId.value) {
      await Promise.all([refreshOverviewData(), refreshPublishData()])
    } else {
      overview.value = null
      publishRows.value = []
    }
  } catch (error) {
    errorMessage.value = error.message || '后台数据加载失败'
  } finally {
    loading.value = false
  }
}

async function bootstrap(selectCurrent = false) {
  await refreshDashboard(selectCurrent)
}

async function changeAccount(accountId) {
  if (!accountId) return
  await dashboardApi.activateAccount(accountId)
  activeAccountId.value = accountId
  await refreshDashboard()
}

async function addArticle() {
  // 导航到灵感库页面
  activeView.value = 'inspiration'
}

function openPublishWithJob(jobId) {
  if (jobId) selectedJobId.value = jobId
  activeView.value = 'publish'
}

async function runInspirationScan() {
  errorMessage.value = ''
  try {
    await dashboardApi.runInspirationScan(activeAccountId.value)
    setTimeout(() => refreshDashboard(), 1000)
  } catch (error) {
    errorMessage.value = error.message || '启动灵感扫描失败'
  }
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
        @change-account="changeAccount"
        @refresh="refreshDashboard()"
      />

      <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
      <div v-if="loading" class="loading-card">正在加载 Vue 管理后台数据...</div>

      <template v-else>
        <OverviewBoard
          v-if="activeView === 'overview'"
          :overview="overview"
          :jobs="jobs"
          @run-scan="runInspirationScan"
          @add-article="addArticle"
        />
        <InspirationBoard
          v-else-if="activeView === 'inspiration'"
          :active-account="activeAccount"
          @refresh="refreshOverviewData()"
        />
        <WechatRadarBoard
          v-else-if="activeView === 'radar'"
          :active-account="activeAccount"
          @refresh="refreshOverviewData()"
        />
        <FormatterBoard
          v-else-if="activeView === 'formatter'"
        />
        <AccountsBoard
          v-else-if="activeView === 'accounts'"
          :accounts="accounts"
          :active-account-id="activeAccountId"
          @refresh="refreshDashboard(true)"
        />
        <TaskCenterBoard
          v-else-if="activeView === 'tasks'"
          :active-account="activeAccount"
          @refresh="refreshJobsData()"
        />
        <SettingsBoard
          v-else
          :health="health"
          :active-account-id="activeAccountId"
          :active-account="activeAccount"
          @refresh="refreshDashboard()"
        />
      </template>
    </main>
  </div>
</template>
