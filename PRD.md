# AutoPlatform 产品需求文档（PRD）

> 文档版本：v3.2  
> 更新日期：2026-04-23  
> 文档状态：执行版（与代码对齐）  
> 适用范围：AutoPlatform 单机部署（Flask + Vue + SQLite）

---

## 1. 项目定位

### 1.1 一句话定位
AutoPlatform 是一个面向公众号运营的多账户内容后台，目标是把"灵感采集 -> AI 改写 -> 模板排版 -> 微信草稿发布"统一到一个可追踪流程中。

### 1.2 目标用户
1. 个人运营者：需要稳定日更，无法承受高运营成本。
2. 小型内容团队：运营多个账号，要求账户隔离与快速切换。
3. 运营负责人：关注进度、失败原因与可回放能力。

### 1.3 当前版本目标
1. 保证账户维度一致：统计、列表、改写参考、流水线触发必须同口径。
2. 保证主链路稳定：采集、采纳、改写、发布全链路可执行。
3. 明确 AI 改写场景：输入可控、输出可验收、失败可恢复。

---

## 2. 全量功能审计（代码对齐）

### 2.1 后台页面能力（Vue）

| 页面 | 路由 | 状态 | 说明 |
|------|------|------|------|
| 概览 | `/dashboard` | 已实现 | 统计卡片（文章/灵感/待处理）、快捷入口 |
| 账户 | `/accounts` | 部分实现 | 列表+切换 ✅；创建/编辑/删除 ❌（API 已具备） |
| 文章 | `/articles` | 已实现 | 状态筛选、改写跳转、发布（带模板选择） |
| 改写 | `/rewrite` | 已实现 | 风格选择、灵感多选（最多 5 条）、额外指令、改写模式切换（manual/auto/none）、发布 |
| 灵感 | `/inspirations` | 已实现 | URL 采集、待决策采纳、详情查看、关键词搜索 |
| 风格 | `/styles` | 已实现 | 内置/自定义风格管理（增删改、启停） |
| 流水线 | `/pipeline` | 部分实现 | 配置面板（style/template/batch）+ 触发运行 ✅；任务列表/进度 ❌ |
| 404 | - | 未实现 | 缺少兜底页面和路由守卫 |

### 2.2 后端 API 能力（Flask）

| 接口 | 状态 | 说明 |
|------|------|------|
| `GET /api/health` | 已实现 | 健康检查 |
| `GET/POST /api/accounts` | 已实现 | 账户列表/创建 |
| `GET/PUT/DELETE /api/accounts/{id}` | 已实现 | 账户详情/更新/删除 |
| `GET /api/accounts/{id}/stats` | 已实现 | 单账户统计 |
| `GET /api/stats` | 已实现 | 统一统计（支持 account_id 可选） |
| `POST /api/inspirations` | 已实现 | 采集灵感（异步 AI 评分） |
| `GET /api/inspirations` | 已实现 | 灵感列表（支持 account_id 过滤） |
| `GET /api/inspirations/{id}` | 已实现 | 灵感详情 |
| `POST /api/inspirations/{id}/approve` | 已实现 | 采纳灵感并创建文章 |
| `GET /api/articles` | 已实现 | 文章列表（支持 account_id + status 过滤） |
| `GET /api/articles/{id}` | 已实现 | 文章详情 |
| `POST /api/articles/{id}/rewrite` | 已实现 | AI 改写（支持 style/use_references/instructions/inspiration_ids） |
| `POST /api/articles/{id}/publish` | 已实现 | 发布到微信草稿（支持 template） |
| `GET/POST /api/styles` | 已实现 | 风格预设列表/创建 |
| `GET/PUT/DELETE /api/styles/{id}` | 已实现 | 风格详情/更新/删除 |
| `POST /api/styles/{id}/toggle` | 已实现 | 启用/禁用风格 |
| `GET /api/templates` | 已实现 | 模板列表 |
| `POST /api/templates/{name}/preview` | 已实现 | 模板预览 |
| `POST /api/pipeline/process` | 已实现 | 流水线批处理（支持 account_id/batch_size/style/template） |
| `/admin` | 已实现 | 兼容重定向到 `/` |

