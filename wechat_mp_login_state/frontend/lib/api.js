export async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    if (options.allow404 && response.status === 404) {
      return { ok: false, not_found: true, status: 404, detail }
    }
    let message = detail || `HTTP ${response.status}`
    try {
      const parsed = JSON.parse(detail || '{}')
      message = parsed.error || parsed.message || message
    } catch {
      // keep raw detail
    }
    const err = new Error(message)
    err.status = response.status
    err.detail = detail
    throw err
  }
  return response.json()
}

export const dashboardApi = {
  health: () => api('/api/health'),
  accounts: () => api('/api/accounts'),
  overview: (accountId) => api(`/api/overview?account_id=${encodeURIComponent(accountId || '')}`),
  pipelineList: ({ accountId, status = '', keyword = '', limit = 500 } = {}) =>
    api(
      `/api/pipeline/list?account_id=${encodeURIComponent(accountId || '')}&status=${encodeURIComponent(status)}&keyword=${encodeURIComponent(keyword)}&limit=${encodeURIComponent(limit)}`
    ),
  pipelinePreview: ({ accountId, recordId } = {}) =>
    api(
      `/api/pipeline/preview?account_id=${encodeURIComponent(accountId || '')}&record_id=${encodeURIComponent(recordId || '')}`
    ),
  pipelineUpdateStatus: (payload) => api('/api/pipeline/update-status', { method: 'POST', body: JSON.stringify(payload) }),
  pipelineDelete: ({ accountId, recordId }) => api(
    `/api/pipeline/${encodeURIComponent(recordId)}/delete?account_id=${encodeURIComponent(accountId || '')}`,
    { method: 'POST', body: JSON.stringify({}) }
  ),
  publishList: ({ accountId, status = '', keyword = '', limit = 500 } = {}) =>
    api(
      `/api/publish/list?account_id=${encodeURIComponent(accountId || '')}&status=${encodeURIComponent(status)}&keyword=${encodeURIComponent(keyword)}&limit=${encodeURIComponent(limit)}`
    ),
  jobs: () => api('/api/jobs'),
  jobDetail: (jobId, options = {}) => api(`/api/jobs/${encodeURIComponent(jobId)}`, options),
  // 状态管理
  getStates: () => api('/api/states'),
  inspirationList: ({ accountId, status = '', keyword = '', limit = 300 } = {}) =>
    api(
      `/api/inspiration/list?account_id=${encodeURIComponent(accountId || '')}&status=${encodeURIComponent(status)}&keyword=${encodeURIComponent(keyword)}&limit=${encodeURIComponent(limit)}`
    ),
  inspirationDelete: ({ accountId, recordId }) => api(
    `/api/inspiration/${encodeURIComponent(recordId)}/delete?account_id=${encodeURIComponent(accountId || '')}`,
    { method: 'POST', body: JSON.stringify({}) }
  ),
  inspirationScanCapture: ({ accountId }) => api(
    `/api/actions/inspiration-scan?account_id=${encodeURIComponent(accountId || '')}`,
    { method: 'POST', body: JSON.stringify({}) }
  ),
  inspirationCapture: ({ accountId, recordId }) => api(
    `/api/inspiration/${encodeURIComponent(recordId)}/capture?account_id=${encodeURIComponent(accountId || '')}`,
    { method: 'POST', body: JSON.stringify({}) }
  ),
  inspirationAdd: ({ accountId, urls, defaultStatus }) => api(
    `/api/inspiration/add?account_id=${encodeURIComponent(accountId || '')}`,
    { method: 'POST', body: JSON.stringify({ urls, default_status: defaultStatus }) }
  ),
  inspirationDelete: ({ accountId, recordId }) => api(
    `/api/inspiration/${encodeURIComponent(recordId)}/delete?account_id=${encodeURIComponent(accountId || '')}`,
    { method: 'POST', body: JSON.stringify({}) }
  ),
  inspirationRetry: ({ accountId, recordId }) => api(
    `/api/inspiration/${encodeURIComponent(recordId)}/retry?account_id=${encodeURIComponent(accountId || '')}`,
    { method: 'POST', body: JSON.stringify({}) }
  ),
  upsertAccount: (payload) => api('/api/accounts/upsert', { method: 'POST', body: JSON.stringify(payload) }),
  deleteAccount: (accountId) => api(`/api/accounts/${encodeURIComponent(accountId)}/delete`, { method: 'POST', body: JSON.stringify({}) }),
  activateAccount: (accountId) => api(`/api/accounts/${encodeURIComponent(accountId)}/activate`, { method: 'POST', body: JSON.stringify({}) }),
  runInspirationScan: (accountId) => api('/api/actions/inspiration-scan', { method: 'POST', body: JSON.stringify({ account_id: accountId }) }),
  runSingleArticle: (payload) => api('/api/actions/single-article', { method: 'POST', body: JSON.stringify(payload) }),
  inspirationRewrite: ({ accountId, recordId, role, model }) => api(
    `/api/inspiration/${encodeURIComponent(recordId)}/rewrite?account_id=${encodeURIComponent(accountId || '')}`,
    { method: 'POST', body: JSON.stringify({ role, model }) }
  ),
  wechatStatus: (accountId) => api(`/api/wechat/status?account_id=${encodeURIComponent(accountId || '')}`),
  wechatSearchMp: (payload) => api('/api/wechat/search-mp', { method: 'POST', body: JSON.stringify(payload) }),
  wechatAddMp: (payload) => api('/api/wechat/add-mp', { method: 'POST', body: JSON.stringify(payload) }),
  wechatListMp: (accountId) => api(`/api/wechat/list-mp?account_id=${encodeURIComponent(accountId || '')}`),
  wechatListArticles: (accountId, mpId) =>
    api(`/api/wechat/list-articles?account_id=${encodeURIComponent(accountId || '')}&mp_id=${encodeURIComponent(mpId || '')}`),
  wechatLogin: (payload) => api('/api/actions/wechat-login', { method: 'POST', body: JSON.stringify(payload) }),
  wechatPullArticles: (payload) => api('/api/actions/wechat-pull-articles', { method: 'POST', body: JSON.stringify(payload) }),
  wechatSyncInspiration: (payload) => api('/api/actions/wechat-sync-inspiration', { method: 'POST', body: JSON.stringify(payload) }),
  wechatFullFlow: (payload) => api('/api/actions/wechat-full-flow', { method: 'POST', body: JSON.stringify(payload) }),
  // 新增：发布草稿到微信
  publishDraft: (payload) => api('/api/publish/draft', { method: 'POST', body: JSON.stringify(payload) }),
  // 文章内容管理
  getArticleContent: (recordId, accountId) => api(`/api/articles/${encodeURIComponent(recordId)}/content?account_id=${encodeURIComponent(accountId || '')}`),
  saveArticleContent: (recordId, payload) => api(`/api/articles/${encodeURIComponent(recordId)}/content`, { method: 'POST', body: JSON.stringify(payload) }),
  renderArticle: (recordId, accountId, type = 'original') => api(`/api/articles/${encodeURIComponent(recordId)}/render?account_id=${encodeURIComponent(accountId || '')}&type=${type}`),
  previewWechat: (recordId, accountId, type = 'original') =>
    api(`/api/articles/${encodeURIComponent(recordId)}/preview-wechat?account_id=${encodeURIComponent(accountId || '')}&type=${type}`),
  
  // 状态管理
  getStates: () => api('/api/states'),
  getInspirationActions: ({ accountId, recordId }) => api(`/api/inspiration/${encodeURIComponent(recordId)}/actions?account_id=${encodeURIComponent(accountId || '')}`),
  // 插件任务
  listPluginTasks: ({ accountId, recordId, pluginType, status, limit = 100 } = {}) => {
    const params = new URLSearchParams()
    if (accountId) params.append('account_id', accountId)
    if (recordId) params.append('record_id', recordId)
    if (pluginType) params.append('plugin_type', pluginType)
    if (status) params.append('status', status)
    params.append('limit', String(limit))
    return api(`/api/plugin-tasks?${params.toString()}`)
  },
  getPluginTask: (taskId) => api(`/api/plugin-tasks/${encodeURIComponent(taskId)}`),
}
