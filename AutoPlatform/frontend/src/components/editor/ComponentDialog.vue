<template>
  <el-dialog v-model="visible" title="插入组件" width="520px" destroy-on-close>
    <!-- 组件选择 -->
    <div class="component-tabs">
      <div
        v-for="comp in components"
        :key="comp.id"
        class="comp-card"
        :class="{ active: selectedId === comp.id }"
        @click="selectComponent(comp)"
      >
        <div class="comp-icon">{{ comp.icon }}</div>
        <div class="comp-label">{{ comp.name }}</div>
      </div>
    </div>

    <!-- 属性表单 -->
    <el-form v-if="selected" label-width="80px" style="margin-top:20px">
      <el-form-item
        v-for="prop in selected.props"
        :key="prop.name"
        :label="prop.label"
        :required="prop.required"
      >
        <el-input
          v-if="prop.type !== 'textarea'"
          v-model="formData[prop.name]"
          :placeholder="prop.placeholder"
          size="small"
        />
        <el-input
          v-else
          v-model="formData[prop.name]"
          type="textarea"
          :rows="3"
          :placeholder="prop.placeholder"
          size="small"
        />
      </el-form-item>

      <!-- 预览 -->
      <div v-if="previewHtml" class="comp-preview" v-html="previewHtml" />
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="doInsert" :disabled="!canInsert">插入</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const emit = defineEmits(['insert'])
const visible = defineModel('visible', { default: false })

const components = [
  {
    id: 'tip',
    name: '提示框',
    icon: '💡',
    desc: '高亮展示小贴士或注意事项',
    props: [
      { name: 'type', label: '类型', placeholder: 'info / success / warning / danger', required: true },
      { name: 'title', label: '标题', placeholder: '可选，如"提示"' },
      { name: 'content', label: '内容', placeholder: '提示内容', required: true, type: 'textarea' },
    ],
    render(p) {
      const colors = {
        info:    { border: '#1890ff', bg: '#e6f7ff', text: '#0050b3' },
        success: { border: '#52c41a', bg: '#f6ffed', text: '#135200' },
        warning: { border: '#faad14', bg: '#fffbe6', text: '#874d00' },
        danger:  { border: '#ff4d4f', bg: '#fff2f0', text: '#a8071a' },
      }
      const c = colors[p.type] || colors.info
      const titleHtml = p.title ? `<p style="margin:0 0 6px;font-size:14px;font-weight:bold;color:${c.text}">${p.title}</p>` : ''
      return `<section style="border-left:4px solid ${c.border};background:${c.bg};padding:12px 16px;margin:16px 0;border-radius:0 6px 6px 0">${titleHtml}<p style="margin:0;font-size:14px;color:${c.text};line-height:1.6">${p.content}</p></section>`
    },
  },
  {
    id: 'qrcode',
    name: '二维码',
    icon: '📱',
    desc: '将 URL 渲染为可扫描的二维码',
    props: [
      { name: 'url', label: 'URL', placeholder: 'https://...', required: true },
      { name: 'text', label: '提示文字', placeholder: '如"扫码访问"' },
      { name: 'size', label: '尺寸(px)', placeholder: '150' },
    ],
    render(p) {
      const size = p.size || 150
      return `<section style="text-align:center;margin:20px auto;padding:16px 0"><img src="https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(p.url)}" alt="QR" style="width:${size}px;height:${size}px;display:block;margin:0 auto;border-radius:4px"><p style="text-align:center;font-size:14px;color:#999;margin-top:8px">${p.text || '扫码访问'}</p></section>`
    },
  },
  {
    id: 'author',
    name: '作者信息',
    icon: '👤',
    desc: '展示作者头像、名称和简介',
    props: [
      { name: 'name', label: '名称', placeholder: '作者名', required: true },
      { name: 'avatar', label: '头像URL', placeholder: 'https://...' },
      { name: 'bio', label: '简介', placeholder: '一句话介绍', type: 'textarea' },
    ],
    render(p) {
      return `<section style="display:flex;align-items:center;gap:12px;padding:16px 0;margin:16px 0"><img src="${p.avatar || 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 56 56%22><rect fill=%22%23e0e0e0%22 width=%2256%22 height=%2256%22 rx=%2228%22/></svg>'}" alt="${p.name}" style="width:56px;height:56px;border-radius:50%;object-fit:cover"><div><p style="margin:0 0 4px;font-size:15px;font-weight:bold">${p.name}</p><p style="margin:0;font-size:13px;color:#999;line-height:1.5">${p.bio || ''}</p></div></section>`
    },
  },
  {
    id: 'badge',
    name: '标签组',
    icon: '🏷️',
    desc: '展示一组彩色标签',
    props: [
      { name: 'tags', label: '标签', placeholder: '用逗号分隔，如 Vue,TypeScript,Vite', required: true },
      { name: 'color', label: '颜色', placeholder: '#07c160' },
    ],
    render(p) {
      const tags = (p.tags || '').split(/[,，]/).map(t => t.trim()).filter(Boolean)
      const color = p.color || '#07c160'
      const badges = tags.map(t => `<span style="display:inline-block;padding:3px 10px;border-radius:12px;font-size:13px;font-weight:500;background:${color}1a;color:${color};border:1px solid ${color}40;margin:2px">${t}</span>`).join('')
      return `<section style="display:flex;flex-wrap:wrap;gap:6px;margin:12px 0">${badges}</section>`
    },
  },
  {
    id: 'infogrid',
    name: '信息网格',
    icon: '📊',
    desc: '多列展示键值对信息',
    props: [
      { name: 'items', label: '数据', placeholder: 'label1:value1, label2:value2 (每行一对)', required: true, type: 'textarea' },
      { name: 'cols', label: '列数', placeholder: '2' },
    ],
    render(p) {
      const lines = (p.items || '').split('\n').filter(Boolean)
      const items = lines.map(line => {
        const idx = line.indexOf(':')
        return idx >= 0 ? { label: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() } : { label: line.trim(), value: '' }
      })
      if (!items.length) return ''
      const cols = Math.min(Math.max(Number(p.cols) || 2, 1), 3)
      let html = `<section style="margin:16px 0;border:1px solid #eee;border-radius:8px;overflow:hidden">`
      for (let r = 0; r < items.length; r += cols) {
        html += `<section style="display:flex">`
        for (let c = 0; c < cols; c++) {
          const item = items[r + c]
          html += `<div style="flex:1;padding:10px 14px;border-right:${c < cols - 1 ? '1px solid #eee' : 'none'};border-bottom:${r + cols < items.length ? '1px solid #eee' : 'none'}">`
          if (item) html += `<p style="margin:0 0 2px;font-size:11px;color:#999;text-transform:uppercase">${item.label}</p><p style="margin:0;font-size:14px;font-weight:500">${item.value}</p>`
          html += `</div>`
        }
        html += `</section>`
      }
      html += `</section>`
      return html
    },
  },
  {
    id: 'card',
    name: '卡片',
    icon: '🃏',
    desc: '带标题、图片、描述的内容卡片',
    props: [
      { name: 'title', label: '标题', placeholder: '卡片标题', required: true },
      { name: 'image', label: '图片URL', placeholder: 'https://...' },
      { name: 'desc', label: '描述', placeholder: '卡片描述文字', type: 'textarea' },
      { name: 'url', label: '链接', placeholder: '点击跳转的 URL' },
    ],
    render(p) {
      const imgHtml = p.image ? `<img src="${p.image}" alt="${p.title}" style="width:100%;max-height:200px;object-fit:cover;border-radius:8px 8px 0 0">` : ''
      const titleTag = p.url ? `<a href="${p.url}" style="color:inherit;text-decoration:none">${p.title}</a>` : p.title
      return `<section style="border:1px solid #e5e5e5;border-radius:8px;overflow:hidden;margin:16px 0;box-shadow:0 2px 8px rgba(0,0,0,0.06)">${imgHtml}<section style="padding:14px 16px"><p style="margin:0 0 6px;font-size:16px;font-weight:600">${titleTag}</p><p style="margin:0;font-size:14px;color:#666;line-height:1.6">${p.desc || ''}</p></section></section>`
    },
  },
  {
    id: 'mpcard',
    name: '公众号名片',
    icon: '📢',
    desc: '展示微信公众号名片',
    props: [
      { name: 'nickname', label: '公众号名称', placeholder: '如 Doocs', required: true },
      { name: 'mpId', label: '公众号ID', placeholder: '原始ID', required: true },
      { name: 'headimg', label: '头像URL', placeholder: 'https://...' },
      { name: 'signature', label: '简介', placeholder: '如 GitHub 开源组织' },
    ],
    render(p) {
      return `<section style="border:1px solid #e5e5e5;border-radius:8px;padding:16px;margin:16px 0;display:flex;align-items:center;gap:14px"><img src="${p.headimg || 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 56 56%22><rect fill=%22%2307c160%22 width=%2256%22 height=%2256%22 rx=%2228%22/></svg>'}" alt="${p.nickname}" style="width:56px;height:56px;border-radius:50%;object-fit:cover"><div><p style="margin:0 0 4px;font-size:15px;font-weight:bold">${p.nickname}</p><p style="margin:0;font-size:13px;color:#999;line-height:1.5">${p.signature || ''}</p></div></section>`
    },
  },
]

