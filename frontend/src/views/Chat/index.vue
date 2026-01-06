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
              <!-- Error Message (仅显示真正的系统错误) -->
              <div v-if="msg.error && msg.isSystemError" class="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <el-icon class="text-red-500 text-xl mt-0.5 flex-shrink-0">
                  <Warning />
                </el-icon>
                <div class="flex-1">
                  <p class="text-sm font-medium text-red-800 dark:text-red-400 mb-1">系统错误</p>
                  <p class="text-sm text-red-700 dark:text-red-300">{{ msg.content }}</p>
                </div>
              </div>

              <!-- Normal Content -->
              <div v-else class="space-y-4">
                <!-- Clarification Request -->
                <div v-if="msg.chartType === 'clarification'" class="space-y-3">
                  <!-- 纯文本消息，自然风格 -->
                  <div class="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap leading-relaxed">
                    {{ msg.content }}
                  </div>
                  
                  <!-- Quick Reply Suggestions -->
                  <div v-if="getClarificationSuggestions(msg.content || '').length > 0" class="space-y-2">
                    <p class="text-xs text-gray-500 dark:text-gray-400 font-medium">✨ 快捷回复：</p>
                    <div class="flex flex-wrap gap-2">
                      <el-tag
                        v-for="(suggestion, idx) in getClarificationSuggestions(msg.content || '')"
                        :key="idx"
                        type="info"
                        effect="plain"
                        size="default"
                        class="cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/40 hover:border-blue-400 dark:hover:border-blue-600 transition-all duration-200 hover:shadow-md"
                        @click="handleQuickReply(suggestion)"
                      >
                        {{ suggestion }}
                      </el-tag>
                    </div>
                  </div>
                </div>
                
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

                <p v-if="msg.content && msg.chartType !== 'clarification'" class="whitespace-pre-wrap">{{ msg.content }}</p>
                
                <!-- 结果摘要（仅显示单数据结果） -->
                <div v-if="msg.chartData && msg.chartData.rows && msg.chartData.rows.length === 1 && msg.chartType !== 'clarification'" class="my-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <div class="flex items-center gap-2 mb-2">
                    <el-icon class="text-blue-500"><CircleCheck /></el-icon>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">查询结果</span>
                  </div>
                  <div class="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {{ formatSingleResult(msg.chartData) }}
                  </div>
                </div>
                
                <!-- Chart -->
                <div v-if="msg.chartData && msg.chartData.columns && msg.chartData.rows && msg.chartData.rows.length > 0" class="space-y-2">
                  <div class="h-80 w-full bg-gray-50 dark:bg-gray-900 rounded-lg p-2 border border-gray-100 dark:border-gray-800">
                     <DynamicChart
                       :chart-type="msg.chartType || 'table'"
                       :data="{ columns: msg.chartData.columns, rows: msg.chartData.rows }"
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
                    
                    <!-- Feedback Buttons -->
                    <div class="flex items-center gap-3 mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
                      <span class="text-xs text-gray-500 dark:text-gray-400">这个结果有帮助吗？</span>
                      <el-button
                        size="small"
                        :type="msg.feedbackGiven === 'like' ? 'success' : 'default'"
                        :disabled="msg.feedbackGiven !== undefined"
                        @click="handleLikeFeedback(msg, index)"
                      >
                        <el-icon class="mr-1"><Select /></el-icon>
                        {{ msg.feedbackGiven === 'like' ? '已喜欢' : '喜欢' }}
                      </el-button>
                      <el-button
                        size="small"
                        :type="msg.feedbackGiven === 'dislike' ? 'danger' : 'default'"
                        :disabled="msg.feedbackGiven !== undefined"
                        @click="handleDislikeFeedback(msg, index)"
                      >
                        <el-icon class="mr-1"><CloseBold /></el-icon>
                        {{ msg.feedbackGiven === 'dislike' ? '已反馈' : '不满意' }}
                      </el-button>
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

    <!-- SQL Correction Dialog -->
    <el-dialog
      v-model="sqlCorrectionDialog"
      title="修正 SQL"
      width="700px"
    >
      <div class="space-y-4">
        <div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">请修改下方的 SQL 查询，然后提交给 AI 学习：</p>
          <el-input
            v-model="correctedSql"
            type="textarea"
            :rows="10"
            placeholder="输入正确的 SQL..."
            class="font-mono text-sm"
          />
        </div>
        <el-alert
          title="提示"
          type="info"
          :closable="false"
          show-icon
        >
          AI 会学习你提供的正确 SQL，下次遇到类似问题时会更准确。
        </el-alert>
      </div>
      
      <template #footer>
        <el-button @click="handleCancelCorrection">取消</el-button>
        <el-button type="primary" @click="handleSubmitCorrection" :loading="submittingFeedback">
          提交修正
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
  WarningFilled,
  QuestionFilled,
  Select,
  CloseBold
} from '@element-plus/icons-vue'
import { getDatasetList, type Dataset } from '@/api/dataset'
import { sendChat, submitFeedback } from '@/api/chat'
import { getDashboards, createDashboard, addCardToDashboard, type Dashboard } from '@/api/dashboard'
import DynamicChart from '@/components/Charts/DynamicChart.vue'

