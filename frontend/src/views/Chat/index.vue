<template>
  <div class="h-full flex flex-col bg-gray-50 dark:bg-gray-950">
    <!-- Header / Toolbar -->
    <div class="h-16 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 flex items-center justify-between flex-shrink-0">
      <div class="flex items-center gap-4">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">智能问答</h2>
        <el-select
          v-model="currentDatasetId"
          placeholder="请选择数据集"
          class="w-64"
          :loading="loadingDatasets"
        >
          <el-option
            v-for="item in datasets"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
      </div>
      <el-button @click="clearMessages" plain size="small">
        <el-icon class="mr-1"><Delete /></el-icon> 清空对话
      </el-button>
    </div>

    <!-- Chat Area -->
    <div class="flex-1 overflow-y-auto p-6 space-y-6" ref="chatContainer">
      <!-- Empty State -->
      <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-gray-400">
        <el-icon class="text-6xl mb-4 text-gray-300 dark:text-gray-700"><ChatDotRound /></el-icon>
        <p class="text-lg mb-2">选择一个数据集，开始探索数据</p>
        <p class="text-sm">试着问： "上个月的销售额是多少？" 或 "按产品类别统计销量"</p>
      </div>

      <!-- Messages -->
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['flex gap-4 max-w-5xl mx-auto', msg.type === 'user' ? 'flex-row-reverse' : '']"
      >
        <!-- Avatar -->
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
          :class="msg.type === 'user' ? 'bg-blue-500 text-white' : 'bg-green-500 text-white'"
        >
          <el-icon v-if="msg.type === 'user'"><User /></el-icon>
          <el-icon v-else><Monitor /></el-icon>
        </div>

        <!-- Content -->
        <div class="flex-1 min-w-0 max-w-[85%]">
          <!-- Text Bubble -->
          <div
            :class="[
              'p-4 rounded-2xl text-sm shadow-sm',
              msg.type === 'user'
                ? 'bg-blue-500 text-white rounded-tr-none'
                : 'bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-tl-none'
            ]"
          >
            <div v-if="msg.loading" class="space-y-3">
              <!-- Fake Loading Steps -->
              <div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>{{ currentLoadingStep }}</span>
              </div>
              <div class="space-y-2 pl-6">
                <div v-for="(step, idx) in loadingSteps" :key="idx" class="flex items-center gap-2 text-xs">
                  <el-icon v-if="idx < currentLoadingStepIndex" class="text-green-500"><Check /></el-icon>
                  <el-icon v-else-if="idx === currentLoadingStepIndex" class="is-loading text-blue-500"><Loading /></el-icon>
                  <el-icon v-else class="text-gray-300"><Clock /></el-icon>
                  <span :class="idx <= currentLoadingStepIndex ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400'">
                    {{ step }}
                  </span>
                </div>
              </div>
            </div>
            
            <div v-else>
              <!-- Error Message -->
              <div v-if="msg.error" class="text-red-500 flex items-center gap-2">
                <el-icon><Warning /></el-icon> {{ msg.content }}
              </div>

              <!-- Normal Content -->
              <div v-else class="space-y-4">
                <!-- Thinking Steps (Real) -->
                <div v-if="msg.steps && msg.steps.length > 0" class="mb-4">
                  <el-collapse class="thinking-steps-collapse">
                    <el-collapse-item :name="1">
                      <template #title>
                        <div class="flex items-center gap-2 text-xs">
                          <el-icon class="text-blue-500"><Operation /></el-icon>
                          <span class="font-medium">
                            {{ getStepsSummary(msg.steps) }}
                          </span>
                        </div>
                      </template>
                      <div class="space-y-2 text-xs">
                        <div
                          v-for="(step, idx) in msg.steps"
                          :key="idx"
                          class="flex items-start gap-2 py-1"
                        >
                          <el-icon
                            :class="getStepIconClass(step)"
                            class="mt-0.5 flex-shrink-0"
                          >
                            <component :is="getStepIcon(step)" />
                          </el-icon>
                          <span
                            :class="getStepTextClass(step)"
                          >
                            {{ step }}
                          </span>
                        </div>
                      </div>
                    </el-collapse-item>
                  </el-collapse>
                </div>

                <p v-if="msg.content" class="whitespace-pre-wrap">{{ msg.content }}</p>
                
                <!-- Chart -->
                <div v-if="msg.chartData" class="space-y-2">
                  <div class="h-80 w-full bg-gray-50 dark:bg-gray-900 rounded-lg p-2 border border-gray-100 dark:border-gray-800">
                     <DynamicChart
                       :chart-type="msg.chartType || 'table'"
                       :data="msg.chartData"
                     />
                  </div>
                  <!-- Save to Dashboard Button -->
                  <div class="flex justify-end">
                    <el-button
                      size="small"
                      @click="handleSaveToDashboard(msg, index)"
                      :icon="DocumentAdd"
                    >
                      保存到看板
                    </el-button>
                  </div>
                </div>

                <!-- SQL Collapse -->
                <el-collapse v-if="msg.sql" class="border-t-0">
                  <el-collapse-item title="查看生成的 SQL" name="1">
                    <div class="bg-gray-900 text-gray-300 p-3 rounded-md font-mono text-xs overflow-x-auto">
                      {{ msg.sql }}
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="p-4 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 flex-shrink-0">
      <div class="max-w-5xl mx-auto flex gap-4">
        <el-input
          v-model="inputMessage"
          placeholder="请输入您的问题..."
          @keyup.enter="handleSend"
          :disabled="!currentDatasetId || sending"
          class="flex-1"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button
          type="primary"
          @click="handleSend"
          :loading="sending"
          :disabled="!currentDatasetId || !inputMessage.trim()"
          class="px-6"
        >
          发送
        </el-button>
      </div>
    </div>

    <!-- Save to Dashboard Dialog -->
    <el-dialog
      v-model="saveToDashboardDialog"
      title="保存到看板"
      width="500px"
    >
      <el-form label-width="100px">
        <el-form-item label="卡片标题">
          <el-input v-model="cardTitle" placeholder="请输入卡片标题" />
        </el-form-item>
        
        <el-form-item label="选择看板" v-if="!showNewDashboardInput">
          <div class="w-full space-y-2">
            <el-select v-model="selectedDashboardId" placeholder="选择已有看板" class="w-full">
              <el-option
                v-for="dashboard in dashboards"
                :key="dashboard.id"
                :label="dashboard.name"
                :value="dashboard.id"
              />
            </el-select>
            <el-button @click="handleCreateNewDashboard" size="small" class="w-full">
              + 新建看板
            </el-button>
          </div>
        </el-form-item>
        
        <el-form-item label="看板名称" v-if="showNewDashboardInput">
          <el-input v-model="newDashboardName" placeholder="请输入新看板名称" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="handleCancelSave">取消</el-button>
        <el-button type="primary" @click="handleConfirmSave" :loading="savingCard">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  User,
  Monitor,
  Delete,
  Search,
  Loading,
  Warning,
  DocumentAdd,
  Check,
  Clock,
  Operation,
  CircleCheck,
  WarningFilled
} from '@element-plus/icons-vue'
import { getDatasetList, type Dataset } from '@/api/dataset'
import { sendChat } from '@/api/chat'
import { getDashboards, createDashboard, addCardToDashboard, type Dashboard } from '@/api/dashboard'
import DynamicChart from '@/components/Charts/DynamicChart.vue'

