<template>
  <div class="ai-settings-page">
    <div class="page-header">
      <div>
        <h2>AI 模型设置</h2>
        <p class="page-desc">管理 AI 模型配置，在线切换当前使用的模型</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>添加模型
      </el-button>
    </div>

    <!-- 当前默认提示 -->
    <div v-if="defaultConfig" class="default-banner">
      <el-icon><CircleCheck /></el-icon>
      当前默认模型：<strong>{{ defaultConfig.name }}</strong>（{{ defaultConfig.model }}）
    </div>

    <!-- 模型卡片列表 -->
    <div class="config-grid">
      <div
        v-for="config in configs"
        :key="config.id"
        class="config-card"
        :class="{ 'is-default': config.is_default }"
      >
        <div class="card-top">
          <div class="card-provider">
            <span class="provider-badge" :class="'provider-' + config.provider">
              {{ providerLabel(config.provider) }}
            </span>
            <el-tag v-if="config.is_default" type="primary" size="small" effect="dark">默认</el-tag>
            <el-tag v-if="!config.is_active" type="info" size="small">已禁用</el-tag>
          </div>
          <div class="card-name">{{ config.name }}</div>
          <div class="card-model">{{ config.model }}</div>
          <div class="card-endpoint">{{ config.endpoint }}</div>
        </div>

        <div class="card-actions">
          <el-button
            v-if="!config.is_default && config.is_active"
            size="small"
            type="primary"
            @click="setDefault(config.id)"
          >
            设为默认
          </el-button>
          <el-tag v-if="config.is_default" type="primary" effect="dark" size="small" class="default-badge">
            <el-icon><CircleCheck /></el-icon> 当前默认
          </el-tag>
          <el-button size="small" @click="openEditDialog(config)">编辑</el-button>
          <el-button size="small" @click="testConfig(config.id)" :loading="testingId === config.id">
            测试
          </el-button>
          <el-button size="small" type="danger" plain @click="handleDelete(config)">
            删除
          </el-button>
        </div>

        <!-- 测试结果 -->
        <div v-if="testResults[config.id]" class="test-result" :class="testResults[config.id].success ? 'success' : 'fail'">
          <template v-if="testResults[config.id].success">
            ✅ 连接成功 · {{ testResults[config.id].latency_ms }}ms
          </template>
          <template v-else>
            ❌ {{ testResults[config.id].error }}
          </template>
        </div>
      </div>
    </div>

    <el-empty v-if="!loading && configs.length === 0" description="暂无 AI 模型配置" />

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑模型配置' : '添加模型配置'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="配置 ID" prop="id" v-if="!isEdit">
          <el-input v-model="form.id" placeholder="如 deepseek-chat" />
          <span class="form-tip">唯一标识，创建后不可修改</span>
        </el-form-item>

        <el-form-item label="显示名称" prop="name">
          <el-input v-model="form.name" placeholder="如 DeepSeek V3" />
        </el-form-item>

        <el-form-item label="提供商" prop="provider">
          <el-select v-model="form.provider" style="width: 100%">
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="火山引擎 (Volcengine)" value="volcengine" />
            <el-option label="OpenAI" value="openai" />
            <el-option label="其他 (兼容 OpenAI)" value="custom" />
          </el-select>
        </el-form-item>

        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="sk-xxx" />
        </el-form-item>

        <el-form-item label="API 端点" prop="endpoint">
          <el-input v-model="form.endpoint" placeholder="https://api.deepseek.com/v1" />
        </el-form-item>

        <el-form-item label="模型 ID" prop="model">
          <el-input v-model="form.model" placeholder="deepseek-chat" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="超时(秒)">
              <el-input-number v-model="form.timeout" :min="30" :max="600" :step="30" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Plus } from '@element-plus/icons-vue'
import api from '../api'

const loading = ref(false)
const configs = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const testingId = ref(null)
const testResults = reactive({})
const formRef = ref(null)

const defaultConfig = computed(() => configs.value.find(c => c.is_default && c.is_active))

const form = ref({
  id: '',
  name: '',
  provider: 'deepseek',
  api_key: '',
  endpoint: 'https://api.deepseek.com/v1',
  model: 'deepseek-chat',
  is_active: true,
  timeout: 240,
})

const rules = {
  id: [{ required: true, message: '请输入配置 ID', trigger: 'blur' }],
  name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择提供商', trigger: 'change' }],
  api_key: [{ required: true, message: '请输入 API Key', trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入 API 端点', trigger: 'blur' }],
  model: [{ required: true, message: '请输入模型 ID', trigger: 'blur' }],
}

const PROVIDER_LABELS = {
  deepseek: 'DeepSeek',
  volcengine: '火山引擎',
  openai: 'OpenAI',
  custom: '自定义',
}

function providerLabel(provider) {
  return PROVIDER_LABELS[provider] || provider
}

async function loadConfigs() {
  loading.value = true
  try {
    configs.value = await api.aiConfigs.list()
  } catch (e) {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  isEdit.value = false
  form.value = {
    id: '',
    name: '',
    provider: 'deepseek',
    api_key: '',
    endpoint: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat',
    is_active: true,
    timeout: 240,
  }
  dialogVisible.value = true
}

function openEditDialog(config) {
  isEdit.value = true
  form.value = { ...config }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (isEdit.value) {
      await api.aiConfigs.update(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.aiConfigs.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadConfigs()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function setDefault(id) {
  try {
    await api.aiConfigs.setDefault(id)
    ElMessage.success('已设为默认模型')
    loadConfigs()
  } catch (e) {
    ElMessage.error(e.message || '设置失败')
  }
}

async function testConfig(id) {
  testingId.value = id
  delete testResults[id]
  try {
    const result = await api.aiConfigs.test(id)
    testResults[id] = result
  } catch (e) {
    testResults[id] = { success: false, error: e.message }
  } finally {
    testingId.value = null
  }
}

async function handleDelete(config) {
  try {
    await ElMessageBox.confirm(`确定删除「${config.name}」？`, '确认删除', { type: 'warning' })
    await api.aiConfigs.delete(config.id)
    ElMessage.success('已删除')
    loadConfigs()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.message || '删除失败')
  }
}

onMounted(loadConfigs)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.page-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}
.page-desc {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.default-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  margin-bottom: 20px;
  background: var(--accent-light);
  border: 1px solid #c7d2fe;
  border-radius: var(--radius);
  color: var(--accent);
  font-size: 14px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.config-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.config-card:hover {
  border-color: var(--accent);
  box-shadow: var(--shadow);
}
.config-card.is-default {
  border-color: var(--accent);
  background: linear-gradient(135deg, var(--accent-light) 0%, #fff 100%);
}

.card-provider {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.provider-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.provider-deepseek { background: #e8f4f8; color: #0d7377; }
.provider-volcengine { background: #fef3c7; color: #92400e; }
.provider-openai { background: #d1fae5; color: #065f46; }
.provider-custom { background: #e2e8f0; color: #475569; }

.card-name {
  font-size: 17px;
  font-weight: 650;
  color: var(--text-primary);
}
.card-model {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
  font-family: monospace;
}
.card-endpoint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border-light);
}

.default-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.test-result {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: var(--radius);
  font-size: 13px;
}
.test-result.success {
  background: var(--success-light);
  color: var(--success);
}
.test-result.fail {
  background: var(--danger-light);
  color: var(--danger);
}

.form-tip {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}
</style>