interface Message {
  type: 'user' | 'ai'
  content?: string
  sql?: string
  chartData?: { columns: string[] | null; rows: any[] | null }  // 允许 columns 和 rows 为 null
  chartType?: string
  loading?: boolean
  error?: boolean
  question?: string  // 保存用户问题
  datasetId?: number  // 保存数据集ID
  steps?: string[]  // 执行步骤
  isSystemError?: boolean  // 区分系统错误和业务澄清
  feedbackGiven?: 'like' | 'dislike'  // 反馈状态
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

// Feedback Dialog State
const sqlCorrectionDialog = ref(false)
const correctedSql = ref('')
const submittingFeedback = ref(false)
const currentFeedbackMessage = ref<Message | null>(null)
const currentFeedbackMessageIndex = ref<number>(-1)

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
    const isClarification = res.chart_type === 'clarification'
    
    // 直接使用后端返回的 columns 和 rows
    const chartData = (res.columns && res.rows) ? {
      columns: res.columns,
      rows: res.rows
    } : undefined
    
    // Debug: 输出数据结构
    console.log('[Chat Debug] API Response:', {
      has_columns: !!res.columns,
      has_rows: !!res.rows,
      rows_length: res.rows?.length,
      chartData: chartData,
      chart_type: res.chart_type
    })
    
