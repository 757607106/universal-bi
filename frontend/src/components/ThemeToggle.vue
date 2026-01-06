<template>
  <button
    @click="toggleTheme"
    class="p-2 rounded-full transition-all duration-300 hover:bg-gray-200 dark:hover:bg-slate-700 focus:outline-none ring-offset-2 focus:ring-2 ring-blue-500"
    :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
  >
    <el-icon :size="20" class="text-gray-600 dark:text-gray-300">
      <Icon :icon="isDark ? 'ep:sunny' : 'ep:moon'" />
    </el-icon>
  </button>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { useTheme } from '@/composables/useTheme'

const { isDark, toggleTheme } = useTheme()
</script>
