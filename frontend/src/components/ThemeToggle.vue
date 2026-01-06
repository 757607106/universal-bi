<template>
  <el-button
    link
    @click="toggleTheme"
    class="relative rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 p-2"
  >
    <el-icon class="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0 text-gray-700">
      <Sunny />
    </el-icon>
    <el-icon class="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100 text-gray-200">
      <Moon />
    </el-icon>
    <span class="sr-only">切换主题</span>
  </el-button>
</template>

<script setup lang="ts">
import { Sunny, Moon } from '@element-plus/icons-vue'
import { useTheme } from '../composables/useTheme'

const { toggleTheme } = useTheme()
</script>
