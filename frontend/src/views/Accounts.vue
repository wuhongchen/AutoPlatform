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
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAccountStore } from '../stores'

const accountStore = useAccountStore()
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

onMounted(() => {
  loadData()
})
</script>