### 2.3 CLI 与脚本能力

| 能力 | 状态 | 说明 |
|------|------|------|
| CLI 全功能 | 已实现 | 账户/采集/改写/发布/模板/流水线/统计 |
| `run.sh` | 已实现 | backend/frontend/dev/build/test/smoke/install/clean/start |
| `Makefile` | 已实现 | 调用 run.sh 的快捷命令 |
| `main.py` | 已实现 | 统一入口：server/dev/cli |

---

## 3. 真实能力边界

### 3.1 已完成（可对外承诺）

1. **多账户上下文与全局切换** — Layout 账户选择器 + localStorage 持久化 + 自动回退到"全部账户"。
2. **灵感采集 -> 采纳建文 -> 改写 -> 发布主链路** — 全链路可执行，单条失败可追踪。
3. **AI 改写场景完整覆盖** — 手动参考 / 自动参考 / 无参考 / 定制指令，均真实生效。
4. **风格系统** — 8 种内置 + 自定义风格管理，支持启用/禁用。
5. **模板系统** — 4 种模板渲染与预览，微信草稿使用 HTML 片段渲染。
6. **统一日志** — API/AI/Manager/Collector 四层结构化日志，含耗时与 token 统计。
7. **AI 调用聚合** — 单一 `_call_llm()` 入口，支持 token 消耗追踪与异常记录。
8. **e2e 测试 + smoke 测试** — 关键链路自动化回归。

### 3.2 未完成（必须如实记录）

1. **流水线任务记录未写入** — `pipeline_records` 表存在，但 `process_pipeline()` 未创建/更新记录，仅通过 logger 记录。
2. **统计返回动态字典** — `GET /api/stats` 按数据库当前值动态聚合，缺固定 schema，缺失状态不返回。
3. **账户前端缺 CRUD** — 账户页只有列表+切换，创建/编辑/删除需通过 CLI 或 API 直接调用。
4. **风格使用次数未回写** — `increment_preset_usage()` 存在但未在改写成功后调用。
5. **改写模式未回写 metadata** — `rewrite_mode` 未写入文章 metadata。
6. **前端缺 404 页面和路由守卫** — 非法路由直接白屏。

---

## 4. AI 改写能力

### 4.1 改写目标
1. 输出可发布 HTML。
2. 支持风格可控、参考可控、指令可控。
3. 失败可回滚到可重试状态。

### 4.2 场景矩阵

| 场景 | 触发 | 状态 | 说明 |
|------|------|------|------|
| R1 手动参考改写 | 改写页勾选 1-5 条灵感 | 已实现 | 按指定 inspiration_ids 组装参考 |
| R2 自动参考改写 | 改写页选择"自动参考"模式 | 已实现 | 系统按相似度阈值筛出前 3 条灵感 |
| R3 无参考快速改写 | 改写页选择"无参考"模式 | 已实现 | 仅基于原文改写 |
| R4 定制指令改写 | 额外指令输入框非空 | 已实现 | instructions 真实注入系统提示词 |
| R5 失败恢复改写 | AI 超时/报错/网络错误 | 已实现 | 状态置 failed，写 error_message，可重试 |
| R6 流水线批改 | Pipeline 页触发 | 已实现 | 支持 style/template 参数，单条失败不阻塞 |

### 4.3 API 契约

`POST /api/articles/{article_id}/rewrite`

请求体：
```json
{
  "style": "tech_expert",
  "use_references": true,
  "inspiration_ids": ["insp_1", "insp_2"],
  "instructions": "增加数据对比，结尾给3条行动建议"
}
```

响应体关键字段：
```json
{
  "id": "article_xxx",
  "status": "rewritten",
  "rewrite_style": "tech_expert",
  "rewrite_references": ["参考标题A", "参考标题B"],
  "custom_instructions": "增加数据对比...",
  "metadata": {
    "used_inspiration_ids": ["insp_1", "insp_2"],
    "reference_count": 2
  },
  "rewritten_html": "<h2>...</h2>"
}
```

