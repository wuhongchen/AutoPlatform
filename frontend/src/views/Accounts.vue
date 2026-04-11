<template>
  <div class="accounts-page">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span>账户列表</span>
        </div>
      </template>

      <el-table :data="accountStore.accounts" v-loading="loading" stripe>
        <el-table-column label="账户名称" prop="name" min-width="150" />
        <el-table-column label="账户ID" prop="account_id" min-width="150" />
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              :type="appStore.selectedAccountId === row.account_id ? 'default' : 'primary'"
              @click="switchAccount(row.account_id)"
            >
              切换到此账户
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAccountStore, useAppStore } from '../stores'

const accountStore = useAccountStore()
const appStore = useAppStore()
const loading = ref(false)

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

function switchAccount(accountId) {
  appStore.setSelectedAccount(accountId)
  ElMessage.success(`已切换到账户：${accountId}`)
}

onMounted(() => {
  loadData()
})
</script>
