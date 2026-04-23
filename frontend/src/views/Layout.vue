<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <el-icon :size="28" color="#4f46e5"><Cpu /></el-icon>
        <span>公众号自动发布系统</span>
      </div>
      
      <el-menu
        :default-active="$route.path"
        router
        class="nav-menu"
        background-color="transparent"
        text-color="#64748b"
        active-text-color="#4f46e5"
      >
        <el-menu-item v-for="route in menuRoutes" :key="route.path" :index="'/' + route.path">
          <el-icon>
            <component :is="iconMap[route.meta.icon]" />
          </el-icon>
          <span>{{ route.meta.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header class="header">
        <h2>{{ $route.meta.title }}</h2>
        <div class="header-actions">
          <el-select
            v-model="selectedAccountModel"
            placeholder="选择账户"
            size="small"
            class="account-switcher"
          >
            <el-option label="全部账户" value="" />
            <el-option
              v-for="acc in accountStore.accounts"
              :key="acc.account_id"
              :label="`${acc.name} (${acc.account_id})`"
              :value="acc.account_id"
            />
          </el-select>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Cpu, HomeFilled, UserFilled, Document, MagicStick,
  Collection, BrushFilled, List
} from '@element-plus/icons-vue'
import { useAccountStore, useAppStore } from '../stores'

const route = useRoute()
const accountStore = useAccountStore()
const appStore = useAppStore()

const iconMap = {
  Cpu, HomeFilled, UserFilled, Document, MagicStick,
  Collection, BrushFilled, List
}

const menuRoutes = computed(() => {
  return route.matched[0]?.children || []
})

const selectedAccountModel = computed({
  get: () => appStore.selectedAccountId,
  set: (value) => appStore.setSelectedAccount(value)
})

onMounted(async () => {
  const accounts = await accountStore.fetchAccounts()
  if (!accounts.length) {
    appStore.setSelectedAccount('')
    return
  }

  // 当前选择不存在时，回退到“全部账户”
  if (appStore.selectedAccountId && !accounts.some(acc => acc.account_id === appStore.selectedAccountId)) {
    appStore.setSelectedAccount('')
  }
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background: #fff;
  border-right: 1px solid #e2e8f0;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  border-bottom: 1px solid #e2e8f0;
}

.logo span {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.nav-menu {
  border-right: none;
  padding: 16px 12px;
}

.nav-menu :deep(.el-menu-item) {
  border-radius: 8px;
  margin-bottom: 4px;
}

.nav-menu :deep(.el-menu-item.is-active) {
  background: #eef2ff;
}

.header {
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.account-switcher {
  width: 260px;
}

.main-content {
  background: #f1f5f9;
  padding: 24px;
  overflow-y: auto;
}
</style>
