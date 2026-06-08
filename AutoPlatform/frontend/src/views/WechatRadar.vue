<template>
  <div class="wechat-radar-page">
    <WechatRadarBoard
      :account-id="currentAccount?.account_id || ''"
      :account-name="currentAccount?.name || ''"
      @refresh="loadInspirations"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import WechatRadarBoard from '../components/WechatRadarBoard.vue'
import { useAccountStore, useAppStore, useInspirationStore } from '../stores'

const accountStore = useAccountStore()
const appStore = useAppStore()
const inspirationStore = useInspirationStore()

const currentAccount = computed(() =>
  accountStore.accounts.find(a => a.account_id === appStore.selectedAccountId) || null
)

function loadInspirations() {
  const params = appStore.selectedAccountId
    ? { account_id: appStore.selectedAccountId }
    : undefined
  inspirationStore.fetchInspirations(params)
}
</script>
