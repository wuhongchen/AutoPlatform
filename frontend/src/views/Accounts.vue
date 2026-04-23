<template>
  <div class="accounts-page">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span>账户列表</span>
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>新建账户
          </el-button>
        </div>
      </template>

      <el-table :data="accountStore.accounts" v-loading="loading" stripe>
        <el-table-column label="账户名称" prop="name" min-width="140" />
        <el-table-column label="账户ID" prop="account_id" min-width="140" />
        <el-table-column label="当前使用" width="120">
          <template #default="{ row }">
            <el-tag v-if="appStore.selectedAccountId === row.account_id" type="success" size="small">
              当前账户
            </el-tag>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="默认风格" width="150">
          <template #default="{ row }">
            {{ row.pipeline_role }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button
                v-if="appStore.selectedAccountId !== row.account_id"
                size="small"
                type="primary"
                @click="switchAccount(row.account_id)"
              >
                切换
              </el-button>
              <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑账户' : '新建账户'"
      width="500px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="账户名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：主账号" />
        </el-form-item>
        <el-form-item label="账户ID" prop="account_id" v-if="!isEdit">
          <el-input v-model="form.account_id" placeholder="唯一标识，例如：main" />
        </el-form-item>
        <el-form-item label="微信AppID">
          <el-input v-model="form.wechat_appid" placeholder="可选" />
        </el-form-item>
        <el-form-item label="微信密钥">
          <el-input v-model="form.wechat_secret" type="password" placeholder="可选" show-password />
        </el-form-item>
        <el-form-item label="默认改写风格">
          <el-select v-model="form.pipeline_role" placeholder="选择默认风格" style="width: 100%">
            <el-option label="科技专家" value="tech_expert" />
            <el-option label="商业分析师" value="business_analyst" />
            <el-option label="故事讲述者" value="storyteller" />
            <el-option label="科普作家" value="popular_science" />
            <el-option label="观点领袖" value="opinion_leader" />
            <el-option label="趋势观察者" value="trend_observer" />
            <el-option label="实战派" value="practitioner" />
            <el-option label="娱乐向" value="entertainment" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAccountStore, useAppStore } from '../stores'
import api from '../api'

const accountStore = useAccountStore()
const appStore = useAppStore()
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = ref({
  name: '',
  account_id: '',
  wechat_appid: '',
  wechat_secret: '',
  pipeline_role: 'tech_expert'
})

const rules = {
  name: [{ required: true, message: '请输入账户名称', trigger: 'blur' }],
  account_id: [{ required: true, message: '请输入账户ID', trigger: 'blur' }]
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

async function loadData() {
  loading.value = true
  await accountStore.fetchAccounts().finally(() => {
    loading.value = false
  })
}

function openCreateDialog() {
  isEdit.value = false
  form.value = {
    name: '',
    account_id: '',
    wechat_appid: '',
    wechat_secret: '',
    pipeline_role: 'tech_expert'
  }
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  form.value = {
    name: row.name,
    account_id: row.account_id,
    wechat_appid: row.wechat_appid || '',
    wechat_secret: row.wechat_secret || '',
    pipeline_role: row.pipeline_role || 'tech_expert'
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
      await api.accounts.update(form.value.account_id, {
        name: form.value.name,
        wechat_appid: form.value.wechat_appid,
        wechat_secret: form.value.wechat_secret,
        pipeline_role: form.value.pipeline_role
      })
      ElMessage.success('更新成功')
    } else {
      await api.accounts.create({
        name: form.value.name,
        account_id: form.value.account_id,
        wechat_appid: form.value.wechat_appid,
        wechat_secret: form.value.wechat_secret,
        pipeline_role: form.value.pipeline_role
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除账户 "${row.name}" 吗？此操作不可恢复。`,
      '确认删除',
      { type: 'warning' }
    )
    await api.accounts.delete(row.account_id)
    // 如果删除的是当前选中账户，重置
    if (appStore.selectedAccountId === row.account_id) {
      appStore.setSelectedAccount('')
    }
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

function switchAccount(accountId) {
  appStore.setSelectedAccount(accountId)
  ElMessage.success(`已切换到账户：${accountId}`)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.text-gray-400 {
  color: #94a3b8;
}
</style>
