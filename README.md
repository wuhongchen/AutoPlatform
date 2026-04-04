# OpenClaw AutoPlatform

基于 OpenClaw 技能理论开发的全自动信息发布与收集平台。

## 核心特性与工作流

1. **双擎架构 (灵感库 + 流水线)**：
   - **内容灵感库 (`manager_inspiration.py`)**: 自动监控并抓取待选文章（支持微信公众号、飞书文档），利用 AI 评估爆款潜力并打分，提取核心视角。
   - **智能内容流水线 (`manager.py pipeline`)**: 以飞书《小龙虾智能内容库》为核心中枢，流转已审核素材，执行长文改写、配图生成及发布全链路自动编排。
2. **AI 清洗与结构重塑**：
   - 自动提取文本结构并转化为优美的 HTML 富文本格式发往微信草稿箱（专属优化 H1/H2 等标题层级与内联样式）。
   - 发布前统一走 `huasheng_editor` 的默认公众号风格（`wechat-default`）进行排版入稿。
   - **智能 OCR 过滤**：AI 上下文语义识别，精准备份原文关键配图，并自动剔除“扫码关注”、“二维码”等相关营销引流图片与话术。
3. **健壮的容错机制**：
   - 处理微信公众平台图文保存时由于多图引发的 `access_token` 过期断连，实现底层主动侦探和无感续排获取 Token。
   - 确保飞书文档的多源形式自动适配转换，URL 绝对纯净萃取。
4. **一键配图封面**：支持“方舟生图 + 即梦回退”双路线生成 16:9 封面，并自动上传至公众号媒体库。

## 快速开始

首次进入项目，建议先看两份引导：
1. `.env` 配置引导：`docs/ENV_SETUP_GUIDE.md`
2. 测试引导：`docs/TESTING_GUIDE.md`

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

在当前目录或 `mp-draft-push` 目录下的 `.env` 文件中配置以下密钥：

微信公众号参数获取入口：`https://developers.weixin.qq.com/platform`

获取与填写步骤（2 分钟）：
1. 打开上面的微信开放平台链接并登录公众号主体账号。
2. 在平台控制台找到公众号应用的 `AppID` 和 `AppSecret`。
3. 回到项目 `.env`，填入 `WECHAT_APPID` 与 `WECHAT_SECRET` 后保存。

也可以直接从模板生成：
```bash
cp .env.example .env
python3 scripts/internal/check_env.py
```

```bash
# 微信公众号 (必须)
WECHAT_APPID=...
WECHAT_SECRET=...

# AI 改写 (可选，用于自动改稿)
LLM_API_KEY=...
LLM_ENDPOINT=...

# 阿里百炼 (OpenAI 兼容)
BAILIAN_API_KEY=...
BAILIAN_ENDPOINT=https://coding.dashscope.aliyuncs.com/v1

# 智谱
ZHIPU_API_KEY=...
ZHIPU_ENDPOINT=https://open.bigmodel.cn/api/paas/v4

# Kimi
KIMI_API_KEY=...
KIMI_ENDPOINT=https://api.moonshot.cn/v1

# MiniMax
MINIMAX_API_KEY=...
MINIMAX_ENDPOINT=https://api.minimax.chat/v1

# 流水线默认改写模型（飞书表内“改写模型”字段优先级更高）
OPENCLAW_PIPELINE_MODEL=kimi-k2.5
OPENCLAW_PIPELINE_ROLE=tech_expert
OPENCLAW_PIPELINE_BATCH_SIZE=3
OPENCLAW_CONTENT_DIRECTION=
OPENCLAW_PROMPT_DIRECTION=
OPENCLAW_WECHAT_PROMPT_DIRECTION=

# OpenClaw 调度优化（可选）
OPENCLAW_SCHEMA_CHECK_ENABLED=1
OPENCLAW_SCHEMA_CHECK_INTERVAL_SEC=21600
OPENCLAW_AUTO_INSTALL=1
OPENCLAW_NON_INTERACTIVE=1

# 可选：接入 wechat-demo-cli（公众号登录态抓正文）
# 1) 先在 demo 项目中完成 login，保证 token/cookie 可用
# 2) 填写 demo_cli/wechat_demo_cli.py 的绝对路径
OPENCLAW_WECHAT_DEMO_ENABLED=0
OPENCLAW_WECHAT_DEMO_CLI=
OPENCLAW_WECHAT_DEMO_PYTHON=python3
OPENCLAW_WECHAT_DEMO_TIMEOUT=180
OPENCLAW_WECHAT_ACCOUNTS_ROOT=

# 公号模板广告位（可选）
WECHAT_AD_ENABLED=0
WECHAT_AD_POSITION=bottom
WECHAT_AD_TITLE=推广信息
WECHAT_AD_TEXT=
WECHAT_AD_LINK_TEXT=
WECHAT_AD_LINK_URL=
WECHAT_AD_IMAGE_PATH=
WECHAT_AD_IMAGE_URL=
WECHAT_AD_IMAGE_LINK_URL=

# 火山引擎 (可选，用于自动生成封面图)
VOLCENGINE_AK=...
VOLCENGINE_SK=...

# 封面生图路由（可选）
# auto: 优先方舟，失败回退即梦
# ark: 仅方舟
# jimeng: 仅即梦
COVER_IMAGE_PROVIDER=auto
ARK_IMAGE_API_KEY=...
ARK_IMAGE_ENDPOINT=https://ark.cn-beijing.volces.com/api/v3
ARK_IMAGE_MODEL=doubao-seedream-5-0-260128
# 可选: doubao-seedream-4-5-251128
ARK_IMAGE_SIZE=1280x720
ARK_IMAGE_RESPONSE_FORMAT=b64_json
```

