<script setup>
defineProps({
  title: String,
  value: [String, Number],
  meta: String,
  tone: { type: String, default: '' },
})
</script>

<template>
  <div class="metric-card" :class="tone">
    <div class="metric-head">
      <h3>{{ title }}</h3>
    </div>
    <div class="metric-value">{{ value }}</div>
    <p class="metric-meta">{{ meta }}</p>
  </div>
</template>
