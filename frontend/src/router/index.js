import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../views/Layout.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      // ── 概览 ──
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '概览', icon: 'HomeFilled' }
      },

      // ── 内容生产 ──
      {
        path: 'content',
        redirect: '/content-flow',
        meta: { title: '内容生产', icon: 'MagicStick' },
        children: [
          {
            path: '/content-flow',
            name: 'ContentFlow',
            component: () => import('../views/ContentFlow.vue'),
            meta: { title: '链接成稿', icon: 'Link' }
          },
          {
            path: '/rewrite',
            name: 'Rewrite',
            component: () => import('../views/Rewrite.vue'),
            meta: { title: 'AI 改写', icon: 'MagicStick' }
          },
          {
            path: '/articles',
            name: 'Articles',
            component: () => import('../views/Articles.vue'),
            meta: { title: '我的文章', icon: 'Document' }
          },
          {
            path: '/records',
            name: 'Records',
            component: () => import('../views/Records.vue'),
            meta: { title: 'AI 记录', icon: 'List' }
          }
        ]
      },

      // ── 信息源管理 ──
      {
        path: 'source',
        redirect: '/feeds',
        meta: { title: '信息源管理', icon: 'Collection' },
        children: [
          {
            path: '/feeds',
            name: 'Feeds',
            component: () => import('../views/Feeds.vue'),
            meta: { title: 'RSS 订阅', icon: 'Connection' }
          },
          {
            path: '/inspirations',
            name: 'Inspirations',
            component: () => import('../views/Inspirations.vue'),
            meta: { title: '素材库', icon: 'Collection' }
          }
        ]
      },

      // ── AI 引擎 ──
      {
        path: 'ai',
        redirect: '/styles',
        meta: { title: 'AI 引擎', icon: 'Cpu' },
        children: [
          {
            path: '/styles',
            name: 'Styles',
            component: () => import('../views/Styles.vue'),
            meta: { title: '改写风格', icon: 'BrushFilled' }
          },
          {
            path: '/ai-settings',
            name: 'AISettings',
            component: () => import('../views/AISettings.vue'),
            meta: { title: 'AI 设置', icon: 'Cpu' }
          }
        ]
      },

      // ── 系统 ──
      {
        path: '/tasks',
        name: 'Tasks',
        component: () => import('../views/Tasks.vue'),
        meta: { title: '任务看板', icon: 'List' }
      },
      {
        path: '/accounts',
        name: 'Accounts',
        component: () => import('../views/Accounts.vue'),
        meta: { title: '账户管理', icon: 'UserFilled' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  window.scrollTo(0, 0)
  next()
})

export default router
