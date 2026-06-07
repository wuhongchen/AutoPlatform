<template>
  <router-view />
</template>

<style>
:root {
  /* === 主色调 === */
  --accent: #6366f1;
  --accent-hover: #4f46e5;
  --accent-light: #eef2ff;
  --accent-gradient: linear-gradient(135deg, #6366f1, #8b5cf6);

  /* === 状态色 === */
  --success: #10b981;
  --success-light: #d1fae5;
  --warning: #f59e0b;
  --warning-light: #fef3c7;
  --danger: #ef4444;
  --danger-light: #fee2e2;
  --info: #3b82f6;

  /* === 背景 === */
  --bg-page: #f1f5f9;
  --bg-card: #ffffff;
  --bg-sidebar: #0f172a;
  --bg-sidebar-hover: rgba(255,255,255,0.06);
  --bg-sidebar-active: rgba(99,102,241,0.15);
  --bg-input: #f8fafc;

  /* === 文字 === */
  --text-primary: #0f172a;
  --text-secondary: #64748b;
  --text-muted: #94a3b8;
  --text-sidebar: rgba(255,255,255,0.65);
  --text-sidebar-active: #ffffff;

  /* === 边框 === */
  --border: #e2e8f0;
  --border-light: #f1f5f9;

  /* === 圆角 === */
  --radius-sm: 6px;
  --radius: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;

  /* === 阴影 === */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.06);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.08);

  /* === 间距 === */
  --gap-xs: 6px;
  --gap-sm: 10px;
  --gap: 16px;
  --gap-lg: 24px;
}

/* === Element Plus 主题覆盖 === */
:root {
  --el-color-primary: var(--accent);
  --el-color-primary-light-3: #a5b4fc;
  --el-color-primary-light-5: #c7d2fe;
  --el-color-primary-light-7: #e0e7ff;
  --el-color-primary-light-9: #eef2ff;
  --el-border-radius-base: var(--radius);
  --el-border-radius-round: var(--radius-lg);
  --el-box-shadow-light: var(--shadow);
  --el-bg-color-overlay: var(--bg-card);
}

.el-card {
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadow-sm) !important;
  transition: box-shadow 0.2s ease;
}
.el-card:hover {
  box-shadow: var(--shadow) !important;
}

.el-button--primary {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
}
.el-button--primary:hover {
  background: var(--accent-hover) !important;
}

.el-menu {
  border-right: none !important;
}

.el-table th.el-table__cell {
  background: #f8fafc !important;
  color: var(--text-secondary) !important;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.el-dialog {
  border-radius: var(--radius-xl) !important;
}

.el-tag {
  border-radius: var(--radius-sm) !important;
}

.el-input__wrapper, .el-textarea__inner, .el-select .el-input__wrapper {
  border-radius: var(--radius) !important;
}

.el-button {
  border-radius: var(--radius) !important;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  background: var(--bg-page);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
