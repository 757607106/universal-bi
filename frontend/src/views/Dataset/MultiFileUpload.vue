<template>
  <div class="multi-upload-container p-8 min-h-full">
    <div class="max-w-4xl mx-auto">
      <!-- 头部引导 -->
      <div class="mb-8">
        <h2 class="text-3xl font-bold mb-3 text-gray-900 dark:text-slate-100 flex items-center">
          <el-icon class="mr-3 text-purple-600"><FolderAdd /></el-icon>
          多表数据上传
        </h2>
        <p class="text-gray-500 dark:text-slate-400 text-lg">
          批量上传您的业务数据表，系统将自动识别表结构并分析关联关系，为您构建智能数据模型。
        </p>
      </div>

      <el-card class="!rounded-xl shadow-lg border-0 dark:bg-slate-800 dark:border-slate-700">
        <!-- 步骤1：命名数据集 -->
        <div class="mb-8">
          <div class="flex items-center mb-4">
            <div class="w-8 h-8 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center font-bold mr-3 dark:bg-purple-900/30 dark:text-purple-400">1</div>
            <h3 class="text-lg font-semibold text-gray-800 dark:text-slate-200">定义数据集名称</h3>
          </div>
          <el-form :model="form" class="pl-11">
            <el-form-item class="!mb-0">
              <el-input
                v-model="form.datasetName"
                placeholder="例如：2024年Q1销售数据分析"
                size="large"
                class="!w-full md:!w-[500px]"
              >
                <template #prefix>
                  <el-icon class="text-gray-400"><Collection /></el-icon>
                </template>
              </el-input>
            </el-form-item>
          </el-form>
        </div>

        <el-divider class="!my-8" />

        <!-- 步骤2：上传文件 -->
        <div>
          <div class="flex items-center mb-4">
            <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold mr-3 dark:bg-blue-900/30 dark:text-blue-400">2</div>
            <h3 class="text-lg font-semibold text-gray-800 dark:text-slate-200">上传数据表文件</h3>
          </div>
          
          <div class="pl-11">
            <el-upload
              ref="uploadRef"
              drag
              multiple
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :file-list="fileList"
              :show-file-list="false"
              accept=".xlsx,.xls,.csv"
              class="upload-area"
            >
              <div v-if="fileList.length === 0" class="py-12 flex flex-col items-center justify-center">
                <div class="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mb-4 dark:bg-blue-900/20">
                  <el-icon class="text-4xl text-blue-500"><UploadFilled /></el-icon>
                </div>
                <div class="text-gray-600 font-medium text-lg mb-2 dark:text-slate-300">
                  点击或拖拽文件到此处
                </div>
                <div class="text-gray-400 text-sm">
                  支持 .xlsx, .xls, .csv 格式，单个文件不超过 20MB
                </div>
              </div>

              <div v-else class="w-full p-6">
                <div class="flex items-center justify-center mb-6">
                  <el-button type="primary" plain round size="small">
                    <el-icon class="mr-1"><Plus /></el-icon>
                    添加更多文件
                  </el-button>
                  <span class="ml-3 text-gray-400 text-sm">已选择 {{ fileList.length }} 个文件</span>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-left" @click.stop>
                  <div
                    v-for="(file, index) in fileList"
                    :key="index"
                    class="file-card group relative p-4 rounded-xl border border-gray-200 bg-gray-50 hover:bg-white hover:shadow-md hover:border-blue-400 transition-all duration-300 dark:bg-slate-800/50 dark:border-slate-700 dark:hover:bg-slate-800"
                  >
                    <!-- 删除按钮 (悬停显示) -->
                    <div class="absolute -top-2 -right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                      <el-button 
                        circle 
                        type="danger" 
                        size="small" 
                        class="!shadow-md"
                        @click="removeFile(file)"
                      >
                        <el-icon><Close /></el-icon>
                      </el-button>
                    </div>

                    <div class="flex items-start gap-3">
                      <!-- 文件图标 -->
                      <div class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0" 
                           :class="getFileIconClass(file.name)">
                        <span class="font-bold text-xs uppercase">{{ getFileExt(file.name) }}</span>
                      </div>
                      
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between mb-1">
                          <h4 class="font-medium text-gray-900 truncate dark:text-slate-200" :title="file.name">
                            {{ file.name }}
                          </h4>
                          <span class="text-xs text-gray-400 ml-2 whitespace-nowrap">{{ formatFileSize(file.size) }}</span>
                        </div>
                        <div class="flex items-center text-xs text-gray-500 bg-white px-2 py-1 rounded border border-gray-100 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-400">
                          <span class="mr-1">表名:</span>
                          <span class="font-mono text-purple-600 dark:text-purple-400">{{ sanitizeTableName(file.name) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </el-upload>
          </div>
        </div>
      </el-card>

      <!-- 底部操作栏 -->
      <div class="flex justify-end items-center mt-8 gap-4">
        <el-button @click="$router.back()" size="large" class="!px-8">取消</el-button>
        <el-button
          type="primary"
          size="large"
          :loading="uploading"
          :disabled="fileList.length === 0 || !form.datasetName"
          @click="handleUpload"
          class="!px-8 !bg-gradient-to-r !from-blue-600 !to-purple-600 !border-none hover:!opacity-90 shadow-lg shadow-blue-500/30"
        >
          <el-icon class="mr-2"><MagicStick /></el-icon>
          开始智能分析
        </el-button>
      </div>
    </div>

    <!-- 上传进度提示 -->
    <el-dialog
      v-model="showProgressDialog"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
      width="400px"
      class="!rounded-2xl"
    >
      <div class="text-center py-6">
        <div class="relative w-20 h-20 mx-auto mb-6">
           <svg class="animate-spin w-full h-full text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <h3 class="text-xl font-bold mb-2 text-gray-900 dark:text-slate-100">{{ progressMessage }}</h3>
        <p class="text-gray-500 text-sm mb-6">正在处理数据并构建知识图谱...</p>
        <el-progress 
          :percentage="uploadProgress" 
          :status="progressStatus" 
          :stroke-width="8"
          striped
          striped-flow
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElLoading, type UploadFile, type UploadUserFile } from 'element-plus'
import { UploadFilled, Document, Upload, Loading, Plus, FolderAdd, Collection, MagicStick, Close } from '@element-plus/icons-vue'
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
.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  min-height: 240px;
  height: auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background-color: transparent;
  border-width: 2px;
  border-style: dashed;
  transition: all 0.3s;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}

.dark .upload-area :deep(.el-upload-dragger:hover) {
  background-color: rgba(59, 130, 246, 0.1);
}
</style>
