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
  publishList: ({ accountId, status = '', keyword = '', limit = 500 } = {}) =>
    api(
      `/api/publish/list?account_id=${encodeURIComponent(accountId || '')}&status=${encodeURIComponent(status)}&keyword=${encodeURIComponent(keyword)}&limit=${encodeURIComponent(limit)}`
    ),
  scheduler: () => api('/api/scheduler'),
  jobs: () => api('/api/jobs'),
  jobDetail: (jobId, options = {}) => api(`/api/jobs/${encodeURIComponent(jobId)}`, options),
  inspirationList: ({ accountId, status = '', keyword = '', limit = 300 } = {}) =>
    api(
      `/api/inspiration/list?account_id=${encodeURIComponent(accountId || '')}&status=${encodeURIComponent(status)}&keyword=${encodeURIComponent(keyword)}&limit=${encodeURIComponent(limit)}`
    ),
  upsertAccount: (payload) => api('/api/accounts/upsert', { method: 'POST', body: JSON.stringify(payload) }),
  deleteAccount: (accountId) => api(`/api/accounts/${encodeURIComponent(accountId)}/delete`, { method: 'POST', body: JSON.stringify({}) }),
  startScheduler: (minutes) => api('/api/scheduler/start', { method: 'POST', body: JSON.stringify({ minutes }) }),
  stopScheduler: () => api('/api/scheduler/stop', { method: 'POST', body: JSON.stringify({}) }),
  activateAccount: (accountId) => api(`/api/accounts/${encodeURIComponent(accountId)}/activate`, { method: 'POST', body: JSON.stringify({}) }),
  runPipeline: (accountId) => api('/api/actions/pipeline-once', { method: 'POST', body: JSON.stringify({ account_id: accountId }) }),
  runFullInspection: (accountId) => api('/api/actions/full-inspection-once', { method: 'POST', body: JSON.stringify({ account_id: accountId }) }),
  runInspirationScan: (accountId) => api('/api/actions/inspiration-scan', { method: 'POST', body: JSON.stringify({ account_id: accountId }) }),
  runSingleArticle: (payload) => api('/api/actions/single-article', { method: 'POST', body: JSON.stringify(payload) }),
  runFullDemo: (payload) => api('/api/actions/full-demo', { method: 'POST', body: JSON.stringify(payload) }),
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
}
