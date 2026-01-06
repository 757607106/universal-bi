<template>
  <div class="h-full overflow-auto bg-gray-50 dark:bg-gray-950">
    <div class="max-w-7xl mx-auto p-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold mb-2 text-gray-900 dark:text-gray-100">数据仪表板</h1>
        <p class="text-gray-600 dark:text-gray-400">关键指标和洞察概览</p>
      </div>

      <!-- KPI 指标 -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <el-card
          v-for="kpi in kpiData"
          :key="kpi.label"
          class="p-6 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 hover:shadow-xl dark:hover:shadow-blue-900/20 transition-all duration-200"
          shadow="hover"
        >
          <div class="flex items-start justify-between mb-4">
            <div :class="`w-12 h-12 rounded-xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center ${kpi.color}`">
              <el-icon class="w-6 h-6">
                <component :is="kpi.icon" />
              </el-icon>
            </div>
            <span :class="`text-sm font-medium px-2 py-1 rounded-lg ${kpi.trend === 'up' ? 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400' : 'text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400'}`">
              {{ kpi.change }}
            </span>
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-1">{{ kpi.label }}</p>
          <p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ kpi.value }}</p>
        </el-card>
      </div>

      <!-- 固定的图表 -->
      <div v-if="pinnedCharts && pinnedCharts.length > 0" class="mb-6">
        <h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">固定的图表</h2>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <el-card
            v-for="(chart, idx) in pinnedCharts"
            :key="idx"
            class="p-6 relative bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800"
            shadow="hover"
          >
            <el-button
              link
              class="absolute top-4 right-4 h-8 w-8 text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400"
              @click="handleRemoveChart(idx)"
            >
              <el-icon class="w-4 h-4">
                <Close />
              </el-icon>
            </el-button>
            <h3 class="font-semibold mb-4 text-gray-900 dark:text-gray-100">{{ chart.title }}</h3>
            <div class="w-full h-[300px]">
              <v-chart :option="getBarChartOption(chart.data)" autoresize />
            </div>
          </el-card>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <el-card class="lg:col-span-2 p-6 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800" shadow="hover">
          <h2 class="font-semibold text-lg mb-4 text-gray-900 dark:text-gray-100">营收趋势</h2>
          <div class="w-full h-[300px]">
            <v-chart :option="lineChartOption" autoresize />
          </div>
        </el-card>

        <el-card class="p-6 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800" shadow="hover">
          <h2 class="font-semibold text-lg mb-4 text-gray-900 dark:text-gray-100">品类销售占比</h2>
          <div class="w-full h-[300px]">
            <v-chart :option="pieChartOption" />
          </div>
          <div class="mt-4 space-y-2">
            <div
              v-for="item in pieChartData"
              :key="item.name"
              class="flex items-center justify-between text-sm"
            >
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full shadow-sm" :style="{ backgroundColor: item.color }" />
                <span class="text-gray-600 dark:text-gray-400">{{ item.name }}</span>
              </div>
              <span class="font-medium text-gray-900 dark:text-gray-100">{{ item.value }}%</span>
            </div>
          </div>
        </el-card>
      </div>

      <div class="grid grid-cols-1 gap-6">
        <el-card class="p-6 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800" shadow="hover">
          <h2 class="font-semibold text-lg mb-4 text-gray-900 dark:text-gray-100">品类销售表现</h2>
          <div class="w-full h-[300px]">
            <v-chart :option="barChartOption" autoresize />
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Money, User, ShoppingCart, DataAnalysis, Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import * as EChartsComponents from 'echarts/components'
import VChart from 'vue-echarts'

const _echartsItemsDashboard = [
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  EChartsComponents.GridComponent,
  EChartsComponents.TooltipComponent,
  EChartsComponents.LegendComponent,
].filter(Boolean)
try {
  use(_echartsItemsDashboard)
} catch (err) {
  // eslint-disable-next-line no-console
  console.warn('echarts use failed (dashboard):', err)
}

interface Props {
  pinnedCharts?: any[]
  onRemoveChart?: (id: string | number) => void
}

interface Emits {
  (e: 'remove-chart', id: string | number): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const kpiData = [
  { label: '总营收', value: '¥331,000', change: '+12.5%', trend: 'up', icon: Money, color: 'text-green-600' },
  { label: '活跃用户', value: '45,678', change: '+8.2%', trend: 'up', icon: User, color: 'text-blue-600' },
  { label: '订单总数', value: '2,341', change: '+23.1%', trend: 'up', icon: ShoppingCart, color: 'text-purple-600' },
  { label: '平均订单额', value: '¥141.38', change: '-2.4%', trend: 'down', icon: DataAnalysis, color: 'text-orange-600' },
]

const lineChartData = [
  { date: '1月', value: 4000 },
  { date: '2月', value: 3000 },
  { date: '3月', value: 5000 },
  { date: '4月', value: 4500 },
  { date: '5月', value: 6000 },
  { date: '6月', value: 5500 },
]

const pieChartData = [
  { name: '电子产品', value: 35, color: '#409EFF' },
  { name: '服装鞋包', value: 25, color: '#67C23A' },
  { name: '家居用品', value: 20, color: '#E6A23C' },
  { name: '图书文娱', value: 12, color: '#F56C6C' },
  { name: '其他', value: 8, color: '#909399' },
]

const barChartData = [
  { category: '电子产品', sales: 45000 },
  { category: '服装鞋包', sales: 38000 },
  { category: '家居用品', sales: 29000 },
  { category: '图书文娱', sales: 21000 },
  { category: '运动户外', sales: 18000 },
]

const lineChartOption = {
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: lineChartData.map(item => item.date),
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
    data: lineChartData.map(item => item.value),
    type: 'line',
    smooth: true,
    lineStyle: {
      color: '#409EFF',
      width: 3
    },
    itemStyle: {
      color: '#409EFF'
    },
    symbolSize: 6
  }],
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderColor: '#e5e7eb',
    textStyle: {
      color: '#333'
    }
  }
}

const pieChartOption = {
  series: [{
    type: 'pie',
    data: pieChartData,
    radius: ['40%', '70%'],
    itemStyle: {
      borderRadius: 5,
      borderColor: '#fff',
      borderWidth: 2
    },
    label: {
      show: false
    }
  }],
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderColor: '#e5e7eb',
    textStyle: {
      color: '#333'
    },
    formatter: '{b}: {c}%'
  }
}

const barChartOption = {
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: barChartData.map(item => item.category),
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
    data: barChartData.map(item => item.sales),
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
}

const getBarChartOption = (data: any[]) => ({
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

const handleRemoveChart = (id: string | number) => {
  emit('remove-chart', id)
  ElMessage.success('已移除图表')
}
</script>
