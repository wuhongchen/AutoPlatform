<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <el-icon :size="28" color="#4f46e5"><Cpu /></el-icon>
        <span>AutoPlatform</span>
      </div>
      
      <el-menu
        :default-active="$route.path"
        router
        class="nav-menu"
        background-color="transparent"
        text-color="#64748b"
        active-text-color="#4f46e5"
      >
        <el-menu-item v-for="route in menuRoutes" :key="route.path" :index="route.path">
          <el-icon>
            <component :is="route.meta.icon" />
          </el-icon>
          <span>{{ route.meta.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header class="header">
        <h2>{{ $route.meta.title }}</h2>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Cpu } from '@element-plus/icons-vue'

const route = useRoute()

const menuRoutes = computed(() => {
  return route.matched[0]?.children || []
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
}

.header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
}

.main-content {
  background: #f1f5f9;
  padding: 24px;
  overflow-y: auto;
}
</style>
