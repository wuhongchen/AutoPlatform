---
name: autoinfo-manager
description: OpenClaw 自动化运营总控技能。用于灵感扫描、流水线改写发布、单篇紧急处理；优先使用 pipeline-once 提高调度稳定性与效率。
metadata: {"openclaw":{"emoji":"🚀","requires":{"python":">=3.9"}}}
---

# autoinfo-manager

## 1) 技能用途
本技能用于驱动本仓库的三类任务：
1. 灵感库扫描与评估
2. 内容流水线改写与发布
3. 单篇文章即时处理

当用户出现以下意图时应触发本技能：
1. “启动灵感扫描 / 分析选题 / 看看最近有什么可写”
2. “跑流水线 / 自动发布 / 处理待发布队列”
3. “把这篇文章改写并发布：<URL>”
4. “修复改写失败/发布失败记录”
5. “跑一下全流程 demo / 验证能不能打通”

## 1.1) 固定场景技能包（OpenClaw 对话即执行）
以下 4 个固定场景应被视为“可执行模型”，当用户对话命中触发词时，直接执行对应命令。

### Scenario S1: 灵感库扫描与评估
触发词示例：
1. “扫描灵感库”
2. “分析选题”
3. “看看最近有什么可写”

执行命令：
```bash
python3 core/manager_inspiration.py
```

成功判据：
1. 日志出现灵感记录处理信息
2. 飞书灵感库记录状态发生更新（如 `待审/已跳过/已采用`）

### Scenario S2: 内容流水线改写与发布
触发词示例：
1. “跑流水线”
2. “自动发布待发布队列”
3. “执行一次发布巡检”

执行命令（推荐单次）：
```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 OPENCLAW_PIPELINE_BATCH_SIZE=3 ./run.sh pipeline-once
```

执行命令（持续监听，仅用户明确要求）：
```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 ./run.sh pipeline
```

成功判据：
1. 日志出现改写/发布节点推进
2. 飞书流水线状态推进到 `🧾 待审核/🚀 待发布/✅ 已发布`

### Scenario S3: 单篇文章即时处理
触发词示例：
1. “处理这篇文章：<URL>”
2. “马上改写并发布这条链接”
3. “单篇测试这条公众号”

执行命令：
```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 ./run.sh "<URL>" "tech_expert" "auto"
```

成功判据：
1. 生成改后文档链接（飞书 docx）
2. 发布模式下可获得草稿 ID 或明确失败原因备注

### Scenario S4: 全流程定时执行
触发词示例：
1. “定时跑全流程”
2. “每隔一段时间巡检并发布”
3. “做成无人值守执行”

执行模型：
1. 调度器固定触发 `pipeline-once`（推荐）
2. 每次触发命令如下：
```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 OPENCLAW_PIPELINE_BATCH_SIZE=3 ./run.sh pipeline-once
```

说明：
1. 不推荐默认常驻 `pipeline`，优先由 OpenClaw/外部定时器周期触发 `pipeline-once`
2. 可通过 `OPENCLAW_PIPELINE_BATCH_SIZE` 控制每轮吞吐，避免超时

技能能力描述（补充）：
1. 负责编排“采集 -> 分析 -> 飞书回写 -> 流水线改写 -> 发布”的全链路动作。
2. 支持 OpenClaw 代理与独立模型双模式运行，并可按记录粒度覆盖改写模型。
3. 支持封面生图双路由（方舟优先 + 即梦回退），避免单供应商不可用导致流程中断。
4. 支持失败记录修复、状态回滚重试与关键字段自检，适合无人值守定时调度。

输入/输出约定（给 OpenClaw 调度器）：
1. 典型输入：公众号 URL、动作类型（scan/pipeline/demo）、可选角色和模型 key。
2. 典型输出：飞书灵感记录 ID、流水线记录 ID、改后文档链接、发布草稿 ID/失败原因。
3. 默认成功判据：日志出现 `✅ 新建灵感记录`、`✅ 新建流水线记录`、`✅ 改写完成`（发布模式再加 `✅ 发布完成`）。
4. 默认失败判据：状态进入 `❌ 改写失败/❌ 发布失败`，并回写 `备注` 字段说明异常原因。

关键模块映射（补充）：
1. 流水线总控：`core/manager.py`
2. 灵感扫描总控：`core/manager_inspiration.py`
3. 飞书读写与文档/附件处理：`modules/feishu.py`
4. 改写与生图路由：`modules/processor.py`
5. 公众号正文结构化处理：`modules/mp_processor.py`
6. 专题内容处理器：`modules/mp_content_processor.py`（已替代旧命名 `xhs_processor.py`）

