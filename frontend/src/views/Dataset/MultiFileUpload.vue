<template>
  <div class="multi-upload-container p-6">
    <div class="mb-6">
      <h2 class="text-2xl font-bold mb-2">多表分析：批量上传文件</h2>
      <p class="text-gray-600">
        支持同时上传多个 Excel/CSV 文件，系统将自动分析表之间的关联关系
      </p>
    </div>

    <!-- 数据集名称输入 -->
    <el-form :model="form" class="mb-4">
      <el-form-item label="数据集名称">
        <el-input
          v-model="form.datasetName"
          placeholder="请输入数据集名称，如：订单分析数据集"
          style="width: 400px"
        />
      </el-form-item>
    </el-form>

    <!-- 文件上传区域 -->
    <el-upload
      ref="uploadRef"
      drag
      multiple
      :auto-upload="false"
      :on-change="handleFileChange"
      :on-remove="handleFileRemove"
      :file-list="fileList"
      accept=".xlsx,.xls,.csv"
      class="mb-4"
    >
      <el-icon class="el-icon--upload" :size="50">
        <upload-filled />
      </el-icon>
      <div class="el-upload__text">
        拖拽多个 Excel/CSV 文件到此处，或 <em>点击选择</em>
      </div>
      <template #tip>
        <div class="el-upload__tip text-sm text-gray-500 mt-2">
          · 支持批量上传，单个文件不超过 20MB<br>
          · 最多同时上传 10 个文件<br>
          · 系统将自动分析表之间的关联关系
        </div>
      </template>
    </el-upload>

    <!-- 文件预览列表 -->
    <div v-if="fileList.length > 0" class="file-preview mb-6">
      <h3 class="text-lg font-semibold mb-3">已选择 {{ fileList.length }} 个文件：</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          v-for="(file, index) in fileList"
          :key="index"
          class="file-card p-4 border border-gray-200 rounded-lg hover:border-blue-400 transition"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center">
              <el-icon class="mr-2 text-green-600" :size="20">
                <document />
              </el-icon>
              <span class="font-medium">{{ file.name }}</span>
            </div>
            <el-tag size="small" type="success">{{ formatFileSize(file.size) }}</el-tag>
          </div>
          <div class="text-sm text-gray-500">
            <span>将生成表名：{{ sanitizeTableName(file.name) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="flex justify-between items-center">
      <el-button @click="clearFiles">清空</el-button>
      <div>
        <el-button @click="$router.back()">取消</el-button>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="fileList.length === 0 || !form.datasetName"
          @click="handleUpload"
        >
          <el-icon class="mr-1"><upload /></el-icon>
          开始上传并分析
        </el-button>
      </div>
    </div>

    <!-- 上传进度提示 -->
    <el-dialog
      v-model="showProgressDialog"
      title="上传进度"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
      width="500px"
    >
      <div class="text-center py-4">
        <el-icon class="text-6xl text-blue-500 mb-4 animate-spin">
          <loading />
        </el-icon>
        <p class="text-lg mb-2">{{ progressMessage }}</p>
        <el-progress :percentage="uploadProgress" :status="progressStatus" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElLoading, type UploadFile, type UploadUserFile } from 'element-plus'
import { UploadFilled, Document, Upload, Loading } from '@element-plus/icons-vue'
import { uploadMultipleFiles } from '@/api/upload'

const router = useRouter()

const form = reactive({
  datasetName: ''
})

const fileList = ref<UploadUserFile[]>([])
const uploading = ref(false)
const showProgressDialog = ref(false)
const uploadProgress = ref(0)
const progressMessage = ref('')
const progressStatus = ref<'success' | 'exception' | 'warning' | undefined>(undefined)

const handleFileChange = (file: UploadFile, files: UploadFile[]) => {
  // 验证文件数量
  if (files.length > 10) {
    ElMessage.warning('最多只能上传 10 个文件')
    files.pop()
    return
  }

  // 验证文件大小
  const maxSize = 20 * 1024 * 1024 // 20MB
  if (file.size && file.size > maxSize) {
    ElMessage.error(`文件 ${file.name} 超过 20MB 限制`)
    const index = files.findIndex(f => f.uid === file.uid)
    if (index > -1) {
      files.splice(index, 1)
    }
    return
  }

  fileList.value = files
}

const handleFileRemove = (file: UploadFile, files: UploadFile[]) => {
  fileList.value = files
}

const clearFiles = () => {
  fileList.value = []
}

const formatFileSize = (size?: number): string => {
  if (!size) return '0 KB'
  const kb = size / 1024
  if (kb < 1024) {
    return `${kb.toFixed(2)} KB`
  }
  const mb = kb / 1024
  return `${mb.toFixed(2)} MB`
}

const sanitizeTableName = (filename: string): string => {
  // 移除扩展名
  let name = filename.replace(/\.(xlsx|xls|csv)$/i, '')

  // 替换特殊字符为下划线
  name = name.replace(/[^\w\u4e00-\u9fa5]/g, '_')

  // 移除多余的下划线
  name = name.replace(/_+/g, '_')

  // 移除首尾下划线
  name = name.replace(/^_|_$/g, '')

  // 如果以数字开头，添加前缀
  if (name && /^\d/.test(name)) {
    name = 'tbl_' + name
  }

  // 限制长度并转小写
  if (name.length > 50) {
    name = name.substring(0, 50)
  }

  return name.toLowerCase()
}

const handleUpload = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }

  if (!form.datasetName.trim()) {
    ElMessage.warning('请输入数据集名称')
    return
  }

  uploading.value = true
  showProgressDialog.value = true
  uploadProgress.value = 10
  progressMessage.value = '正在上传文件...'

  try {
    // 准备文件
    const files = fileList.value.map(f => f.raw as File)

    // 模拟进度更新
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 60) {
        uploadProgress.value += 5
      }
    }, 300)

    // 调用上传 API
    const result = await uploadMultipleFiles(files, form.datasetName)

    clearInterval(progressInterval)
    uploadProgress.value = 80
    progressMessage.value = 'AI 正在分析表关系...'

    // 模拟分析进度
    await new Promise(resolve => setTimeout(resolve, 1500))

    uploadProgress.value = 100
    progressMessage.value = '上传成功！'
    progressStatus.value = 'success'

    await new Promise(resolve => setTimeout(resolve, 500))

    showProgressDialog.value = false
    ElMessage.success('上传成功！正在跳转到关系建模...')

    // 跳转到可视化建模页面
    router.push({
      name: 'dataset-modeling',
      params: { id: result.dataset_id.toString() }
    })
  } catch (error: any) {
    progressStatus.value = 'exception'
    progressMessage.value = '上传失败'
    ElMessage.error(error.message || '文件上传失败')

    setTimeout(() => {
      showProgressDialog.value = false
      progressStatus.value = undefined
    }, 2000)
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.multi-upload-container {
  max-width: 900px;
  margin: 0 auto;
}

.file-preview {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
}

.file-card {
  background: white;
}

:deep(.el-upload-dragger) {
  width: 100%;
  height: 200px;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
