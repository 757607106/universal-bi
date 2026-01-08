<template>
  <div class="fluctuation-analysis-panel bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-lg overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700 bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20">
      <div class="flex items-center gap-2">
        <el-icon class="text-xl text-orange-600 dark:text-orange-400"><TrendCharts /></el-icon>
        <h3 class="font-semibold text-gray-900 dark:text-slate-100">数据波动分析</h3>
      </div>
      <el-button @click="$emit('close')" text circle>
        <el-icon><Close /></el-icon>
      </el-button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="p-8 flex flex-col items-center justify-center">
      <el-icon class="text-4xl text-blue-500 dark:text-cyan-400 is-loading"><Loading /></el-icon>
      <p class="mt-4 text-sm text-gray-500 dark:text-slate-400">正在分析数据波动...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="p-6">
      <el-alert type="error" :title="error" :closable="false" show-icon />
    </div>

    <!-- Analysis Results -->
    <div v-else-if="analysisData" class="space-y-4 p-4">
      <!-- Trend Chart (if ECharts available) -->
      <div v-if="analysisData.stats && chartData" class="bg-gray-50 dark:bg-slate-900 rounded-lg p-4 border border-gray-200 dark:border-slate-800">
        <h4 class="text-sm font-medium text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <el-icon><DataLine /></el-icon>
          趋势图
        </h4>
        <div ref="chartContainer" class="h-64 w-full"></div>
      </div>

      <!-- Statistics Summary -->
      <div v-if="analysisData.stats" class="bg-gradient-to-r from-blue-50/50 to-cyan-50/50 dark:from-slate-900/50 dark:to-slate-800/50 rounded-lg p-4 border border-blue-200/50 dark:border-slate-700/50">
        <h4 class="text-sm font-medium text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <el-icon><DataAnalysis /></el-icon>
          统计摘要
        </h4>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="stat-item">
            <p class="text-xs text-gray-500 dark:text-slate-400">最大值</p>
            <p class="text-lg font-bold text-gray-900 dark:text-slate-100">{{ formatNumber(analysisData.stats.max_value) }}</p>
          </div>
          <div class="stat-item">
            <p class="text-xs text-gray-500 dark:text-slate-400">最小值</p>
            <p class="text-lg font-bold text-gray-900 dark:text-slate-100">{{ formatNumber(analysisData.stats.min_value) }}</p>
          </div>
          <div class="stat-item">
            <p class="text-xs text-gray-500 dark:text-slate-400">平均值</p>
            <p class="text-lg font-bold text-gray-900 dark:text-slate-100">{{ formatNumber(analysisData.stats.avg) }}</p>
          </div>
          <div class="stat-item">
            <p class="text-xs text-gray-500 dark:text-slate-400">标准差</p>
            <p class="text-lg font-bold text-gray-900 dark:text-slate-100">{{ formatNumber(analysisData.stats.std_dev) }}</p>
          </div>
          <div class="stat-item">
            <p class="text-xs text-gray-500 dark:text-slate-400">趋势</p>
            <p class="text-lg font-bold" :class="getTrendClass(analysisData.stats.trend)">{{ analysisData.stats.trend }}</p>
          </div>
          <div class="stat-item">
            <p class="text-xs text-gray-500 dark:text-slate-400">变异系数</p>
            <p class="text-lg font-bold text-gray-900 dark:text-slate-100">{{ analysisData.stats.coefficient_of_variation.toFixed(1) }}%</p>
          </div>
          <div class="stat-item">
            <p class="text-xs text-gray-500 dark:text-slate-400">数据点</p>
            <p class="text-lg font-bold text-gray-900 dark:text-slate-100">{{ analysisData.stats.data_points }}</p>
          </div>
          <div class="stat-item">
            <p class="text-xs text-gray-500 dark:text-slate-400">异常点</p>
            <p class="text-lg font-bold text-orange-600 dark:text-orange-400">{{ analysisData.stats.anomaly_points.length }}</p>
          </div>
        </div>

        <!-- Anomaly Points Detail -->
        <div v-if="analysisData.stats.anomaly_points.length > 0" class="mt-4 pt-4 border-t border-blue-200 dark:border-slate-700">
          <p class="text-xs font-medium text-gray-600 dark:text-slate-400 mb-2">异常点详情：</p>
          <div class="flex flex-wrap gap-2">
            <el-tag
              v-for="(point, idx) in analysisData.stats.anomaly_points"
              :key="idx"
              type="warning"
              size="small"
              effect="plain"
            >
              {{ point.time }}: {{ formatNumber(point.value) }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- AI Insight -->
      <div class="bg-gradient-to-r from-purple-50/50 to-pink-50/50 dark:from-slate-900/50 dark:to-slate-800/50 rounded-lg p-4 border border-purple-200/50 dark:border-slate-700/50">
        <h4 class="text-sm font-medium text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <el-icon><ChatDotRound /></el-icon>
          AI 归因分析
        </h4>
        <p class="text-sm text-gray-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
          {{ analysisData.ai_insight }}
        </p>
      </div>

      <!-- Drill Down -->
      <div v-if="analysisData.drill_down" class="bg-gradient-to-r from-green-50/50 to-teal-50/50 dark:from-slate-900/50 dark:to-slate-800/50 rounded-lg p-4 border border-green-200/50 dark:border-slate-700/50">
        <h4 class="text-sm font-medium text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <el-icon><Histogram /></el-icon>
          多维钻取
        </h4>
        <p class="text-xs text-gray-500 dark:text-slate-400 mb-3">
          异常时间点: {{ analysisData.drill_down.anomaly_time }} ({{ formatNumber(analysisData.drill_down.anomaly_value) }})
        </p>
        <p class="text-xs text-gray-500 dark:text-slate-400 mb-2">按 <strong>{{ analysisData.drill_down.dimension }}</strong> 维度拆解：</p>
        
        <!-- Drill Down Chart -->
        <div class="space-y-2">
          <div
            v-for="(item, idx) in analysisData.drill_down.breakdown"
            :key="idx"
            class="flex items-center gap-2"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-gray-700 dark:text-slate-300 truncate">{{ item.dimension_value }}</span>
                <span class="text-xs font-medium text-gray-900 dark:text-slate-100">{{ item.contribution_pct.toFixed(1) }}%</span>
              </div>
              <div class="h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-green-500 to-teal-500 transition-all duration-300"
                  :style="{ width: `${item.contribution_pct}%` }"
                ></div>
              </div>
            </div>
            <span class="text-xs text-gray-500 dark:text-slate-400 whitespace-nowrap">{{ formatNumber(item.value) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Close,
  Loading,
  TrendCharts,
  DataLine,
  DataAnalysis,
  ChatDotRound,
  Histogram
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import type { FluctuationAnalysisResponse } from '@/api/suggestions'

interface Props {
  datasetId: number
  sql: string
  timeColumn: string
  valueColumn: string
  rawData?: any[]  // 原始数据（可选）
}

const props = defineProps<Props>()
const emit = defineEmits(['close'])

const loading = ref(false)
const error = ref<string | null>(null)
const analysisData = ref<FluctuationAnalysisResponse | null>(null)
const chartContainer = ref<HTMLElement | null>(null)
const chartData = ref<any>(null)

let chartInstance: echarts.ECharts | null = null

// 格式化数字
const formatNumber = (num: number): string => {
  if (Number.isInteger(num)) {
    return num.toLocaleString()
  }
  return num.toFixed(2)
}

// 获取趋势样式类
const getTrendClass = (trend: string): string => {
  if (trend === '上升') {
    return 'text-green-600 dark:text-green-400'
  } else if (trend === '下降') {
    return 'text-red-600 dark:text-red-400'
  }
  return 'text-gray-600 dark:text-gray-400'
}

// 渲染ECharts图表
const renderChart = () => {
  if (!chartContainer.value || !analysisData.value?.stats || !props.rawData) {
    return
  }

  // 初始化图表
  if (!chartInstance) {
    chartInstance = echarts.init(chartContainer.value)
  }

  // 准备数据
  const times = props.rawData.map(d => d[props.timeColumn])
  const values = props.rawData.map(d => d[props.valueColumn])
  const anomalyPoints = analysisData.value.stats.anomaly_points

  // 标注异常点
  const markPoints = anomalyPoints.map(ap => ({
    name: '异常',
    value: ap.value,
    xAxis: ap.index,
    yAxis: ap.value,
    itemStyle: {
      color: '#f59e0b'
    }
  }))

  // 配置选项
  const option = {
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: {
        rotate: 45,
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10
      }
    },
    series: [
      {
        data: values,
        type: 'line',
        smooth: true,
        lineStyle: {
          color: '#3b82f6',
          width: 2
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
            ]
          }
        },
        markPoint: {
          data: markPoints,
          symbol: 'pin',
          symbolSize: 50
        },
        markLine: {
          data: [
            {
              type: 'average',
              name: '平均值',
              lineStyle: {
                type: 'dashed',
                color: '#10b981'
              }
            }
          ]
        }
      }
    ],
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const param = params[0]
        return `${param.name}<br/>${param.seriesName}: ${formatNumber(param.value)}`
      }
    }
  }

  chartInstance.setOption(option)
}

