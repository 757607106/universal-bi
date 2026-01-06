<template>
  <div class="h-screen flex flex-col bg-gray-50 dark:bg-gray-950 transition-colors duration-300">
    <!-- 头部导航 -->
    <header class="bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
      <div class="px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#409EFF] to-[#3182ce] flex items-center justify-center shadow-lg shadow-blue-500/30">
              <el-icon class="w-6 h-6 text-white">
                <DataAnalysis />
              </el-icon>
            </div>
            <div>
              <h1 class="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 dark:from-white dark:to-gray-300 bg-clip-text text-transparent">
                通用 BI 平台
              </h1>
              <p class="text-xs text-gray-500 dark:text-gray-400">企业级智能分析套件</p>
            </div>
          </div>

          <div class="flex items-center gap-4">
            <nav class="flex gap-1 p-1 bg-gray-100/50 dark:bg-gray-800/50 rounded-xl">
              <el-button
                v-for="item in navigation"
                :key="item.id"
                :type="activeView === item.id ? 'primary' : 'default'"
                class="!border-none !m-0 !rounded-lg transition-all duration-300"
                :class="[
                  activeView === item.id 
                    ? '!bg-white dark:!bg-gray-700 !text-blue-600 dark:!text-blue-400 shadow-sm' 
                    : '!bg-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                ]"
                text
                @click="setActiveView(item.id)"
              >
                <el-icon class="w-4 h-4 mr-1">
                  <component :is="item.icon" />
                </el-icon>
                <span class="font-medium">{{ item.label }}</span>
              </el-button>
            </nav>

            <div class="h-8 w-px bg-gray-200 dark:bg-gray-700 mx-2" />

            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>

    <!-- 主要内容区 -->
    <main class="flex-1 overflow-hidden">
      <router-view />
    </main>

    <!-- 全局通知使用 Element Plus 的 Message/Notification，移除不存在的 el-toaster 组件 -->
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { DataAnalysis, Files, ChatDotRound, Grid } from '@element-plus/icons-vue'
import ThemeToggle from './components/ThemeToggle.vue'
import { useTheme } from './composables/useTheme'

// 初始化主题
const { theme } = useTheme()

const router = useRouter()
const route = useRoute()

type View = 'connections' | 'datasets' | 'chat' | 'dashboard'

const activeView = computed<View>(() => {
  const path = route.path
  if (path.startsWith('/dashboard')) return 'dashboard'
  if (path.startsWith('/chat')) return 'chat'
  if (path.startsWith('/datasets')) return 'datasets'
  return 'connections'
})

const setActiveView = (view: View) => {
  router.push(`/${view}`)
}

const navigation = [
  { id: 'connections' as View, label: '数据连接', icon: DataAnalysis },
  { id: 'datasets' as View, label: '数据集', icon: Files },
  { id: 'chat' as View, label: '智能问答', icon: ChatDotRound },
  { id: 'dashboard' as View, label: '数据看板', icon: Grid },
]
</script>
