# 火山引擎即梦 AI 图片生成技能

> 🎨 使用即梦 AI v4.0 模型生成高质量图片

---

## 🚀 快速开始

### 1. 配置凭证

```bash
cd ~/.openclaw/workspace/skills/volcengine-jimeng-image
cp .env.example .env
# 编辑 .env 填入你的 AK/SK
```

### 2. 安装依赖

```bash
npm install
```

### 3. 生成图片

```bash
npx ts-node scripts/text2image.ts "一只可爱的熊猫在吃竹子"
```

---

## 📋 使用方法

### 基础用法

```bash
# 生成图片 (默认 v31, 16:9, 1 张)
npx ts-node scripts/text2image.ts "提示词"

# 指定模型版本
npx ts-node scripts/text2image.ts "提示词" --version v40

# 指定尺寸
npx ts-node scripts/text2image.ts "提示词" --ratio 1:1

# 批量生成
npx ts-node scripts/text2image.ts "提示词" --count 4
```

### 完整参数

```
用法：ts-node text2image.ts "提示词" [选项]

选项:
  --version <v30|v31|v40>  API 版本 (默认：v31)
  --ratio <宽高比>         图片宽高比 (默认：9:16)
  --count <数量>           生成数量 1-4 (默认：1)
  --width <宽度>           指定宽度 (可选)
  --height <高度>          指定高度 (可选)
  --size <面积>            指定面积 (可选)
  --seed <种子>            随机种子 (可选)
  --output <目录>          图片下载目录 (默认：./output)
  --no-download            不下载图片，只返回 URL
  --debug                  开启调试模式
```

---

## 📁 目录结构

```
volcengine-jimeng-image/
├── SKILL.md              # 技能定义
├── README.md             # 使用说明
├── .env.example          # 环境变量示例
├── package.json          # 依赖配置
├── scripts/
│   ├── common.ts         # 共享工具
│   ├── text2image.ts     # 文生图脚本
│   └── text2video.ts     # 文生视频脚本
└── output/               # 输出目录
    └── {task_hash}/
        ├── param.json
        ├── response.json
        ├── taskId.txt
        └── {image}.jpg
```

---

## 💡 使用示例

### 示例 1: 公众号封面图

```bash
npx ts-node scripts/text2image.ts "AI 工具界面，科技感，蓝色调" --version v40 --ratio 16:9
```

### 示例 2: 产品宣传图

```bash
npx ts-node scripts/text2image.ts "智能手表，黑色表带，金属质感，白色背景" --ratio 1:1
```

### 示例 3: 批量生成

```bash
npx ts-node scripts/text2image.ts "四季风景，自然风光" --count 4 --ratio 16:9
```

---

## ⚠️ 注意事项

### SK 格式

**重要**：SK 使用原始 Base64 值，不要解码！

```bash
# ✅ 正确
VOLCENGINE_SK=Wm1WaE9XWTVOVGt6TWpBek5HSXlaamt4WW1ReFlUQXpaRFpsTWpaaE56WQ==

# ❌ 错误 (不要解码)
VOLCENGINE_SK=fea9f95932034b2f91bd1a03d6e26a76
```

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
