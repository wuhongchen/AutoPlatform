---
name: volcengine-jimeng-image
description: 火山引擎即梦 AI 图片生成技能。使用即梦 AI v4.0 模型生成高质量图片。支持文生图、图生图、智能扩图等功能。当用户需要生成图片、创建封面图、制作配图时触发。
metadata:
  openclaw:
    emoji: "🎨"
    category: "image-generation"
    tags: ["volcengine", "jimeng", "image", "ai", "text-to-image"]
---

# 火山引擎即梦 AI 图片生成

> 使用火山引擎即梦 AI v4.0 模型生成高质量图片

---

## 🎯 功能特性

### 核心功能
- ✅ **文生图** - 根据文本描述生成图片
- ✅ **图生图** - 基于参考图生成新图片
- ✅ **智能扩图** - 智能扩展图片边界
- ✅ **高清放大** - 提升图片分辨率
- ✅ **批量任务** - 批量提交和管理多个任务

### 支持模型
- ✅ **即梦 AI v3.0** - 基础版本
- ✅ **即梦 AI v3.1** - 增强版本
- ✅ **即梦 AI v4.0** - 最新版本 (推荐)

### 图片规格
- **分辨率**: 最高 2048x2048
- **宽高比**: 1:1, 16:9, 9:16, 3:4, 4:3, 2:3, 3:2, 1:2, 2:1
- **数量**: 1-4 张/次
- **格式**: JPG/PNG

---

## 🚀 使用方法

### 基础用法

**触发词**:
```
生成一张图片：一只可爱的熊猫在吃竹子
帮我画一只猫咪
创建封面图：AI 工具教程
```

**完整参数**:
```
生成图片：一只可爱的熊猫在吃竹子
- 模型：v40 (默认)
- 尺寸：16:9 (默认)
- 数量：1 (默认)
- 风格：卡通/写实/油画/水彩等
```

### 高级用法

**指定模型版本**:
```
使用即梦 v3.1 生成图片：山水风景画
```

**指定尺寸**:
```
生成 1:1 尺寸图片：产品宣传图
生成 9:16 竖版图：手机壁纸
```

**批量生成**:
```
生成 4 张图片：科幻城市夜景
```

**风格指定**:
```
生成油画风格图片：向日葵
生成水彩风格图片：海边日落
```

---

## 🎨 扩展功能

### 1️⃣ 图生图功能

**脚本**: `scripts/image2image.ts`

**用法**:
```bash
npx ts-node scripts/image2image.ts "提示词" <参考图路径> [选项]
```

**选项**:
- `--version <v30|v31>` - API 版本 (默认：v31)
- `--ratio <宽高比>` - 图片宽高比 (默认：1:1)
- `--count <数量>` - 生成数量 1-4 (默认：1)
- `--strength <强度>` - 重绘强度 0-1 (默认：0.7)
- `--seed <种子>` - 随机种子 (可选)
- `--output <目录>` - 图片下载目录 (默认：./output)

**示例**:
```bash
# 基于参考图生成油画风格
npx ts-node scripts/image2image.ts "油画风格" ./input.jpg --strength 0.7

# 生成 1:1 尺寸，重绘强度 0.8
npx ts-node scripts/image2image.ts "水彩风格" ./photo.jpg --ratio 1:1 --strength 0.8

# 批量生成 4 张变体
npx ts-node scripts/image2image.ts "赛博朋克风格" ./input.jpg --count 4
```

**使用场景**:
- 🎨 风格迁移 (照片→油画/水彩/素描)
- 🖼️ 基于草图生成成品图
- 🔄 生成图片变体
- 🎭 调整图片风格

---

### 2️⃣ 智能扩图

**脚本**: `scripts/outpaint.ts`

**用法**:
```bash
npx ts-node scripts/outpaint.ts <图片路径> [选项]
```

