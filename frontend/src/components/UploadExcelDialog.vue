<template>
  <el-dialog
    v-model="dialogVisible"
    title="导入 Excel/CSV 文件"
    width="600px"
    :close-on-click-modal="false"
    @closed="handleClose"
  >
    <div class="space-y-4">
      <!-- 文件名输入 -->
      <el-form label-width="100px">
        <el-form-item label="数据集名称">
          <el-input
            v-model="datasetName"
            placeholder="默认使用文件名"
            :disabled="uploading"
          />
        </el-form-item>
      </el-form>

      <!-- 上传区域 -->
      <el-upload
        ref="uploadRef"
        class="upload-area"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :before-upload="beforeUpload"
        :limit="1"
        accept=".xlsx,.xls,.csv"
        :disabled="uploading"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip text-gray-500 dark:text-slate-400">
            支持 .xlsx / .xls / .csv 格式，文件大小不超过 10MB
          </div>
        </template>
      </el-upload>

      <!-- 文件信息显示 -->
      <div v-if="selectedFile" class="p-4 bg-gray-50 dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-700">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <el-icon class="text-blue-500 text-2xl"><Document /></el-icon>
            <div>
              <div class="font-medium text-gray-900 dark:text-slate-100">{{ selectedFile.name }}</div>
              <div class="text-sm text-gray-500 dark:text-slate-400">{{ formatFileSize(selectedFile.size) }}</div>
            </div>
          </div>
          <el-button
            v-if="!uploading"
            size="small"
            text
            type="danger"
            @click="handleRemoveFile"
          >
            移除
          </el-button>
        </div>
      </div>

      <!-- 上传进度 -->
      <div v-if="uploading" class="space-y-2">
        <el-progress :percentage="uploadProgress" :status="uploadStatus" />
        <div class="text-center text-sm text-gray-500 dark:text-slate-400">
          {{ uploadStatusText }}
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <el-button @click="handleCancel" :disabled="uploading">取消</el-button>
        <el-button
          type="primary"
          @click="handleUpload"
          :loading="uploading"
          :disabled="!selectedFile"
        >
          {{ uploading ? '上传中...' : '开始上传' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Document } from '@element-plus/icons-vue'
import { uploadQuickDataset } from '@/api/dataset'
import type { UploadInstance, UploadRawFile } from 'element-plus'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)
const datasetName = ref('')
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref<'' | 'success' | 'exception'>('')
const uploadStatusText = ref('')

// 监听文件变化，自动设置数据集名称
watch(selectedFile, (newFile) => {
  if (newFile && !datasetName.value) {
    // 提取文件名（不含扩展名）
    const fileName = newFile.name.substring(0, newFile.name.lastIndexOf('.'))
    datasetName.value = fileName
  }
})

const handleFileChange = (file: any) => {
  selectedFile.value = file.raw
}

const beforeUpload = (file: UploadRawFile) => {
  // 文件大小限制 10MB
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过 10MB')
    return false
  }

  // 文件类型限制
  const validTypes = ['.xlsx', '.xls', '.csv']
  const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!validTypes.includes(fileExt)) {
    ElMessage.error('仅支持 .xlsx、.xls、.csv 格式的文件')
    return false
  }

  return true
}

const handleRemoveFile = () => {
  selectedFile.value = null
  uploadRef.value?.clearFiles()
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = ''
  uploadStatusText.value = '正在上传文件...'

  try {
    // 模拟上传进度
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 200)

    uploadStatusText.value = '正在上传并处理文件...'
    
    await uploadQuickDataset(
      selectedFile.value,
      datasetName.value.trim() || undefined
    )

    clearInterval(progressInterval)
    uploadProgress.value = 100
    uploadStatus.value = 'success'
    uploadStatusText.value = '上传成功！数据集已创建并训练完成'

    ElMessage.success('文件上传成功，数据集已创建')
    
    // 延迟关闭，让用户看到成功状态
    setTimeout(() => {
      emit('success')
      dialogVisible.value = false
    }, 1000)
    
  } catch (error: any) {
    uploadStatus.value = 'exception'
    uploadStatusText.value = '上传失败'
    ElMessage.error(error?.message || '文件上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

const handleCancel = () => {
  if (!uploading.value) {
    dialogVisible.value = false
  }
}

const handleClose = () => {
  // 重置状态
  selectedFile.value = null
  datasetName.value = ''
  uploadProgress.value = 0
  uploadStatus.value = ''
  uploadStatusText.value = ''
  uploadRef.value?.clearFiles()
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}
</script>

<style scoped>
.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload) {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  border: 2px dashed #d1d5db;
  background-color: transparent;
  transition: all 0.3s;
}

.dark .upload-area :deep(.el-upload-dragger) {
  border-color: #475569;
  background-color: rgba(51, 65, 85, 0.3);
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: #3b82f6;
}

.dark .upload-area :deep(.el-upload-dragger:hover) {
  border-color: #60a5fa;
}

.upload-area :deep(.el-icon--upload) {
  font-size: 48px;
  color: #3b82f6;
  margin-bottom: 16px;
}

.dark .upload-area :deep(.el-icon--upload) {
  color: #60a5fa;
}

.upload-area :deep(.el-upload__text) {
  color: #6b7280;
}

.dark .upload-area :deep(.el-upload__text) {
  color: #94a3b8;
}

.upload-area :deep(.el-upload__text em) {
  color: #3b82f6;
  font-style: normal;
}

.dark .upload-area :deep(.el-upload__text em) {
  color: #60a5fa;
}
</style>