    messages.value[aiMsgIndex] = {
      type: 'ai',
      loading: false,
      content: res.answer_text || undefined,
      sql: res.sql || undefined,
      chartData: chartData,
      chartType: res.chart_type,
      question: question,
      datasetId: currentDatasetId.value,
      steps: res.steps,
      error: false,
      isSystemError: false
    }
  } catch (error: any) {
    console.error(error)
    
    // 区分 HTTP 错误类型
    const statusCode = error.response?.status
    const isServerError = statusCode && statusCode >= 500
    
    messages.value[aiMsgIndex] = {
      type: 'ai',
      loading: false,
      error: true,
      isSystemError: isServerError,
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
  const hasMultiRound = steps.some(s => s.includes('多轮推理') || s.includes('中间 SQL'))
  
  if (hasMultiRound) {
    return 'AI 进行了多轮推理 🧠'
  } else if (hasCorrection) {
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

// Clarification Helpers
const getClarificationSuggestions = (content: string): string[] => {
  if (!content) return []
  
  // 尝试从 AI 回复中提取建议
  const suggestions: string[] = []
  
  // 1. 检测是否包含"还是"分隔的选项（最优先，直接来自AI的建议）
  if (content.includes('还是')) {
    const parts = content.split('还是')
    for (const part of parts) {
      // 提取""或「」包裹的内容
      const quotedMatch = part.match(/["「](.*?)["」]/)
      if (quotedMatch && quotedMatch[1] && quotedMatch[1].length < 30) {
        suggestions.push(quotedMatch[1].trim())
        continue
      }
      
      // 提取常见的业务术语
      const termMatch = part.match(/(个数|总数|金额|数量|订单|客户|用户|消费|销售|按.{1,4}分组|按.{1,4}统计)/)
      if (termMatch && termMatch[1] && termMatch[1].length < 20) {
        suggestions.push(termMatch[1].trim())
      }
    }
  }
  
  // 2. 检测是否包含"或"分隔的选项
  if (content.includes('或')) {
    const parts = content.split('或')
    for (const part of parts) {
      const quotedMatch = part.match(/["「](.*?)["」]/)
      if (quotedMatch && quotedMatch[1] && quotedMatch[1].length < 30) {
        suggestions.push(quotedMatch[1].trim())
      }
    }
  }
  
  // 3. 检测是否包含列表式的选项（如："1. 选项A  2. 选项B"）
  const listMatches = content.match(/[\d一二三四五][\.、]\s*([^\d一二三四五\.、\n]{2,20})/g)
  if (listMatches) {
    for (const match of listMatches) {
      const cleanMatch = match.replace(/^[\d一二三四五][\.、]\s*/, '').trim()
      if (cleanMatch.length >= 2 && cleanMatch.length <= 20) {
        suggestions.push(cleanMatch)
      }
    }
  }
  
  // 4. 根据关键词提供智能建议
  const contentLower = content.toLowerCase()
  
  // 时间相关
  if (contentLower.includes('时间') || contentLower.includes('日期') || contentLower.includes('周期') || contentLower.includes('范围')) {
    if (suggestions.length < 3) {
      suggestions.push('最近 7 天', '最近 30 天', '本月')
    }
  }
  
  // 统计维度相关
  if (contentLower.includes('分组') || contentLower.includes('统计') || contentLower.includes('维度')) {
    if (suggestions.length < 3) {
      suggestions.push('按日统计', '按月统计', '按类型分组')
    }
  }
  
  // 客户相关
  if (contentLower.includes('客户') || contentLower.includes('用户')) {
    if (suggestions.length < 3) {
      suggestions.push('VIP 客户', '普通客户', '所有客户')
    }
  }
  
  // 订单相关
  if (contentLower.includes('订单')) {
    if (suggestions.length < 3) {
      suggestions.push('已完成订单', '待处理订单', '所有订单')
    }
  }
  
  // 5. 如果仍然没有提取到建议，返回通用默认建议
  if (suggestions.length === 0) {
    return [
      '显示最近 30 天的数据',
      '按月统计',
      '查询所有类型'
    ]
  }
  
  // 去重并限制数量
  return [...new Set(suggestions)].slice(0, 5)
}

const handleQuickReply = (suggestion: string) => {
  if (!currentDatasetId.value) {
    ElMessage.warning('请先选择一个数据集')
    return
  }
  
  // 获取上一个用户问题
  const lastUserMessage = messages.value.filter(m => m.type === 'user').pop()
  if (!lastUserMessage) return
  
  // 组合原始问题和建议
  const enhancedQuestion = `${lastUserMessage.content}，${suggestion}`
  
  // 自动填充到输入框
  inputMessage.value = enhancedQuestion
  
  // 聚焦到输入框
  nextTick(() => {
    const inputEl = document.querySelector('.el-input__inner') as HTMLInputElement
    if (inputEl) {
      inputEl.focus()
    }
  })
}

// Format single result for better display
const formatSingleResult = (chartData: { columns: string[] | null; rows: any[] | null }) => {
  if (!chartData.rows || chartData.rows.length !== 1 || !chartData.columns) {
    return ''
  }
  
  const row = chartData.rows[0]
  const parts: string[] = []
  
  chartData.columns.forEach((col, index) => {
    const value = row[col]
    
    // 格式化数值
    if (typeof value === 'number') {
      if (Number.isInteger(value)) {
        parts.push(`${col}: ${value.toLocaleString()}`)
      } else {
        parts.push(`${col}: ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
      }
    } else {
      parts.push(`${col}: ${value}`)
    }
  })
  
  return parts.join(' | ')
}

// Feedback Handlers
const handleLikeFeedback = async (msg: Message, index: number) => {
  if (!msg.sql || !msg.question || !msg.datasetId) {
    ElMessage.warning('无法提交反馈，缺少必要信息')
    return
  }
  
  submittingFeedback.value = true
  
  try {
    const response = await submitFeedback({
      dataset_id: msg.datasetId,
      question: msg.question,
      sql: msg.sql,
      rating: 1
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      // 标记为已反馈
      messages.value[index].feedbackGiven = 'like'
    } else {
      ElMessage.warning(response.message)
    }
  } catch (error: any) {
    console.error(error)
    ElMessage.error('反馈提交失败')
  } finally {
    submittingFeedback.value = false
  }
}

const handleDislikeFeedback = (msg: Message, index: number) => {
  if (!msg.sql || !msg.question || !msg.datasetId) {
    ElMessage.warning('无法提交反馈，缺少必要信息')
    return
  }
  
  // 打开 SQL 修正对话框
  currentFeedbackMessage.value = msg
  currentFeedbackMessageIndex.value = index
  correctedSql.value = msg.sql  // 预填充当前 SQL
  sqlCorrectionDialog.value = true
}

const handleCancelCorrection = () => {
  sqlCorrectionDialog.value = false
  correctedSql.value = ''
  currentFeedbackMessage.value = null
  currentFeedbackMessageIndex.value = -1
}

const handleSubmitCorrection = async () => {
  if (!currentFeedbackMessage.value || currentFeedbackMessageIndex.value === -1) {
    return
  }
  
  if (!correctedSql.value.trim()) {
    ElMessage.warning('请输入修正后的 SQL')
    return
  }
  
  submittingFeedback.value = true
  
  try {
    const response = await submitFeedback({
      dataset_id: currentFeedbackMessage.value.datasetId!,
      question: currentFeedbackMessage.value.question!,
      sql: correctedSql.value.trim(),
      rating: -1
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      // 标记为已反馈
      messages.value[currentFeedbackMessageIndex.value].feedbackGiven = 'dislike'
      // 关闭对话框
      handleCancelCorrection()
    } else {
      ElMessage.warning(response.message)
    }
  } catch (error: any) {
    console.error(error)
    ElMessage.error('修正提交失败')
  } finally {
    submittingFeedback.value = false
  }
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
