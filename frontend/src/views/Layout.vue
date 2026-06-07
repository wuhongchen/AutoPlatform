<template>
  <el-container class="layout-container">
    <!-- 暗色侧边栏 -->
    <el-aside width="260px" class="sidebar">
      <!-- Logo 区 -->
      <div class="sidebar-brand">
        <div class="brand-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="url(#brand-grad)"/>
            <path d="M7 10h14M7 14h10M7 18h14" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
            <defs>
              <linearGradient id="brand-grad" x1="0" y1="0" x2="28" y2="28">
                <stop stop-color="#6366f1"/><stop offset="1" stop-color="#8b5cf6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div class="brand-text">
          <span class="brand-name">AutoPlatform</span>
          <span class="brand-desc">公众号内容后台</span>
        </div>
      </div>

      <!-- 导航菜单 -->
      <div class="sidebar-nav">
        <router-link
          v-for="route in menuRoutes"
          :key="route.path"
          :to="'/' + route.path"
          class="nav-item"
          :class="{ active: $route.path === '/' + route.path }"
        >
          <el-icon class="nav-icon">
            <component :is="iconMap[route.meta.icon]" />
          </el-icon>
          <span class="nav-label">{{ route.meta.title }}</span>
          <span v-if="$route.path === '/' + route.path" class="nav-dot" />
        </router-link>
      </div>

      <!-- 底部信息 -->
      <div class="sidebar-footer">
        <div class="sidebar-user">
          <el-avatar :size="32" style="background: #6366f1;">AP</el-avatar>
          <div class="user-info">
            <div class="user-name">AutoPlatform</div>
            <div class="user-version">v2.1.0</div>
          </div>
        </div>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-area">
      <!-- 顶部栏 -->
      <el-header class="header">
        <div class="header-left">
          <span class="header-title">{{ $route.meta.title }}</span>
        </div>
        <div class="header-right">
          <el-select
            v-model="selectedAccountModel"
            placeholder="选择账户"
            size="default"
            class="account-switcher"
            :popper-class="'account-dropdown'"
          >
            <el-option
              v-for="acc in accountStore.accounts"
              :key="acc.account_id"
              :label="`${acc.name} (${acc.account_id})`"
              :value="acc.account_id"
            />
          </el-select>
        </div>
      </el-header>

      <!-- 内容 -->
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
  HomeFilled, UserFilled, Document, MagicStick,
  Collection, BrushFilled, List, Link, Cpu, Connection
} from '@element-plus/icons-vue'
import { useAccountStore, useAppStore } from '../stores'

const route = useRoute()
const accountStore = useAccountStore()
const appStore = useAppStore()

const iconMap = {
  HomeFilled, UserFilled, Document, MagicStick,
  Collection, BrushFilled, List, Link, Cpu, Connection
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
  if (!appStore.selectedAccountId || !accounts.some(acc => acc.account_id === appStore.selectedAccountId)) {
    appStore.setSelectedAccount(accounts[0].account_id)
  }
})
</script>

<style scoped>
/* === 整体布局 === */
.layout-container {
  height: 100vh;
}

/* === 侧边栏 === */
.sidebar {
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.brand-icon {
  flex-shrink: 0;
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.brand-name {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.02em;
}

.brand-desc {
  font-size: 11px;
  color: var(--text-sidebar);
  letter-spacing: 0.02em;
}

/* === 导航 === */
.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius);
  color: var(--text-sidebar);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 2px;
  position: relative;
  transition: all 0.15s ease;
}

.nav-item:hover {
  background: var(--bg-sidebar-hover);
  color: #fff;
}

.nav-item.active {
  background: var(--bg-sidebar-active);
  color: var(--text-sidebar-active);
}

.nav-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.nav-label {
  white-space: nowrap;
}

.nav-dot {
  position: absolute;
  right: 12px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
}

/* === 侧边栏底部 === */
.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.user-version {
  font-size: 11px;
  color: var(--text-sidebar);
  margin-top: 1px;
}

/* === 主区域 === */
.main-area {
  background: var(--bg-page);
}

/* === 顶部栏 === */
.header {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  height: 60px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}

.header-title {
  font-size: 17px;
  font-weight: 650;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.account-switcher {
  width: 280px;
}

/* === 内容区 === */
.main-content {
  padding: 24px 28px;
  overflow-y: auto;
  min-height: 0;
}
</style>
