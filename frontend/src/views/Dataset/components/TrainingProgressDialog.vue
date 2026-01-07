<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="模型训练进度"
    width="700px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
  >
    <div class="training-progress-container">
      <!-- 状态指示器 -->
      <div class="mb-4 flex items-center justify-between">
        <el-tag :type="getStatusTagType(status)" size="large" effect="dark">
          <div class="flex items-center gap-2">
            <el-icon v-if="status === 'training'" class="is-loading"><Loading /></el-icon>
            <el-icon v-else-if="status === 'completed'"><CircleCheck /></el-icon>
            <el-icon v-else-if="status === 'failed'"><CircleClose /></el-icon>
            <el-icon v-else-if="status === 'paused'"><VideoPause /></el-icon>
            <span>{{ getStatusText(status) }}</span>
          </div>
        </el-tag>
        <span class="text-sm text-gray-500">数据集 ID: {{ datasetId }}</span>
      </div>

      <!-- 动画区域 -->
      <div 
        class="animation-area mb-4 rounded-lg flex items-center justify-center"
        :class="status === 'training' ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-gray-50 dark:bg-gray-800'"
      >
        <div v-if="status === 'training'" class="text-center">
          <div class="pulse-animation mb-2">
            <el-icon :size="40" class="text-blue-500"><DataAnalysis /></el-icon>
          </div>
          <p class="text-blue-600 dark:text-blue-400 font-medium">Data flowing...</p>
          <p class="text-xs text-gray-500 mt-1">{{ currentStep }}</p>
        </div>
        <div v-else-if="status === 'completed'" class="text-center">
          <el-icon :size="40" class="text-green-500 mb-2"><SuccessFilled /></el-icon>
          <p class="text-green-600 dark:text-green-400 font-medium">训练完成</p>
        </div>
        <div v-else-if="status === 'failed'" class="text-center">
          <el-icon :size="40" class="text-red-500 mb-2"><CircleCloseFilled /></el-icon>
          <p class="text-red-600 dark:text-red-400 font-medium">训练失败</p>
          <p class="text-xs text-gray-500 mt-1">{{ errorMsg }}</p>
        </div>
        <div v-else-if="status === 'paused'" class="text-center">
          <el-icon :size="40" class="text-orange-500 mb-2"><VideoPause /></el-icon>
          <p class="text-orange-600 dark:text-orange-400 font-medium">训练已暂停</p>
        </div>
        <div v-else class="text-center">
          <el-icon :size="40" class="text-gray-400 mb-2"><Clock /></el-icon>
          <p class="text-gray-500 font-medium">等待开始...</p>
        </div>
      </div>

      <!-- 进度条 -->
      <div class="mb-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm text-gray-600 dark:text-gray-400">训练进度</span>
          <span class="text-sm font-bold text-gray-900 dark:text-gray-100">{{ progress }}%</span>
        </div>
        <el-progress 
          :percentage="progress" 
          :status="getProgressStatus(status)"
          :stroke-width="12"
        />
      </div>

      <!-- 日志终端 -->
      <div class="log-terminal">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm text-gray-600 dark:text-gray-400">训练日志</span>
          <el-button 
            size="small" 
            text 
            @click="refreshLogs"
            :loading="logsLoading"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
        <div 
          ref="logScrollRef"
          class="log-content bg-gray-900 rounded-lg p-4 overflow-y-auto"
        >
          <div 
            v-for="(log, index) in logs" 
            :key="index"
            class="log-line text-green-400 font-mono text-xs mb-1"
          >
            <span class="text-gray-500">{{ formatLogTime(log.created_at) }}</span>
            <span class="ml-2">{{ log.content }}</span>
          </div>
          <div v-if="logs.length === 0" class="text-gray-500 text-center py-4">
            暂无日志
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <!-- 停止训练按钮 -->
        <el-button
          v-if="status === 'training'"
          type="danger"
          @click="handleStop"
          :loading="actionLoading"
        >
          <el-icon><VideoPause /></el-icon>
          <span class="ml-1">停止训练</span>
        </el-button>

        <!-- 继续训练按钮 -->
        <el-button
          v-if="status === 'paused'"
          type="primary"
          @click="handleResume"
          :loading="actionLoading"
        >
          <el-icon><VideoPlay /></el-icon>
          <span class="ml-1">继续训练</span>
        </el-button>

        <!-- 重试按钮 -->
        <el-button
          v-if="status === 'failed'"
          type="warning"
          @click="handleRetry"
          :loading="actionLoading"
        >
          <el-icon><RefreshRight /></el-icon>
          <span class="ml-1">重试</span>
        </el-button>

        <!-- 完成按钮 -->
        <el-button
          v-if="status === 'completed'"
          type="success"
          @click="handleClose"
        >
          <el-icon><CircleCheck /></el-icon>
          <span class="ml-1">完成</span>
        </el-button>

        <!-- 关闭按钮 -->
        <el-button @click="handleClose">
          关闭
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted } from 'vue'
import { 
  Loading, 
  CircleCheck, 
  CircleClose, 
  VideoPause,
  VideoPlay,
  DataAnalysis,
  SuccessFilled,
  CircleCloseFilled,
  Clock,
  Refresh,
  RefreshRight
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { 
  getTrainingProgress, 
  getTrainingLogs, 
  pauseTraining, 
  trainDataset,
  type TrainingLog
} from '@/api/dataset'

// Props
interface Props {
  modelValue: boolean
  datasetId: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'refresh': []
}>()

// State
const status = ref<'pending' | 'training' | 'completed' | 'failed' | 'paused'>('pending')
const progress = ref(0)
const currentStep = ref('')
const errorMsg = ref<string | null>(null)
const logs = ref<TrainingLog[]>([])
const actionLoading = ref(false)
const logsLoading = ref(false)
const logScrollRef = ref<HTMLElement | null>(null)

let pollingTimer: ReturnType<typeof setInterval> | null = null

// Methods
const fetchProgress = async () => {
  try {
    const res = await getTrainingProgress(props.datasetId)
    status.value = res.status
    progress.value = res.process_rate
    currentStep.value = res.current_step || ''
    errorMsg.value = res.error_msg

    // 如果状态变为终止状态，停止轮询
    if (['completed', 'failed'].includes(res.status)) {
      stopPolling()
      // 获取最终日志
      await refreshLogs()
    }
  } catch (error: any) {
    console.error('获取训练进度失败:', error)
    // 如果接口不存在，使用降级处理
    if (error?.response?.status === 404) {
      ElMessage.warning('训练进度接口暂未实现，使用模拟数据')
      stopPolling()
    }
  }
}

const refreshLogs = async () => {
  try {
    logsLoading.value = true
    const res = await getTrainingLogs(props.datasetId, 50)
    logs.value = res
    
    // 滚动到底部
    await nextTick()
    if (logScrollRef.value) {
      logScrollRef.value.scrollTop = logScrollRef.value.scrollHeight
    }
  } catch (error: any) {
    console.error('获取训练日志失败:', error)
    if (error?.response?.status !== 404) {
      ElMessage.error('获取训练日志失败')
    }
  } finally {
    logsLoading.value = false
  }
}

const startPolling = () => {
  if (pollingTimer) return
  
  // 立即获取一次
  fetchProgress()
  refreshLogs()
  
  // 启动轮询（每1秒）
  pollingTimer = setInterval(() => {
    fetchProgress()
    // 每5次更新获取一次日志
    if (Math.random() < 0.2) {
      refreshLogs()
    }
  }, 1000)
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const handleStop = async () => {
  try {
    actionLoading.value = true
    await pauseTraining(props.datasetId)
    ElMessage.success('已发送停止请求')
    await fetchProgress()
  } catch (error) {
    ElMessage.error('停止训练失败')
  } finally {
    actionLoading.value = false
  }
}

const handleResume = async () => {
  try {
    actionLoading.value = true
    await trainDataset(props.datasetId)
    ElMessage.success('已重新启动训练')
    startPolling()
  } catch (error) {
    ElMessage.error('继续训练失败')
  } finally {
    actionLoading.value = false
  }
}

const handleRetry = async () => {
  try {
    actionLoading.value = true
    await trainDataset(props.datasetId)
    ElMessage.success('已重新启动训练')
    startPolling()
  } catch (error) {
    ElMessage.error('重试失败')
  } finally {
    actionLoading.value = false
  }
}

const handleClose = () => {
  stopPolling()
  emit('update:modelValue', false)
  emit('refresh')
}

const getStatusText = (s: string) => {
  const map: Record<string, string> = {
    pending: '等待中',
    training: '训练中',
    completed: '已完成',
    failed: '失败',
    paused: '已暂停'
  }
  return map[s] || s
}

const getStatusTagType = (s: string) => {
  const map: Record<string, any> = {
    pending: 'info',
    training: 'primary',
    completed: 'success',
    failed: 'danger',
    paused: 'warning'
  }
  return map[s] || 'info'
}

const getProgressStatus = (s: string) => {
  if (s === 'completed') return 'success'
  if (s === 'failed') return 'exception'
  return undefined
}

const formatLogTime = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

// Watchers
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    // 对话框打开时启动轮询
    startPolling()
  } else {
    // 对话框关闭时停止轮询
    stopPolling()
  }
})

// Lifecycle
onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.training-progress-container {
  min-height: 400px;
}

.animation-area {
  height: 150px;
  border: 2px dashed #e5e7eb;
  transition: all 0.3s;
}

.animation-area.bg-blue-50 {
  border-color: #3b82f6;
}

.pulse-animation {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.1);
  }
}

.log-terminal {
  margin-top: 1rem;
}

.log-content {
  height: 200px;
  font-family: 'Courier New', Courier, monospace;
}

.log-content::-webkit-scrollbar {
  width: 6px;
}

.log-content::-webkit-scrollbar-track {
  background: #1f2937;
  border-radius: 3px;
}

.log-content::-webkit-scrollbar-thumb {
  background: #4b5563;
  border-radius: 3px;
}

.log-content::-webkit-scrollbar-thumb:hover {
  background: #6b7280;
}

.log-line {
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
