<script setup>
defineProps({
  accounts: { type: Array, required: true },
  activeAccountId: { type: String, default: '' },
})
const emit = defineEmits(['change-account'])
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
    </div>
  </header>
</template>
