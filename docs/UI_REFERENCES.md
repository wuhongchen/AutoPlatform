# UI 参考图存档

本轮后台重构使用的界面参考图已复制到项目目录，作为后续迭代的视觉基线。

## 存放位置

1. `assets/ui-references/ref-overview.png`
2. `assets/ui-references/ref-account.png`
3. `assets/ui-references/ref-board.png`
4. `assets/ui-references/ref-inspiration.png`
5. `assets/ui-references/ref-failures-a.png`
6. `assets/ui-references/ref-failures-b.png`

## 对应页面映射

1. `ref-overview.png`
   对应后台“概览”页，包含 KPI 卡片、账户健康概况、任务状态、警告区。
2. `ref-account.png`
   对应后台“账户号 / 账户设置”页，包含多账户目录、凭证配置、业务表、提示词方向。
3. `ref-board.png`
   对应后台“写作管理链”页，采用卡片式状态看板表达改写与发布节点。
4. `ref-inspiration.png`
   对应后台“灵感库”页，采用左筛选、中卡片流、右侧智能详情面板。
5. `ref-failures-a.png` 与 `ref-failures-b.png`
   对应后台“追踪中心”页，采用失败指标卡 + 表格 + 右侧链路修复面板。

## 当前落地原则

1. 不改动后端主流程，只优化管理后台的壳层和信息架构。
2. 保持“飞书是内容存储中心，本地后台是运行与观测中心”的边界。
3. 优先复用已有 API：账户、概览、任务日志、定时执行、流程动作。
4. 页面风格以“深色侧边导航 + 玻璃感内容工作区 + 高信息密度卡片”为统一设计语言。
