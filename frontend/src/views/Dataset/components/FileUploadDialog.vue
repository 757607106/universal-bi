<template>
  <el-dialog
    v-model="visible"
    title="上传Excel/CSV文件"
    width="600px"
    :before-close="handleClose"
    class="file-upload-dialog"
  >
    <div class="upload-container">
      <el-upload
        ref="uploadRef"
        class="upload-demo"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :before-upload="beforeUpload"
        :limit="1"
        :on-exceed="handleExceed"
        accept=".xlsx,.xls,.csv"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .xlsx / .xls / .csv 格式，最大 20MB，最多 50,000 行
          </div>
        </template>
      </el-upload>

      <!-- 文件信息展示 -->
      <div v-if="selectedFile" class="file-info mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <el-icon class="text-blue-500"><Document /></el-icon>
            <span class="font-medium">{{ selectedFile.name }}</span>
          </div>
          <el-tag type="info" size="small">{{ formatFileSize(selectedFile.size) }}</el-tag>
        </div>
      </div>

      <!-- 上传进度 -->
      <div v-if="uploading" class="mt-4">
        <el-progress :percentage="uploadProgress" :status="uploadStatus" />
        <p class="text-sm text-gray-500 mt-2 text-center">{{ uploadMessage }}</p>
      </div>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose" :disabled="uploading">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleUpload" 
          :loading="uploading"
          :disabled="!selectedFile"
        >
          {{ uploading ? '上传中...' : '开始上传' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox, type UploadInstance, type UploadRawFile, type UploadFile } from 'element-plus'
import { UploadFilled, Document } from '@element-plus/icons-vue'
import { uploadFile, type FileUploadResponse } from '@/api/upload'
import { useRouter } from 'vue-router'

const router = useRouter()

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'refresh'): void
}>()

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref<'success' | 'exception' | 'warning' | undefined>(undefined)
const uploadMessage = ref('准备上传...')

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 文件选择
const handleFileChange = (uploadFile: UploadFile) => {
  if (uploadFile.raw) {
    selectedFile.value = uploadFile.raw
  }
}

// 文件上传前检查
const beforeUpload = (rawFile: UploadRawFile) => {
  const isValidType = /\.(xlsx?|csv)$/i.test(rawFile.name)
  const isLt20M = rawFile.size / 1024 / 1024 < 20

  if (!isValidType) {
    ElMessage.error('只支持 .xlsx、.xls 或 .csv 格式的文件！')
    return false
  }
  if (!isLt20M) {
    ElMessage.error('文件大小不能超过 20MB！')
    return false
  }
  return true
}

// 文件数量超限
const handleExceed = () => {
  ElMessage.warning('只能上传一个文件，请删除后重新上传')
}

// 开始上传
const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = undefined
  uploadMessage.value = '正在上传文件...'

  try {
    // 模拟进度
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 80) {
        uploadProgress.value += 10
      }
    }, 200)

    // 调用上传API
    const result: FileUploadResponse = await uploadFile(selectedFile.value)

    clearInterval(progressInterval)
    uploadProgress.value = 90
    uploadMessage.value = '正在处理文件...'

    // 模拟处理进度
    await new Promise(resolve => setTimeout(resolve, 500))
    uploadProgress.value = 100
    uploadStatus.value = 'success'
    uploadMessage.value = '上传成功！'

    // 显示成功消息并询问是否跳转
    await ElMessageBox.confirm(
      `${result.message}\n\n文件名: ${result.dataset_name}\n导入行数: ${result.row_count}\n列数: ${result.column_count}\n\n数据集正在训练中，预计需要1-2分钟。\n是否立即前往对话界面？（训练完成后即可提问）`,
      '上传成功',
      {
        confirmButtonText: '前往对话',
        cancelButtonText: '留在此页',
        type: 'success',
      }
    ).then(() => {
      // 跳转到对话界面，传递dataset_id
      router.push({
        name: 'Chat',
        query: {
          dataset: String(result.dataset_id)
        }
      })
    }).catch(() => {
      // 用户选择留在当前页，刷新数据集列表
      emit('refresh')
    })

    // 关闭对话框
    handleClose()

  } catch (error: any) {
    uploadProgress.value = 100
    uploadStatus.value = 'exception'
    uploadMessage.value = '上传失败'
    
    const errorMsg = error.response?.data?.detail || error.message || '上传失败，请重试'
    ElMessage.error(errorMsg)
    console.error('Upload error:', error)
  } finally {
    uploading.value = false
  }
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 关闭对话框
const handleClose = () => {
  if (uploading.value) {
    ElMessage.warning('正在上传中，请稍候...')
    return
  }
  
  // 重置状态
  selectedFile.value = null
  uploadProgress.value = 0
  uploadStatus.value = undefined
  uploadMessage.value = '准备上传...'
  uploadRef.value?.clearFiles()
  
  visible.value = false
}
</script>

<style scoped>
.upload-container {
  padding: 20px 0;
}

.el-upload__tip {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 8px;
}

.file-info {
  border: 1px solid var(--el-color-primary-light-5);
}

:deep(.el-upload-dragger) {
  padding: 40px;
}

:deep(.el-icon--upload) {
  font-size: 67px;
  color: var(--el-color-primary);
  margin-bottom: 16px;
}

:deep(.el-upload__text) {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

:deep(.el-upload__text em) {
  color: var(--el-color-primary);
  font-style: normal;
}
</style>

