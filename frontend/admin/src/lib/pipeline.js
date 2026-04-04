export const NAV_ITEMS = [
  { key: 'overview', label: '概览', icon: '⌂', status: 'ready' },
  { key: 'accounts', label: '账户号', icon: '⎈', status: 'ready' },
  { key: 'inspiration', label: '灵感库', icon: '◫', status: 'ready' },
  { key: 'radar', label: '雷达舱', icon: '⌁', status: 'ready' },
  { key: 'formatter', label: '公众号排版', icon: '✧', status: 'ready' },
  { key: 'pipeline', label: '写作管理链', icon: '⇄', status: 'ready' },
  { key: 'publish', label: '发布日志', icon: '☰', status: 'ready' },
  { key: 'trace', label: '追踪中心', icon: '◎', status: 'ready' },
  { key: 'settings', label: '设置', icon: '⚙', status: 'ready' },
]

export const PIPELINE_COLUMNS = [
  { key: '待重写', label: '待改写', icon: '🧲', note: '等待进入改写流程', tone: 'waiting' },
  { key: '重写中', label: '重写中', icon: '✍️', note: '模型正在生成初稿', tone: 'progress' },
  { key: '待审核', label: '待审核', icon: '🧾', note: '等待人工确认', tone: 'review' },
  { key: '待发布', label: '待发布', icon: '🚀', note: '稿件可进入发布', tone: 'publish' },
  { key: '发布中', label: '发布中', icon: '📤', note: '正在同步草稿', tone: 'publish' },
  { key: '已发布', label: '已发布', icon: '✅', note: '发布或同步完成', tone: 'success' },
  { key: '失败异常', label: '失败异常', icon: '❌', note: '需要人工修复', tone: 'danger' },
]

export function normalizePipelineStage(status) {
  const text = String(status || '').trim()
  if (!text) return '待重写'
  const plain = text.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '').toLowerCase()

  if (
    plain.includes('发布失败') ||
    plain.includes('改写失败') ||
    plain.includes('重写失败') ||
    plain.includes('同步失败') ||
    plain.includes('失败') ||
    plain.includes('异常')
  ) {
    return '失败异常'
  }
  if (plain.includes('发布中') || plain.includes('同步中')) return '发布中'
  if (plain.includes('已发布') || plain.includes('发布成功') || plain.includes('流程全通') || plain.includes('同步完成')) return '已发布'
  if (plain.includes('待发布') || plain.includes('确认发布')) return '待发布'
  if (plain.includes('待审核') || plain.includes('审核')) return '待审核'
  if (plain.includes('改写中') || plain.includes('重写中') || plain.includes('处理中')) return '重写中'
  if (plain.includes('待改写') || plain.includes('待重写') || plain.includes('入池') || plain.includes('待处理') || plain.includes('采集完成')) return '待重写'
  return text
}

export function stageMeta(stage) {
  return PIPELINE_COLUMNS.find((item) => item.key === stage) || PIPELINE_COLUMNS[0]
}

export function groupPipeline(items = []) {
  const groups = Object.fromEntries(PIPELINE_COLUMNS.map((item) => [item.key, []]))
  items.forEach((item) => {
    const stage = normalizePipelineStage(item.status)
    if (!groups[stage]) groups[stage] = []
    groups[stage].push(item)
  })
  return groups
}

export function countsFromPipeline(items = []) {
  const counts = { total: items.length, waitingRewrite: 0, waitingPublish: 0, published: 0, failed: 0 }
  items.forEach((item) => {
    const stage = normalizePipelineStage(item.status)
    if (stage === '待重写' || stage === '重写中') counts.waitingRewrite += 1
    if (stage === '待发布' || stage === '发布中') counts.waitingPublish += 1
    if (stage === '已发布') counts.published += 1
    if (stage === '失败异常') counts.failed += 1
  })
  return counts
}
