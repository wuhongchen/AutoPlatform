# AutoInfo 管理后台

本后台是对现有后端流程的“管理壳层”，不会改动飞书存储模型和文档链接逻辑。

## 1) 启动

```bash
cd /Users/hongchen/Downloads/code/wxz/autoinfo-platform
./run_admin.sh

# 或手动启动
python3 -m pip install -r requirements.txt
python3 admin_server.py
```

默认地址：
`http://127.0.0.1:8701`

补充入口：
1. `http://127.0.0.1:8701/vue`：Vue 标准化前端预览
2. `docs/FRONTEND_STANDARD.md`：后续所有前端设计与开发标准

可选环境变量：
1. `ADMIN_HOST`（默认 `127.0.0.1`）
2. `ADMIN_PORT`（默认 `8701`）
3. `ADMIN_PYTHON_PATH`（默认 `python3`）

## 1.1) 当前后台信息架构（按新版 UI 重构）

1. `概览`：展示当前激活账户的 KPI、账户健康、任务节奏、预警信息。
2. `账户号`：管理多账户基础资料、公众号参数、飞书参数、业务表与提示词方向。
3. `灵感库`：以卡片流方式查看最近灵感记录，并可直接送入写作链。
4. `雷达舱`：公众号关注与抓取子系统入口（扫码状态、关注号、文章拉取与入库）。
5. `公众号排版`：内嵌 `huasheng_editor`，用于 Markdown 到公众号样式排版与复制。
6. `写作管理链`：以看板方式查看待重写、待审核、待发布、已发布与失败节点。
7. `发布日志`：统一查看后台任务与发布动作日志。
8. `追踪中心`：聚合重写失败、发布失败、文档链接失效、字段缺失等异常。
9. `系统基础设置`：包含定时执行、接入说明、设计参考资产。

## 2) 支持的管理动作

1. 灵感库扫描与评估
2. 流水线单次巡检（改写与发布）
3. 单篇文章即时处理（URL + role + model）
4. 全流程 Demo（可选 skip publish）
5. 定时执行（周期触发 `pipeline-once`）
6. 微信登录态采集（扫码登录、关注号检索、文章拉取、同步灵感库、全流程）
7. 公众号排版（`/tools/huasheng/` 内嵌编辑器）
8. 页面已拆分为两个功能区：
   - `运行控制`：流程动作、统计、任务与日志
   - `系统基础设置`：多账户管理、定时执行

## 2.1) 多账户隔离配置（新增）

后台首页顶部新增“多账户管理”，每个账户都可独立配置并激活：
1. 公众号参数：`WECHAT_APPID`、`WECHAT_SECRET`、`WECHAT_AUTHOR`
2. 飞书参数：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_APP_TOKEN`
3. 多维表格：`FEISHU_INSPIRATION_TABLE`、`FEISHU_PIPELINE_TABLE`、`FEISHU_PUBLISH_LOG_TABLE`
4. 流水线默认：`OPENCLAW_PIPELINE_ROLE`、`OPENCLAW_PIPELINE_MODEL`、`OPENCLAW_PIPELINE_BATCH_SIZE`
5. 提示词方向：`OPENCLAW_CONTENT_DIRECTION`、`OPENCLAW_PROMPT_DIRECTION`、`OPENCLAW_WECHAT_PROMPT_DIRECTION`
6. 微信采集配置：`wechat_demo_cli`、`wechat_workspace`、`wechat_state_dir`、`wechat_runtime_cwd`、`wechat_default_mp_id`

执行规则：
1. 所有后台动作默认按“当前激活账户”运行
2. 任务日志会显示账户名，便于排查
3. 当前版本账户配置临时存储在 `output/admin_accounts.json`
4. 产品目标态会迁移到本地数据库统一管理账户、索引、日志与链路追踪
5. 管理后台巡检 agent 已补充页面壳层检查，会验证账户号页的动作栏、目录、表单块和帮助文案是否存在。

### 字段说明（建议同步到后台表单文案）

#### 账户基础信息
1. `账户名称`：运营侧可读名称，例如“主号”“AI 资讯号”“客户 A 号”。
2. `账户 ID`：系统唯一标识，建议使用稳定、可读的英文或短码，不建议使用随机字符串作为长期 ID。
3. `启用状态`：`1` 表示启用，`0` 表示禁用。禁用账户不可触发抓取、改写、发布。
4. `创建时间 / 更新时间 / 最近运行时间`：建议在后台展示为只读字段，用于追踪账户生命周期。

#### 微信公众号参数
1. `WECHAT_APPID`：公众号 AppID。
2. `WECHAT_SECRET`：公众号 AppSecret。
3. `WECHAT_AUTHOR`：草稿默认作者名。它不是鉴权参数，而是文章展示参数。

#### 飞书参数
1. `FEISHU_APP_ID`：飞书开放平台应用 ID。
2. `FEISHU_APP_SECRET`：飞书开放平台应用密钥。
3. `FEISHU_APP_TOKEN`：飞书多维表格 App Token，用于定位这套业务表所在的 Bitable。
4. `FEISHU_ADMIN_USER_ID`：飞书管理员用户 ID，用于文档授权、加协作者等动作。

#### 飞书业务表
1. `FEISHU_INSPIRATION_TABLE`：灵感库表名，存原文、评分、建议方向等。
2. `FEISHU_PIPELINE_TABLE`：流水线表名，存改写、审核、发布状态等。
3. `FEISHU_PUBLISH_LOG_TABLE`：发布记录表名，存最终发稿结果与草稿 ID。

#### 流水线默认参数
1. `OPENCLAW_PIPELINE_MODEL`：默认改写模型。
2. `OPENCLAW_PIPELINE_ROLE`：默认改写角色。
3. `OPENCLAW_PIPELINE_BATCH_SIZE`：每次巡检处理的最大任务数，表示批大小，不表示模型并发。

#### 内容方向参数
1. `OPENCLAW_CONTENT_DIRECTION`：这个账号主要做什么内容。
2. `OPENCLAW_PROMPT_DIRECTION`：通用改写方向，决定文章整体表达风格。
3. `OPENCLAW_WECHAT_PROMPT_DIRECTION`：公众号成稿方向，决定标题感、导语感、段落感和手机端阅读感。

#### 微信采集参数（新增）
1. `wechat_demo_cli`：可选，当前账户独立指定 `wechat_demo_cli.py` 路径。
2. `wechat_workspace`：当前账户微信采集工作目录根路径。
3. `wechat_state_dir`：当前账户关注号/文章缓存状态目录。
4. `wechat_runtime_cwd`：当前账户登录态运行目录（二维码、token、cookie 隔离）。
5. `wechat_default_mp_id`：当前账户默认采集目标公众号 ID。

## 3) 可观测项

1. 灵感库状态统计
2. 流水线状态统计
3. 最近记录列表（灵感库/流水线）
4. 任务队列与实时日志

## 4) 存储边界

1. 内容存储仍在飞书（多维表格 + docx）
2. 后台仅做触发、监控、日志聚合
3. 不修改原有链接字段和文档生成逻辑
## 5) UI 参考图存档

本轮用于重构后台的参考图已保存到项目内：
1. 目录：`assets/ui-references/`
2. 索引说明：`docs/UI_REFERENCES.md`
