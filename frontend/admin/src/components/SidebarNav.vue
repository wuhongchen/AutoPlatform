<script setup>
defineProps({
  items: { type: Array, required: true },
  activeView: { type: String, required: true },
})
const emit = defineEmits(['change'])
</script>

<template>
  <aside class="sidebar-shell">
    <div class="brand-block">
      <div class="brand-title">AutoInfo 运营台</div>
    </div>

    <nav class="nav-list">
      <button
        v-for="item in items"
        :key="item.key"
        class="nav-btn"
        :class="{ active: item.key === activeView }"
        @click="emit('change', item.key)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
        <span v-if="item.status !== 'ready'" class="nav-plan">规划中</span>
      </button>
    </nav>

    <div class="sidebar-note">
      新页面统一基于 Vue 组件、设计令牌、状态语义和 API 适配层继续开发。
    </div>
  </aside>
</template>
