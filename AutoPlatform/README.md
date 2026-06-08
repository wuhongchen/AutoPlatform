# AutoPlatform

面向公众号运营的内容采集、后台写稿、AI 改写、模板排版、草稿发布平台。

## 特性

- **文章采集** - 抓取公众号文章并沉淀到素材库
- **后台写稿** - 支持直接在后台新建、编辑文章内容
- **AI改写** - 8种改写风格可选，支持手动参考 / 自动参考 / 无参考
- **广告位配置** - 支持按账户配置公众号头部 / 底部固定广告位
- **模板系统** - 4种排版风格，已优化移动端阅读样式
- **异步任务** - 采集 / 改写 / 发布统一走任务队列
- **一键发布** - 生成公众号草稿

## 安装

```bash
pip install -r requirements.txt
```

## 配置

```bash
cp .env.example .env
# 编辑 .env 填入配置
```

必需配置:
- `WECHAT_APPID` - 微信公众号AppID
- `WECHAT_SECRET` - 微信公众号密钥
- `AI_API_KEY` - AI模型API密钥

## 使用

### 命令行

```bash
# 创建账户
python -m app.cli.main account-create --name "主账号" --id main --appid wx... --secret ...

# 采集文章
python -m app.cli.main collect --url "https://mp.weixin.qq.com/s/xxx" --account main

# 查看改写风格
python -m app.cli.main styles

# 改写 - 使用指定风格
python -m app.cli.main rewrite --id <article_id> --style business_analyst

# 改写 - 引用灵感库内容
python -m app.cli.main rewrite --id <article_id> --style tech_expert

# 改写 - 不引用灵感库
python -m app.cli.main rewrite --id <article_id> --style storytelling --no-ref

# 改写 - 添加额外指令
python -m app.cli.main rewrite --id <article_id> --instructions "多用比喻，通俗易懂"

# 查看排版模板
python -m app.cli.main templates

# 预览模板
python -m app.cli.main preview --template tech --output preview.html

# 发布文章（选择模板）
python -m app.cli.main publish --id <article_id> --template business

# 查看统计
python -m app.cli.main stats
```

### 改写风格

8种预设改写风格：

| 风格ID | 名称 | 特点 | 适用场景 |
|--------|------|------|----------|
| `tech_expert` | 科技专家 | 深入浅出，专业不晦涩 | 技术解读 |
| `business_analyst` | 商业分析师 | 数据支撑，商业洞察 | 行业分析 |
| `storyteller` | 故事讲述者 | 情感共鸣，故事包装 | 人物故事 |
| `popular_science` | 科普作家 | 通俗易懂，寓教于乐 | 知识科普 |
| `opinion_leader` | 观点领袖 | 犀利观点，引发思考 | 评论观点 |
| `trend_observer` | 趋势观察者 | 敏锐洞察，前瞻分析 | 趋势预测 |
| `practitioner` | 实战派 | 干货满满，实操性强 | 经验分享 |
| `entertainment` | 娱乐向 | 轻松有趣，阅读门槛低 | 泛娱乐 |

### API服务

```bash
# 启动服务
python main.py server
```

**API端点:**

```
GET  /api/health              - 健康检查
GET  /api/accounts            - 列出账户
POST /api/accounts            - 创建账户
POST /api/inspirations        - 采集文章
GET  /api/inspirations        - 列出素材
GET  /api/inspirations/<id>   - 素材详情
POST /api/inspirations/<id>/create-article - 从素材创建文章
POST /api/inspirations/<id>/approve - 兼容旧接口，等价于 create-article
GET  /api/articles            - 列出文章
POST /api/articles            - 后台手工创建文章
GET  /api/articles/<id>       - 获取文章详情
PUT  /api/articles/<id>       - 后台编辑文章
POST /api/articles/<id>/rewrite   - 创建改写任务
  Body: {"style": "business_analyst", "use_references": true}
POST /api/articles/<id>/publish   - 创建发布任务
GET  /api/templates           - 列出排版模板
POST /api/templates/<name>/preview - 预览模板
GET  /api/styles              - 列出改写风格
GET  /api/tasks               - 查看异步任务
```

**改写API示例：**
```bash
curl -X POST http://127.0.0.1:8701/api/articles/<id>/rewrite \
  -H "Content-Type: application/json" \
  -d '{
    "style": "business_analyst",
    "use_references": true,
    "instructions": "多用数据支撑观点"
  }'
```

**后台写稿 API 示例：**
```bash
curl -X POST http://127.0.0.1:8701/api/articles \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "main",
    "source_title": "手工写的文章",
    "source_author": "运营团队",
    "content": "第一段\n\n第二段",
    "publish_ready": true
  }'
```

### 灵感引用功能

改写时自动引用灵感库中相关内容：
- 自动计算内容相似度
- 借鉴参考文章的风格和角度
- 保持原创性的同时丰富内容

禁用引用：
```bash
python -m app.cli.main rewrite --id <id> --no-ref
```

## 项目结构

```
app/
├── api/server.py          # API服务
├── cli/main.py            # 命令行工具
├── core/manager.py        # 业务逻辑
├── models/                # 数据模型
├── services/              # 服务层
│   ├── ai.py             # AI服务
│   ├── collector.py      # 采集服务
│   ├── storage.py        # 存储服务
│   ├── wechat.py         # 微信服务
│   └── style_presets.py  # 改写风格预设
├── templates/             # 排版模板
│   ├── default.py
│   ├── minimal.py
│   ├── tech.py
│   └── business.py
└── config.py             # 配置管理
```

## 自定义风格

创建自定义改写风格：

1. 在 `app/services/style_presets.py` 添加新预设
2. 继承 `StylePreset` 类
3. 定义 `system_prompt` 和风格参数

## 数据存储

使用SQLite本地数据库，自动创建在 `data/db/` 目录。
