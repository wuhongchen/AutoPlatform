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
        meta: { title: '我的文章', icon: 'Document' }
      },
      {
        path: 'records',
        name: 'Records',
        component: () => import('../views/Records.vue'),
        meta: { title: 'AI记录', icon: 'List' }
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
        meta: { title: '素材库', icon: 'Collection' }
      },
      {
        path: 'styles',
        name: 'Styles',
        component: () => import('../views/Styles.vue'),
        meta: { title: '改写风格', icon: 'BrushFilled' }
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('../views/Tasks.vue'),
        meta: { title: '任务看板', icon: 'List' }
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

// 路由守卫：页面切换时自动滚动到顶部
router.beforeEach((to, from, next) => {
  window.scrollTo(0, 0)
  next()
})

export default router
