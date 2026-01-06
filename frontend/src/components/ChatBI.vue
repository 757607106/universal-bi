<template>
  <div class="h-full flex flex-col bg-gray-50 dark:bg-gray-950">
    <!-- 头部选择器 -->
    <div class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 p-4 shadow-sm">
      <div class="max-w-5xl mx-auto flex items-center gap-4">
        <div class="flex items-center gap-2">
          <el-icon class="w-5 h-5 text-[#409EFF]">
            <DataAnalysis />
          </el-icon>
          <span class="font-medium text-gray-900 dark:text-gray-100">数据集:</span>
        </div>
        <el-select v-model="selectedDataset" class="w-64">
          <el-option label="生产环境分析" value="production" />
          <el-option label="销售数据" value="sales" />
          <el-option label="客户洞察" value="customer" />
        </el-select>
      </div>
    </div>

    <!-- 消息区域 -->
    <div class="flex-1 overflow-auto bg-gray-50 dark:bg-gray-950">
      <div class="max-w-5xl mx-auto p-8 space-y-6">
        <div
          v-for="(message, idx) in messages"
          :key="idx"
          :class="`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`"
        >
          <div v-if="message.type === 'user'" class="bg-gradient-to-r from-[#409EFF] to-[#3182ce] text-white px-4 py-3 rounded-2xl max-w-md shadow-lg shadow-blue-500/20">
            <p class="text-sm">{{ message.content }}</p>
          </div>

          <el-card v-else class="max-w-2xl p-6 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-lg">
            <p class="text-sm text-gray-700 dark:text-gray-300 mb-4">{{ message.content }}</p>

            <div v-if="message.chartData" class="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-4">
              <h3 class="font-semibold mb-4 text-gray-900 dark:text-gray-100">月度营收统计</h3>
              <div class="w-full h-[300px]">
                <v-chart :option="getChartOption(message.chartData)" autoresize />
              </div>
            </div>

            <div class="flex gap-2">
              <el-button
                link
                size="small"
                @click="handleViewSQL(message.sql)"
              >
                <el-icon class="w-4 h-4 mr-2">
                  <Document />
                </el-icon>
                查看 SQL
              </el-button>
              <el-button
                link
                size="small"
                @click="handlePinToDashboard(message)"
              >
                <el-icon class="w-4 h-4 mr-2">
                  <Star />
                </el-icon>
                固定到仪表板
              </el-button>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 p-4 shadow-lg">
      <div class="max-w-5xl mx-auto flex gap-3">
        <el-input
          v-model="input"
          placeholder="询问关于您数据的问题..."
          @keyup.enter="handleSend"
          class="flex-1"
        />
        <el-button
          type="primary"
          @click="handleSend"
          class="bg-[#409EFF] hover:bg-[#3182ce] rounded-lg shadow-lg shadow-blue-500/30"
        >
          <el-icon class="w-4 h-4">
            <ArrowRight />
          </el-icon>
        </el-button>
      </div>
    </div>

    <SQLViewDialog
      v-model="sqlDialogOpen"
      :sql="currentSQL"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { DataAnalysis, Document, Star, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import * as EChartsComponents from 'echarts/components'
import VChart from 'vue-echarts'
import SQLViewDialog from './SQLViewDialog.vue'

// 初始化 ECharts 需要的渲染器/图表/组件，容错处理避免未定义项导致应用崩溃
const _echartsItems = [
  CanvasRenderer,
  BarChart,
  EChartsComponents.GridComponent,
  EChartsComponents.TooltipComponent,
].filter(Boolean)
try {
  use(_echartsItems)
} catch (err) {
  // 如果注册失败，打印警告但不阻断应用渲染
  // 运行时可能由预构建导致的导出差异引起，继续保持功能降级
  // eslint-disable-next-line no-console
  console.warn('echarts use failed:', err)
}

interface Message {
  type: 'user' | 'ai'
  content: string
  data?: any
  chartData?: any[]
  sql?: string
}

interface Emits {
  (e: 'pin-chart', chartData: any): void
}

const emit = defineEmits<Emits>()

const mockChartData = [
  { month: '1月', revenue: 45000 },
  { month: '2月', revenue: 52000 },
  { month: '3月', revenue: 48000 },
  { month: '4月', revenue: 61000 },
  { month: '5月', revenue: 58000 },
  { month: '6月', revenue: 67000 },
]

const mockSQL = `SELECT
  DATE_TRUNC('month', order_date) as month,
  SUM(total_amount) as revenue
FROM orders
WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '6 months')
  AND order_date < DATE_TRUNC('month', CURRENT_DATE)
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;`

const initialMessages: Message[] = [
  {
    type: 'user',
    content: '显示最近6个月的营收趋势',
  },
  {
    type: 'ai',
    content: '这是最近6个月的营收趋势分析。数据显示总体呈上升趋势，总营收为 331,000 元。',
    chartData: mockChartData,
    sql: mockSQL,
  },
]

const messages = ref<Message[]>(initialMessages)
const input = ref('')
const selectedDataset = ref('production')
const sqlDialogOpen = ref(false)
const currentSQL = ref('')

const getChartOption = (data: any[]) => ({
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: data.map(item => item.month),
    axisLine: {
      lineStyle: {
        color: '#888'
      }
    }
  },
  yAxis: {
    type: 'value',
    axisLine: {
      lineStyle: {
        color: '#888'
      }
    }
  },
  series: [{
    data: data.map(item => item.revenue),
    type: 'bar',
    itemStyle: {
      color: '#409EFF',
      borderRadius: [8, 8, 0, 0]
    }
  }],
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderColor: '#e5e7eb',
    textStyle: {
      color: '#333'
    }
  }
})

const handleSend = () => {
  if (!input.value.trim()) return

  messages.value.push({ type: 'user', content: input.value })

  // 模拟 AI 响应
  setTimeout(() => {
    messages.value.push({
      type: 'ai',
      content: '我已经分析了您的请求。根据数据集，这是我发现的结果。',
      chartData: mockChartData,
      sql: mockSQL,
    })
  }, 1000)

  input.value = ''
}

const handleViewSQL = (sql?: string) => {
  if (sql) {
    currentSQL.value = sql
    sqlDialogOpen.value = true
  }
}

const handlePinToDashboard = (message: Message) => {
  if (message.chartData) {
    emit('pin-chart', {
      title: '月度营收统计',
      type: 'bar',
      data: message.chartData,
    })
    ElMessage.success('已固定到数据看板')
  }
}
</script>