**选项**:
- `--width <宽度>` - 目标宽度 (默认：原图宽度*1.5)
- `--height <高度>` - 目标高度 (默认：原图高度*1.5)
- `--prompt <提示词>` - 扩图提示词 (可选)
- `--output <目录>` - 图片下载目录 (默认：./output)

**示例**:
```bash
# 扩展为宽屏 16:9
npx ts-node scripts/outpaint.ts ./photo.jpg --width 1536 --height 1024

# 扩展并指定内容
npx ts-node scripts/outpaint.ts ./photo.jpg --width 2048 --height 1024 --prompt "海滩风景"

# 扩展为竖屏 9:16
npx ts-node scripts/outpaint.ts ./photo.jpg --width 576 --height 1024
```

**使用场景**:
- 📐 扩展图片适应不同尺寸需求
- 🖼️ 制作宽屏壁纸
- 📱 制作竖屏手机壁纸
- 🎨 创意扩图创作

---

### 3️⃣ 高清放大

**脚本**: `scripts/super-resolution.ts`

**用法**:
```bash
npx ts-node scripts/super-resolution.ts <图片路径> [选项]
```

**选项**:
- `--scale <倍数>` - 放大倍数 2/4 (默认：2)
- `--output <目录>` - 图片下载目录 (默认：./output)

**示例**:
```bash
# 2 倍放大
npx ts-node scripts/super-resolution.ts ./small.jpg --scale 2

# 4 倍超高清放大
npx ts-node scripts/super-resolution.ts ./old-photo.jpg --scale 4

# 放大并保存到指定目录
npx ts-node scripts/super-resolution.ts ./low-res.jpg --scale 4 --output ./hd-output
```

**使用场景**:
- 🔍 提升老照片清晰度
- 📷 打印前提升分辨率
- 🖥️ 大屏展示前优化
- 🎨 提升素材质量

---

### 4️⃣ 批量任务管理

**脚本**: `scripts/batch.ts`

**用法**:
```bash
npx ts-node scripts/batch.ts <任务文件> [选项]
```

**选项**:
- `--max-concurrent <数量>` - 最大并发数 (默认：3)
- `--output <目录>` - 图片下载目录 (默认：./output)

**任务文件格式** (`tasks.json`):
```json
[
  {
    "prompt": "AI 工具界面，科技感，蓝色调",
    "version": "v40",
    "ratio": "16:9",
    "count": 1
  },
  {
    "prompt": "AI 科技，蓝色调，未来感",
    "version": "v40",
    "ratio": "16:9",
    "count": 1
  },
  {
    "prompt": "自动化工作流程，AI 员工",
    "version": "v40",
    "ratio": "16:9",
    "count": 1
  }
]
```

**示例**:
```bash
# 批量生成 3 张封面图
npx ts-node scripts/batch.ts tasks.json --max-concurrent 3

# 使用示例任务文件
npx ts-node scripts/batch.ts example-batch-tasks.json

# 高并发批量生成 (5 个并发)
npx ts-node scripts/batch.ts large-tasks.json --max-concurrent 5
```

**使用场景**:
- 📦 批量生成公众号封面图
- 🎯 A/B 测试不同风格
- 📊 批量生成素材库
- 🎨 批量创作系列图片

---

### 综合使用示例

**场景 1: 公众号封面图工作流**
```bash
# 1. 文生图生成基础图
npx ts-node scripts/text2image.ts "AI 工具界面，科技感" --version v40 --ratio 16:9

# 2. 智能扩图调整为精确尺寸
npx ts-node scripts/outpaint.ts ./output/*/1.jpg --width 1920 --height 1080

# 3. 高清放大提升质量
npx ts-node scripts/super-resolution.ts ./output/*/outpaint_1.jpg --scale 2
```

**场景 2: 风格迁移工作流**
```bash
# 1. 图生图转换为油画风格
npx ts-node scripts/image2image.ts "油画风格，梵高" ./photo.jpg --strength 0.7

# 2. 高清放大提升细节
npx ts-node scripts/super-resolution.ts ./output/*/1.jpg --scale 4
```

