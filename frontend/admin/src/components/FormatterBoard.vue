<script setup>
import { ref } from 'vue'

const iframeKey = ref(0)
const editorUrl = '/tools/huasheng/'

function reloadIframe() {
  iframeKey.value += 1
}
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>公众号排版</h1>
        <p>二级功能：已融合 huasheng_editor 排版能力，可直接进行 Markdown 排版与一键复制到公众号。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" @click="reloadIframe">刷新排版器</button>
        <a class="primary-btn" :href="editorUrl" target="_blank" rel="noreferrer">新窗口打开排版器</a>
      </div>
    </div>

    <div class="global-info">
      已接入本地排版引擎，支持多主题样式、代码高亮、图片处理与公众号兼容复制。
    </div>

    <div class="panel-card formatter-panel">
      <iframe
        :key="iframeKey"
        class="formatter-iframe"
        :src="editorUrl"
        title="公众号内容排版器"
      ></iframe>
    </div>
  </section>
</template>
