---
name: system-doctor
description: 项目管理员工具。用于检查飞书 Token、微信权限、诊断网络环境以及初始化多维表格字段。
metadata: {"openclaw":{"emoji":"🩺","requires":{"python":">=3.9"}}}
---

# system-doctor (系统医生)

## 🎯 功能
当系统运行报错、无法连接飞书/微信、或刚拉取代码需要初始化环境时，调用此技能。

## 🛠️ 指令路由
- "检查权限" / "诊断环境" -> `python3 scripts/internal/diagnose.py`
- "检查微信Token" -> `python3 scripts/internal/check_token.py`
- "初始化表格" -> `python3 scripts/internal/create_missing_fields.py`

---

---
name: content-scout
description: 内容侦察兵。负责多信源（RSS）抓取、选题分析、爆款潜力打分。
metadata: {"openclaw":{"emoji":"🔭"}}
---

# content-scout (内容侦察兵)

## 🎯 功能
负责前段的灵感挖掘。

## 🛠️ 指令路由
- "同步RSS资讯" -> `python3 scripts/sync_rss_to_inspiration.py`
- "分析当前选题" -> `python3 core/manager_inspiration.py` (单次运行)

---

---
name: autoinfo-orchestrator
description: 全自动发布总控。将改写、生图、发布三个动作串联成流水线。
metadata: {"openclaw":{"emoji":"🚀"}}
---

# autoinfo-orchestrator (全自动发布)

## 🎯 功能
负责中后段的闭环生产。

## 🛠️ 指令路由
- "开启全自动流水线" -> `python3 core/manager.py pipeline`
- "发布单篇文章" -> `python3 core/manager.py [URL] [ROLE] [MODEL]`
