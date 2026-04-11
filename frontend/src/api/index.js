import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
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
    const message = error.response?.data?.error || error.message || '请求失败'
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
    get: (id) => api.get(`/inspirations/${id}`)
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

  // 流水线
  pipeline: {
    process: (data) => api.post('/pipeline/process', data)
  }
}
