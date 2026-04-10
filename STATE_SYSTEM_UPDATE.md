# 状态系统更新文档

## 1. 新状态系统设计

### 1.1 状态列表

| 状态 | 说明 | 图标 | 样式 |
|------|------|------|------|
| 待采集 | 刚添加，等待采集 | 📥 | info |
| 采集中 | 正在采集内容 | 📡 | progress |
| 采集失败 | 采集失败可重试 | ❌ | danger |
| 采集完成 | 内容已采集 | 📄 | info |
| 评分中 | AI评分中 | 🧠 | progress |
| 已评分 | 评分完成 | 📊 | info |
| 待改写 | 等待改写 | 📝 | waiting |
| 改写中 | AI改写中 | ✍️ | progress |
| 改写失败 | 改写失败可重试 | ❌ | danger |
| 已改写 | 改写完成 | ✨ | success |
| 待发布 | 等待发布 | 🚀 | waiting |
| 发布中 | 发布中 | 📤 | progress |
| 发布失败 | 发布失败可重试 | ❌ | danger |
| 已发布 | 发布成功 | ✅ | success |
| 已跳过 | 评分低或用户跳过 | ⏭️ | muted |

### 1.2 状态流转

```
待采集 → 采集中 → 采集完成 → 评分中 → 已评分 → 待改写 → 改写中 → 已改写 → 待发布 → 发布中 → 已发布
                                      ↓                              ↓
                                   已跳过(评分<5)              各环节失败(可重试)
```

### 1.3 状态分组

| 分组 | 包含状态 | 用途 |
|------|---------|------|
| pending | 待采集、采集完成、已评分、待改写 | 待处理筛选 |
| processing | 采集中、评分中、改写中、发布中 | 处理中筛选 |
| completed | 已改写、已发布 | 已完成筛选 |
| failed | 采集失败、改写失败、发布失败 | 失败筛选 |
| skipped | 已跳过 | 跳过筛选 |

## 2. 定时巡检功能移除

### 2.1 移除的API

- `GET /api/scheduler` - 获取调度器状态
- `POST /api/scheduler/start` - 启动调度器
- `POST /api/scheduler/stop` - 停止调度器

### 2.2 移除的前端功能

- 顶部工具栏的调度器状态显示
- 调度器开启/关闭按钮
- 定时巡检相关的任务触发

### 2.3 新的工作方式

- **手动触发**: 用户手动点击操作按钮
- **事件驱动**: 操作完成后自动更新状态
- **插件任务**: 通过插件任务表追踪异步操作

## 3. 文章内容存储

### 3.1 新表结构

```sql
-- 文章内容存储表（替代飞书文档）
CREATE TABLE article_contents (
    record_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    original_html TEXT NOT NULL DEFAULT '',
    original_text TEXT NOT NULL DEFAULT '',
    original_json TEXT NOT NULL DEFAULT '{}',
    rewritten_html TEXT NOT NULL DEFAULT '',
    rewritten_text TEXT NOT NULL DEFAULT '',
    rewritten_json TEXT NOT NULL DEFAULT '{}',
    images_json TEXT NOT NULL DEFAULT '[]',
    files_dir TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 3.2 API端点

- `GET /api/articles/:id/content` - 获取文章内容
- `POST /api/articles/:id/content` - 保存文章内容
- `GET /api/articles/:id/render` - 渲染文章为HTML预览

### 3.3 与灵感库的关联

- `inspiration_records.record_id` → `article_contents.record_id`
- 一篇文章对应一条灵感记录和一条内容记录
- 内容分离存储，便于大文本处理

## 4. 插件任务系统

### 4.1 新表结构

```sql
CREATE TABLE plugin_tasks (
    task_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    record_id TEXT NOT NULL,
    plugin_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    params_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error_msg TEXT NOT NULL DEFAULT '',
    started_at TEXT,
    ended_at TEXT,
    created_at TEXT NOT NULL
);
```

### 4.2 API端点

- `GET /api/plugin-tasks` - 获取任务列表
- `GET /api/plugin-tasks/:id` - 获取单个任务

### 4.3 任务状态

- `pending` - 待执行
- `running` - 运行中
- `success` - 成功
- `failed` - 失败

## 5. 概览页面更新

### 5.1 新的数据格式

```javascript
{
  "summary": {
    "total_articles": 94,
    "published": 10,
    "processing": 5,
    "pending": 70,
    "failed": 5,
    "skipped": 4
  },
  "state_groups": {
    "pending": 70,
    "processing": 5,
    "completed": 10,
    "failed": 5,
    "skipped": 4
  },
  "status_breakdown": {
    "待采集": 20,
    "采集完成": 30,
    "已评分": 20,
    ...
  },
  "tasks": {
    "pending": 2,
    "running": 1,
    "success": 50,
    "failed": 3
  }
}
```

### 5.2 新的展示卡片

1. **全部文章** - 总数量 + 已完成数
2. **待处理** - 等待采集/评分/改写
3. **处理中** - 正在进行中
4. **失败/跳过** - 需要关注

## 6. 前端更新

### 6.1 状态筛选器

```vue
<select v-model="statusFilter">
  <option value="all">全部</option>
  <option value="pending">待处理</option>
  <option value="processing">处理中</option>
  <option value="completed">已完成</option>
  <option value="failed">失败</option>
  <option value="skipped">已跳过</option>
</select>
```

### 6.2 状态显示

```vue
<span class="badge" :class="getStateStyle(item.status).badge">
  {{ getStateStyle(item.status).icon }} {{ item.status }}
</span>
```

## 7. 兼容旧数据

### 7.1 状态映射

```javascript
const LEGACY_STATE_MAP = {
  "待分析": "待采集",
  "待审": "已评分",
  "已处理": "已改写",
  "已同步": "已改写",
  "已跳过": "已跳过",
  "抓取失败": "采集失败",
  "处理异常": "采集失败",
  // ... 其他映射
}
```

### 7.2 数据迁移

- 旧状态自动映射为新状态
- `pipeline_records` 表保留但不再使用
- 新数据写入 `article_contents` 和 `plugin_tasks` 表

## 8. API变更汇总

### 8.1 新增API

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/states | 获取所有状态定义 |
| GET | /api/inspiration/:id/actions | 获取可用操作 |
| GET | /api/articles/:id/content | 获取文章内容 |
| POST | /api/articles/:id/content | 保存文章内容 |
| GET | /api/articles/:id/render | 渲染文章 |
| GET | /api/plugin-tasks | 获取插件任务列表 |
| GET | /api/plugin-tasks/:id | 获取单个任务 |

### 8.2 移除API

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/scheduler | 调度器状态 |
| POST | /api/scheduler/start | 启动调度器 |
| POST | /api/scheduler/stop | 停止调度器 |

### 8.3 修改API

| 端点 | 变更 |
|------|------|
| /api/overview | 返回格式更新为新状态系统 |
| /api/inspiration/list | 支持新的状态分组筛选 |

## 9. 实施检查清单

- [x] 创建新的状态管理模块
- [x] 更新数据库Schema
- [x] 移除定时巡检API
- [x] 更新概览API
- [x] 更新前端状态筛选
- [x] 更新前端概览页面
- [x] 移除前端调度器相关代码
- [ ] 实现文章内容存储API
- [ ] 实现插件任务API
- [ ] 测试全流程
