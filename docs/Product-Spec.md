# Product Specification: autoinfo-platform (OpenClaw)

## 项目背景 (Background)
本项目是一个全自动的内容运营与发布平台，旨在帮助创作者从微信公众号等渠道快速采集高质量内容，通过 AI 进行个性化角色改写，并自动生成配图，最后同步至目标微信公众号草稿箱，实现自动化发布。

## 核心功能 (Core Features)
1.  **内容采集 (Collection)**：支持微信公众号文章的完整采集（标题、作者、正文、图片）。
2.  **AI 角色改写 (Rewriting)**：支持多种 AI 角色（如：爆文运营专家、资深技术博主、每日新闻速递）对文章进行风格转换。
3.  **多模型集成 (LLM Integration)**：集成 KIMI (Moonshot)、火山方舟 (Doubao)、阿里云百炼 (Qwen) 等主流大模型。
4.  **AI 封面图生成 (Cover Generation)**：集成火山引擎即梦 (Jimeng) AI 生图，根据文章主题自动生成 16:9 高清封面。
5.  **微信自动化发布 (Publishing)**：自动上传素材并创建公众号草稿。

## 流水线步骤 (Pipeline Steps)

| 阶段 | 步骤名称 | 核心逻辑 | 负责人/模块 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| **I. 采集** | **1. 网页内容抓取** | 使用 BeautifulSoup4 提取微信文章 HTML 结构及纯文本。 | `modules/collector.py` | ✅ 已完成 |
| **II. 加工** | **2. 模型鉴权与调用** | 适配 OpenAI 格式的 API 协议，支持多模型动态切换。 | `modules/models.py` | ✅ 已完成 |
| **II. 加工** | **3. 角色化 AI 改写** | 基于预定义的 System Prompt（资深专家视角）进行重写。 | `modules/processor.py` | ✅ 已完成 |
| **III. 素材** | **4. AI 原生生图** | 纯 Python 实现火山引擎签名算法，生成任务并轮询下载。 | `modules/processor.py` | ✅ 已完成 |
| **IV. 发布** | **5. 微信素材上传** | 自动将本地生成的封面图上传至微信 Media 库。 | `modules/publisher.py` | ✅ 已完成 |
| **IV. 发布** | **6. 草稿创建** | 构建微信 Drafts JSON 报文进行同步，处理中文转义。 | `modules/publisher.py` | ✅ 已完成 |

## 环境变量配置 (Env Config)
- `WECHAT_APPID / WECHAT_SECRET`: 微信开发接口凭证
- `VOLCENGINE_AK / VOLCENGINE_SK`: 火山引擎（生图）密钥
- `VOLC_ARK_API_KEY`: 火山方舟（对话）密钥
- `KIMI_API_KEY / BAILIAN_API_KEY`: 其他模型密钥

## 技术栈 (Technology Stack)
- **Language**: Python 3.9+
- **APIs**: WeChat Official Account, Volcengine Ark, Moonshot AI, DashScope.
- **Libs**: `requests`, `BeautifulSoup4`, `python-dotenv`, `hashlib`.
