import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/connections'
  },
  {
    path: '/connections',
    name: 'connections',
    component: () => import('@/components/DataConnectionHub.vue')
  },
  {
    path: '/datasets',
    name: 'datasets',
    component: () => import('@/views/Dataset/index.vue')
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/Chat/index.vue')
  },
  {
    path: '/dashboard',
    name: 'dashboard-list',
    component: () => import('@/views/Dashboard/index.vue')
  },
  {
    path: '/dashboard/:id',
    name: 'dashboard-detail',
    component: () => import('@/views/Dashboard/Detail.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
