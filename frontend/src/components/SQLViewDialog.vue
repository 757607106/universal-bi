<template>
  <el-dialog
    v-model="dialogVisible"
    title="SQL 查询语句"
    width="700px"
  >
    <div class="mt-4">
      <div class="relative">
        <pre class="bg-gray-900 dark:bg-gray-950 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm border border-gray-700">
          <code>{{ sql }}</code>
        </pre>
        <el-button
          link
          class="absolute top-2 right-2 text-gray-400 hover:text-white"
          @click="handleCopy"
        >
          <el-icon :class="copied ? 'text-green-400' : ''">
            <component :is="copied ? Check : DocumentCopy" class="w-4 h-4" />
          </el-icon>
        </el-button>
      </div>
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
        此 SQL 语句由 AI 自动生成，您可以直接复制到数据库客户端执行
      </p>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Check, DocumentCopy } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

interface Props {
  modelValue: boolean
  sql: string
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const dialogVisible = ref(false)
const copied = ref(false)

// 同步 v-model
watch(() => props.modelValue, (newVal) => {
  dialogVisible.value = newVal
})

watch(dialogVisible, (newVal) => {
  emit('update:modelValue', newVal)
})

const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(props.sql)
    copied.value = true
    ElMessage.success('SQL 已复制到剪贴板')
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    ElMessage.error('复制失败')
  }
}
</script>
