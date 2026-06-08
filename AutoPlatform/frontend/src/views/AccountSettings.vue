<template>
  <div class="account-settings-page">
    <div class="page-header">
      <div>
        <h2>账号设置</h2>
        <p class="page-desc">管理当前账号的发布和改写配置</p>
      </div>
      <el-tag v-if="currentAccount" type="primary" size="large" effect="dark">{{ currentAccount.name }}</el-tag>
    </div>

    <div v-if="!currentAccount" class="empty-box">
      <el-empty description="请先在顶部选择一个账户" />
    </div>

    <el-card v-else shadow="never" class="settings-card">
      <el-form :model="form" label-width="140px" label-position="left">
        <div class="section-title">基础信息</div>
        <el-form-item label="账户名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="账户 ID">
          <el-input v-model="form.account_id" disabled />
        </el-form-item>
        <el-form-item label="作者名称">
          <el-input v-model="form.wechat_author" placeholder="W 小龙虾" />
        </el-form-item>

        <div class="section-title">微信配置</div>
        <el-form-item label="AppID">
          <el-input v-model="form.wechat_appid" placeholder="wx..." />
        </el-form-item>
        <el-form-item label="AppSecret">
          <el-input v-model="form.wechat_secret" type="password" show-password />
        </el-form-item>

        <div class="section-title">流水线默认</div>
        <el-form-item label="默认改写风格">
          <el-select v-model="form.pipeline_role" style="width: 320px">
            <el-option v-for="s in styleStore.styles" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="批处理数量">
          <el-input-number v-model="form.pipeline_batch_size" :min="1" :max="20" />
        </el-form-item>

        <div class="section-title">内容方向</div>
        <el-form-item label="内容方向">
          <el-input v-model="form.content_direction" placeholder="如 AI产品、出海..." type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="提示词方向">
          <el-input v-model="form.prompt_direction" placeholder="改写提示词偏好..." type="textarea" :rows="2" />
        </el-form-item>

        <div class="form-actions">
          <el-button type="primary" size="large" @click="saveSettings" :loading="saving">
            保存设置
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAccountStore, useAppStore, useStyleStore } from '../stores'
import api from '../api'

const accountStore = useAccountStore()
const appStore = useAppStore()
const styleStore = useStyleStore()

const saving = ref(false)
const form = reactive({
  name: '', account_id: '', wechat_author: '',
  wechat_appid: '', wechat_secret: '',
  pipeline_role: 'tech_expert', pipeline_batch_size: 3,
  content_direction: '', prompt_direction: '',
})

const currentAccount = computed(() =>
  accountStore.accounts.find(a => a.account_id === appStore.selectedAccountId) || null
)

function loadAccount() {
  if (!currentAccount.value) return
  Object.assign(form, { ...currentAccount.value })
}

async function saveSettings() {
  if (!currentAccount.value) return
  saving.value = true
  try {
    await api.accounts.update(currentAccount.value.account_id, { ...form })
    await accountStore.fetchAccounts()
    ElMessage.success('设置已保存')
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await accountStore.fetchAccounts()
  await styleStore.fetchStyles()
  loadAccount()
})
watch(() => appStore.selectedAccountId, loadAccount)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-header h2 { margin: 0; font-size: 22px; font-weight: 700; color: var(--text-primary); }
.page-desc { margin: 6px 0 0; font-size: 14px; color: var(--text-secondary); }

.settings-card { max-width: 720px; }
.settings-card :deep(.el-card__body) { padding: 28px 32px; }

.section-title {
  font-size: 14px; font-weight: 700; color: var(--accent);
  padding: 0 0 10px; margin: 28px 0 16px;
  border-bottom: 1px solid var(--accent-light);
}
.section-title:first-child { margin-top: 0; }

.form-actions { margin-top: 32px; padding-top: 20px; border-top: 1px solid var(--border-light); }

.empty-box { padding: 80px 0; }
</style>
