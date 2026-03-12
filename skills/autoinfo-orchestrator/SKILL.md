---
name: autoinfo-manager
description: OpenClaw 自动化运营平台总控中心。负责从选题分析、内容改写、AI 生图到微信发布的全链路调度。
metadata: {"openclaw":{"emoji":"🚀","requires":{"python":">=3.9"}}}
---

# autoinfo-manager (总控技能)

## 🎯 业务目标

作为 OpenClaw 系统的顶层调度器，它将多个原子技能串联起来，实现真正的“无人值守”自媒体运营方案。

---

## 🛠️ 触发指令

当你（OpenClaw Agent）接收到以下指令时，应激活此技能：
- "启动灵感扫描" / "分析选题"
- "运行内容流水线" / "开始自动化发布"
- "处理这篇文章：[URL]"

---

## 🧩 核心模式定义

### 1. 灵感分析模式 (Inspiration Mode)
- **触发逻辑**：用户想要扫描飞书灵感库并获取 AI 评分。
- **调用方式**：执行 `python3 manager_inspiration.py`。
- **内部流转**：
    1. 扫描飞书“内容灵感库”。
    2. 调用 LLM 进行深度分析并打分。
    3. 创建飞书原文文档并转存图片。
    4. 回写分析结果至飞书。

### 2. 流水线自动化模式 (Pipeline Mode)
- **触发逻辑**：用户想要开启后台持续监听，批量生产内容。
- **调用方式**：执行 `python3 manager.py pipeline`。
- **内部流转**：
    1. 监听飞书“智能内容库”。
    2. 发现 `✅ 采集完成` 状态的任务。
    3. 调度底层 `mp-draft-push` 和 `volcengine-jimeng-image` 技能。
    4. 完成“改写 -> 生图 -> 发布”闭环。

### 3. 单篇即时模式 (One-off Mode)
- **参数要求**：
    - `url`: 必填，文章链接。
    - `role`: 默认 `tech_expert`。
    - `model`: 默认 `volcengine` (豆包)。
- **执行逻辑**：调用 `./run.sh [url] [role] [model]`。

---

## 📂 协同技能列表 (Sub-Skills)

总控中心依赖以下原子技能：
- [x] **mp-draft-push**: 处理具体的微信草稿推送。
- [x] **volcengine-jimeng-image**: 负责 AI 封面图生成。
- [x] **wechat-auto-publisher**: (备用) 浏览器自动化运营。

---

## ⚙️ 环境变量要求

执行此总控技能前，请确保配置文件 `.env` 已具备：
- `FEISHU_*`: 飞书 API 权限（文档、表格）。
- `WECHAT_*`: 微信公众号后台权限。
- `VOLCENGINE_*` / `KIMI_*`: LLM 与图像生成权限。

---

## 🚀 模拟执行指令建议

如果您（OpenClaw）希望在命令行中模拟此流程：

**场景：用户输入 "帮我处理这篇文章 https://mp.weixin.qq.com/s/xxx"**

OpenClaw 动作：
```bash
# 模拟原子化执行
python3 manager.py "https://mp.weixin.qq.com/s/xxx" tech_expert volcengine
```