// 执行分析
const performAnalysis = async () => {
  loading.value = true
  error.value = null

  try {
    const { analyzeFluctuation } = await import('@/api/suggestions')
    
    const response = await analyzeFluctuation({
      dataset_id: props.datasetId,
      sql: props.sql,
      time_column: props.timeColumn,
      value_column: props.valueColumn,
      enable_drill_down: true
    })

    analysisData.value = response

    // 渲染图表
    if (props.rawData && response.stats) {
      await nextTick()
      renderChart()
    }
  } catch (err: any) {
    console.error('Fluctuation analysis failed:', err)
    error.value = err.response?.data?.detail || '波动分析失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  performAnalysis()
})

// 监听窗口大小变化
watch(() => chartContainer.value, () => {
  if (chartInstance) {
    chartInstance.resize()
  }
})
</script>

<style scoped>
.fluctuation-analysis-panel {
  max-height: 80vh;
  overflow-y: auto;
}

.stat-item {
  @apply text-center;
}

/* 优化滚动条样式 */
.fluctuation-analysis-panel::-webkit-scrollbar {
  width: 6px;
}

.fluctuation-analysis-panel::-webkit-scrollbar-track {
  @apply bg-gray-100 dark:bg-slate-800;
}

.fluctuation-analysis-panel::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-slate-600 rounded-full;
}

.fluctuation-analysis-panel::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-slate-500;
}
</style>