## 2) OpenClaw 调用总原则
1. 默认优先单次巡检：`pipeline-once`，不要默认起常驻进程。
2. 默认非交互调用：设置 `OPENCLAW_NON_INTERACTIVE=1`。
3. 默认关闭重复依赖安装：设置 `OPENCLAW_AUTO_INSTALL=0`（环境已就绪时）。
4. 大队列分批跑：设置 `OPENCLAW_PIPELINE_BATCH_SIZE=3`（可调 1~5）。
5. 除非用户明确要求，不要强制重改写（不要默认设 `OPENCLAW_FORCE_REWRITE=1`）。

## 3) 标准动作与命令

### Action A: 环境诊断/初始化
适用：用户说“检查环境”、“初始化飞书表结构”、“字段不对”。

执行命令：
```bash
python3 scripts/internal/diagnose.py
python3 scripts/setup/setup_inspiration_library.py
python3 scripts/setup/setup_content_library.py
```

### Action B: 灵感扫描
适用：用户说“开始收集灵感”、“分析灵感库”。

执行命令：
```bash
python3 core/manager_inspiration.py
```

### Action C: 流水线单次巡检（推荐）
适用：OpenClaw 定时任务、批处理场景。

执行命令（推荐）：
```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 OPENCLAW_PIPELINE_BATCH_SIZE=3 ./run.sh pipeline-once
```

等价命令：
```bash
OPENCLAW_PIPELINE_BATCH_SIZE=3 python3 core/manager.py pipeline-once
```

### Action D: 流水线守护模式（仅用户明确要求）
适用：用户明确要求“持续监听”。

执行命令：
```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 ./run.sh pipeline
```

### Action E: 单篇即时处理
适用：用户给定 URL，要立即改写/发布。

执行命令：
```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 ./run.sh "<URL>" "tech_expert" "auto"
```

也可直接：
```bash
python3 core/manager.py "<URL>" "tech_expert" "auto"
```

### Action F: 全流程 Demo（从 URL 到流水线执行）
适用：用户要快速验证“完整链路是否能跑起来”。

执行命令（联调模式，推荐先跑）：
```bash
python3 scripts/internal/demo_full_flow.py --url "<URL>" --skip-publish
```

执行命令（正式模式，包含发布）：
```bash
python3 scripts/internal/demo_full_flow.py --url "<URL>"
```

结果判定（关键日志）：
1. 灵感库写入成功：`✅ 新建灵感记录: rec...`
2. 流水线写入成功：`✅ 新建流水线记录: rec...`
3. 改写执行成功：`✅ 改写完成`
4. 发布执行成功（正式模式）：`✅ 发布完成`

失败处置：
1. 首次联调推荐先加 `--skip-publish`，先验证抓取、改写、飞书回写。
2. 去掉 `--skip-publish` 后可走发布链路（需微信白名单 IP 与公众号权限就绪）。
3. 若发布失败，优先检查公众号 IP 白名单与 `WECHAT_APPID/WECHAT_SECRET`。
4. 若模型调用失败，先执行 `python3 scripts/internal/check_env.py` 查看模型路由与 key 状态。

### Action G: 单点链路验证（抓取 -> 飞书文档 -> Bitable 附件）
适用：用户要定位素材转存问题，但不想跑完整流水线。

执行命令：
```bash
python3 scripts/internal/single_point_test.py
```

### Action H: 环境与路由体检
适用：用户问“当前到底会走哪个模型/哪个生图路由”。

执行命令：
```bash
python3 scripts/internal/check_env.py
```

### Action I: 管理后台启动（新增）
适用：用户需要可视化管理页面，统一触发扫描/流水线/单篇/Demo/定时执行。

执行命令：
```bash
python3 admin_server.py
```

访问地址：
1. `http://127.0.0.1:8701`
2. 可通过 `ADMIN_HOST/ADMIN_PORT` 修改监听地址
3. 支持多账户：每个账户独立配置公众号参数、飞书参数、表格名、改写方向提示词；动作按“激活账户”执行

## 4) 模型与参数约定
模型优先级：
1. CLI 第三个参数（单篇模式）
2. 飞书记录字段 `改写模型`（流水线单条）
3. 环境变量 `OPENCLAW_PIPELINE_MODEL`（流水线默认）
4. 自动模型路由（`OPENCLAW_MODEL_PROVIDER`）
5. 兜底模型

常用可选模型 key：
1. `auto`（推荐：优先 OpenClaw 代理，无则回退独立模型）
2. `openclaw`（强制走 OpenClaw 代理）
3. `kimi-k2.5`
4. `qwen3.5-plus`
5. `qwen3-max-2026-01-23`
6. `qwen3-coder-next`
7. `qwen3-coder-plus`
8. `glm-5`
9. `glm-4.7`
10. `MiniMax-M2.5`
11. `volcengine`

OpenClaw 代理读取规则（无需额外改代码）：
1. 端点优先读取：`OPENCLAW_PROXY_ENDPOINT` / `OPENCLAW_LLM_ENDPOINT` / `OPENCLAW_ENDPOINT` / `OPENAI_BASE_URL`
2. Key 优先读取：`OPENCLAW_PROXY_API_KEY` / `OPENCLAW_LLM_API_KEY` / `OPENCLAW_API_KEY` / `OPENAI_API_KEY`
3. 模型优先读取：`OPENCLAW_PROXY_MODEL` / `OPENCLAW_LLM_MODEL` / `OPENAI_MODEL`