**场景 3: 批量素材生成**
```bash
# 创建任务文件
cat > tasks.json << 'EOF'
[
  {"prompt": "春天风景，樱花", "version": "v40", "ratio": "16:9"},
  {"prompt": "夏天风景，海滩", "version": "v40", "ratio": "16:9"},
  {"prompt": "秋天风景，枫叶", "version": "v40", "ratio": "16:9"},
  {"prompt": "冬天风景，雪景", "version": "v40", "ratio": "16:9"}
]
EOF

# 批量生成四季系列
npx ts-node scripts/batch.ts tasks.json --max-concurrent 4
```

---

## 📋 配置说明

### 环境变量

在 `~/.openclaw/workspace/skills/volcengine-jimeng-image/.env` 中配置：

```bash
# 火山引擎 Access Key ID
export VOLCENGINE_AK=AKLTxxxxxxxxxxxxxxxxxxxxxxxxx

# 火山引擎 Secret Access Key (原始 Base64 值，不要解码)
export VOLCENGINE_SK=Wm1WaE9XWTVOVGt6TWpBek5HSXlaamt4WW1ReFlUQXpaRFpsTWpaaE56WQ==
```

### ⚠️ 重要提示

**SK 格式**：
- ✅ 正确：使用原始 Base64 值 (脚本会自动解码)
- ❌ 错误：使用解码后的值

**示例**：
```bash
# ✅ 正确
VOLCENGINE_SK=Wm1WaE9XWTVOVGt6TWpBek5HSXlaamt4WW1ReFlUQXpaRFpsTWpaaE56WQ==

# ❌ 错误 (不要解码)
VOLCENGINE_SK=fea9f95932034b2f91bd1a03d6e26a76
```

---

## 🎨 提示词技巧

### 优质提示词结构

```
[主体] + [动作/状态] + [环境/背景] + [风格] + [质量要求]
```

**示例**：
```
一只可爱的熊猫 (主体)
在吃竹子 (动作)
在竹林中，阳光透过竹叶 (环境)
卡通风格，宫崎骏风格 (风格)
高清，细节丰富，8K 分辨率 (质量)
```

### 风格关键词

**艺术风格**:
- 卡通/动漫/二次元
- 写实/照片级
- 油画/水彩/素描
- 赛博朋克/蒸汽朋克
- 中国风/水墨画

**质量关键词**:
- 高清/4K/8K
- 细节丰富
- 专业摄影
- 电影级
- 工作室品质

**光线关键词**:
- 自然光
- 逆光
- 侧光
- 柔光
- 霓虹灯

---

## 📁 输出说明

### 文件结构

```
~/.openclaw/workspace/skills/volcengine-jimeng-image/output/
└── {task_hash}/
    ├── param.json          # 生成参数
    ├── response.json       # API 响应
    ├── taskId.txt          # 任务 ID
    └── {image}.jpg         # 生成的图片
```

### 元数据

**param.json**:
```json
{
  "prompt": "一只可爱的熊猫在吃竹子",
  "version": "v40",
  "ratio": "16:9",
  "count": 1,
  "req_key": "jimeng_t2i_v40",
  "timestamp": "2026-02-28T08:59:59.022Z"
}
```

---

## 💰 成本说明

### 价格

| 分辨率 | 价格 | 免费额度 |
|--------|------|---------|
| 512x512 | ¥0.03/张 | 新用户¥100 |
| 1024x1024 | ¥0.05/张 | 约 2000 张 |
| 2048x2048 | ¥0.10/张 | |

### 成本估算

**日常使用**:
- 每天 10 篇 × 1 张封面 = 10 张/天
- 10 张 × ¥0.05 = ¥0.50/天
- ¥100 体验金可用约 200 天

**批量使用**:
- 100 张 × ¥0.05 = ¥5.00
- 1000 张 × ¥0.05 = ¥50.00

---

## ⚠️ 注意事项

