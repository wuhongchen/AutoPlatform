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
const message = ref('')
const errorMessage = ref('')

const form = reactive({
  id: '',
  name: '',
  enabled: true,
  wechat_appid: '',
  wechat_secret: '',
  wechat_author: '',
  created_at: '',
  updated_at: '',
})

const currentAccount = computed(() => props.accounts.find((it) => it.id === selectedId.value) || null)

function setInfo(text) {
  message.value = text || ''
  errorMessage.value = ''
}

function setError(err) {
  if (!err) {
    errorMessage.value = ''
  } else if (typeof err === 'string') {
    errorMessage.value = err
  } else if (err.response && err.response.data && err.response.data.message) {
    errorMessage.value = err.response.data.message
  } else if (err.message !== undefined && err.message !== null) {
    errorMessage.value = err.message
  } else {
    try {
      errorMessage.value = typeof err === 'object' ? JSON.stringify(err) : String(err)
    } catch {
      errorMessage.value = '操作失败'
    }
  }
}

function fillForm(account) {
  const src = account || {}
  form.id = src.id || ''
  form.name = src.name || ''
  form.enabled = src.enabled !== false
  form.wechat_appid = src.wechat_appid || ''
  form.wechat_secret = src.wechat_secret || ''
  form.wechat_author = src.wechat_author || ''
  form.created_at = src.created_at || ''
  form.updated_at = src.updated_at || ''
}

function toPayload() {
  return {
    id: String(form.id || '').trim(),
    name: String(form.name || '').trim(),
    enabled: !!form.enabled,
    wechat_appid: String(form.wechat_appid || '').trim(),
    wechat_secret: String(form.wechat_secret || '').trim(),
    wechat_author: String(form.wechat_author || '').trim(),
  }
}

async function selectAccount(id) {
  selectedId.value = id
  fillForm(currentAccount.value)
  setInfo('')
  setError({ message: '' })
}

function generateId() {
  if (!form.id) {
    form.id = 'acc_' + Math.random().toString(36).slice(2, 10)
  }
}

async function saveAccount() {
  if (!form.name) {
    setError({ message: '请输入账户名称' })
    return
  }
  generateId()
  busy.value = true
  try {
    await dashboardApi.upsertAccount(toPayload())
    setInfo(form.id ? '账户已更新' : '账户已创建')
    emit('refresh')
  } catch (err) {
    setError(err)
  } finally {
    busy.value = false
  }
}

async function activateAccount(id) {
  busy.value = true
  try {
    await dashboardApi.activateAccount(id)
    setInfo('账户已激活')
    emit('refresh')
  } catch (err) {
    setError(err)
  } finally {
    busy.value = false
  }
}

async function deleteAccount(id) {
  if (!confirm(`确定要删除账户 ${id} 吗？此操作不可恢复。`)) return
  busy.value = true
  try {
    await dashboardApi.deleteAccount(id)
    setInfo('账户已删除')
    selectedId.value = ''
    fillForm({})
    emit('refresh')
  } catch (err) {
    setError(err)
  } finally {
    busy.value = false
  }
}

watch(
  () => props.accounts,
  () => {
    if (selectedId.value && !props.accounts.find((a) => a.id === selectedId.value)) {
      selectedId.value = ''
      fillForm({})
    }
  },
  { deep: true }
)
</script>

