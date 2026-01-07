<template>
  <div class="table-node bg-white dark:bg-slate-800 rounded-lg shadow-lg border-2 border-gray-200 dark:border-slate-700 min-w-[200px] overflow-hidden transition-all duration-200"
       :class="{ 'border-blue-500 dark:border-blue-500': data.selected }">
    <!-- 头部：表名 -->
    <div class="header bg-gradient-to-r from-blue-600 to-blue-700 dark:from-blue-700 dark:to-blue-800 px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <el-icon class="text-white" :size="18">
          <Grid />
        </el-icon>
        <span class="text-white font-bold text-sm truncate">{{ data.tableName }}</span>
      </div>
      <el-tag size="small" class="!bg-blue-500/30 !border-blue-400 !text-white" effect="dark">
        {{ data.fields?.length || 0 }}
      </el-tag>
    </div>

    <!-- 内容区：字段列表（前5个） -->
    <div class="fields-list divide-y divide-gray-100 dark:divide-slate-700">
      <div 
        v-for="(field, index) in displayFields" 
        :key="index"
        class="field-item px-4 py-2 flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
      >
        <!-- 字段类型图标 -->
        <el-icon class="text-gray-400 dark:text-slate-500" :size="14">
          <component :is="getFieldIcon(field.type)" />
        </el-icon>
        
        <!-- 字段名 -->
        <span class="text-xs text-gray-700 dark:text-slate-300 truncate flex-1">
          {{ field.name }}
        </span>
        
        <!-- 字段类型标签 -->
        <span class="text-[10px] text-gray-400 dark:text-slate-500 uppercase">
          {{ formatFieldType(field.type) }}
        </span>
      </div>
      
      <!-- 更多字段提示 -->
      <div v-if="hasMoreFields" class="px-4 py-2 text-center">
        <span class="text-xs text-gray-400 dark:text-slate-500">
          +{{ data.fields.length - 5 }} 个字段
        </span>
      </div>
    </div>

    <!-- 连接点 Handles -->
    <Handle 
      type="source" 
      :position="Position.Right" 
      class="!w-3 !h-3 !bg-blue-500 !border-2 !border-white dark:!border-slate-800"
    />
    <Handle 
      type="target" 
      :position="Position.Left" 
      class="!w-3 !h-3 !bg-green-500 !border-2 !border-white dark:!border-slate-800"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Grid, Key, Calendar, Document, Link } from '@element-plus/icons-vue'

interface Field {
  name: string
  type: string
  isPrimaryKey?: boolean
  isForeignKey?: boolean
}

interface TableNodeData {
  tableName: string
  fields: Field[]
  selected?: boolean
}

interface Props {
  data: TableNodeData
}

const props = defineProps<Props>()

// 显示前5个字段
const displayFields = computed(() => {
  return props.data.fields?.slice(0, 5) || []
})

// 判断是否有更多字段
const hasMoreFields = computed(() => {
  return props.data.fields && props.data.fields.length > 5
})

// 根据字段类型返回图标组件
const getFieldIcon = (type: string) => {
  const lowerType = type.toLowerCase()
  
  if (lowerType.includes('int') || lowerType.includes('number') || lowerType.includes('numeric') || lowerType.includes('decimal')) {
    return Key
  }
  if (lowerType.includes('date') || lowerType.includes('time')) {
    return Calendar
  }
  if (lowerType.includes('bool')) {
    return Document
  }
  if (lowerType.includes('varchar') || lowerType.includes('text') || lowerType.includes('char')) {
    return Document
  }
  
  return Document
}

// 格式化字段类型显示
const formatFieldType = (type: string) => {
  if (type.length > 8) {
    return type.substring(0, 8)
  }
  return type
}
</script>

<style scoped>
.table-node {
  cursor: pointer;
  user-select: none;
}

.table-node:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
}

/* Handle 悬停效果 */
:deep(.vue-flow__handle) {
  transition: all 0.2s;
}

:deep(.vue-flow__handle:hover) {
  transform: scale(1.3);
}
</style>
