<template>
  <div class="h-screen w-full flex bg-gray-50 dark:bg-dark-bg text-slate-900 dark:text-slate-200 overflow-hidden font-sans transition-colors duration-300 relative">
    <!-- 动态背景层 (仅在 Dark Mode 启用) -->
    <div class="absolute inset-0 z-0 pointer-events-none opacity-0 dark:opacity-100 transition-opacity duration-1000">
      <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-primary-glow/20 blur-[120px] animate-float"></div>
      <div class="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-cyber-purple/20 blur-[120px] animate-float" style="animation-delay: -3s"></div>
      <div class="absolute inset-0 bg-cyber-grid opacity-[0.15]"></div>
    </div>

    <!-- 侧边栏 Sidebar -->
    <Sidebar class="z-30 relative" />

    <!-- 主内容区 -->
    <main class="flex-1 flex flex-col min-w-0 bg-transparent relative z-10 transition-colors duration-300">
      <!-- 顶部 Header -->
      <header class="h-16 flex-shrink-0 flex items-center justify-between px-6 bg-white/70 dark:bg-dark-glass backdrop-blur-md border-b border-gray-200/50 dark:border-white/5 z-20 sticky top-0 transition-all duration-300 shadow-sm dark:shadow-none">
        <!-- 左侧: 面包屑或标题 -->
        <div class="flex items-center text-sm">
          <span class="text-gray-500 dark:text-slate-400 mr-2 font-medium">工作台</span>
          <span class="mx-2 text-gray-300 dark:text-slate-600">/</span>
          <span class="text-gray-900 dark:text-slate-100 font-semibold tracking-wide bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-slate-300">
            {{ currentViewLabel }}
          </span>
        </div>

        <!-- 右侧: 工具栏 -->
        <div class="flex items-center gap-4">
          <!-- 搜索框 -->
          <div class="relative group">
            <el-input
              v-model="searchQuery"
              placeholder="搜索数据、报表..."
              class="w-64 !bg-transparent custom-search-input"
              :prefix-icon="SearchIcon"
            />
          </div>

          <!-- 通知铃铛 (功能开发中) -->
          <el-tooltip content="通知功能开发中" placement="bottom">
            <button class="relative p-2 rounded-full text-gray-400 dark:text-slate-400 hover:text-primary dark:hover:text-primary-glow transition-colors group">
              <el-icon class="w-5 h-5 group-hover:animate-swing"><BellIcon /></el-icon>
              <span class="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white dark:border-dark-bg"></span>
            </button>
          </el-tooltip>

          <!-- 设置 -->
          <ThemeToggle />
          <button class="p-2 rounded-full text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 hover:bg-gray-100 dark:hover:bg-white/5 transition-colors">
            <el-icon class="w-5 h-5"><SettingIcon /></el-icon>
          </button>
        </div>
      </header>

      <!-- 页面内容容器 -->
      <div class="flex-1 overflow-y-auto overflow-x-hidden p-6 scroll-smooth relative">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRenderIcon } from '@/components/ReIcon'
import Sidebar from '@/components/Sidebar.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { useUserStore } from '@/store/modules/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 组件加载时获取用户信息（如果还没有）
onMounted(async () => {
  if (!userStore.userId && userStore.token) {
    try {
      await userStore.getUserInfo()
    } catch (error) {
      console.error('获取用户信息失败:', error)
    }
  }
})

type View = 'connections' | 'datasets' | 'chat' | 'dashboard' | 'settings'

const searchQuery = ref('')

const SearchIcon = useRenderIcon('ep:search')
const BellIcon = useRenderIcon('ep:bell')
const SettingIcon = useRenderIcon('ep:setting')

// Navigation list used for title resolution
const navigation = [
  { id: 'connections' as View, label: '数据连接', icon: useRenderIcon('ep:data-analysis') },
  { id: 'datasets' as View, label: '数据集管理', icon: useRenderIcon('ep:files') },
  { id: 'chat' as View, label: '智能问答', icon: useRenderIcon('ep:chat-dot-round') },
  { id: 'dashboard' as View, label: '数据看板', icon: useRenderIcon('ep:grid') },
  { id: 'settings' as View, label: '系统设置', icon: useRenderIcon('ep:setting') },
]

const activeView = computed<View>(() => {
  const path = route.path
  if (path.startsWith('/dashboard')) return 'dashboard'
  if (path.startsWith('/chat')) return 'chat'
  if (path.startsWith('/datasets')) return 'datasets'
  if (path.startsWith('/settings')) return 'settings'
  return 'connections'
})

const currentViewLabel = computed(() => {
  const item = navigation.find(n => n.id === activeView.value)
  return item ? item.label : '首页'
})
</script>

<style scoped>
/* Mobile Drawer Styles */
:deep(.mobile-sidebar-drawer .el-drawer__body) {
  padding: 0;
  background-color: transparent;
}

/* 搜索框自定义样式 - 覆盖 Element Plus */
:deep(.custom-search-input .el-input__wrapper) {
  border-radius: 9999px !important; /* Pill shape */
  background-color: rgba(255, 255, 255, 0.5) !important;
  box-shadow: none !important;
  border: 1px solid rgba(226, 232, 240, 0.8); /* gray-200 */
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding-left: 16px;
}

:deep(.custom-search-input .el-input__wrapper:hover) {
  border-color: #94a3b8; /* slate-400 */
  background-color: rgba(255, 255, 255, 0.8) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

:deep(.custom-search-input .el-input__wrapper.is-focus) {
  border-color: #3b82f6 !important; /* blue-500 */
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
  background-color: white !important;
  width: 280px; /* Expand on focus */
}

/* Dark mode adjustments */
:deep(.dark .custom-search-input .el-input__wrapper) {
  background-color: rgba(30, 41, 59, 0.4) !important; /* slate-800/40 */
  border-color: rgba(255, 255, 255, 0.1);
}

:deep(.dark .custom-search-input .el-input__wrapper:hover) {
  border-color: rgba(255, 255, 255, 0.2);
  background-color: rgba(30, 41, 59, 0.6) !important;
}

:deep(.dark .custom-search-input .el-input__wrapper.is-focus) {
  border-color: #3b82f6 !important;
  background-color: rgba(15, 23, 42, 0.8) !important; /* slate-900 */
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
}

/* Page Transition */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.98);
}

@keyframes swing {
  20% { transform: rotate(15deg); }
  40% { transform: rotate(-10deg); }
  60% { transform: rotate(5deg); }
  80% { transform: rotate(-5deg); }
  100% { transform: rotate(0deg); }
}

.animate-swing {
  animation: swing 1s ease-in-out;
}
</style>
