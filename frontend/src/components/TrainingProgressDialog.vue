<template>
  <el-dialog
    v-model="dialogVisible"
    title="AI 模型训练中"
    width="500px"
    :close-on-click-modal="isComplete"
    :close-on-press-escape="isComplete"
    :show-close="!isComplete"
  >
    <div class="py-6 space-y-6">
      <div v-if="isComplete" class="flex flex-col items-center justify-center py-8">
        <el-icon class="w-16 h-16 text-green-500 mb-4">
          <CircleCheck />
        </el-icon>
        <h3 class="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">训练完成！</h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 text-center">
          AI 模型已成功训练完成，现在可以开始智能问答了
        </p>
      </div>

      <div v-else>
        <div class="flex items-center gap-3">
          <el-icon class="w-5 h-5 animate-spin text-[#409EFF]">
            <Loading />
          </el-icon>
          <span class="text-sm text-gray-600 dark:text-gray-400">{{ currentStep }}</span>
        </div>

        <div class="space-y-2">
          <div class="flex justify-between text-sm">
            <span class="text-gray-600 dark:text-gray-400">训练进度</span>
            <span class="font-medium text-[#409EFF]">{{ progress }}%</span>
          </div>
          <el-progress :percentage="progress" :stroke-width="8" />
        </div>

        <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p class="text-sm text-blue-800 dark:text-blue-300">
            正在分析数据表结构和关系，这可能需要几分钟时间，请耐心等待...
          </p>
        </div>
      </div>
    </div>

    <template v-if="isComplete" #footer>
      <div class="dialog-footer">
        <el-button
          type="primary"
          @click="handleClose"
          class="bg-[#409EFF] hover:bg-[#3182ce] shadow-lg shadow-blue-500/30"
        >
          开始使用
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { CircleCheck, Loading } from '@element-plus/icons-vue'

interface Props {
  modelValue: boolean
  progress: number
  currentStep: string
  isComplete: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'close'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const dialogVisible = ref(false)

// 同步 v-model
watch(() => props.modelValue, (newVal) => {
  dialogVisible.value = newVal
})

watch(dialogVisible, (newVal) => {
  emit('update:modelValue', newVal)
})

const handleClose = () => {
  dialogVisible.value = false
  emit('close')
}
</script>
