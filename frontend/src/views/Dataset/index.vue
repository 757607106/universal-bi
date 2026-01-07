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
              <el-tag :type="getStatusType(dataset.training_status)" effect="dark" size="small" class="!bg-gray-100 dark:!bg-slate-700 !border-gray-200 dark:!border-slate-600 !text-gray-700 dark:!text-slate-200">
                <div class="flex items-center gap-1">
                  <el-icon v-if="dataset.training_status === 'training'" class="is-loading"><Loading /></el-icon>
                  {{ getStatusText(dataset.training_status) }}
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
              <span class="text-gray-600 dark:text-slate-300">{{ formatDate(dataset.last_trained_at) }}</span>
            </div>
            
            <div class="pt-4 border-t border-gray-200 dark:border-slate-700 flex justify-end gap-2">
              <el-button size="small" @click="handleGoModeling(dataset)" class="!bg-purple-50 dark:!bg-purple-500/10 !border-purple-200 dark:!border-purple-500/50 !text-purple-600 dark:!text-purple-400 hover:!bg-purple-100 dark:hover:!bg-purple-500/20">
                <el-icon class="mr-1"><MagicStick /></el-icon>
                可视化建模
              </el-button>
              <el-button v-if="dataset.training_status !== 'training'" size="small" @click="handleRetrain(dataset)" class="!bg-gray-100 dark:!bg-slate-700 hover:!bg-gray-200 dark:hover:!bg-slate-600 !border-gray-200 dark:!border-slate-600 !text-gray-700 dark:!text-slate-200">
                重新训练
              </el-button>
              <el-button size="small" type="primary" plain class="!bg-blue-50 dark:!bg-blue-500/10 !border-blue-200 dark:!border-blue-500/50 !text-blue-600 dark:!text-blue-400 hover:!bg-blue-100 dark:hover:!bg-blue-500/20">详情</el-button>
            </div>
          </div>
        </el-card>
      </div>

      <el-empty v-if="datasetList.length === 0" description="暂无数据集，请点击右上角创建" />

      <DatasetWizard
        v-model="wizardVisible"
        @refresh="fetchDatasets"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Files, Loading, MagicStick } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDatasetList, trainDataset, type Dataset } from '@/api/dataset'
import DatasetWizard from './components/DatasetWizard.vue'

const router = useRouter()
const wizardVisible = ref(false)
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
  const hasTraining = list.some(d => d.training_status === 'training' || d.training_status === 'pending')
  if (hasTraining && !pollingTimer) {
    pollingTimer = setInterval(fetchDatasets, 3000)
  } else if (!hasTraining && pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const handleRetrain = async (dataset: Dataset) => {
  try {
    await trainDataset(dataset.id)
    ElMessage.success('已触发重新训练')
    fetchDatasets()
  } catch (error) {
    ElMessage.error('触发训练失败')
  }
}

const getStatusType = (status: string) => {
  switch (status) {
    case 'completed': return 'success'
    case 'training': return 'primary'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'completed': return '已完成'
    case 'training': return '训练中'
    case 'failed': return '失败'
    case 'pending': return '等待中'
    default: return status
  }
}

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

// 跳转到可视化建模页面
const handleGoModeling = (dataset: any) => {
  // 传递 datasource_id 到建模页面
  router.push({
    path: '/datasets/modeling',
    query: {
      dataset_id: dataset.id,
      datasource_id: dataset.datasource_id
    }
  })
}

onMounted(() => {
  fetchDatasets()
})

onUnmounted(() => {
  if (pollingTimer) clearInterval(pollingTimer)
})
</script>
