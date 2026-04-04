<script setup>
import { computed, ref, watch } from 'vue'
import { dashboardApi } from '../lib/api'
import { PIPELINE_COLUMNS, countsFromPipeline, groupPipeline, normalizePipelineStage, stageMeta } from '../lib/pipeline'

const props = defineProps({
  pipelineItems: { type: Array, default: () => [] },
  activeAccount: { type: Object, default: () => ({}) },
  selectedPipelineId: { type: String, default: '' },
})
const emit = defineEmits(['select', 'run-pipeline', 'run-selected', 'refresh'])

const items = computed(() => props.pipelineItems || [])
const grouped = computed(() => groupPipeline(items.value))
const visibleColumns = computed(() => PIPELINE_COLUMNS.filter((item) => item.key !== '发布中' || (grouped.value['发布中'] || []).length))
const counts = computed(() => countsFromPipeline(items.value))
const selected = computed(() => items.value.find((item) => item.record_id === props.selectedPipelineId) || items.value[0] || null)

const actionBusy = ref(false)
const errorMessage = ref('')
const infoMessage = ref('')
const flowRemark = ref('')

const previewOpen = ref(false)
const previewLoading = ref(false)
const previewError = ref('')
const previewItem = ref(null)

function accountName() {
  return props.activeAccount?.name || props.activeAccount?.id || '当前账户'
}

function displayModel(item) {
  return item.model || props.activeAccount?.pipeline_model || 'auto'
}

function displayRole() {
  return props.activeAccount?.pipeline_role || 'tech_expert'
}

function stageKey(item) {
  return normalizePipelineStage(item?.status)
}

function openLabel(item) {
  if (item.rewritten_doc) return '打开改后文档'
  if (item.source_doc_url) return '打开原文文档'
  return '打开原文入口'
}

function targetUrl(item) {
  const candidate = item.rewritten_doc || item.source_doc_url || item.url || ''
  return /^https?:\/\//.test(String(candidate || '').trim()) ? candidate : ''
}

function previewSource(item) {
  const candidate = item.rewritten_doc || item.source_doc_url || ''
  return /^https?:\/\//.test(String(candidate || '').trim()) ? candidate : ''
}

function flowOptions(item) {
  const stage = stageKey(item)
  const optionsByStage = {
    待重写: [
      { status: '重写中', label: '标记重写中', tone: 'warn' },
      { status: '待审核', label: '直接送审', tone: 'ghost' },
      { status: '失败异常', label: '标记失败', tone: 'danger' },
    ],
    重写中: [
      { status: '待审核', label: '改为待审核', tone: 'primary' },
      { status: '失败异常', label: '标记失败', tone: 'danger' },
    ],
    待审核: [
      { status: '待发布', label: '审核通过', tone: 'primary' },
      { status: '待重写', label: '退回待改写', tone: 'warn' },
      { status: '失败异常', label: '标记失败', tone: 'danger' },
    ],
    待发布: [
      { status: '发布中', label: '进入发布中', tone: 'warn' },
      { status: '已发布', label: '标记已发布', tone: 'primary' },
      { status: '失败异常', label: '标记失败', tone: 'danger' },
    ],
    发布中: [
      { status: '已发布', label: '发布成功', tone: 'primary' },
      { status: '失败异常', label: '发布失败', tone: 'danger' },
    ],
    已发布: [
      { status: '待发布', label: '回退待发布', tone: 'ghost' },
    ],
    失败异常: [
      { status: '待重写', label: '回退待改写', tone: 'warn' },
      { status: '待审核', label: '回退待审核', tone: 'ghost' },
    ],
  }
  return optionsByStage[stage] || []
}

async function updateSelectedStatus(nextStatus) {
  if (!selected.value || !props.activeAccount?.id || !nextStatus) return
  actionBusy.value = true
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    await dashboardApi.pipelineUpdateStatus({
      account_id: props.activeAccount.id,
      record_id: selected.value.record_id,
      status: nextStatus,
      remark: String(flowRemark.value || '').trim(),
      clear_remark: !String(flowRemark.value || '').trim(),
    })
    infoMessage.value = `状态已更新为：${nextStatus}`
    flowRemark.value = ''
    emit('refresh')
  } catch (err) {
    errorMessage.value = err?.message || '状态更新失败'
  } finally {
    actionBusy.value = false
  }
}

