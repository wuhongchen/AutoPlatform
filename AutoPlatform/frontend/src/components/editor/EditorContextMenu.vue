<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="context-menu-overlay"
      @click="close"
      @contextmenu.prevent="close"
    >
      <div
        ref="menuRef"
        class="context-menu"
        :style="{ left: x + 'px', top: y + 'px' }"
      >
        <!-- 插入 -->
        <div class="menu-group-label">插入</div>
        <div class="menu-item" @click="emit('insertImage')">
          <el-icon><Picture /></el-icon> 图片链接
        </div>
        <div class="menu-item" @click="emit('uploadImage')">
          <el-icon><Upload /></el-icon> 上传图片到图床
        </div>
        <div class="menu-item" @click="emit('insert', '\n---\n')">
          <el-icon><Minus /></el-icon> 分隔线
        </div>
        <div class="menu-item" @click="emit('insert', '\n```\n\n```\n')">
          <el-icon><Document /></el-icon> 代码块
        </div>
        <div class="menu-item" @click="emit('insert', '\n| 列1 | 列2 |\n| --- | --- |\n| | |\n')">
          <el-icon><Grid /></el-icon> 表格
        </div>
        <div class="menu-item" @click="emit('component')">
          <el-icon><CopyDocument /></el-icon> 插入组件
        </div>

        <div class="menu-divider" />

        <!-- 格式 -->
        <div class="menu-group-label">文本格式</div>
        <div class="menu-item" @click="emit('insert', '**bold**')">
          <strong>B</strong> 加粗
        </div>
        <div class="menu-item" @click="emit('insert', '*italic*')">
          <em>I</em> 斜体
        </div>
        <div class="menu-item" @click="emit('insert', '~~strikethrough~~')">
          <s>S</s> 删除线
        </div>
        <div class="menu-item" @click="emit('insert', '`code`')">
          &lt;/&gt; 行内代码
        </div>
        <div class="menu-item" @click="emit('insertLink')">
          <el-icon><Link /></el-icon> 超链接
        </div>

        <div class="menu-divider" />

        <!-- 标题 -->
        <div class="menu-group-label">标题</div>
        <div class="menu-item" @click="emit('heading', 1)">H1 一级标题</div>
        <div class="menu-item" @click="emit('heading', 2)">H2 二级标题</div>
        <div class="menu-item" @click="emit('heading', 3)">H3 三级标题</div>

        <div class="menu-divider" />

        <!-- 列表 -->
        <div class="menu-item" @click="emit('insert', '\n- item')">
          <el-icon><List /></el-icon> 无序列表
        </div>
        <div class="menu-item" @click="emit('insert', '\n1. item')">
          <el-icon><Tickets /></el-icon> 有序列表
        </div>
        <div class="menu-item" @click="emit('insert', '\n> quote')">
          <el-icon><ChatLineSquare /></el-icon> 引用块
        </div>

        <div class="menu-divider" />

        <!-- 文档 -->
        <div class="menu-group-label">文档</div>
        <div class="menu-item" @click="emit('format')">
          <el-icon><MagicStick /></el-icon> 一键排版
        </div>
        <div class="menu-item" @click="emit('exportMd')">
          <el-icon><Download /></el-icon> 导出 .md
        </div>
        <div class="menu-item danger" @click="emit('clear')">
          <el-icon><Delete /></el-icon> 清空内容
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import {
  Picture, Upload, Minus, Document, Grid, Link,
  List, Tickets, ChatLineSquare, MagicStick, Download, Delete,
} from '@element-plus/icons-vue'

const props = defineProps({
  visible: Boolean,
  x: Number,
  y: Number,
})

const emit = defineEmits([
  'close', 'insert', 'heading', 'insertImage', 'uploadImage',
  'insertLink', 'format', 'exportMd', 'clear', 'component',
])

function close() {
  emit('close')
}
</script>

<style scoped>
.context-menu-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
}

.context-menu {
  position: fixed;
  z-index: 10000;
  min-width: 200px;
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  padding: 6px 0;
  font-size: 13px;
}

.menu-group-label {
  padding: 4px 14px 2px;
  font-size: 11px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  cursor: pointer;
  color: #333;
  transition: background 0.15s;
}

.menu-item:hover {
  background: #f0f0ff;
  color: #6366f1;
}

.menu-item.danger:hover {
  background: #fef0f0;
  color: #f56c6c;
}

.menu-divider {
  height: 1px;
  background: #eee;
  margin: 4px 8px;
}
</style>