const selectedId = ref(null)
const selected = computed(() => components.find(c => c.id === selectedId.value))
const formData = ref({})
const previewHtml = computed(() => {
  if (!selected.value) return ''
  try {
    return selected.value.render({ ...formData.value })
  } catch { return '' }
})

const canInsert = computed(() => {
  if (!selected.value) return false
  return selected.value.props.filter(p => p.required).every(p => formData.value[p.name])
})

function selectComponent(comp) {
  selectedId.value = comp.id
  formData.value = {}
  for (const p of comp.props) {
    formData.value[p.name] = p.default || ''
  }
}

function doInsert() {
  if (!canInsert.value) return
  emit('insert', previewHtml.value)
  visible.value = false
  selectedId.value = null
  formData.value = {}
}

watch(visible, (v) => {
  if (!v) { selectedId.value = null; formData.value = {} }
})
</script>

<style scoped>
.component-tabs {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.comp-card {
  text-align: center;
  padding: 12px 8px;
  border: 2px solid #e5e5e5;
  border-radius: 8px;
  cursor: pointer;
  transition: all .15s;
}

.comp-card:hover { border-color: #6366f1; }
.comp-card.active { border-color: #6366f1; background: #f0f0ff; }

.comp-icon { font-size: 28px; margin-bottom: 4px; }
.comp-label { font-size: 12px; font-weight: 500; color: #666; }

.comp-preview {
  margin-top: 12px;
  padding: 10px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px dashed #ddd;
  max-height: 200px;
  overflow-y: auto;
}
</style>
