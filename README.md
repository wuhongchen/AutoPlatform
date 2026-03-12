# OpenClaw AutoPlatform

基于 OpenClaw 技能理论开发的全自动信息发布与收集平台。

## 功能介绍

1. **一键采集**：支持微信公众号文章一键抓取并清洗内容。
2. **AI 改写 (需配置)**：调用 LLM 对原始文章进行摘要生成、标题优化以及正文改写，提升原创度。
3. **AI 配图 (需配置)**：集成火山引擎即梦 AI，根据文章主题自动生成 16:9 的封面头图。
4. **全自动发布**：自动将加工后的内容推送到微信公众号草稿箱，包含封面图上传与文章创建。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

在当前目录或 `mp-draft-push` 目录下的 `.env` 文件中配置以下密钥：

```bash
# 微信公众号 (必须)
WECHAT_APPID=...
WECHAT_SECRET=...

# AI 改写 (可选，用于自动改稿)
LLM_API_KEY=...
LLM_ENDPOINT=...

# 火山引擎 (可选，用于自动生成封面图)
VOLCENGINE_AK=...
VOLCENGINE_SK=...
```

### 3. 运行发布

你可以直接使用运营助手脚本：
```bash
./run.sh "https://mp.weixin.qq.com/s/xxx"
```
或者手动运行：
```bash
python manager.py "https://mp.weixin.qq.com/s/xxx"
```

## 目录说明

- `run.sh`: **运营操作入口**，提供交互式界面和环境检查。
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
- `modules/`:
  - `collector.py`: 内容抓取模块。
  - `feishu.py`: 飞书 API 封装，包含图片处理核心逻辑。
  - `processor.py`: AI 加工模块（改稿、生图）。
  - `publisher.py`: 公众号发布模块。
- `archive/`: 存放历史测试脚本与实验性代码。
- `output/`: 存放流程中的中间产物。
