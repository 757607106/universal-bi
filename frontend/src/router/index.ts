import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { getToken } from '@/utils/auth'
import { useUserStore } from '@/store/modules/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login/index.vue'),
    meta: {
      title: '登录',
      showLink: false,
      rank: 101
    }
  },
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    redirect: '/connections',
    children: [
      {
        path: 'connections',
        name: 'connections',
        component: () => import('@/components/DataConnectionHub.vue')
      },
      {
        path: 'datasets',
        name: 'datasets',
        component: () => import('@/views/Dataset/index.vue')
      },
      {
        path: 'data-tables',
        name: 'data-tables',
        component: () => import('@/views/DataTable/index.vue'),
        meta: {
          title: '数据表'
        }
      },
      {
        path: 'datasets/modeling/:id',
        name: 'dataset-modeling',
        component: () => import('@/views/Dataset/modeling/index.vue'),
        meta: {
          title: '可视化建模'
        }
      },
      {
        path: 'chat',
        name: 'chat',
        component: () => import('@/views/Chat/index.vue')
      },
      {
        path: 'dashboard',
        name: 'dashboard-list',
        component: () => import('@/views/Dashboard/index.vue')
      },
      {
        path: 'dashboard/:id',
        name: 'dashboard-detail',
        component: () => import('@/views/Dashboard/Detail.vue')
      },
      {
        path: 'system/user',
        name: 'system-user',
        component: () => import('@/views/System/User/index.vue'),
        meta: {
          title: '用户管理',
          roles: ['admin', 'superuser'],
          requireSuperuser: true
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const token = getToken()
  
  // 未登录，跳转到登录页
  if (to.path !== '/login' && !token) {
    next({ path: '/login' })
    return
  }
  
  // 已登录，访问登录页，跳转到首页
  if (to.path === '/login' && token) {
    next({ path: '/' })
    return
  }
  
  // 检查是否需要超级管理员权限
  if (to.meta.requireSuperuser) {
    const userStore = useUserStore()
    
    // 如果还没有获取用户信息，先获取
    if (!userStore.userId) {
      try {
        await userStore.getUserInfo()
      } catch (error) {
        console.error('获取用户信息失败:', error)
        next({ path: '/login' })
        return
      }
    }
    
    // 检查是否为超级管理员
    if (!userStore.is_superuser) {
      console.warn('权限不足，需要超级管理员权限')
      next({ path: '/' })
      return
    }
  }
  
  next()
})

export default router
