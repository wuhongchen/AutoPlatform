<template>
  <div class="md-toolbar">
    <el-button-group class="toolbar-group">
      <el-button size="small" @click="$emit('insert', '**bold**')" title="加粗 (Ctrl+B)">
        <strong>B</strong>
      </el-button>
      <el-button size="small" @click="$emit('insert', '*italic*')" title="斜体 (Ctrl+I)">
        <em>I</em>
      </el-button>
      <el-button size="small" @click="$emit('insert', '~~strikethrough~~')" title="删除线">
        <s>S</s>
      </el-button>
      <el-button size="small" @click="$emit('insert', '`code`')" title="行内代码">
        &lt;/&gt;
      </el-button>
    </el-button-group>

    <el-button-group class="toolbar-group">
      <el-button size="small" @click="$emit('heading', 1)" title="一级标题">H1</el-button>
      <el-button size="small" @click="$emit('heading', 2)" title="二级标题">H2</el-button>
      <el-button size="small" @click="$emit('heading', 3)" title="三级标题">H3</el-button>
    </el-button-group>

    <el-button-group class="toolbar-group">
      <el-button size="small" @click="$emit('insert', '\n- item')" title="无序列表">
        <el-icon><List /></el-icon>
      </el-button>
      <el-button size="small" @click="$emit('insert', '\n1. item')" title="有序列表">
        <el-icon><Tickets /></el-icon>
      </el-button>
      <el-button size="small" @click="$emit('insert', '\n> quote')" title="引用">
        <el-icon><ChatLineSquare /></el-icon>
      </el-button>
    </el-button-group>

    <el-button-group class="toolbar-group">
      <el-button size="small" @click="$emit('insertLink')" title="插入链接">
        <el-icon><Link /></el-icon>
      </el-button>
      <el-button size="small" @click="$emit('insertImage')" title="从链接插入图片">
        <el-icon><Picture /></el-icon>
      </el-button>
      <el-button size="small" @click="$emit('uploadImage')" title="上传图片到图床" type="warning" plain>
        <el-icon><Upload /></el-icon> 图床
      </el-button>
      <el-button size="small" @click="$emit('insert', '\n---\n')" title="分隔线">
        <el-icon><Minus /></el-icon>
      </el-button>
    </el-button-group>

    <el-button-group class="toolbar-group">
      <el-button size="small" @click="$emit('insert', '\n```\n\n```\n')" title="代码块">
        代码块
      </el-button>
      <el-button size="small" @click="$emit('insert', '\n| 列1 | 列2 |\n| --- | --- |\n| | |\n')" title="表格">
        表格
      </el-button>
    </el-button-group>

    <div class="toolbar-right">
      <el-select
        v-model="localTheme"
        size="small"
        style="width: 110px"
        @change="$emit('update:theme', $event)"
      >
        <el-option label="经典主题" value="default" />
        <el-option label="优雅主题" value="grace" />
        <el-option label="极简主题" value="simple" />
      </el-select>

      <el-button size="small" type="primary" @click="$emit('format')" :loading="formatting">
        <el-icon><MagicStick /></el-icon>
        一键排版
      </el-button>

      <el-button size="small" @click="$emit('save')" :loading="saving">
        <el-icon><Document /></el-icon>
        保存
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  theme: { type: String, default: 'default' },
  formatting: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
})

defineEmits([
  'insert',
  'heading',
  'insertLink',
  'insertImage',
  'uploadImage',
  'format',
  'save',
  'update:theme',
])

const localTheme = ref(props.theme)
watch(() => props.theme, (v) => { localTheme.value = v })
</script>

<style scoped>
.md-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fafafa;
  border-bottom: 1px solid #e5e5e5;
  flex-wrap: wrap;
}

.toolbar-group {
  margin-right: 4px;
}

.toolbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
