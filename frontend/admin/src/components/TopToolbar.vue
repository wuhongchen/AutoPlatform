<script setup>
defineProps({
  accounts: { type: Array, required: true },
  activeAccountId: { type: String, default: '' },
  schedulerText: { type: String, required: true },
  schedulerRunning: { type: Boolean, default: false },
})
const emit = defineEmits(['change-account', 'refresh'])
</script>

<template>
  <header class="topbar-shell">
    <div class="toolbar-left">
      <div class="account-select-shell">
        <span class="account-select-icon">微</span>
        <select :value="activeAccountId" @change="emit('change-account', $event.target.value)">
          <option v-for="item in accounts" :key="item.id" :value="item.id">
            {{ item.name }}{{ item.enabled === false ? ' [禁用]' : '' }}
          </option>
        </select>
      </div>
      <div class="scheduler-chip" :class="schedulerRunning ? 'ok' : 'warn'">
        <span class="dot"></span>
        <span>{{ schedulerText }}</span>
      </div>
    </div>
    <div class="toolbar-right">
      <button class="ghost-btn" @click="emit('refresh')">刷新数据</button>
    </div>
  </header>
</template>
