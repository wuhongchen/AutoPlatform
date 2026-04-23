import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// HTTP 状态码错误映射
const HTTP_ERROR_MAP = {
  400: '请求参数错误',
  401: '未授权，请重新登录',
  403: '没有权限执行此操作',
  404: '请求的资源不存在',
  408: '请求超时，请稍后重试',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务暂时不可用',
  504: '网关超时'
}

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const serverMessage = error.response?.data?.error
    const message = serverMessage || HTTP_ERROR_MAP[status] || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

// API 方法
export default {
  // 健康检查
  health: () => api.get('/health'),
  stats: (params) => api.get('/stats', { params }),

  // 账户
  accounts: {
    list: () => api.get('/accounts'),
    get: (id) => api.get(`/accounts/${id}`),
    create: (data) => api.post('/accounts', data),
    update: (id, data) => api.put(`/accounts/${id}`, data),
    delete: (id) => api.delete(`/accounts/${id}`),
    stats: (id) => api.get(`/accounts/${id}/stats`)
  },

  // 文章
  articles: {
    list: (params) => api.get('/articles', { params }),
    get: (id) => api.get(`/articles/${id}`),
    rewrite: (id, data) => api.post(`/articles/${id}/rewrite`, data),
    publish: (id, data) => api.post(`/articles/${id}/publish`, data)
  },

  // 灵感库
  inspirations: {
    list: (params) => api.get('/inspirations', { params }),
    collect: (data) => api.post('/inspirations', data),
    approve: (id) => api.post(`/inspirations/${id}/approve`),
    get: (id) => api.get(`/inspirations/${id}`),
    delete: (id) => api.delete(`/inspirations/${id}`)
  },

  // 风格预设
  styles: {
    list: (params) => api.get('/styles', { params }),
    get: (id) => api.get(`/styles/${id}`),
    create: (data) => api.post('/styles', data),
    update: (id, data) => api.put(`/styles/${id}`, data),
    delete: (id) => api.delete(`/styles/${id}`),
    toggle: (id) => api.post(`/styles/${id}/toggle`)
  },

  // 模板
  templates: {
    list: () => api.get('/templates'),
    preview: (name, data) => api.post(`/templates/${name}/preview`, data)
  },

  // 流水线（批量任务）
  pipeline: {
    process: (data) => api.post('/pipeline/process', data)
  },

  // 任务
  tasks: {
    list: (params) => api.get('/tasks', { params }),
    get: (id) => api.get(`/tasks/${id}`),
    create: (data) => api.post('/tasks', data),
    delete: (id) => api.delete(`/tasks/${id}`)
  }
}
