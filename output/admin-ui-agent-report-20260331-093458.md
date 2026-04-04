# 管理后台测试 Agent 报告

- 地址：`http://127.0.0.1:52843`
- 检查时间：`2026-03-31 09:34:58`
- 总计：`34`
- 通过：`34`
- 失败：`0`

## 明细

- ✅ [api] health endpoint：{"active_account": {"id": "default", "name": "默认账户"}, "defaults": {"batch": "3", "model": "kimi-k2.5", "role": "tech_expert"}, "ok": true, "project_root": "/Users/hongchen/Downloads/code/wxz/autoinfo-platform", "python": "python3", "time": "2026-03-31 09:34:55"}
- ✅ [api] accounts endpoint：active_account_id=default, accounts=2
- ✅ [api] overview endpoint：overview_ok=True, inspiration_total=60
- ✅ [api] jobs endpoint：jobs=0
- ✅ [api] scheduler endpoint：{"minutes": 0, "next_run_at": "", "running": false}
- ✅ [page] view overview：selector=#view-overview
- ✅ [page] view accounts：selector=#view-accounts
- ✅ [page] view inspiration：selector=#view-inspiration
- ✅ [page] view pipeline：selector=#view-pipeline
- ✅ [page] view publish：selector=#view-publish
- ✅ [page] view trace：selector=#view-trace
- ✅ [page] view settings：selector=#view-settings
- ✅ [page] sidebar navigation：nav_views=['overview', 'accounts', 'inspiration', 'pipeline', 'publish', 'trace', 'settings']
- ✅ [page] overview metrics：selector=#overviewMetricGrid
- ✅ [page] overview warnings：selector=#overviewAlertCard
- ✅ [page] accounts form：selector=#accName
- ✅ [page] inspiration grid：selector=#inspirationGrid
- ✅ [page] pipeline kanban：selector=#pipelineKanban
- ✅ [page] publish table：selector=#publishRows
- ✅ [page] trace table：selector=#traceRows
- ✅ [page] settings scheduler：selector=#schMinutes
- ✅ [page] global log console：selector=#jobLogs
- ✅ [page] page titles：missing=none
- ✅ [page] action binding /api/actions/inspiration-scan：/api/actions/inspiration-scan
- ✅ [page] action binding /api/actions/pipeline-once：/api/actions/pipeline-once
- ✅ [page] action binding /api/actions/single-article：/api/actions/single-article
- ✅ [page] action binding /api/actions/full-demo：/api/actions/full-demo
- ✅ [action] create temp account：{"content_direction": "测试内容方向", "created_at": "2026-03-31 09:34:58", "enabled": true, "feishu_admin_user_id": "7278949264247013380", "feishu_app_id": "cli_a85b1afbbcb99013", "feishu_app_secret": "<redacted>", "feishu_app_token": "<redacted>", "feishu_inspiration_table": "内容灵感库", "feishu_pipeline_table": "小龙虾智能内容库", "feishu_publish_log_table": "发布记录", "id": "ui-test-1774920898", "last_run_at": "", "name": "UI 测试账户", "pipeline_batch_size": 2, "pipeline_model": "auto", "pipeline_role": "tech_expert", "prompt_direction": "测试改写方向", "updated_at": "2026-03-31 09:34:58", "wechat_appid": "wx0d47adc0348efc8e", "wechat_author": "W 小龙虾", "wechat_prompt_direction": "测试公众号成稿方向", "wechat_secret": "<redacted>"}
- ✅ [action] activate temp account：{"active_account_id": "ui-test-1774920898", "item": {"content_direction": "测试内容方向", "created_at": "2026-03-31 09:34:58", "enabled": true, "feishu_admin_user_id": "7278949264247013380", "feishu_app_id": "cli_a85b1afbbcb99013", "feishu_app_secret": "<redacted>", "feishu_app_token": "<redacted>", "feishu_inspiration_table": "内容灵感库", "feishu_pipeline_table": "小龙虾智能内容库", "feishu_publish_log_table": "发布记录", "id": "ui-test-1774920898", "last_run_at": "", "name": "UI 测试账户", "pipeline_batch_size": 2, "pipeline_model": "auto", "pipeline_role": "tech_expert", "prompt_direction": "测试改写方向", "updated_at": "2026-03-31 09:34:58", "wechat_appid": "wx0d47adc0348efc8e", "wechat_author": "W 小龙虾", "wechat_prompt_direction": "测试公众号成稿方向", "wechat_secret": "<redacted>"}, "ok": true}
- ✅ [action] verify temp account active：active=ui-test-1774920898
- ✅ [action] restore original active account：{"active_account_id": "default", "item": {"content_direction": "", "created_at": "2026-03-31 00:47:46", "enabled": false, "feishu_admin_user_id": "7278949264247013380", "feishu_app_id": "cli_a85b1afbbcb99013", "feishu_app_secret": "<redacted>", "feishu_app_token": "<redacted>", "feishu_inspiration_table": "内容灵感库", "feishu_pipeline_table": "小龙虾智能内容库", "feishu_publish_log_table": "发布记录", "id": "default", "last_run_at": "", "name": "默认账户", "pipeline_batch_size": 3, "pipeline_model": "kimi-k2.5", "pipeline_role": "tech_expert", "prompt_direction": "", "updated_at": "2026-03-31 09:29:20", "wechat_appid": "wx0d47adc0348efc8e", "wechat_author": "W 小龙虾", "wechat_prompt_direction": "", "wechat_secret": "<redacted>"}, "ok": true}
- ✅ [action] delete temp account：{"active_account_id": "default", "ok": true}
- ✅ [action] scheduler start：{"minutes": 59, "next_run_at": "", "running": true}
- ✅ [action] scheduler restore stopped state：{"minutes": 59, "next_run_at": "", "running": false}
