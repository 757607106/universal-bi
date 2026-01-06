<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="400px"
    :before-close="handleClose"
  >
    <p class="text-gray-600 dark:text-gray-400">{{ description }}</p>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">
          取消
        </el-button>
        <el-button
          type="danger"
          @click="handleConfirm"
        >
          删除
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  title: string
  description: string
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
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
}

const handleConfirm = () => {
  emit('confirm')
  dialogVisible.value = false
}
</script>
