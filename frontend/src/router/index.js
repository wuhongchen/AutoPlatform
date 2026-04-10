import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../views/Layout.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '概览', icon: 'HomeFilled' }
      },
      {
        path: 'accounts',
        name: 'Accounts',
        component: () => import('../views/Accounts.vue'),
        meta: { title: '账户管理', icon: 'UserFilled' }
      },
      {
        path: 'articles',
        name: 'Articles',
        component: () => import('../views/Articles.vue'),
        meta: { title: '文章管理', icon: 'Document' }
      },
      {
        path: 'rewrite',
        name: 'Rewrite',
        component: () => import('../views/Rewrite.vue'),
        meta: { title: 'AI 改写', icon: 'MagicStick' }
      },
      {
        path: 'inspirations',
        name: 'Inspirations',
        component: () => import('../views/Inspirations.vue'),
        meta: { title: '灵感库', icon: 'Lightbulb' }
      },
      {
        path: 'styles',
        name: 'Styles',
        component: () => import('../views/Styles.vue'),
        meta: { title: '改写风格', icon: 'BrushFilled' }
      },
      {
        path: 'pipeline',
        name: 'Pipeline',
        component: () => import('../views/Pipeline.vue'),
        meta: { title: '流水线', icon: 'Refresh' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