封面生图路由说明：
1. `COVER_IMAGE_PROVIDER=auto`：先走方舟 `images/generations`，失败自动回退即梦。
2. `COVER_IMAGE_PROVIDER=ark`：只使用方舟（未配方舟会直接跳过生图）。
3. `COVER_IMAGE_PROVIDER=jimeng`：只使用即梦 AK/SK 签名接口。

微信公众号 demo 抓取路由说明：
1. 默认使用内置抓取器（无需额外依赖）。
2. 当 `OPENCLAW_WECHAT_DEMO_ENABLED=1` 且 `OPENCLAW_WECHAT_DEMO_CLI` 可用时，微信链接会优先走 `wechat_demo_cli.py fetch-content`。
3. demo 抓取失败会自动回退到内置抓取器，不会中断原流程。
4. 该能力仅影响 `mp.weixin.qq.com` 链接，其他网页抓取逻辑不变。
5. 多账户隔离目录默认在 `output/wechat_accounts/<account_id>/`，也可用 `OPENCLAW_WECHAT_ACCOUNTS_ROOT` 自定义根目录。

### 3. 运行发布

你可以直接使用运营助手脚本：
```bash
./run.sh "https://mp.weixin.qq.com/s/xxx"
```

指定模型运行（第三个参数为 `model_key`）：
```bash
./run.sh "https://mp.weixin.qq.com/s/xxx" tech_expert "qwen3.5-plus"
./run.sh "https://mp.weixin.qq.com/s/xxx" tech_expert "glm-5"
./run.sh "https://mp.weixin.qq.com/s/xxx" tech_expert "kimi-k2.5"
./run.sh "https://mp.weixin.qq.com/s/xxx" tech_expert "MiniMax-M2.5"
```

流水线模式下也可切模型：
1. 设置环境变量 `OPENCLAW_PIPELINE_MODEL`（全局默认）
2. 或在飞书流水线表中填写 `改写模型` 字段（单条记录优先）
3. 默认开启“改写去重”：若记录已存在可读取的 `改后文档链接`，会跳过重复调用模型。
如需强制重改，可设置 `OPENCLAW_FORCE_REWRITE=1`。
4. 可设置 `OPENCLAW_PIPELINE_BATCH_SIZE` 控制单次巡检处理条数（默认 3，适合 OpenClaw 定时触发）。

新版流水线节点（状态机）：
1. `🧲 待改写`
2. `✍️ 改写中`
3. `🧾 待审核`
4. `🚀 待发布`
5. `📤 发布中`
6. `✅ 已发布`
7. `❌ 改写失败 / ❌ 发布失败`

或者手动运行：
```bash
python3 core/manager.py "https://mp.weixin.qq.com/s/xxx" tech_expert "qwen3.5-plus"
```

### 4. 快速操作（与 `SKILL.md` 同步）

1. 环境诊断与表结构初始化
```bash
python3 scripts/internal/diagnose.py
python3 scripts/setup/setup_inspiration_library.py
python3 scripts/setup/setup_content_library.py
```

2. 灵感扫描
```bash
python3 core/manager_inspiration.py
```

