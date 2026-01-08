<template>
  <aside class="w-64 flex-shrink-0 flex flex-col bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-800 transition-colors duration-300">
    <!-- Logo 区域 -->
    <div class="h-16 flex items-center px-6 border-b border-gray-100 dark:border-slate-800">
      <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/20 mr-3">
        <el-icon class="w-5 h-5 text-white font-bold"><DataAnalysis /></el-icon>
      </div>
      <span class="text-xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 dark:from-blue-400 dark:to-cyan-400 bg-clip-text text-transparent tracking-wide">
        Universal BI
      </span>
    </div>

    <!-- 导航菜单 -->
    <nav class="flex-1 overflow-y-auto py-6 px-3 space-y-1">
      <template v-for="item in navigation" :key="item.id">
        <router-link
          :to="item.path"
          custom
          v-slot="{ navigate, isActive }"
        >
          <button
            @click="navigate"
            class="w-full flex items-center px-3 py-3 rounded-lg text-sm font-medium transition-all duration-200 group relative"
            :class="[
              isActive
                ? 'bg-blue-50 text-blue-600 dark:bg-slate-800 dark:text-blue-400'
                : 'text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800/50 hover:text-gray-900 dark:hover:text-slate-200'
            ]"
          >
            <!-- 左侧高亮条 (选中状态) -->
            <div
              v-if="isActive"
              class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-blue-500 rounded-r-full shadow-sm"
            ></div>

            <el-icon class="w-5 h-5 mr-3 transition-colors" :class="isActive ? 'text-blue-500' : 'text-gray-400 dark:text-slate-500 group-hover:text-gray-600 dark:group-hover:text-slate-300'">
              <component :is="item.icon" />
            </el-icon>
            <span>{{ item.label }}</span>
          </button>
        </router-link>
      </template>
    </nav>

    <!-- 底部区域 -->
    <div class="p-4 border-t border-gray-100 dark:border-slate-800 space-y-4">
      <!-- 主题切换 -->
      <div class="flex items-center justify-between px-2">
        <span class="text-xs font-medium text-gray-400 dark:text-slate-500 uppercase tracking-wider">Theme</span>
        <ThemeToggle />
      </div>

      <!-- 用户信息 -->
      <div class="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer group" @click="handleLogout">
        <el-avatar :size="36" class="!bg-blue-100 !text-blue-600 dark:!bg-blue-900 dark:!text-blue-200 border-2 border-white dark:border-slate-700 shadow-sm">{{ userStore.avatar }}</el-avatar>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-gray-900 dark:text-slate-200 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{{ userStore.username }}</p>
          <p class="text-xs text-gray-500 dark:text-slate-500 truncate">{{ userStore.email }}</p>
        </div>
        <el-icon class="text-gray-400 dark:text-slate-500 group-hover:text-blue-500 transition-colors">
          <component :is="useRenderIcon('ep:switch-button')" />
        </el-icon>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRenderIcon } from '@/components/ReIcon'
import ThemeToggle from './ThemeToggle.vue'
import { useUserStore } from '@/store/modules/user'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const router = useRouter()

const baseNavigation = [
  { id: 'connections', label: '数据连接', icon: useRenderIcon('ep:data-analysis'), path: '/connections' },
  { id: 'data-tables', label: '数据表', icon: useRenderIcon('ep:document'), path: '/data-tables' },
  { id: 'datasets', label: '数据集管理', icon: useRenderIcon('ep:files'), path: '/datasets' },
  { id: 'chat', label: '智能问答', icon: useRenderIcon('ep:chat-dot-round'), path: '/chat' },
  { id: 'dashboard', label: '数据看板', icon: useRenderIcon('ep:grid'), path: '/dashboard' },
]

const adminNavigation = [
  { id: 'system-user', label: '用户管理', icon: useRenderIcon('ep:user'), path: '/system/user' },
]

// 根据用户权限动态生成导航菜单
const navigation = computed(() => {
  if (userStore.is_superuser) {
    return [...baseNavigation, ...adminNavigation]
  }
  return baseNavigation
})

// 退出登录
const handleLogout = async () => {
  try {
    await userStore.logOut()
    ElMessage.success('退出登录成功')
    router.push('/login')
  } catch (error) {
    console.error('退出登录失败:', error)
    ElMessage.error('退出登录失败')
  }
}
</script>
