# AutoPlatform 前端

基于 Vue 3 + Vite + Element Plus 的管理后台。

## 开发环境

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

开发服务器运行在 http://localhost:5173，会自动代理 API 请求到 http://127.0.0.1:8701。

## 生产构建

```bash
# 构建生产版本
npm run build
```

构建输出到 `../app/static/dist/` 目录，Flask 会自动提供这些静态文件。

## 功能模块

- **Dashboard** - 概览统计
- **Accounts** - 账户管理
- **Articles** - 文章管理
- **Rewrite** - AI 改写（支持风格选择 + 灵感多选）
- **Inspirations** - 灵感库
- **Styles** - 改写风格管理（8种预设 + 自定义）
- **Pipeline** - 流水线任务
