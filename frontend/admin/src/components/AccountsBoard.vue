<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { dashboardApi } from '../lib/api'

const props = defineProps({
  accounts: { type: Array, default: () => [] },
  activeAccountId: { type: String, default: '' },
})
const emit = defineEmits(['refresh'])

const selectedId = ref('')
const busy = ref(false)
const isDraft = ref(false)
const message = ref('')
const errorMessage = ref('')

const form = reactive({
  id: '',
  name: '',
  enabled: true,
  wechat_appid: '',
  wechat_secret: '',
  wechat_author: '',
  feishu_app_id: '',
  feishu_app_secret: '',
  feishu_app_token: '',
  feishu_admin_user_id: '',
  feishu_inspiration_table: '',
  feishu_pipeline_table: '',
  feishu_publish_log_table: '',
  pipeline_role: 'tech_expert',
  pipeline_model: 'auto',
  pipeline_batch_size: 3,
  content_direction: '',
  prompt_direction: '',
  wechat_prompt_direction: '',
  wechat_demo_cli: '',
  wechat_workspace: '',
  wechat_state_dir: '',
  wechat_runtime_cwd: '',
  wechat_default_mp_id: '',
  created_at: '',
  updated_at: '',
  last_run_at: '',
})

const currentAccount = computed(() => props.accounts.find((it) => it.id === selectedId.value) || null)

function setInfo(text) {
  message.value = text || ''
  errorMessage.value = ''
}

function setError(err) {
  errorMessage.value = err?.message || String(err || '操作失败')
}

function fillForm(account) {
  const src = account || {}
  form.id = src.id || ''
  form.name = src.name || ''
  form.enabled = src.enabled !== false
  form.wechat_appid = src.wechat_appid || ''
  form.wechat_secret = src.wechat_secret || ''
  form.wechat_author = src.wechat_author || ''
  form.feishu_app_id = src.feishu_app_id || ''
  form.feishu_app_secret = src.feishu_app_secret || ''
  form.feishu_app_token = src.feishu_app_token || ''
  form.feishu_admin_user_id = src.feishu_admin_user_id || ''
  form.feishu_inspiration_table = src.feishu_inspiration_table || ''
  form.feishu_pipeline_table = src.feishu_pipeline_table || ''
  form.feishu_publish_log_table = src.feishu_publish_log_table || ''
  form.pipeline_role = src.pipeline_role || 'tech_expert'
  form.pipeline_model = src.pipeline_model || 'auto'
  form.pipeline_batch_size = Number(src.pipeline_batch_size || 3)
  form.content_direction = src.content_direction || ''
  form.prompt_direction = src.prompt_direction || ''
  form.wechat_prompt_direction = src.wechat_prompt_direction || ''
  form.wechat_demo_cli = src.wechat_demo_cli || ''
  form.wechat_workspace = src.wechat_workspace || ''
  form.wechat_state_dir = src.wechat_state_dir || ''
  form.wechat_runtime_cwd = src.wechat_runtime_cwd || ''
  form.wechat_default_mp_id = src.wechat_default_mp_id || ''
  form.created_at = src.created_at || ''
  form.updated_at = src.updated_at || ''
  form.last_run_at = src.last_run_at || ''
}

function toPayload() {
  return {
    id: String(form.id || '').trim(),
    name: String(form.name || '').trim(),
    enabled: !!form.enabled,
    wechat_appid: String(form.wechat_appid || '').trim(),
    wechat_secret: String(form.wechat_secret || '').trim(),
    wechat_author: String(form.wechat_author || '').trim(),
    feishu_app_id: String(form.feishu_app_id || '').trim(),
    feishu_app_secret: String(form.feishu_app_secret || '').trim(),
    feishu_app_token: String(form.feishu_app_token || '').trim(),
    feishu_admin_user_id: String(form.feishu_admin_user_id || '').trim(),
    feishu_inspiration_table: String(form.feishu_inspiration_table || '').trim(),
    feishu_pipeline_table: String(form.feishu_pipeline_table || '').trim(),
    feishu_publish_log_table: String(form.feishu_publish_log_table || '').trim(),
    pipeline_role: String(form.pipeline_role || 'tech_expert').trim() || 'tech_expert',
    pipeline_model: String(form.pipeline_model || 'auto').trim() || 'auto',
    pipeline_batch_size: Number(form.pipeline_batch_size || 3),
    content_direction: String(form.content_direction || '').trim(),
    prompt_direction: String(form.prompt_direction || '').trim(),
    wechat_prompt_direction: String(form.wechat_prompt_direction || '').trim(),
    wechat_demo_cli: String(form.wechat_demo_cli || '').trim(),
    wechat_workspace: String(form.wechat_workspace || '').trim(),
    wechat_state_dir: String(form.wechat_state_dir || '').trim(),
    wechat_runtime_cwd: String(form.wechat_runtime_cwd || '').trim(),
    wechat_default_mp_id: String(form.wechat_default_mp_id || '').trim(),
  }
}