角色字段：
1. `改写角色`（飞书字段）
2. 默认 `tech_expert`

封面生图路由（新增）：
1. `COVER_IMAGE_PROVIDER=auto`（推荐）：优先方舟生图，失败自动回退即梦。
2. `COVER_IMAGE_PROVIDER=ark`：只走方舟 `images/generations`。
3. `COVER_IMAGE_PROVIDER=jimeng`：只走即梦 AK/SK。
4. 方舟参数：`ARK_IMAGE_API_KEY`、`ARK_IMAGE_ENDPOINT`、`ARK_IMAGE_MODEL`、`ARK_IMAGE_SIZE`、`ARK_IMAGE_RESPONSE_FORMAT`。
   - 推荐模型：`doubao-seedream-5-0-260128`（默认）
   - 备选模型：`doubao-seedream-4-5-251128`
5. 即梦参数：`VOLCENGINE_AK`、`VOLCENGINE_SK`。

## 5) 流水线状态机（必须按新状态识别）
1. `🧲 待改写`
2. `✍️ 改写中`
3. `🧾 待审核`
4. `🚀 待发布`
5. `📤 发布中`
6. `✅ 已发布`
7. `❌ 改写失败`
8. `❌ 发布失败`
9. `❌ 失败`

兼容旧状态文案时，交给系统内部 canonical 映射处理，不要在技能层写死旧状态推进逻辑。

## 6) OpenClaw 运行效率约定
1. 触发频率高时，固定用 `pipeline-once`，让外部调度器重复调用。
2. 批大小由 `OPENCLAW_PIPELINE_BATCH_SIZE` 控制，避免单次处理过多导致超时。
3. 字段检查已支持间隔控制：
   - `OPENCLAW_SCHEMA_CHECK_ENABLED=1`
   - `OPENCLAW_SCHEMA_CHECK_INTERVAL_SEC=21600`
4. `run.sh` 已支持依赖哈希缓存，`requirements.txt` 未变化会跳过安装。

## 7) 失败处理与自动处置
看到以下错误时按对应动作处理：
1. `No module named ...`
   - 执行：`python3 -m pip install -r requirements.txt`
2. `Missing environment variables` 或鉴权失败
   - 检查并补全 `.env`：`FEISHU_*`, `WECHAT_*`, `LLM/模型相关 key`
   - 微信公众号 `AppID/AppSecret` 获取入口：`https://developers.weixin.qq.com/platform`
   - 必填项：`WECHAT_APPID=...`、`WECHAT_SECRET=...`
3. `document_id max len is 27` / 无法解析 doc token
   - 优先检查飞书字段 `改后文档链接` 是否为 `https://www.feishu.cn/docx/...`
   - 必要时执行修复脚本：
```bash
python3 scripts/internal/repair_failed_records.py
```
4. 改写失败但无失败备注
   - 回写失败原因并重跑到 `🧲 待改写` 后再执行 `pipeline-once`
5. 封面未生成（方舟/即梦）
   - 先检查 `COVER_IMAGE_PROVIDER` 是否与配置匹配
   - `ark` 模式需至少有 `ARK_IMAGE_API_KEY + ARK_IMAGE_ENDPOINT`
   - `jimeng` 模式需 `VOLCENGINE_AK + VOLCENGINE_SK`
   - `auto` 模式会先尝试方舟，再自动回退即梦

## 8) 推荐环境变量模板
```bash
OPENCLAW_NON_INTERACTIVE=1
OPENCLAW_AUTO_INSTALL=0
OPENCLAW_PIPELINE_BATCH_SIZE=3
OPENCLAW_MODEL_PROVIDER=auto
OPENCLAW_PIPELINE_MODEL=auto
OPENCLAW_PIPELINE_ROLE=tech_expert
OPENCLAW_SCHEMA_CHECK_ENABLED=1
OPENCLAW_SCHEMA_CHECK_INTERVAL_SEC=21600
COVER_IMAGE_PROVIDER=auto
OPENCLAW_CONTENT_DIRECTION=
OPENCLAW_PROMPT_DIRECTION=
OPENCLAW_WECHAT_PROMPT_DIRECTION=
```

独立模型模式（不走 OpenClaw 代理）可选补充：
```bash
OPENCLAW_MODEL_PROVIDER=independent
OPENCLAW_INDEPENDENT_MODEL=kimi-k2.5
```

## 9) 执行边界
1. 本技能负责“调度与发布链路”。
2. 不在技能层硬编码业务表字段迁移逻辑，字段变更优先走 `scripts/setup/*`。
3. 未经用户要求，不做 destructive 操作（删表、批量删记录、清库）。
