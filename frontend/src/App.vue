<template>
  <div class="h-screen w-full flex bg-gray-50 dark:bg-slate-950 text-slate-900 dark:text-slate-200 overflow-hidden font-sans transition-colors duration-300">
    <!-- 侧边栏 Sidebar -->
    <Sidebar />

    <!-- 主内容区 -->
    <main class="flex-1 flex flex-col min-w-0 bg-gray-50 dark:bg-slate-950 relative transition-colors duration-300">
      <!-- 顶部 Header -->
      <header class="h-16 flex-shrink-0 flex items-center justify-between px-6 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-gray-200 dark:border-slate-800 z-20 sticky top-0 transition-colors duration-300">
        <!-- 左侧: 面包屑或标题 -->
        <div class="flex items-center text-sm">
          <span class="text-gray-500 dark:text-slate-400 mr-2">工作台</span>
          <span class="mx-2 text-gray-300 dark:text-slate-600">/</span>
          <span class="text-gray-900 dark:text-slate-200 font-medium">{{ currentViewLabel }}</span>
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

          <!-- 通知铃铛 -->
          <button class="relative p-2 rounded-full text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors">
            <el-icon class="w-5 h-5"><BellIcon /></el-icon>
            <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-white dark:border-slate-900"></span>
          </button>

          <!-- 设置 -->
          <ThemeToggle />
          <button class="p-2 rounded-full text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors">
            <el-icon class="w-5 h-5"><SettingIcon /></el-icon>
          </button>
        </div>
      </header>

      <!-- 页面内容容器 -->
      <div class="flex-1 overflow-y-auto overflow-x-hidden p-6 scroll-smooth">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRenderIcon } from '@/components/ReIcon'
import Sidebar from '@/components/Sidebar.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'

const router = useRouter()
const route = useRoute()

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
/* 搜索框自定义样式 - 覆盖 Element Plus */
:deep(.custom-search-input .el-input__wrapper) {
  border-radius: 9999px !important; /* Pill shape */
  background-color: rgba(241, 245, 249, 1) !important; /* slate-100 for light */
  box-shadow: none !important;
  border: 1px solid transparent !important;
  padding-left: 1rem;
  transition: all 0.3s;
}

.dark :deep(.custom-search-input .el-input__wrapper) {
  background-color: rgba(30, 41, 59, 0.5) !important; /* slate-800/50 for dark */
  border: 1px solid rgba(51, 65, 85, 1) !important; /* slate-700 */
}

:deep(.custom-search-input .el-input__wrapper:hover),
:deep(.custom-search-input .el-input__wrapper.is-focus) {
  border-color: #3b82f6 !important; /* blue-500 */
  background-color: white !important;
}

.dark :deep(.custom-search-input .el-input__wrapper:hover),
.dark :deep(.custom-search-input .el-input__wrapper.is-focus) {
  background-color: rgba(30, 41, 59, 1) !important;
}

/* 页面切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
