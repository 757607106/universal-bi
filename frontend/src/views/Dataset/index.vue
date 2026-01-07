<template>
  <div class="h-full overflow-auto bg-transparent p-8">
    <div class="max-w-7xl mx-auto">
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-3xl font-bold mb-2 text-gray-900 dark:text-slate-100">数据集管理</h1>
          <p class="text-gray-500 dark:text-slate-400">构建和管理用于 AI 分析的业务数据集</p>
        </div>
        <div class="flex gap-3">
          <el-button type="primary" @click="wizardVisible = true" class="bg-blue-600 shadow-lg shadow-blue-500/30 hover:bg-blue-500 border-none">
            <el-icon class="mr-2"><Plus /></el-icon>
            新建数据集
          </el-button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <el-card
          v-for="dataset in datasetList"
          :key="dataset.id"
          class="hover:shadow-lg transition-all duration-300 border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-200 group hover:border-blue-500 dark:hover:border-blue-500/50"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <el-icon class="text-blue-500"><Files /></el-icon>
                <span class="font-bold text-gray-900 dark:text-slate-100 truncate">{{ dataset.name }}</span>
              </div>
              <el-tag :type="getStatusType(dataset.status || dataset.training_status)" effect="dark" size="small">
                <div class="flex items-center gap-1">
                  <el-icon v-if="(dataset.status || dataset.training_status) === 'training'" class="is-loading"><Loading /></el-icon>
                  <el-icon v-else-if="(dataset.status || dataset.training_status) === 'completed'" class="text-green-500"><CircleCheck /></el-icon>
                  <el-icon v-else-if="(dataset.status || dataset.training_status) === 'failed'" class="text-red-500"><CircleClose /></el-icon>
                  <el-icon v-else-if="(dataset.status || dataset.training_status) === 'paused'" class="text-gray-400"><VideoPause /></el-icon>
                  <el-icon v-else-if="(dataset.status || dataset.training_status) === 'pending'" class="text-orange-500"><Clock /></el-icon>
                  {{ getStatusText(dataset.status || dataset.training_status) }}
                </div>
              </el-tag>
            </div>
          </template>
          
          <div class="space-y-4">
            <div class="flex items-center justify-between text-sm">
              <span class="text-gray-500 dark:text-slate-400">Collection</span>
              <span class="font-mono text-xs bg-gray-50 dark:bg-slate-900/50 px-2 py-1 rounded text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-700">{{ dataset.collection_name || 'N/A' }}</span>
            </div>
            
            <div class="flex items-center justify-between text-sm">
              <span class="text-gray-500 dark:text-slate-400">包含表</span>
              <span class="font-medium text-gray-900 dark:text-slate-200">{{ dataset.schema_config?.length || 0 }} 个</span>
            </div>

            <div class="flex items-center justify-between text-sm">
              <span class="text-gray-500 dark:text-slate-400">上次训练</span>
              <span class="text-gray-600 dark:text-slate-300">{{ formatDate(dataset.last_train_at || dataset.last_trained_at) }}</span>
            </div>
            
            <div class="pt-4 border-t border-gray-200 dark:border-slate-700 flex justify-end gap-2 flex-wrap">
              <el-button size="small" @click="handleGoModeling(dataset)" class="!bg-purple-50 dark:!bg-purple-500/10 !border-purple-200 dark:!border-purple-500/50 !text-purple-600 dark:!text-purple-400 hover:!bg-purple-100 dark:hover:!bg-purple-500/20">
                <el-icon class="mr-1"><MagicStick /></el-icon>
                可视化建模
              </el-button>
              <el-button size="small" @click="handleOpenBusinessTermManager(dataset)" class="!bg-orange-50 dark:!bg-orange-500/10 !border-orange-200 dark:!border-orange-500/50 !text-orange-600 dark:!text-orange-400 hover:!bg-orange-100 dark:hover:!bg-orange-500/20">
                <el-icon class="mr-1"><Collection /></el-icon>
                业务术语
              </el-button>
              <el-button size="small" @click="handleViewTrainingData(dataset)" class="!bg-green-50 dark:!bg-green-500/10 !border-green-200 dark:!border-green-500/50 !text-green-600 dark:!text-green-400 hover:!bg-green-100 dark:hover:!bg-green-500/20">
                <el-icon class="mr-1"><Files /></el-icon>
                训练数据
              </el-button>
              <el-button v-if="(dataset.status || dataset.training_status) !== 'training'" size="small" @click="handleRetrain(dataset)" class="!bg-gray-100 dark:!bg-slate-700 hover:!bg-gray-200 dark:hover:!bg-slate-600 !border-gray-200 dark:!border-slate-600 !text-gray-700 dark:!text-slate-200">
                重新训练
              </el-button>
              <el-button v-if="(dataset.status || dataset.training_status) === 'training'" size="small" type="primary" @click="handleShowProgress(dataset)" class="!bg-blue-500 hover:!bg-blue-600">
                <el-icon class="mr-1"><View /></el-icon>
                查看进度
              </el-button>
              <el-button size="small" type="danger" plain @click="handleDelete(dataset)" class="!bg-red-50 dark:!bg-red-500/10 !border-red-200 dark:!border-red-500/50 !text-red-600 dark:!text-red-400 hover:!bg-red-100 dark:hover:!bg-red-500/20">
                <el-icon class="mr-1"><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </div>
        </el-card>
      </div>

      <el-empty v-if="datasetList.length === 0" description="暂无数据集，请点击右上角创建" />

      <DatasetWizard
        v-model="wizardVisible"
        @refresh="fetchDatasets"
      />

      <TrainingProgressDialog
        v-model="progressDialogVisible"
        :dataset-id="selectedDatasetId"
        @refresh="fetchDatasets"
      />

      <TrainingDataDialog
        v-model="trainingDataDialogVisible"
        :dataset-id="selectedDatasetId"
      />

      <BusinessTermManager
        v-model="businessTermManagerVisible"
        :dataset-id="selectedDatasetId"
        @refresh="fetchDatasets"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Files, Loading, MagicStick, View, CircleCheck, CircleClose, VideoPause, Clock, Delete, Collection } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDatasetList, trainDataset, deleteDataset, type Dataset } from '@/api/dataset'
