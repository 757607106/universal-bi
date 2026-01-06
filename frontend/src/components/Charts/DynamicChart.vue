<template>
  <div class="w-full h-full min-h-[400px]">
    <!-- Empty State for Clarification or No Data -->
    <div 
      v-if="chartType === 'clarification' || !data || !data.columns || data.columns.length === 0 || !data.rows || data.rows.length === 0"
      class="h-full flex flex-col items-center justify-center text-gray-400 dark:text-gray-500 space-y-4 p-8"
    >
      <el-icon class="text-7xl opacity-40">
        <QuestionFilled v-if="chartType === 'clarification'" />
        <DataAnalysis v-else />
      </el-icon>
      <div class="text-center space-y-3 max-w-md">
        <p class="text-lg font-semibold text-gray-600 dark:text-gray-400">
          {{ chartType === 'clarification' ? '💡 需要更多信息' : '⚠️ 暂无数据' }}
        </p>
        <p class="text-sm text-gray-500 dark:text-gray-500 leading-relaxed">
          {{ chartType === 'clarification' 
             ? 'AI 需要更多信息才能生成图表，请根据上方问题提供更多细节' 
             : '查询执行成功，但没有找到符合条件的数据。请尝试调整查询条件或扩大范围' 
          }}
        </p>
      </div>
    </div>

    <!-- Table View -->
    <div v-else-if="chartType === 'table'" class="h-full overflow-auto">
      <el-table :data="data.rows" border stripe style="width: 100%" height="100%">
        <el-table-column
          v-for="col in data.columns"
          :key="col"
          :prop="col"
          :label="col"
          min-width="150"
          show-overflow-tooltip
        />
      </el-table>
    </div>

    <!-- ECharts View -->
    <v-chart
      v-else
      class="chart"
      :option="chartOption"
      autoresize
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DataZoomComponent
} from 'echarts/components'
import { QuestionFilled, DataAnalysis } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'

// Register ECharts components
use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DataZoomComponent
])

interface Props {
  chartType: string
  data: {
    columns: string[]
    rows: any[]
  }
}

const props = defineProps<Props>()

const chartOption = computed(() => {
  // 防御性检查:确保数据存在且不为空
  if (props.chartType === 'table' || 
      !props.data.columns || 
      props.data.columns.length === 0 || 
      !props.data.rows || 
      props.data.rows.length === 0) {
    return {}
  }

  const xAxisCol = props.data.columns[0]
  const yAxisCol = props.data.columns[1]

  const xAxisData = props.data.rows.map(row => row[xAxisCol])
  const seriesData = props.data.rows.map(row => row[yAxisCol])

  const commonOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    legend: {
      data: [yAxisCol]
    }
  }

  if (props.chartType === 'bar') {
    return {
      ...commonOption,
      xAxis: {
        type: 'category',
        data: xAxisData,
        axisLabel: {
          interval: 0,
          rotate: 30
        }
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          name: yAxisCol,
          type: 'bar',
          data: seriesData,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: '#2dd4bf' }, // teal-400
                { offset: 1, color: '#0f766e' }  // teal-700
              ]
            },
            borderRadius: [4, 4, 0, 0]
          },
          emphasis: {
            itemStyle: {
              color: '#14b8a6'
            }
          }
        }
      ]
    }
  }

  if (props.chartType === 'line') {
    return {
      ...commonOption,
      xAxis: {
        type: 'category',
        data: xAxisData,
        boundaryGap: false
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          name: yAxisCol,
          type: 'line',
          data: seriesData,
          smooth: true,
          symbol: 'circle',
          symbolSize: 8,
          itemStyle: {
            color: '#3b82f6' // blue-500
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(59, 130, 246, 0.5)' },
                { offset: 1, color: 'rgba(59, 130, 246, 0.01)' }
              ]
            }
          }
        }
      ]
    }
  }

  // Fallback for pie or others if needed
  return {}
})
</script>

<style scoped>
.chart {
  height: 100%;
  width: 100%;
}
</style>
