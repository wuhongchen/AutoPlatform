class PipelineState:
    # 新版节点命名（统一、可读、可视化）
    QUEUED_REWRITE = "🧲 待改写"
    REWRITE_RUNNING = "✍️ 改写中"
    REVIEW_READY = "🧾 待审核"
    PUBLISH_READY = "🚀 待发布"
    PUBLISH_RUNNING = "📤 发布中"
    PUBLISHED = "✅ 已发布"
    REWRITE_FAILED = "❌ 改写失败"
    PUBLISH_FAILED = "❌ 发布失败"
    FAILED = "❌ 失败"


PIPELINE_STATUS_OPTIONS = [
    {"name": PipelineState.QUEUED_REWRITE},
    {"name": PipelineState.REWRITE_RUNNING},
    {"name": PipelineState.REVIEW_READY},
    {"name": PipelineState.PUBLISH_READY},
    {"name": PipelineState.PUBLISH_RUNNING},
    {"name": PipelineState.PUBLISHED},
    {"name": PipelineState.REWRITE_FAILED},
    {"name": PipelineState.PUBLISH_FAILED},
    {"name": PipelineState.FAILED},
]


# 旧状态 -> 新状态（兼容历史数据）
LEGACY_TO_CANONICAL = {
    "✅ 采集完成": PipelineState.QUEUED_REWRITE,
    "处理中": PipelineState.REWRITE_RUNNING,
    "✨ 已改写(待审)": PipelineState.REVIEW_READY,
    "🚀 确认发布": PipelineState.PUBLISH_READY,
    "发布中": PipelineState.PUBLISH_RUNNING,
    "✨ 流程全通": PipelineState.PUBLISHED,
    "❌ 改写失败": PipelineState.REWRITE_FAILED,
    "❌ 发布失败": PipelineState.PUBLISH_FAILED,
    "❌ 失败": PipelineState.FAILED,
}


def canonical_pipeline_status(status):
    s = str(status or "").strip()
    if not s:
        return ""
    if s in LEGACY_TO_CANONICAL:
        return LEGACY_TO_CANONICAL[s]
    return s


def is_rewrite_stage(status):
    s = canonical_pipeline_status(status)
    return s in {PipelineState.QUEUED_REWRITE, PipelineState.REWRITE_RUNNING}


def is_publish_stage(status):
    s = canonical_pipeline_status(status)
    return s in {PipelineState.PUBLISH_READY, PipelineState.PUBLISH_RUNNING}
