<template>
  <div class="md-preview-wrapper">
    <div class="preview-header">
      <span class="preview-label">微信排版预览</span>
      <span class="preview-hint">{{ wordCount }} 字 · 阅读约 {{ readingTime }} 分钟</span>
    </div>
    <div class="preview-phone-frame">
      <div class="phone-status-bar">
        <span>{{ currentTime }}</span>
        <span>微信公众平台</span>
      </div>
      <div class="phone-content" id="output" v-html="renderedHtml"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  html: { type: String, default: '' },
  css: { type: String, default: '' },
})

const renderedHtml = ref('')
const wordCount = ref(0)
const readingTime = ref(1)
const currentTime = ref('')

function updateTime() {
  const now = new Date()
  currentTime.value = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
}

onMounted(() => {
  updateTime()
  setInterval(updateTime, 30000)
})

watch(() => props.html, (html) => {
  renderedHtml.value = html
  // 计算字数
  const text = (html || '').replace(/<[^>]+>/g, '').trim()
  wordCount.value = text.length
  readingTime.value = Math.max(1, Math.ceil(text.length / 400))
})

watch(() => props.css, (css) => {
  // 注入主题 CSS
  let styleEl = document.getElementById('md-preview-theme')
  if (!styleEl) {
    styleEl = document.createElement('style')
    styleEl.id = 'md-preview-theme'
    document.head.appendChild(styleEl)
  }
  styleEl.textContent = css
})
</script>

<style scoped>
.md-preview-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f0f0f0;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #fff;
  border-bottom: 1px solid #e5e5e5;
}

.preview-label {
  font-weight: 600;
  font-size: 14px;
  color: #333;
}

.preview-hint {
  font-size: 12px;
  color: #999;
}

.preview-phone-frame {
  flex: 1;
  max-width: 420px;
  width: 100%;
  margin: 20px auto;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.phone-status-bar {
  display: flex;
  justify-content: space-between;
  padding: 12px 20px 8px;
  font-size: 12px;
  color: #999;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.phone-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  font-size: 15px;
  line-height: 1.75;
  -webkit-overflow-scrolling: touch;
}
</style>
