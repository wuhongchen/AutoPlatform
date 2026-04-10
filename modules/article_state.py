"""
文章状态管理 - 简化版（插件化架构）
移除复杂的流水线状态，使用直观的状态流转
"""

from typing import Optional


class ArticleState:
    """简化后的文章状态"""
    # 初始状态
    PENDING_COLLECT = "待采集"           # 刚添加，等待采集

    # 采集相关
    COLLECTING = "采集中"                # 正在采集
    COLLECT_FAILED = "采集失败"          # 采集失败
    COLLECTED = "采集完成"               # 内容已采集

    # AI评分相关
    SCORING = "评分中"                   # AI评分中
    SCORED = "已评分"                    # 评分完成

    # 改写相关
    PENDING_REWRITE = "待改写"           # 等待改写
    REWRITING = "改写中"                 # AI改写中
    REWRITE_FAILED = "改写失败"          # 改写失败
    REWRITTEN = "已改写"                 # 改写完成

    # 发布相关
    PENDING_PUBLISH = "待发布"           # 等待发布
    PUBLISHING = "发布中"                # 发布中
    PUBLISH_FAILED = "发布失败"          # 发布失败
    PUBLISHED = "已发布"                 # 发布成功

    # 其他
    SKIPPED = "已跳过"                   # 评分低或用户跳过
    DELETED = "已删除"                   # 已删除


# 状态分组（用于筛选）
STATE_GROUPS = {
    "all": "全部",
    "pending": "待处理",      # 待采集、采集完成、已评分、待改写
    "processing": "处理中",   # 采集中、评分中、改写中、发布中
    "completed": "已完成",    # 已改写、已发布
    "failed": "失败",         # 采集失败、改写失败、发布失败
    "skipped": "已跳过",      # 已跳过
}

# 状态流转规则
# 定义每个状态可以流转到哪些状态
STATE_TRANSITIONS = {
    # 初始 → 采集
    ArticleState.PENDING_COLLECT: [ArticleState.COLLECTING],

    # 采集 → 评分/失败
    ArticleState.COLLECTING: [ArticleState.COLLECTED, ArticleState.COLLECT_FAILED],
    ArticleState.COLLECT_FAILED: [ArticleState.COLLECTING],  # 可重试
    ArticleState.COLLECTED: [ArticleState.SCORING],

    # 评分 → 改写/跳过
    ArticleState.SCORING: [ArticleState.SCORED],
    ArticleState.SCORED: [ArticleState.PENDING_REWRITE, ArticleState.SKIPPED],

    # 改写 → 发布/失败
    ArticleState.PENDING_REWRITE: [ArticleState.REWRITING],
    ArticleState.REWRITING: [ArticleState.REWRITTEN, ArticleState.REWRITE_FAILED],
    ArticleState.REWRITE_FAILED: [ArticleState.REWRITING],  # 可重试
    ArticleState.REWRITTEN: [ArticleState.PENDING_PUBLISH],

    # 发布 → 完成/失败
    ArticleState.PENDING_PUBLISH: [ArticleState.PUBLISHING],
    ArticleState.PUBLISHING: [ArticleState.PUBLISHED, ArticleState.PUBLISH_FAILED],
    ArticleState.PUBLISH_FAILED: [ArticleState.PUBLISHING],  # 可重试
}

# 状态对应的颜色/样式
STATE_STYLES = {
    ArticleState.PENDING_COLLECT: {"badge": "info", "icon": "📥"},
    ArticleState.COLLECTING: {"badge": "progress", "icon": "📡"},
    ArticleState.COLLECT_FAILED: {"badge": "danger", "icon": "❌"},
    ArticleState.COLLECTED: {"badge": "info", "icon": "📄"},
    ArticleState.SCORING: {"badge": "progress", "icon": "🧠"},
    ArticleState.SCORED: {"badge": "info", "icon": "📊"},
    ArticleState.PENDING_REWRITE: {"badge": "waiting", "icon": "📝"},
    ArticleState.REWRITING: {"badge": "progress", "icon": "✍️"},
    ArticleState.REWRITE_FAILED: {"badge": "danger", "icon": "❌"},
    ArticleState.REWRITTEN: {"badge": "success", "icon": "✨"},
    ArticleState.PENDING_PUBLISH: {"badge": "waiting", "icon": "🚀"},
    ArticleState.PUBLISHING: {"badge": "progress", "icon": "📤"},
    ArticleState.PUBLISH_FAILED: {"badge": "danger", "icon": "❌"},
    ArticleState.PUBLISHED: {"badge": "success", "icon": "✅"},
    ArticleState.SKIPPED: {"badge": "muted", "icon": "⏭️"},
    ArticleState.DELETED: {"badge": "muted", "icon": "🗑️"},
}