interface Message {
  type: 'user' | 'ai'
  content?: string
  sql?: string
  chartData?: { columns: string[]; rows: any[] }
  chartType?: string
  loading?: boolean
  error?: boolean
  question?: string  // 保存用户问题
  datasetId?: number  // 保存数据集ID
  steps?: string[]  // 执行步骤
}

const currentDatasetId = ref<number | undefined>(undefined)
const datasets = ref<Dataset[]>([])
const loadingDatasets = ref(false)
const messages = ref<Message[]>([])
const inputMessage = ref('')
const sending = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

// Loading Animation State
const loadingSteps = [
  '正在理解问题...',
  '检索业务术语...',
  '生成查询逻辑...',
  '执行 SQL 查询...'
]
const currentLoadingStepIndex = ref(0)
const currentLoadingStep = ref(loadingSteps[0])
let loadingInterval: number | null = null

// Dashboard Dialog State
const saveToDashboardDialog = ref(false)
const dashboards = ref<Dashboard[]>([])
const selectedDashboardId = ref<number | undefined>(undefined)
const cardTitle = ref('')
const showNewDashboardInput = ref(false)
const newDashboardName = ref('')
const savingCard = ref(false)
const currentSavingMessage = ref<Message | null>(null)

onMounted(async () => {
  loadingDatasets.value = true
  try {
    const res = await getDatasetList()
    // Filter only completed datasets
    datasets.value = res.filter(d => d.training_status === 'completed')
    if (datasets.value.length > 0) {
      currentDatasetId.value = datasets.value[0].id
    }
  } catch (error) {
    ElMessage.error('Failed to load datasets')
  } finally {
    loadingDatasets.value = false
  }
})