---

## 5. 已知问题与解决方案

| 问题 | 影响 | 方案 | 优先级 |
|------|------|------|--------|
| 流水线任务记录未写入 | 无法追踪批次处理过程 | process_pipeline 中创建/更新 PipelineRecord | P1 |
| 统计非固定 schema | 前端展示不稳定 | 后端返回固定字段，缺失状态填 0 | P1 |
| 账户前端缺 CRUD | 必须通过 CLI 管理账户 | 重写 Accounts.vue | P1 |
| 风格使用次数未回写 | 无法统计风格热度 | rewrite 成功后调用 increment_preset_usage | P2 |
| 前端缺 404/守卫 | 非法路由白屏 | 新增 NotFound.vue + router guard | P2 |

---

## 6. 功能优先级

### P0（必须保持）
1. 多账户切换与按账户筛选稳定（持续回归）。
2. AI 改写主链路稳定：instructions 生效 + rewrite_mode 明确 + 失败可恢复。
3. 日志可观测：关键动作可追踪、失败可诊断。

### P1（应该补齐）
1. 流水线任务记录与可视化。
2. 统计固定 schema 与状态映射。
3. 账户前端 CRUD 补齐。

### P2（可以延后）
1. 风格使用次数回写与推荐。
2. 改写质量评分与 A/B 结果对比。
3. 多平台发布扩展。

---

## 7. 验收标准

### 7.1 关键场景验收
1. 手动参考改写：选 2 条灵感，输出 `reference_count=2`。
2. 自动参考改写：不选灵感但选 auto，有可用参考时 `reference_count>=1`。
3. 无参考改写：选 none，输出 `reference_count=0`。
4. 指令改写：输入指令，结果应体现指令约束。
5. 改写失败：状态 `failed`，错误信息可见，重试可恢复。
6. 发布失败：缺微信配置时返回明确错误。

### 7.2 API 契约检查
1. `GET /api/stats` 支持 `account_id` 可选。
2. `GET /api/articles`、`GET /api/inspirations` 支持按账号过滤。
3. `POST /api/articles/{id}/rewrite` 支持 `instructions` 并真实生效。
4. 错误响应统一包含 `error` 字段。

### 7.3 自动化测试
1. `make smoke` 覆盖关键链路回归。
2. e2e 覆盖：账户/灵感/改写/发布全流程。

---

## 8. 非功能需求

### 8.1 性能
1. `GET /api/health` P95 < 100ms。
2. `GET /api/stats` P95 < 300ms。
3. 列表接口 100 条记录 P95 < 1s。

### 8.2 可靠性
1. 状态迁移必须可追踪（时间 + 错误）。
2. 外部依赖失败不吞错。
3. 批处理单条失败不阻塞全局。

### 8.3 安全
1. 密钥不入库不入仓库（仅 .env）。
2. 默认本机监听 127.0.0.1。
3. 错误信息可诊断但不泄露敏感信息。

### 8.4 可观测
1. 关键动作日志包含 account_id/entity_id/status/error。
2. AI 调用记录 model/token/duration/task_name。
3. 可查看最近失败样本。

---

## 9. 里程碑建议

### M1（已完成）
1. 修复 instructions 注入链路（C1）。
2. 新增 rewrite_mode 三态切换（C2）。
3. 统一日志系统。
4. AI 调用聚合。

### M2（当前）
1. 补齐账户前端 CRUD。
2. 统计固定 schema。
3. 流水线任务记录写入。

### M3（后续）
1. 风格使用统计回写。
2. 流水线页面任务列表。
3. 改写质量自动评分。

---

## 10. 出入范围

### 本 PRD 覆盖
1. 当前代码已实现的能力与边界。
2. AI 改写能力的可执行场景。
3. 近期迭代优先级与验收标准。

### 本 PRD 暂不覆盖
1. 多用户权限体系。
2. 云端分布式部署。
3. 非微信平台发布与商业化计费。