async function withBusy(fn) {
  busy.value = true
  errorMessage.value = ''
  try {
    await fn()
  } catch (err) {
    setError(err)
  } finally {
    busy.value = false
  }
}

async function saveAccount() {
  const payload = toPayload()
  if (!payload.id) {
    setError(new Error('账户 ID 不能为空'))
    return
  }
  if (!payload.name) {
    payload.name = payload.id
  }

  await withBusy(async () => {
    await dashboardApi.upsertAccount(payload)
    selectedId.value = payload.id
    isDraft.value = false
    setInfo(`账户已保存：${payload.name}`)
    emit('refresh')
  })
}

function newDraft() {
  const randomId = Math.random().toString(16).slice(2, 10)
  fillForm({
    id: randomId,
    name: '新账户',
    enabled: true,
    wechat_author: 'W 小龙虾',
    pipeline_role: 'tech_expert',
    pipeline_model: 'auto',
    pipeline_batch_size: 3,
  })
  isDraft.value = true
  selectedId.value = ''
  setInfo('已创建账户草稿，请补全参数后保存。')
}

async function activateCurrent() {
  const targetId = String(form.id || '').trim()
  if (!targetId) {
    setError(new Error('请先保存账户，再执行激活。'))
    return
  }
  await withBusy(async () => {
    await dashboardApi.activateAccount(targetId)
    selectedId.value = targetId
    isDraft.value = false
    setInfo(`已切换激活账户：${targetId}`)
    emit('refresh')
  })
}

async function toggleEnabled() {
  form.enabled = !form.enabled
  await saveAccount()
}

async function deleteCurrent() {
  const targetId = String(currentAccount.value?.id || '').trim()
  if (!targetId) {
    setError(new Error('请先选择已存在账户。'))
    return
  }
  if (!confirm(`确认删除账户 ${targetId} 吗？`)) return

  await withBusy(async () => {
    await dashboardApi.deleteAccount(targetId)
    setInfo(`账户已删除：${targetId}`)
    selectedId.value = ''
    emit('refresh')
  })
}

function resetCurrent() {
  if (isDraft.value) {
    newDraft()
    return
  }
  fillForm(currentAccount.value || {})
  setInfo('已重置为当前账户保存值。')
}

watch(
  () => [props.accounts, props.activeAccountId],
  () => {
    if (isDraft.value) return
    const ids = (props.accounts || []).map((it) => it.id)
    if (!selectedId.value || !ids.includes(selectedId.value)) {
      selectedId.value = props.activeAccountId || ids[0] || ''
    }
    fillForm((props.accounts || []).find((it) => it.id === selectedId.value) || {})
  },
  { deep: true, immediate: true }
)