<template>
  <section class="page-section">
    <div class="page-headline page-headline-row">
      <div>
        <h1>账户管理</h1>
        <p>管理公众号配置。当前使用本地数据库模式，飞书相关配置已移除。</p>
      </div>
    </div>

    <div v-if="errorMessage" class="global-error">{{ errorMessage }}</div>
    <div v-if="message" class="global-info">{{ message }}</div>

    <div class="accounts-layout">
      <div class="panel-card account-list">
        <h3>账户列表</h3>
        <div class="account-items">
          <div
            v-for="acc in accounts"
            :key="acc.id"
            class="account-item"
            :class="{ active: acc.id === activeAccountId, selected: acc.id === selectedId }"
            @click="selectAccount(acc.id)"
          >
            <div class="account-name">
              <span v-if="acc.id === activeAccountId" class="active-badge">当前</span>
              {{ acc.name }}
            </div>
            <div class="account-meta">ID: {{ acc.id }}</div>
          </div>
        </div>
        <button class="primary-btn" style="margin-top: 12px; width: 100%;" @click="selectAccount(''); fillForm({ id: '', name: '', enabled: true, wechat_appid: '', wechat_secret: '', wechat_author: '' })">+ 新建账户</button>
      </div>

      <div class="panel-card account-form">
        <h3>{{ selectedId ? '编辑账户' : '新建账户' }}</h3>
        <div class="ab-form">
          <div class="ab-form-item">
            <label class="ab-label">账户名称 <span class="required">*</span></label>
            <div class="ab-input-group">
              <input class="ab-input" v-model="form.name" placeholder="例如：主账户" />
            </div>
          </div>
          <div class="ab-form-item">
            <label class="ab-label">账户ID</label>
            <div class="ab-input-group">
              <input class="ab-input" v-model="form.id" placeholder="留空自动生成" :disabled="!!selectedId" />
            </div>
          </div>
          <div class="ab-form-item">
            <div class="ab-label"></div>
            <div class="ab-input-group">
              <label class="ab-checkbox-label">
                <input class="ab-checkbox" v-model="form.enabled" type="checkbox" />
                <span>启用此账户</span>
              </label>
            </div>
          </div>
          
          <div class="ab-form-section">
            <h4>微信公众号配置</h4>
            <div class="ab-form-item">
              <label class="ab-label">AppID</label>
              <div class="ab-input-group">
                <input class="ab-input" v-model="form.wechat_appid" placeholder="wx..." />
              </div>
            </div>
            <div class="ab-form-item">
              <label class="ab-label">AppSecret</label>
              <div class="ab-input-group">
                <input class="ab-input" v-model="form.wechat_secret" type="password" placeholder="Secret Key" />
              </div>
            </div>
            <div class="ab-form-item">
              <label class="ab-label">作者名称</label>
              <div class="ab-input-group">
                <input class="ab-input" v-model="form.wechat_author" placeholder="公众号显示的作者名" />
              </div>
            </div>
          </div>

          <div v-if="form.created_at" class="ab-form-item ab-meta-info">
            <div class="ab-label"></div>
            <div class="ab-input-group">
              <div class="ab-meta-text">创建时间: {{ form.created_at }}</div>
              <div class="ab-meta-text">更新时间: {{ form.updated_at }}</div>
            </div>
          </div>
        </div>

        <div class="ab-form-actions">
          <button class="primary-btn" :disabled="busy" @click="saveAccount">{{ busy ? '保存中...' : '保存账户' }}</button>
          <button v-if="selectedId && selectedId !== activeAccountId" class="ghost-btn" :disabled="busy" @click="activateAccount(selectedId)">设为当前账户</button>
          <button v-if="selectedId && accounts.length > 1" class="danger-btn" :disabled="busy" @click="deleteAccount(selectedId)">删除</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.accounts-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
}
.account-list {
  max-height: 600px;
  overflow-y: auto;
}
.account-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.account-item {
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--line);
  cursor: pointer;
  transition: all 0.2s;
}
.account-item:hover {
  background: var(--surface-soft);
}
.account-item.active {
  border-color: var(--success);
  background: rgba(7, 193, 96, 0.05);
}
.account-item.selected {
  border-color: var(--brand);
}
.account-name {
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}
.active-badge {
  background: var(--success);
  color: white;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
}
.account-meta {
  font-size: 12px;
  color: var(--text-soft);
  margin-top: 4px;
}
.ab-form {
  margin-top: 24px;
}
.ab-form-item {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}
.ab-form-item.ab-meta-info {
  align-items: flex-start;
}
.ab-label {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  width: 120px;
  text-align: right;
  padding-right: 16px;
  font-size: 14px;
  color: var(--text);
  font-weight: 500;
  flex-shrink: 0;
  box-sizing: border-box;
}
.ab-label .required {
  color: var(--danger, #ff4d4f);
  margin-left: 4px;
}
.ab-input-group {
  flex: 1;
  max-width: 320px;
}
.ab-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  transition: all 0.2s;
}
.ab-input:focus {
  outline: none;
  border-color: var(--brand);
}
.ab-input[disabled] {
  background: var(--surface-soft);
  color: var(--text-soft);
  cursor: not-allowed;
}
.ab-checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  color: var(--text);
  font-size: 14px;
}
.ab-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
}
.ab-form-section {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px dashed var(--line);
}
.ab-form-section h4 {
  margin: 0 0 20px 24px;
  font-size: 15px;
  color: var(--text);
  font-weight: 600;
}
.ab-meta-text {
  font-size: 12px;
  color: var(--text-soft);
  line-height: 1.6;
}
.ab-form-actions {
  display: flex;
  gap: 12px;
  margin-top: 32px;
  padding-left: 120px;
}
@media (max-width: 768px) {
  .accounts-layout {
    grid-template-columns: 1fr;
  }
  .ab-form-item {
    flex-direction: column;
    align-items: flex-start;
  }
  .ab-label {
    text-align: left;
    width: 100%;
    padding-right: 0;
    margin-bottom: 8px;
  }
  .ab-form-actions {
    padding-left: 0;
  }
  .ab-form-section h4 {
    margin-left: 0;
  }
}
</style>
