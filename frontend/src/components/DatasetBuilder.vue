<template>
  <div class="h-full overflow-auto bg-gray-50 dark:bg-gray-950">
    <div class="max-w-7xl mx-auto p-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold mb-2 text-gray-900 dark:text-gray-100">数据集构建器</h1>
        <p class="text-gray-600 dark:text-gray-400">选择数据表创建您的 AI 驱动数据集</p>
      </div>

      <div class="flex items-center gap-2 mb-6">
        <div class="flex items-center gap-2 text-sm">
          <div class="w-8 h-8 rounded-full bg-[#409EFF] text-white flex items-center justify-center font-medium shadow-lg shadow-blue-500/30">1</div>
          <span class="font-medium text-gray-900 dark:text-gray-100">选择连接</span>
        </div>
        <el-icon class="w-4 h-4 text-gray-400 dark:text-gray-600">
          <ArrowRight />
        </el-icon>
        <div class="flex items-center gap-2 text-sm">
          <div class="w-8 h-8 rounded-full bg-[#409EFF] text-white flex items-center justify-center font-medium shadow-lg shadow-blue-500/30">2</div>
          <span class="font-medium text-gray-900 dark:text-gray-100">选择数据表</span>
        </div>
        <el-icon class="w-4 h-4 text-gray-400 dark:text-gray-600">
          <ArrowRight />
        </el-icon>
        <div class="flex items-center gap-2 text-sm">
          <div class="w-8 h-8 rounded-full border-2 border-gray-300 dark:border-gray-700 text-gray-400 dark:text-gray-600 flex items-center justify-center font-medium">3</div>
          <span class="text-gray-400 dark:text-gray-600">训练 AI</span>
        </div>
      </div>

      <div class="grid grid-cols-5 gap-6">
        <el-card class="col-span-2 p-6 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800" shadow="hover">
          <div class="flex items-center gap-2 mb-4">
            <el-icon class="w-5 h-5 text-[#409EFF]">
              <DataAnalysis />
            </el-icon>
            <h2 class="font-semibold text-lg text-gray-900 dark:text-gray-100">可用数据表</h2>
          </div>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">生产环境数据库 • PostgreSQL</p>

          <div class="space-y-2 max-h-[500px] overflow-auto">
            <div
              v-for="table in availableTables"
              :key="table.name"
              :class="`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                selectedLeft.includes(table.name)
                  ? 'bg-[#409EFF]/10 dark:bg-[#409EFF]/20 border-[#409EFF] shadow-md'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-800 border-gray-200 dark:border-gray-700'
              }`"
              @click="toggleLeftSelection(table.name)"
            >
              <div class="flex items-start gap-3">
                <el-checkbox
                  :model-value="selectedLeft.includes(table.name)"
                  @change="toggleLeftSelection(table.name)"
                />
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <el-icon class="w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0">
                      <Grid />
                    </el-icon>
                    <span class="font-medium text-sm text-gray-900 dark:text-gray-100">{{ table.name }}</span>
                  </div>
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ table.rows }} 行数据</p>
                </div>
              </div>
            </div>
          </div>
        </el-card>

        <div class="flex items-center justify-center">
          <el-button
            type="primary"
            :disabled="selectedLeft.length === 0"
            class="bg-[#409EFF] hover:bg-[#3182ce] rounded-lg shadow-lg shadow-blue-500/30 disabled:shadow-none"
            @click="transferToRight"
          >
            <el-icon class="w-5 h-5">
              <ArrowRight />
            </el-icon>
          </el-button>
        </div>

        <el-card class="col-span-2 p-6 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800" shadow="hover">
          <div class="flex items-center gap-2 mb-4">
            <el-icon class="w-5 h-5 text-[#409EFF]">
              <MagicStick />
            </el-icon>
            <h2 class="font-semibold text-lg text-gray-900 dark:text-gray-100">已选用于 AI 训练</h2>
          </div>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">已选择 {{ selectedTables.length }} 个数据表</p>

          <div class="space-y-2 max-h-[500px] overflow-auto mb-6">
            <div v-if="selectedTables.length === 0" class="text-center py-12 text-gray-400 dark:text-gray-600">
              <el-icon class="w-12 h-12 mx-auto mb-2 opacity-50">
                <Grid />
              </el-icon>
              <p class="text-sm">暂未选择数据表</p>
            </div>
            <div
              v-else
              v-for="table in selectedTables"
              :key="table"
              class="p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:shadow-md transition-shadow"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <el-icon class="w-4 h-4 text-gray-400 dark:text-gray-500">
                    <Grid />
                  </el-icon>
                  <span class="font-medium text-sm text-gray-900 dark:text-gray-100">{{ table }}</span>
                </div>
                <el-button
                  link
                  size="small"
                  @click="removeFromRight(table)"
                  class="h-6 px-2 text-xs text-gray-500 dark:text-gray-400 hover:text-red-500 dark:hover:text-red-400"
                >
                  移除
                </el-button>
              </div>
            </div>
          </div>

          <el-button
            v-if="selectedTables.length > 0"
            type="primary"
            size="large"
            class="w-full bg-[#409EFF] hover:bg-[#3182ce] rounded-lg shadow-lg shadow-blue-500/30"
            @click="startTraining"
          >
            <el-icon class="w-4 h-4 mr-2">
              <MagicStick />
            </el-icon>
            开始训练 AI 模型
          </el-button>
        </el-card>
      </div>
    </div>

    <TrainingProgressDialog
      v-model="trainingDialogOpen"
      :progress="trainingProgress"
      :current-step="currentStep"
      :is-complete="isTrainingComplete"
      @close="handleTrainingClose"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ArrowRight, DataAnalysis, Grid, MagicStick } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import TrainingProgressDialog from './TrainingProgressDialog.vue'

interface Table {
  name: string
  schema: string
  rows: string
}

const availableTables: Table[] = [
  { name: '客户信息表', schema: 'public', rows: '125,430' },
  { name: '订单记录表', schema: 'public', rows: '342,891' },
  { name: '商品信息表', schema: 'public', rows: '5,234' },
  { name: '交易流水表', schema: 'public', rows: '891,234' },
  { name: '用户账户表', schema: 'public', rows: '45,678' },
  { name: '库存管理表', schema: 'public', rows: '12,456' },
  { name: '供应商信息表', schema: 'public', rows: '892' },
  { name: '商品分类表', schema: 'public', rows: '234' },
]

const selectedLeft = ref<string[]>([])
const selectedTables = ref<string[]>([])
const trainingDialogOpen = ref(false)
const trainingProgress = ref(0)
const currentStep = ref('')
const isTrainingComplete = ref(false)

const toggleLeftSelection = (table: string) => {
  const index = selectedLeft.value.indexOf(table)
  if (index > -1) {
    selectedLeft.value.splice(index, 1)
  } else {
    selectedLeft.value.push(table)
  }
}

const transferToRight = () => {
  const count = selectedLeft.value.length
  selectedTables.value.push(...selectedLeft.value)
  selectedLeft.value = []
  ElMessage.success(`已添加 ${count} 个数据表`)
}

const removeFromRight = (table: string) => {
  const index = selectedTables.value.indexOf(table)
  if (index > -1) {
    selectedTables.value.splice(index, 1)
  }
  ElMessage.success('已移除数据表')
}

const startTraining = () => {
  trainingDialogOpen.value = true
  trainingProgress.value = 0
  isTrainingComplete.value = false

  const steps = [
    { progress: 15, step: '正在连接数据库...' },
    { progress: 30, step: '正在分析表结构...' },
    { progress: 50, step: '正在识别字段关系...' },
    { progress: 70, step: '正在构建数据模型...' },
    { progress: 85, step: '正在训练 AI 模型...' },
    { progress: 100, step: '训练完成' },
  ]

  let currentStepIndex = 0
  const interval = setInterval(() => {
    if (currentStepIndex < steps.length) {
      trainingProgress.value = steps[currentStepIndex].progress
      currentStep.value = steps[currentStepIndex].step
      currentStepIndex++
    } else {
      clearInterval(interval)
      isTrainingComplete.value = true
    }
  }, 1500)
}

const handleTrainingClose = () => {
  trainingDialogOpen.value = false
  if (isTrainingComplete.value) {
    ElMessage.success('AI 模型训练完成！')
  }
}
</script>