3. 流水线单次巡检（推荐给 OpenClaw 调度）
```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 OPENCLAW_PIPELINE_BATCH_SIZE=3 ./run.sh pipeline-once
```

4. 流水线守护模式（仅在你明确需要常驻时）
```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 ./run.sh pipeline
```

5. 单篇即时处理
```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 ./run.sh "<URL>" "tech_expert" "auto"
```

6. 全流程 Demo（首次联调建议先跳过发布）
```bash
python3 scripts/internal/demo_full_flow.py --url "<URL>" --skip-publish
```

7. 单点链路验证（抓取 -> 飞书文档 -> Bitable 附件）
```bash
python3 scripts/internal/single_point_test.py
```

8. 模型与封面生图路由体检
```bash
python3 scripts/internal/check_env.py
```

9. 微信登录态采集 CLI（多账户独立）
```bash
# 查看当前激活账户状态
python3 scripts/wechat_ingest_cli.py status

# 指定账户扫码登录（仅生成二维码并返回）
python3 scripts/wechat_ingest_cli.py --account-id default login --no-wait --qr-display both

# 检索并添加关注号
python3 scripts/wechat_ingest_cli.py --account-id default search-mp "机器之心" --limit 8
python3 scripts/wechat_ingest_cli.py --account-id default add-mp --keyword "机器之心" --pick 1

# 拉取文章并同步到飞书灵感库
python3 scripts/wechat_ingest_cli.py --account-id default pull-articles --mp-id MP_WXS_xxx --pages 1 --mode api
python3 scripts/wechat_ingest_cli.py --account-id default sync-inspiration --mp-id MP_WXS_xxx --limit 20

# 一条命令跑全流程（检索/关注/拉取/入灵感库）
python3 scripts/wechat_ingest_cli.py --account-id default full-flow --keyword "机器之心" --pick 1 --pages 1 --sync-limit 20

# 或使用一键入口脚本
./run_wechat_ingest.sh --account-id default full-flow --keyword "机器之心" --pick 1 --pages 1 --sync-limit 20
```

### 5. 管理后台（新增）

启动后台：
```bash
python3 admin_server.py
```

访问：
`http://127.0.0.1:8701`

补充入口：
1. Vue 标准化前端预览：`http://127.0.0.1:8701/vue`

后台能力：
1. 灵感库扫描触发
2. 流水线单次巡检触发
3. 单篇即时处理
4. 全流程 Demo 触发
5. 定时执行 `pipeline-once`
6. 微信登录态采集动作（扫码登录、检索关注号、拉取文章、同步灵感库、全流程）
7. 公众号排版二级功能（内嵌 `huasheng_editor`，入口：`/tools/huasheng/`）
8. 多账户配置与切换（公众号参数、飞书参数、独立表格、微信采集隔离目录）
9. 账户级提示词方向配置（改写方向 / 公众号方向）
10. 任务日志与状态看板（含账户标识）

详细说明见：
`docs/ADMIN_DASHBOARD.md`

前端标准见：
`docs/FRONTEND_STANDARD.md`

## 目录说明

- `run.sh`: **运营操作入口**，提供交互式界面和环境检查。
- `run_wechat_ingest.sh`: 微信登录态采集的一键入口（支持多账户）。
- `manager.py`: 核心编排器，负责调度各模块。
- `config.py`: 配置管理，自动加载环境变量。
- `docs/`: 存放项目相关方案文档。
- `skills/`: **融合技能库 (Plug-in Skills)**
  - `mp-draft-push/`: 微信公众号高级发布技能。
  - `volcengine-jimeng-image/`: 即梦 AI 生图与视频处理技能。
  - `wechat-auto-publisher/`: 微信自动化运营 JS 工具包。
- `scripts/`:
  - `setup/`: 存放多维表格环境初始化脚本。
  - `utils/`: 存放独立的图片转码与上传验证工具。
  - `wechat_ingest_cli.py`: 微信登录态采集 CLI（扫码/关注/拉取/入灵感库）。
- `modules/`:
  - `collector.py`: 内容抓取模块。
  - `feishu.py`: 飞书 API 封装，包含图片处理核心逻辑。
  - `processor.py`: AI 加工模块（改稿、生图）。
  - `publisher.py`: 公众号发布模块。
- `archive/`: 存放历史测试脚本与实验性代码。
- `output/`: 存放流程中的中间产物。