import DatasetWizard from './components/DatasetWizard.vue'
import TrainingProgressDialog from './components/TrainingProgressDialog.vue'
import TrainingDataDialog from './components/TrainingDataDialog.vue'
import BusinessTermManager from './components/BusinessTermManager.vue'

const router = useRouter()
const wizardVisible = ref(false)
const progressDialogVisible = ref(false)
const trainingDataDialogVisible = ref(false)
const businessTermManagerVisible = ref(false)
const selectedDatasetId = ref(0)
const datasetList = ref<Dataset[]>([])
let pollingTimer: ReturnType<typeof setInterval> | null = null

const fetchDatasets = async () => {
  try {
    const res = await getDatasetList()
    datasetList.value = res
    checkPolling(res)
  } catch (error) {
    ElMessage.error('获取数据集列表失败')
  }
}

const checkPolling = (list: Dataset[]) => {
  const hasTraining = list.some(d => (d.status || d.training_status) === 'training' || (d.status || d.training_status) === 'pending')
  
  // 【修复】只有在有训练任务且轮询未开启时才启动
  if (hasTraining && !pollingTimer) {
    console.log('检测到训练任务，开启轮询')
    pollingTimer = setInterval(fetchDatasets, 3000)
  } 
  // 【修复】没有训练任务且轮询开启时才关闭
  else if (!hasTraining && pollingTimer) {
    console.log('没有训练任务，关闭轮询')
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const handleRetrain = async (dataset: Dataset) => {
  try {
    await trainDataset(dataset.id)
    ElMessage.success('已触发重新训练')
    
    // 打开进度对话框
    selectedDatasetId.value = dataset.id
    progressDialogVisible.value = true
    
    fetchDatasets()
  } catch (error) {
    ElMessage.error('触发训练失败')
  }
}

const handleShowProgress = (dataset: Dataset) => {
  selectedDatasetId.value = dataset.id
  progressDialogVisible.value = true
}

// 查看训练数据
const handleViewTrainingData = (dataset: Dataset) => {
  selectedDatasetId.value = dataset.id
  trainingDataDialogVisible.value = true
}

// 打开业务术语管理
const handleOpenBusinessTermManager = (dataset: Dataset) => {
  selectedDatasetId.value = dataset.id
  businessTermManagerVisible.value = true
}

const handleDelete = async (dataset: Dataset) => {
  try {
    await ElMessageBox.confirm(
      `确认删除数据集 "${dataset.name}" 吗？

删除后将无法恢复，包括：
- 已训练的数据
- 业务术语
- 建模配置
- 训练日志`,
      '删除确认',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    
    await deleteDataset(dataset.id)
    ElMessage.success('数据集已删除')
    fetchDatasets()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.message || '删除失败')
    }
  }
}

const getStatusType = (status: string) => {
  switch (status) {
    case 'completed': return 'success'
    case 'training': return 'primary'
    case 'failed': return 'danger'
    case 'paused': return 'info'
    case 'pending': return 'warning'
    default: return 'info'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'completed': return '已完成'
    case 'training': return '训练中'
    case 'failed': return '失败'
    case 'pending': return '等待中'
    case 'paused': return '已暂停'
    default: return status
  }
}

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

// 跳转到可视化建模页面
const handleGoModeling = (dataset: any) => {
  router.push(`/datasets/modeling/${dataset.id}`)
}

onMounted(() => {
  fetchDatasets()
})

onUnmounted(() => {
  if (pollingTimer) clearInterval(pollingTimer)
})
</script>
