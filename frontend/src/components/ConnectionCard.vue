<template>
  <el-card
    class="relative p-0 hover:shadow-xl dark:hover:shadow-blue-900/10 transition-all duration-300 bg-white dark:bg-slate-800/60 dark:backdrop-blur-md border-gray-200 dark:border-slate-700 group hover:-translate-y-1 rounded-2xl overflow-visible"
    :body-style="{ padding: '1.5rem' }"
    shadow="never"
  >
    <div class="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl opacity-0 group-hover:opacity-10 transition duration-500 blur"></div>
    
    <div class="relative flex items-start justify-between mb-6">
      <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-500/10 dark:to-indigo-500/10 flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-sm border border-blue-100 dark:border-blue-500/20">
        <el-icon class="w-7 h-7 text-blue-600 dark:text-blue-400">
          <DataAnalysis />
        </el-icon>
      </div>
      <el-dropdown
        trigger="click"
        class="opacity-0 group-hover:opacity-100 transition-all duration-200 transform translate-x-2 group-hover:translate-x-0"
        @command="handleCommand"
      >
        <el-button link class="!h-8 !w-8 !p-0 rounded-full hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors">
          <el-icon class="w-5 h-5 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300">
            <More />
          </el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu class="!rounded-xl !p-2">
            <el-dropdown-item command="edit" class="!rounded-lg !mb-1">
              <el-icon><Edit /></el-icon> 编辑
            </el-dropdown-item>
            <el-dropdown-item command="delete" class="!rounded-lg text-red-600 dark:text-red-400 hover:!bg-red-50 dark:hover:!bg-red-900/20">
              <el-icon><Delete /></el-icon> 删除
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <h3 class="font-bold text-xl mb-2 text-gray-900 dark:text-slate-100 tracking-tight transition-colors">{{ name }}</h3>
    <div class="flex items-center gap-2 mb-6">
      <span class="px-2.5 py-1 rounded-md bg-gray-100 dark:bg-slate-700/50 text-xs font-medium text-gray-600 dark:text-slate-400 border border-gray-200 dark:border-slate-600 transition-colors">
        {{ type }}
      </span>
    </div>

    <div class="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-slate-700/50 transition-colors">
      <div class="flex items-center gap-2">
        <span class="relative flex h-2.5 w-2.5">
          <span 
            v-if="status === '已连接'"
            class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
          ></span>
          <span 
            :class="`relative inline-flex rounded-full h-2.5 w-2.5 ${status === '已连接' ? 'bg-green-500' : 'bg-gray-400 dark:bg-slate-600'}`"
          ></span>
        </span>
        <span class="text-sm font-medium text-gray-600 dark:text-slate-400 transition-colors">{{ status }}</span>
      </div>
      <span v-if="lastSync" class="text-xs text-gray-400 dark:text-slate-500 font-medium transition-colors">{{ lastSync }}</span>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { DataAnalysis, More, Edit, Delete } from '@element-plus/icons-vue'

interface Props {
  name: string
  type: string
  status: '已连接' | '未连接'
  lastSync?: string
}

interface Emits {
  (e: 'edit'): void
  (e: 'delete'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const handleCommand = (command: string) => {
  if (command === 'edit') {
    emit('edit')
  } else if (command === 'delete') {
    emit('delete')
  }
}
</script>