async function openPreview(item) {
  if (!item?.record_id || !props.activeAccount?.id) return
  previewOpen.value = true
  previewLoading.value = true
  previewError.value = ''
  previewItem.value = null
  try {
    const data = await dashboardApi.pipelinePreview({
      accountId: props.activeAccount.id,
      recordId: item.record_id,
    })
    previewItem.value = data.item || null
  } catch (err) {
    previewError.value = err?.message || '预览加载失败'
  } finally {
    previewLoading.value = false
  }
}

watch(
  selected,
  () => {
    flowRemark.value = ''
    errorMessage.value = ''
    infoMessage.value = ''
  }
)
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>写作管理链</h1>
        <p>后续所有写作类页面都按这套 Vue 看板标准继续开发，先把结构、语义和组件边界立住。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" @click="emit('run-pipeline')">+ 批量运行</button>
        <button class="primary-btn" :disabled="!selected" @click="emit('run-selected', selected)">重跑当前任务</button>
      </div>
    </div>
    <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
    <div v-if="infoMessage" class="global-info">{{ infoMessage }}</div>

    <div class="pipeline-shell">
      <div class="pipeline-board panel-card panel-soft">
        <div class="pipeline-columns">
          <section
            v-for="column in visibleColumns"
            :key="column.key"
            class="pipeline-lane"
            :class="`tone-${stageMeta(column.key).tone}`"
          >
            <header class="lane-head">
              <div class="lane-title-wrap">
                <span class="lane-icon">{{ stageMeta(column.key).icon }}</span>
                <div>
                  <h3>{{ column.label }}</h3>
                  <p>{{ stageMeta(column.key).note }}</p>
                </div>
              </div>
              <span class="lane-count">{{ (grouped[column.key] || []).length }}</span>
            </header>

            <div class="lane-list">
              <article
                v-for="item in grouped[column.key] || []"
                :key="item.record_id"
                class="task-card"
                :class="{ active: selected?.record_id === item.record_id }"
                @click="emit('select', item.record_id)"
                @keydown.enter="emit('select', item.record_id)"
                tabindex="0"
              >
                <strong class="task-title">{{ item.title || '未命名标题' }}</strong>
                <div class="task-chip-row">
                  <span class="task-chip">🏷️ {{ accountName() }}</span>
                  <span class="task-chip">🤖 {{ displayModel(item) }}</span>
                  <span class="task-chip">🧠 {{ displayRole() }}</span>
                </div>
                <div class="task-meta">📄 {{ item.rewritten_doc ? '已生成改后文档' : '暂未生成改后文档' }}</div>
                <div class="task-meta">⚠️ {{ item.remark || '当前无明显阻塞' }}</div>
                <div class="task-meta">🕒 {{ item.updated_at || item.record_id || '-' }}</div>
                <div class="task-card-actions">
                  <a v-if="targetUrl(item)" class="task-link" :href="targetUrl(item)" target="_blank" rel="noreferrer" @click.stop>
                    ↗ {{ openLabel(item) }}
                  </a>
                  <button
                    v-if="stageKey(item) === '待审核' || previewSource(item)"
                    class="soft-btn task-mini-btn"
                    @click.stop="openPreview(item)"
                  >
                    查看内容
                  </button>
                </div>
              </article>
              <div v-if="!(grouped[column.key] || []).length" class="empty-block">暂无记录</div>
            </div>
          </section>
        </div>
      </div>

      <aside class="pipeline-side">
        <div class="panel-card">
          <h3>吞吐量</h3>
          <div class="side-stat-big">{{ counts.total }}</div>
          <p class="panel-tip">当前账户写作链任务总量</p>
          <div class="side-metrics">
            <div><span>待改写</span><strong>{{ counts.waitingRewrite }}</strong></div>
            <div><span>待发布</span><strong>{{ counts.waitingPublish }}</strong></div>
            <div><span>已发布</span><strong>{{ counts.published }}</strong></div>
            <div><span>失败率</span><strong>{{ counts.total ? Math.round((counts.failed / counts.total) * 100) : 0 }}%</strong></div>
          </div>
        </div>

        <div class="panel-card" v-if="selected">
          <h3>链路详情</h3>
          <div class="detail-badge">{{ normalizePipelineStage(selected.status) }}</div>
          <h4 class="detail-title">{{ selected.title || '未命名标题' }}</h4>
          <div class="detail-meta-list">
            <div><span>账户</span><strong>{{ accountName() }}</strong></div>
            <div><span>模型</span><strong>{{ displayModel(selected) }}</strong></div>
            <div><span>角色</span><strong>{{ displayRole() }}</strong></div>
            <div><span>记录 ID</span><strong>{{ selected.record_id }}</strong></div>
          </div>
          <div class="detail-note">
            <strong>下一步建议：</strong>{{ stageMeta(normalizePipelineStage(selected.status)).note }}。<br />
            <strong>当前备注：</strong>{{ selected.remark || '暂无失败备注，当前链路可继续推进。' }}
          </div>
          <div class="detail-actions">
            <a v-if="selected.url" class="ghost-btn inline-btn" :href="selected.url" target="_blank" rel="noreferrer">打开原文入口</a>
            <a v-if="selected.source_doc_url" class="ghost-btn inline-btn" :href="selected.source_doc_url" target="_blank" rel="noreferrer">打开原文文档</a>
            <a v-if="selected.rewritten_doc" class="ghost-btn inline-btn" :href="selected.rewritten_doc" target="_blank" rel="noreferrer">打开改后文档</a>
            <button class="soft-btn inline-btn" :disabled="actionBusy" @click="openPreview(selected)">查看内容预览</button>
            <button class="primary-btn" @click="emit('run-selected', selected)">重跑当前任务</button>
          </div>

          <label class="flow-remark-label">
            流转备注（可选）
            <textarea v-model="flowRemark" placeholder="例如：已人工审核通过，进入待发布"></textarea>
          </label>
          <div class="flow-actions">
            <button
              v-for="opt in flowOptions(selected)"
              :key="`${selected.record_id}-${opt.status}`"
              :class="opt.tone === 'danger' ? 'danger-btn' : opt.tone === 'warn' ? 'warn-btn' : opt.tone === 'primary' ? 'primary-btn' : 'ghost-btn'"
              :disabled="actionBusy"
              @click="updateSelectedStatus(opt.status)"
            >
              {{ actionBusy ? '处理中...' : opt.label }}
            </button>
          </div>
        </div>
        <div v-else class="panel-card empty-block">当前还没有可展示的写作链记录。</div>
      </aside>
    </div>

    <div v-if="previewOpen" class="modal-mask" @click.self="previewOpen = false">
      <div class="modal-card">
        <h3>内容预览</h3>
        <p v-if="previewLoading" class="panel-tip">正在读取飞书文档内容...</p>
        <div v-else-if="previewError" class="global-error">{{ previewError }}</div>
        <template v-else-if="previewItem">
          <div class="kv-list">
            <div><span>标题</span><strong>{{ previewItem.title || '-' }}</strong></div>
            <div><span>状态</span><strong>{{ previewItem.status || '-' }}</strong></div>
            <div><span>文档入口</span><strong>{{ previewItem.preview_source || '-' }}</strong></div>
          </div>
          <div class="log-panel preview-content-panel">
            <pre>{{ previewItem.preview_content || '当前文档暂无可读正文（可能是空文档或权限不足）。' }}</pre>
          </div>
        </template>
        <div class="detail-actions">
          <a
            v-if="previewItem?.preview_source"
            class="ghost-btn inline-btn"
            :href="previewItem.preview_source"
            target="_blank"
            rel="noreferrer"
          >
            打开飞书文档
          </a>
          <button class="primary-btn inline-btn" @click="previewOpen = false">关闭预览</button>
        </div>
      </div>
    </div>
  </section>
</template>
