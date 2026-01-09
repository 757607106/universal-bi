<template>
  <aside class="w-64 flex-shrink-0 flex flex-col bg-white/70 dark:bg-dark-glass border-r border-gray-200/50 dark:border-white/5 backdrop-blur-md transition-colors duration-300 relative z-30 shadow-[4px_0_24px_rgba(0,0,0,0.02)] dark:shadow-none">
    <!-- Logo 区域 -->
    <div class="h-16 flex items-center px-6 border-b border-gray-100/50 dark:border-white/5">
      <div class="relative w-8 h-8 mr-3 group">
        <div class="absolute inset-0 bg-gradient-to-br from-primary to-cyber-cyan rounded-lg blur-sm opacity-50 group-hover:opacity-100 transition-opacity duration-500 animate-pulse-glow"></div>
        <div class="relative w-full h-full rounded-lg bg-gradient-to-br from-primary to-cyber-cyan flex items-center justify-center shadow-lg text-white">
          <el-icon class="w-5 h-5 font-bold"><DataAnalysis /></el-icon>
        </div>
      </div>
      <span class="text-xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 dark:from-white dark:to-slate-300 bg-clip-text text-transparent tracking-wide">
        Universal BI
      </span>
    </div>

    <!-- 导航菜单 -->
    <nav class="flex-1 overflow-y-auto py-6 px-3 space-y-1.5 custom-scrollbar">
      <template v-for="item in navigation" :key="item.id">
        <router-link
          :to="item.path"
          custom
          v-slot="{ navigate, isActive }"
        >
          <button
            @click="navigate(); $emit('click-item')"
            class="w-full flex items-center px-3 py-3 rounded-xl text-sm font-medium transition-all duration-300 group relative overflow-hidden"
            :class="[
              isActive
                ? 'text-white shadow-neon'
                : 'text-gray-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
            ]"
          >
            <!-- 选中背景 (赛博渐变) -->
            <div
              v-if="isActive"
              class="absolute inset-0 bg-gradient-to-r from-primary to-cyber-cyan opacity-100"
            ></div>
            
            <!-- 悬停背景 (玻璃光泽) -->
            <div
              v-else
              class="absolute inset-0 bg-white dark:bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 border border-transparent dark:border-white/5"
            ></div>

            <!-- 悬停流光动画 -->
            <div v-if="!isActive" class="absolute inset-0 opacity-0 group-hover:opacity-20 bg-gradient-to-r from-transparent via-white to-transparent -translate-x-full group-hover:animate-shimmer" style="background-size: 200% 100%"></div>

            <el-icon class="w-5 h-5 mr-3 transition-transform duration-300 group-hover:scale-110 relative z-10" :class="isActive ? 'text-white' : 'text-gray-400 dark:text-slate-500 group-hover:text-primary dark:group-hover:text-primary-glow'">
              <component :is="item.icon" />
            </el-icon>
            <span class="relative z-10 tracking-wide">{{ item.label }}</span>
            
            <!-- 选中指示点 -->
            <div v-if="isActive" class="absolute right-3 w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)]"></div>
          </button>
        </router-link>
      </template>
    </nav>

    <!-- 底部区域 -->
    <div class="p-4 border-t border-gray-100/50 dark:border-white/5 space-y-4 bg-gray-50/50 dark:bg-white/[0.02]">
      <!-- 用户信息 -->
      <div class="relative group cursor-pointer" @click="handleLogout">
        <div class="absolute inset-0 bg-white dark:bg-white/5 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 border border-transparent dark:border-white/5 shadow-lg dark:shadow-none"></div>
        <div class="flex items-center gap-3 px-3 py-2.5 relative z-10">
          <div class="relative">
            <el-avatar :size="36" class="!bg-gradient-to-br !from-primary !to-cyber-purple !text-white border-2 border-white dark:border-dark-bg shadow-md">
              {{ userStore.avatar }}
            </el-avatar>
            <div class="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-white dark:border-dark-bg"></div>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-gray-900 dark:text-slate-200 truncate group-hover:text-primary dark:group-hover:text-primary-glow transition-colors">{{ userStore.username }}</p>
            <p class="text-xs text-gray-500 dark:text-slate-500 truncate">点击退出登录</p>
          </div>
          <el-icon class="text-gray-400 dark:text-slate-600 group-hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 transform translate-x-2 group-hover:translate-x-0 duration-300">
            <component :is="useRenderIcon('ep:switch-button')" />
          </el-icon>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRenderIcon } from '@/components/ReIcon'
import { useUserStore } from '@/store/modules/user'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis } from '@element-plus/icons-vue'

const userStore = useUserStore()
const router = useRouter()

const baseNavigation = [
  { id: 'connections', label: '数据连接', icon: useRenderIcon('ep:data-analysis'), path: '/connections' },
  { id: 'datasets', label: '数据中心', icon: useRenderIcon('ep:files'), path: '/datasets' }, // Updated label
  { id: 'chat', label: '智能问答', icon: useRenderIcon('ep:chat-dot-round'), path: '/chat' },
  { id: 'dashboard', label: '数据看板', icon: useRenderIcon('ep:grid'), path: '/dashboard' },
]

const adminNavigation = [
  { id: 'system-user', label: '用户管理', icon: useRenderIcon('ep:user'), path: '/system/user' },
]

// 根据用户权限动态生成导航菜单
const navigation = computed(() => {
  // 移除独立的 'data-tables' 入口，因为已整合进数据集
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

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.3);
  border-radius: 4px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.5);
}
</style>
