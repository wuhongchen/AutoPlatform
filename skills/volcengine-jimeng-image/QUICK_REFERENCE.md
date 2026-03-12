# 火山引擎即梦 AI - 快速参考手册

> 🎨 一图流快速查询所有功能用法

---

## 📋 命令速查表

| 功能 | 命令 | 示例 |
|------|------|------|
| **文生图** | `npm run generate -- "提示词"` | `npm run generate -- "熊猫"` |
| **图生图** | `npm run image2image -- "提示词" <图>` | `npm run image2image -- "油画" ./in.jpg` |
| **智能扩图** | `npm run outpaint -- <图>` | `npm run outpaint -- ./photo.jpg` |
| **高清放大** | `npm run super-resolution -- <图>` | `npm run super-resolution -- ./small.jpg` |
| **批量任务** | `npm run batch -- <任务文件>` | `npm run batch -- tasks.json` |

---

## 🎨 文生图 (text2image.ts)

```bash
# 基础用法
npx ts-node scripts/text2image.ts "一只可爱的熊猫在吃竹子"

# 指定模型版本
npx ts-node scripts/text2image.ts "山水风景" --version v40

# 指定尺寸
npx ts-node scripts/text2image.ts "产品宣传" --ratio 1:1
npx ts-node scripts/text2image.ts "手机壁纸" --ratio 9:16

# 批量生成
npx ts-node scripts/text2image.ts "科幻城市" --count 4

# 指定输出目录
npx ts-node scripts/text2image.ts "海边日落" --output ./my-images

# 开启调试模式
npx ts-node scripts/text2image.ts "测试" --debug
```

**参数说明**:
- `--version <v30|v31|v40>` - API 版本 (默认：v31)
- `--ratio <宽高比>` - 图片宽高比 (默认：9:16)
- `--count <数量>` - 生成数量 1-4 (默认：1)
- `--output <目录>` - 输出目录 (默认：./output)
- `--debug` - 开启调试模式

---

## 🖼️ 图生图 (image2image.ts)

```bash
# 基础用法
npx ts-node scripts/image2image.ts "油画风格" ./input.jpg

# 调节重绘强度 (0-1, 越大变化越大)
npx ts-node scripts/image2image.ts "水彩风格" ./photo.jpg --strength 0.8

# 指定尺寸
npx ts-node scripts/image2image.ts "赛博朋克" ./input.jpg --ratio 16:9

# 批量生成变体
npx ts-node scripts/image2image.ts "多种风格" ./input.jpg --count 4
```

**参数说明**:
- `--version <v30|v31>` - API 版本 (默认：v31)
- `--ratio <宽高比>` - 图片宽高比 (默认：1:1)
- `--count <数量>` - 生成数量 1-4 (默认：1)
- `--strength <强度>` - 重绘强度 0-1 (默认：0.7)
- `--output <目录>` - 输出目录

---

## 🔍 智能扩图 (outpaint.ts)

```bash
# 基础用法 (默认扩展 1.5 倍)
npx ts-node scripts/outpaint.ts ./photo.jpg

# 指定目标尺寸
npx ts-node scripts/outpaint.ts ./photo.jpg --width 1920 --height 1080

# 指定扩展内容
npx ts-node scripts/outpaint.ts ./photo.jpg --width 2048 --prompt "海滩风景"

# 制作竖屏壁纸
npx ts-node scripts/outpaint.ts ./photo.jpg --width 576 --height 1024
```

**参数说明**:
- `--width <宽度>` - 目标宽度
- `--height <高度>` - 目标高度
- `--prompt <提示词>` - 扩图提示词
- `--output <目录>` - 输出目录

---

## 🔎 高清放大 (super-resolution.ts)

```bash
# 2 倍放大
npx ts-node scripts/super-resolution.ts ./small.jpg --scale 2

# 4 倍超高清放大
npx ts-node scripts/super-resolution.ts ./old.jpg --scale 4

# 指定输出目录
npx ts-node scripts/super-resolution.ts ./low.jpg --scale 4 --output ./hd
```

**参数说明**:
- `--scale <倍数>` - 放大倍数 2 或 4 (默认：2)
- `--output <目录>` - 输出目录

---

## 📦 批量任务 (batch.ts)

**1. 创建任务文件** (`tasks.json`):
```json
[
  {
    "prompt": "AI 工具界面，科技感",
    "version": "v40",
    "ratio": "16:9",
    "count": 1
  },
  {
    "prompt": "AI 科技，蓝色调",
    "version": "v40",
    "ratio": "16:9",
    "count": 1
  }
]
```

**2. 执行批量任务**:
```bash
# 基础用法
npx ts-node scripts/batch.ts tasks.json

# 指定并发数
npx ts-node scripts/batch.ts tasks.json --max-concurrent 5

# 使用示例文件
npx ts-node scripts/batch.ts example-batch-tasks.json
```

**参数说明**:
- `--max-concurrent <数量>` - 最大并发数 (默认：3)
- `--output <目录>` - 输出目录

---

## 💡 常用场景

### 场景 1: 公众号封面图
```bash
# 生成 16:9 封面图
npx ts-node scripts/text2image.ts "AI 工具，科技感，蓝色调" --version v40 --ratio 16:9
```

### 场景 2: 产品宣传图
```bash
# 生成 1:1 产品图
npx ts-node scripts/text2image.ts "智能手表，黑色表带，白色背景" --ratio 1:1
```

### 场景 3: 风格迁移
```bash
# 照片转油画
npx ts-node scripts/image2image.ts "油画风格，梵高" ./photo.jpg --strength 0.7
```

### 场景 4: 老照片修复
```bash
# 4 倍放大提升清晰度
npx ts-node scripts/super-resolution.ts ./old-photo.jpg --scale 4
```

### 场景 5: 批量生成素材
```bash
# 批量生成四季系列
npx ts-node scripts/batch.ts seasons.json --max-concurrent 4
```

---

## ⚠️ 注意事项

### SK 格式 (重要！)
```bash
# ✅ 正确：使用原始 Base64 值
VOLCENGINE_SK=Wm1WaE9XWTVOVGt6TWpBek5HSXlaamt4WW1ReFlUQXpaRFpsTWpaaE56WQ==

# ❌ 错误：不要解码
VOLCENGINE_SK=fea9f95932034b2f91bd1a03d6e26a76
```

### 并发限制
- 同时任务数：≤ 5 个
- 每秒请求数：≤ 2 个

### 内容规范
- ❌ 禁止生成政治敏感、色情、暴力内容
- ⚠️ 避免真人肖像、知名品牌 Logo
- ✅ 遵守法律法规和平台规范

---

## 🔗 相关链接

- **官方文档**: https://www.volcengine.com/docs/85621/1820192
- **API 文档**: https://www.volcengine.com/docs/85621/1817045
- **定价说明**: https://www.volcengine.com/docs/85621/1820193

---

*最后更新：2026-02-28*
