<template>
  <div class="w-full h-full min-h-[400px]">
    <!-- Empty State for Clarification or No Data -->
    <div 
      v-if="chartType === 'clarification' || !data || !data.columns || data.columns.length === 0 || !data.rows || data.rows.length === 0"
      class="h-full flex flex-col items-center justify-center text-slate-400 space-y-4 p-8"
    >
      <el-icon class="text-7xl opacity-40 text-slate-600">
        <QuestionFilled v-if="chartType === 'clarification'" />
        <DataAnalysis v-else />
      </el-icon>
      <div class="text-center space-y-3 max-w-md">
        <p class="text-lg font-semibold text-slate-300">
          {{ chartType === 'clarification' ? '💡 需要更多信息' : '⚠️ 暂无数据' }}
        </p>
        <p class="text-sm text-slate-500 leading-relaxed">
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
import { computed, watch } from 'vue'
import { useTheme } from '@/composables/useTheme'
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

const colorPalette = ['#38bdf8', '#818cf8', '#34d399', '#f472b6'] // Cyan, Indigo, Emerald, Pink

const { isDark } = useTheme()

// Optional: Explicitly watch isDark if side effects were needed, 
// but computed chartOption handles reactivity automatically.
watch(isDark, () => {
  // Theme change triggers computed re-evaluation
})

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

  // Theme Colors
  const isDarkMode = isDark.value
  const textColor = isDarkMode ? '#ccc' : '#333'
  const textColorSecondary = isDarkMode ? '#94a3b8' : '#64748b' // slate-400 vs slate-500
  const axisLineColor = isDarkMode ? '#475569' : '#cbd5e1' // slate-600 vs slate-300
  const gridColor = isDarkMode ? '#334155' : '#e2e8f0' // slate-700 vs slate-200
  const tooltipBg = isDarkMode ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)'
  const tooltipBorder = isDarkMode ? '#334155' : '#e2e8f0'
  const tooltipText = isDarkMode ? '#f1f5f9' : '#1e293b'
  const pieBorderColor = isDarkMode ? '#1e293b' : '#ffffff'

  const commonOption = {
    backgroundColor: 'transparent',
    color: colorPalette,
    textStyle: {
      color: textColorSecondary
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      textStyle: {
        color: tooltipText
      },
      axisPointer: {
        type: 'shadow',
        label: {
          backgroundColor: gridColor
        }
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
      borderColor: gridColor,
      show: false // Hide outer border
    },
    legend: {
      data: [yAxisCol],
      textStyle: {
        color: textColorSecondary
      },
      bottom: 0
    }
  }

  if (props.chartType === 'bar') {
    return {
      ...commonOption,
      xAxis: {
        type: 'category',
        data: xAxisData,
        axisLine: {
          lineStyle: {
            color: axisLineColor
          }
        },
        axisLabel: {
          interval: 0,
          rotate: 30,
          color: textColorSecondary
        },
        axisTick: {
          alignWithLabel: true
        }
      },
      yAxis: {
        type: 'value',
        splitLine: {
          lineStyle: {
            color: gridColor,
            type: 'dashed',
            opacity: 0.3
          }
        },
        axisLabel: {
          color: textColorSecondary
        }
      },
      series: [
        {
          name: yAxisCol,
          type: 'bar',
          data: seriesData,
          itemStyle: {
            borderRadius: [4, 4, 0, 0]
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0,0,0,0.3)'
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
        boundaryGap: false,
        axisLine: {
          lineStyle: {
            color: axisLineColor
          }
        },
        axisLabel: {
          color: textColorSecondary,
          rotate: 30
        },
        axisTick: {
          show: false
        }
      },
      yAxis: {
        type: 'value',
        splitLine: {
          lineStyle: {
            color: gridColor,
            type: 'dashed',
            opacity: 0.3
          }
        },
        axisLabel: {
          color: textColorSecondary
        }
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
            color: colorPalette[0], // Use first color
            borderWidth: 2,
            borderColor: '#fff'
          },
          lineStyle: {
            width: 3,
            shadowColor: 'rgba(56, 189, 248, 0.5)', // Cyan shadow
            shadowBlur: 10
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(56, 189, 248, 0.3)' },
                { offset: 1, color: 'rgba(56, 189, 248, 0.01)' }
              ]
            }
          }
        }
      ]
    }
  }

  if (props.chartType === 'pie') {
    const pieData = props.data.rows.map(row => ({
      name: row[xAxisCol],
      value: row[yAxisCol]
    }))

    return {
      ...commonOption,
      tooltip: {
        trigger: 'item',
        backgroundColor: tooltipBg,
        borderColor: tooltipBorder,
        textStyle: { color: tooltipText }
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        textStyle: { color: textColorSecondary }
      },
      series: [
        {
          name: yAxisCol,
          type: 'pie',
          radius: ['40%', '70%'], // Donut chart
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: pieBorderColor,
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 20,
              fontWeight: 'bold',
              color: textColor
            }
          },
          labelLine: {
            show: false
          },
          data: pieData
        }
      ]
    }
  }

  // Fallback for others if needed
  return {}
})
</script>

<style scoped>
.chart {
  height: 100%;
  width: 100%;
}
</style>