onUnmounted(() => {
  if (loadingInterval) {
    clearInterval(loadingInterval)
  }
})

const startLoadingAnimation = () => {
  currentLoadingStepIndex.value = 0
  currentLoadingStep.value = loadingSteps[0]
  
  loadingInterval = window.setInterval(() => {
    currentLoadingStepIndex.value = (currentLoadingStepIndex.value + 1) % loadingSteps.length
    currentLoadingStep.value = loadingSteps[currentLoadingStepIndex.value]
  }, 1500)
}

const stopLoadingAnimation = () => {
  if (loadingInterval) {
    clearInterval(loadingInterval)
    loadingInterval = null
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const clearMessages = () => {
  messages.value = []
}

const handleSend = async () => {
  if (!currentDatasetId.value) {
    ElMessage.warning('请先选择一个数据集')
    return
  }
  
  const question = inputMessage.value.trim()
  if (!question) return

  // 1. Add User Message
  messages.value.push({ type: 'user', content: question })
  inputMessage.value = ''
  scrollToBottom()

  // 2. Add AI Loading Placeholder
  const aiMsgIndex = messages.value.length
  messages.value.push({ type: 'ai', loading: true })
  sending.value = true
  startLoadingAnimation()  // 启动加载动画
  scrollToBottom()

  try {
    // 3. Call API
    const res = await sendChat({
      dataset_id: currentDatasetId.value,
      question: question
    })

    // 4. Update AI Message (保存问题和数据集ID)
    messages.value[aiMsgIndex] = {
      type: 'ai',
      loading: false,
      content: res.answer_text,
      sql: res.sql,
      chartData: res.data,
      chartType: res.chart_type,
      question: question,  // 保存原始问题
      datasetId: currentDatasetId.value,  // 保存数据集ID
      steps: res.steps  // 保存执行步骤
    }
  } catch (error: any) {
    console.error(error)
    messages.value[aiMsgIndex] = {
      type: 'ai',
      loading: false,
      error: true,
      content: error.response?.data?.detail || '抱歉，处理您的问题时出现了错误。请稍后重试。'
    }
  } finally {
    stopLoadingAnimation()  // 停止加载动画
    sending.value = false
    scrollToBottom()
  }
}

// Step Analysis Helpers
const getStepsSummary = (steps: string[]) => {
  const hasError = steps.some(s => s.includes('失败') || s.includes('出错'))
  const hasCorrection = steps.some(s => s.includes('修正') || s.includes('自动修复'))
  
  if (hasCorrection) {
    return 'AI 已自动修正 SQL 并生成结果 ✨'
  } else if (hasError) {
    return '查看执行详情 (含警告)'
  } else {
    return '查看执行步骤 ✓'
  }
}

const getStepIcon = (step: string) => {
  if (step.includes('失败') || step.includes('出错')) {
    return WarningFilled
  } else if (step.includes('成功') || step.includes('已修正')) {
    return CircleCheck
  } else {
    return Clock
  }
}

const getStepIconClass = (step: string) => {
  if (step.includes('失败') || step.includes('出错')) {
    return 'text-orange-500'
  } else if (step.includes('成功') || step.includes('已修正')) {
    return 'text-green-500'
  } else {
    return 'text-blue-500'
  }
}

const getStepTextClass = (step: string) => {
  if (step.includes('失败') || step.includes('出错')) {
    return 'text-gray-600 dark:text-gray-400'
  } else {
    return 'text-gray-700 dark:text-gray-300'
  }
}

// Save to Dashboard
const handleSaveToDashboard = async (msg: Message, index: number) => {
  currentSavingMessage.value = msg
  cardTitle.value = msg.question || '未命名图表'
  
  // Load dashboards
  try {
    dashboards.value = await getDashboards()
  } catch (error) {
    ElMessage.error('加载看板列表失败')
    return
  }
  
  saveToDashboardDialog.value = true
}

const handleCreateNewDashboard = () => {
  showNewDashboardInput.value = true
}

const handleConfirmSave = async () => {
  if (!currentSavingMessage.value) return
  
  let targetDashboardId = selectedDashboardId.value
  
  // Create new dashboard if needed
  if (showNewDashboardInput.value && newDashboardName.value.trim()) {
    try {
      const newDashboard = await createDashboard(newDashboardName.value.trim())
      targetDashboardId = newDashboard.id
      ElMessage.success('看板创建成功')
    } catch (error) {
      ElMessage.error('创建看板失败')
      return
    }
  }
  
  if (!targetDashboardId) {
    ElMessage.warning('请选择或创建一个看板')
    return
  }
  
  if (!cardTitle.value.trim()) {
    ElMessage.warning('请输入卡片标题')
    return
  }
  
  // Save card
  savingCard.value = true
  try {
    await addCardToDashboard(targetDashboardId, {
      title: cardTitle.value.trim(),
      dataset_id: currentSavingMessage.value.datasetId!,
      sql: currentSavingMessage.value.sql!,
      chart_type: currentSavingMessage.value.chartType || 'table'
    })
    
    ElMessage.success('已保存到看板')
    saveToDashboardDialog.value = false
    
    // Reset state
    selectedDashboardId.value = undefined
    showNewDashboardInput.value = false
    newDashboardName.value = ''
    currentSavingMessage.value = null
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingCard.value = false
  }
}

const handleCancelSave = () => {
  saveToDashboardDialog.value = false
  selectedDashboardId.value = undefined
  showNewDashboardInput.value = false
  newDashboardName.value = ''
  currentSavingMessage.value = null
}
</script>

<style scoped>
/* Thinking Steps Collapse Custom Styling */
.thinking-steps-collapse :deep(.el-collapse-item__header) {
  padding: 8px 12px;
  background-color: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  font-size: 13px;
}

.dark .thinking-steps-collapse :deep(.el-collapse-item__header) {
  background-color: #1f2937;
  border-color: #374151;
}

.thinking-steps-collapse :deep(.el-collapse-item__content) {
  padding: 12px 12px 8px 12px;
  background-color: #fefefe;
  border: 1px solid #e5e7eb;
  border-top: none;
  border-bottom-left-radius: 6px;
  border-bottom-right-radius: 6px;
}

.dark .thinking-steps-collapse :deep(.el-collapse-item__content) {
  background-color: #111827;
  border-color: #374151;
}

.thinking-steps-collapse :deep(.el-collapse-item__wrap) {
  border: none;
}
</style>