# 兼容旧状态映射（用于数据迁移）
LEGACY_STATE_MAP = {
    # 旧状态 → 新状态
    "待分析": ArticleState.PENDING_COLLECT,
    "待审": ArticleState.SCORED,
    "已处理": ArticleState.REWRITTEN,
    "已同步": ArticleState.REWRITTEN,
    "已跳过": ArticleState.SKIPPED,
    "抓取失败": ArticleState.COLLECT_FAILED,
    "处理异常": ArticleState.COLLECT_FAILED,
    # 流水线状态
    "🧲 待改写": ArticleState.PENDING_REWRITE,
    "✍️ 改写中": ArticleState.REWRITING,
    "🧾 待审核": ArticleState.REWRITTEN,
    "🚀 待发布": ArticleState.PENDING_PUBLISH,
    "📤 发布中": ArticleState.PUBLISHING,
    "✅ 已发布": ArticleState.PUBLISHED,
    "❌ 改写失败": ArticleState.REWRITE_FAILED,
    "❌ 发布失败": ArticleState.PUBLISH_FAILED,
    "❌ 失败": ArticleState.COLLECT_FAILED,
}


def normalize_state(status: Optional[str]) -> str:
    """标准化状态（兼容旧数据）"""
    if not status:
        return ArticleState.PENDING_COLLECT

    # 直接匹配
    if status in STATE_STYLES:
        return status

    # 兼容旧状态
    if status in LEGACY_STATE_MAP:
        return LEGACY_STATE_MAP[status]

    # 尝试模糊匹配
    status_lower = status.lower().strip()
    for old, new in LEGACY_STATE_MAP.items():
        if old.lower() in status_lower or status_lower in old.lower():
            return new

    # 默认返回待采集
    return ArticleState.PENDING_COLLECT


def get_state_style(state: str) -> dict:
    """获取状态样式"""
    normalized = normalize_state(state)
    return STATE_STYLES.get(normalized, {"badge": "default", "icon": "•"})


def can_transition(from_state: str, to_state: str) -> bool:
    """检查状态是否可以流转"""
    normalized_from = normalize_state(from_state)
    normalized_to = normalize_state(to_state)

    allowed = STATE_TRANSITIONS.get(normalized_from, [])
    return normalized_to in allowed


def get_available_actions(state: str) -> list:
    """获取当前状态可用的操作"""
    normalized = normalize_state(state)

    actions = {
        ArticleState.PENDING_COLLECT: ["collect"],
        ArticleState.COLLECTED: ["score"],
        ArticleState.SCORED: ["rewrite", "skip"],
        ArticleState.PENDING_REWRITE: ["rewrite"],
        ArticleState.REWRITTEN: ["publish"],
        ArticleState.PENDING_PUBLISH: ["publish"],
        ArticleState.COLLECT_FAILED: ["retry_collect", "delete"],
        ArticleState.REWRITE_FAILED: ["retry_rewrite", "delete"],
        ArticleState.PUBLISH_FAILED: ["retry_publish", "delete"],
        ArticleState.SKIPPED: ["delete"],
        ArticleState.PUBLISHED: ["view_publish", "delete"],
    }

    return actions.get(normalized, [])


def get_state_group(state: str) -> str:
    """获取状态所属分组"""
    normalized = normalize_state(state)

    pending = [ArticleState.PENDING_COLLECT, ArticleState.COLLECTED,
               ArticleState.SCORED, ArticleState.PENDING_REWRITE]
    processing = [ArticleState.COLLECTING, ArticleState.SCORING,
                  ArticleState.REWRITING, ArticleState.PUBLISHING]
    completed = [ArticleState.REWRITTEN, ArticleState.PUBLISHED]
    failed = [ArticleState.COLLECT_FAILED, ArticleState.REWRITE_FAILED,
              ArticleState.PUBLISH_FAILED]

    if normalized in pending:
        return "pending"
    elif normalized in processing:
        return "processing"
    elif normalized in completed:
        return "completed"
    elif normalized in failed:
        return "failed"
    elif normalized == ArticleState.SKIPPED:
        return "skipped"
    else:
        return "other"
