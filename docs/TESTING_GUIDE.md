# 测试引导（从 0 到可发布）

本引导按“最小风险”顺序验证：先测配置，再测链路，最后测流水线。

## 1) 配置体检

```bash
python3 scripts/internal/check_env.py
```

目标：
1. 必填项无缺失
2. 模型路由符合预期（OpenClaw 或独立模型）

## 2) 表结构初始化（首次必做）

```bash
python3 scripts/setup/setup_inspiration_library.py
python3 scripts/setup/setup_content_library.py
```

目标：
1. 飞书灵感库与流水线表存在且字段齐全

## 3) 单篇链路测试（推荐先做）

```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 ./run.sh "<文章URL>" "tech_expert" "auto"
```

目标：
1. 能完成采集 -> 改写 -> 发布到草稿箱
2. 飞书记录能回写 `改后文档链接` 与状态

## 4) 流水线单次巡检测试

```bash
OPENCLAW_NON_INTERACTIVE=1 OPENCLAW_AUTO_INSTALL=0 OPENCLAW_PIPELINE_BATCH_SIZE=1 ./run.sh pipeline-once
```

目标：
1. 仅处理 1 条，便于观察
2. 状态按 `待改写/待发布` 正确推进

## 5) 常见失败与定位

1. 微信鉴权失败
   - 检查 `WECHAT_APPID` / `WECHAT_SECRET`
   - 参数获取入口：`https://developers.weixin.qq.com/platform`
2. 改后文档链接为空或非 URL
   - 执行：`python3 scripts/internal/repair_failed_records.py`
3. OpenClaw 代理没生效
   - 看 `run.sh` 是否提示“回退到独立模型”
   - 补齐代理 endpoint + key
4. 飞书写入失败
   - 检查 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_APP_TOKEN`
   - 运行：`python3 scripts/internal/diagnose.py`

## 6) 一键全流程 Demo（灵感库起步）

使用内置 demo 从“灵感库新增 URL”开始跑完整链路：

```bash
python3 scripts/internal/demo_full_flow.py --url "https://mp.weixin.qq.com/s/wrsaOwVYDKd2lEDmRs65Jg"
```

如果你只想跑到改写完成，不执行发布：

```bash
python3 scripts/internal/demo_full_flow.py --url "https://mp.weixin.qq.com/s/wrsaOwVYDKd2lEDmRs65Jg" --skip-publish
```

## 7) 管理后台测试 Agent（页面与展示巡检）

```bash
python3 scripts/internal/test_admin_ui_agent.py
```

目标：
1. 自动启动管理后台并检查所有页面视图是否存在
2. 验证关键展示区域、按钮绑定和主要接口可用性
3. 巡检 `灵感库 / 追踪中心 / 发布日志` 的关键区块是否存在（筛选、明细、表格、动作按钮）
4. 巡检账户页壳层结构（动作栏、目录、表单分区、字段帮助文案）是否完整
5. 巡检窄屏相关防溢出规则（工具栏换行策略、横向滚动保护、看板宽度保护）
6. 巡检 Vue 预览页壳层（`/vue`）是否可访问、静态资源是否可加载、响应式媒体查询是否存在
7. 安全测试多账户创建/切换/删除与定时任务开关
8. 输出报告到 `output/admin-ui-agent-report-*.json` 与 `output/admin-ui-agent-report-*.md`

说明：
1. 默认不触发真实抓取、改写、发布动作
2. 适合作为后台 UI 改版后的回归巡检入口

## 8) 微信登录态采集链路测试（多账户）

```bash
# 1) 查看运行状态
./run_wechat_ingest.sh --account-id default status

# 2) 扫码登录（生成二维码后返回）
./run_wechat_ingest.sh --account-id default login --no-wait --qr-display both

# 3) 检索并关注目标公众号
./run_wechat_ingest.sh --account-id default search-mp "机器之心" --limit 8
./run_wechat_ingest.sh --account-id default add-mp --keyword "机器之心" --pick 1

# 4) 拉取文章列表并同步到灵感库
./run_wechat_ingest.sh --account-id default pull-articles --mp-id MP_WXS_xxx --pages 1 --mode api
./run_wechat_ingest.sh --account-id default sync-inspiration --mp-id MP_WXS_xxx --limit 20
```

目标：
1. 每个账户写入独立目录（默认 `output/wechat_accounts/<account_id>/`）。
2. 文章 URL 成功进入飞书灵感库，并标记为 `待分析`。