### 内容规范

**禁止生成**:
- ❌ 政治敏感内容
- ❌ 色情低俗内容
- ❌ 暴力恐怖内容
- ❌ 侵权内容
- ❌ 虚假信息

**建议避免**:
- ⚠️ 真人肖像 (可能涉及肖像权)
- ⚠️ 知名品牌 Logo (可能涉及商标权)
- ⚠️ 医疗建议 (可能涉及医疗广告)

### 使用限制

**并发限制**:
- 同时任务数：≤ 5 个
- 每秒请求数：≤ 2 个

**配额限制**:
- 每日生成上限：根据账号等级
- 单张图片大小：≤ 10MB

### 错误处理

**常见错误**:
1. **SignatureDoesNotMatch** - 检查 SK 格式 (使用原始 Base64 值)
2. **InvalidParameter** - 检查提示词是否合规
3. **QuotaExceeded** - 超出每日配额
4. **TaskTimeout** - 生成超时，重试即可

---

## 🔧 故障排查

### 问题 1: 签名验证失败

**错误**: `SignatureDoesNotMatch`

**解决**:
```bash
# 检查 SK 格式
cat .env

# ✅ 正确：原始 Base64 值
VOLCENGINE_SK=Wm1WaE9XWTVOVGt6TWpBek5HSXlaamt4WW1ReFlUQXpaRFpsTWpaaE56WQ==

# ❌ 错误：解码后的值
VOLCENGINE_SK=fea9f95932034b2f91bd1a03d6e26a76
```

### 问题 2: 任务提交失败

**错误**: `InvalidParameter`

**解决**:
1. 检查提示词是否包含敏感词
2. 简化提示词，避免过于复杂
3. 检查宽高比是否支持

### 问题 3: 生成超时

**错误**: `TaskTimeout`

**解决**:
1. 重试任务
2. 降低分辨率
3. 减少生成数量

---

## 📚 示例库

### 示例 1: 公众号封面图

```
生成公众号封面图：AI 工具教程
- 提示词：AI 工具界面，电脑屏幕，科技感，蓝色调，简洁风格
- 尺寸：16:9
- 模型：v40
```

### 示例 2: 产品宣传图

```
生成产品宣传图：智能手表
- 提示词：智能手表，黑色表带，金属质感，产品展示，白色背景
- 尺寸：1:1
- 模型：v40
```

### 示例 3: 艺术创作

```
生成油画风格图片：星空
- 提示词：星空，银河，梵高风格，油画，旋转的星云，深蓝色调
- 尺寸：16:9
- 模型：v40
```

### 示例 4: 批量生成

```
生成 4 张图片：四季风景
- 提示词：春/夏/秋/冬四季风景，自然风光，高清
- 尺寸：16:9
- 数量：4
- 模型：v40
```

---

## 🔗 相关资源

### 官方文档
- [即梦 AI 官方文档](https://www.volcengine.com/docs/85621/1820192)
- [API 接口文档](https://www.volcengine.com/docs/85621/1817045)
- [定价说明](https://www.volcengine.com/docs/85621/1820193)

### 提示词资源
- [PromptHero](https://prompthero.com/) - AI 提示词库
- [Prompt Engineering Guide](https://www.promptingguide.ai/) - 提示词工程指南

### 社区
- [火山引擎开发者社区](https://developer.volcengine.com/)
- [即梦 AI 用户群](https://example.com/jimeng-group)

---

## 📝 更新日志

### v1.0.0 (2026-02-28)
- ✅ 初始版本
- ✅ 支持文生图功能
- ✅ 支持 v30/v31/v40 模型
- ✅ 支持多种宽高比
- ✅ 自动下载图片
- ✅ 完整的错误处理

### 计划更新
- 🔄 图生图功能
- 🔄 智能扩图
- 🔄 高清放大
- 🔄 批量任务管理

---

*最后更新：2026-02-28*  
*维护者：OpenClaw 团队*