watch(selectedId, () => {
  if (!selectedId.value) return
  isDraft.value = false
  fillForm((props.accounts || []).find((it) => it.id === selectedId.value) || {})
})
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>账户号</h1>
        <p>多账户隔离管理公众号参数、飞书参数、模型参数与微信采集工作目录。</p>
      </div>
      <div class="page-actions">
        <button class="ghost-btn" :disabled="busy" @click="newDraft">创建账户</button>
        <button class="ghost-btn" :disabled="busy" @click="resetCurrent">重置表单</button>
        <button class="soft-btn" :disabled="busy" @click="activateCurrent">启用为当前账户</button>
        <button class="warn-btn" :disabled="busy" @click="toggleEnabled">{{ form.enabled ? '关闭' : '启用' }}</button>
        <button class="danger-btn" :disabled="busy" @click="deleteCurrent">清理</button>
        <button class="primary-btn" :disabled="busy" @click="saveAccount">保存账户</button>
      </div>
    </div>

    <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
    <div v-if="message" class="global-info">{{ message }}</div>

    <div class="accounts-grid">
      <div class="panel-card">
        <h3>账户目录 <span v-if="isDraft" class="badge warn">草稿中</span></h3>
        <div class="account-card-list">
          <button
            v-for="item in accounts"
            :key="item.id"
            class="account-card"
            :class="{ active: selectedId === item.id }"
            @click="selectedId = item.id"
          >
            <div class="account-card-head">
              <strong>{{ item.name }}</strong>
              <span class="badge" :class="item.enabled === false ? 'bad' : 'ok'">
                {{ item.enabled === false ? '已关闭' : '已启用' }}
              </span>
            </div>
            <div class="account-card-meta">ID: {{ item.id }}</div>
            <div class="account-card-meta">默认模型: {{ item.pipeline_model || 'auto' }}</div>
            <div class="account-card-meta">最近运行: {{ item.last_run_at || '-' }}</div>
          </button>
          <div v-if="!accounts.length" class="empty-block">暂无账户，请先创建。</div>
        </div>
      </div>

      <div class="panel-card">
        <h3>账户配置</h3>
        <div class="form-grid-2">
          <label>账户名称<input v-model="form.name" type="text" /></label>
          <label>账户 ID<input v-model="form.id" type="text" /></label>
          <label>启用状态
            <select v-model="form.enabled">
              <option :value="true">1 / 启用</option>
              <option :value="false">0 / 禁用</option>
            </select>
          </label>
          <label>最近运行时间<input :value="form.last_run_at || '-'" type="text" readonly /></label>
          <label>创建时间<input :value="form.created_at || '-'" type="text" readonly /></label>
          <label>更新时间<input :value="form.updated_at || '-'" type="text" readonly /></label>
        </div>

        <h4 class="section-title">微信公众号</h4>
        <div class="form-grid-3">
          <label>公众号 AppID<input v-model="form.wechat_appid" type="text" /></label>
          <label>公众号 AppSecret<input v-model="form.wechat_secret" type="text" /></label>
          <label>默认作者<input v-model="form.wechat_author" type="text" /></label>
        </div>

        <h4 class="section-title">飞书配置</h4>
        <div class="form-grid-2">
          <label>飞书应用 ID<input v-model="form.feishu_app_id" type="text" /></label>
          <label>飞书应用密钥<input v-model="form.feishu_app_secret" type="text" /></label>
          <label>飞书多维表格 Token<input v-model="form.feishu_app_token" type="text" /></label>
          <label>飞书管理员用户 ID<input v-model="form.feishu_admin_user_id" type="text" /></label>
        </div>

        <h4 class="section-title">业务表</h4>
        <div class="form-grid-3">
          <label>灵感库表名<input v-model="form.feishu_inspiration_table" type="text" /></label>
          <label>流水线表名<input v-model="form.feishu_pipeline_table" type="text" /></label>
          <label>发布日志表名<input v-model="form.feishu_publish_log_table" type="text" /></label>
        </div>

        <h4 class="section-title">管线默认</h4>
        <div class="form-grid-3">
          <label>默认角色<input v-model="form.pipeline_role" type="text" /></label>
          <label>默认模型<input v-model="form.pipeline_model" type="text" /></label>
          <label>批处理数量<input v-model.number="form.pipeline_batch_size" type="number" min="1" /></label>
        </div>

        <h4 class="section-title">方向提示</h4>
        <div class="form-grid-1">
          <label>内容方向提示<textarea v-model="form.content_direction" rows="2"></textarea></label>
          <label>通用改写提示方向<textarea v-model="form.prompt_direction" rows="2"></textarea></label>
          <label>公众号成稿提示方向<textarea v-model="form.wechat_prompt_direction" rows="2"></textarea></label>
        </div>

        <h4 class="section-title">微信采集隔离</h4>
        <div class="form-grid-2">
          <label>采集 CLI 路径（可选）<input v-model="form.wechat_demo_cli" type="text" placeholder="可选：账户专用 wechat_demo_cli.py 路径" /></label>
          <label>默认公众号 ID<input v-model="form.wechat_default_mp_id" type="text" /></label>
          <label>采集工作目录<input v-model="form.wechat_workspace" type="text" placeholder="默认 output/wechat_accounts/<id>" /></label>
          <label>状态目录<input v-model="form.wechat_state_dir" type="text" /></label>
          <label>运行目录<input v-model="form.wechat_runtime_cwd" type="text" /></label>
        </div>
      </div>
    </div>
  </section>
</template>
