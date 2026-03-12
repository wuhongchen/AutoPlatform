# Product Specification CHANGELOG

## [v1.1.0] - 2026-03-03

### Added
- **内容灵感库 (Content Inspiration Library)**: 
  - 独立于现有发布流水线的灵感采集与筛选模块。
  - 支持微信公众号 URL 互动数据抓取（阅读量/点赞量）。
  - 集成 AI 爆款评分与推荐理由生成。
  - 实现基于飞书表格状态流转的自动化流转逻辑。

### Modified
- **小龙虾智能内容库**: 降级为单纯的“发布流水线进程库”，仅接收灵感库筛选后的任务。
