<template>
  <div class="h-full flex flex-col bg-transparent">
    <!-- Header -->
    <div class="h-16 border-b border-gray-200 dark:border-slate-700/50 bg-white/50 dark:bg-transparent px-6 flex items-center justify-between flex-shrink-0 transition-colors">
      <div class="flex items-center gap-4">
        <el-button :icon="ArrowLeft" @click="goBack" circle size="small" class="!bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-700 !text-gray-600 dark:!text-slate-300 hover:!bg-gray-100 dark:hover:!bg-slate-700 transition-colors" />
        <div>
          <h2 class="text-lg font-semibold text-gray-900 dark:text-slate-100 transition-colors">{{ dashboard?.name }}</h2>
          <p v-if="dashboard?.description" class="text-sm text-gray-500 dark:text-slate-400 transition-colors">{{ dashboard.description }}</p>
        </div>
      </div>
      
      <div class="flex items-center gap-4">
        <!-- Time Filter -->
        <el-radio-group v-model="timeRange" size="small" class="!bg-gray-100 dark:!bg-slate-800 p-0.5 rounded-lg border border-gray-200 dark:border-slate-700 transition-colors">
          <el-radio-button label="today">今日</el-radio-button>
          <el-radio-button label="week">本周</el-radio-button>
          <el-radio-button label="month">本月</el-radio-button>
        </el-radio-group>

        <el-button :icon="Refresh" @click="refreshAllCards" size="small" class="!bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-700 !text-gray-600 dark:!text-slate-300 hover:!bg-gray-100 dark:hover:!bg-slate-700 transition-colors">
          刷新数据
        </el-button>

        <el-button
          :icon="FolderAdd"
          @click="showSaveTemplateDialog = true"
          size="small"
          class="!bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-700 !text-gray-600 dark:!text-slate-300 hover:!bg-gray-100 dark:hover:!bg-slate-700 transition-colors"
        >
          保存为模板
        </el-button>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6 space-y-6">
      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center h-64">
        <el-icon class="is-loading text-4xl text-gray-400 dark:text-slate-400"><Loading /></el-icon>
      </div>

      <!-- Empty State -->
      <div v-else-if="!dashboard || dashboard.cards.length === 0" class="flex flex-col items-center justify-center h-64">
        <el-icon class="text-6xl text-gray-300 dark:text-slate-700 mb-4 transition-colors"><Document /></el-icon>
        <p class="text-gray-500 dark:text-slate-400 mb-4 transition-colors">还没有添加任何卡片</p>
        <p class="text-sm text-gray-400 dark:text-slate-500 transition-colors">在智能问答页面生成图表后，点击"保存到看板"添加卡片</p>
      </div>

      <template v-else>
        <!-- KPI Cards Section (Mock) -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div 
            v-for="(kpi, index) in kpiCards" 
            :key="index"
            class="relative overflow-hidden rounded-xl border border-gray-100 dark:border-slate-700/50 bg-white dark:bg-slate-800/80 p-6 transition-all hover:-translate-y-1 hover:border-blue-500/30 hover:shadow-lg hover:shadow-blue-500/10 group shadow-sm"
          >
            <!-- Decorative Background Icon -->
            <div class="absolute -right-4 -top-4 text-9xl text-gray-50 dark:text-slate-700/10 transition-transform group-hover:scale-110 group-hover:rotate-12">
              <component :is="kpi.icon" />
            </div>
            
            <div class="relative z-10">
              <div class="flex items-center gap-2 mb-2">
                <div class="p-2 rounded-lg" :class="kpi.iconBg">
                  <el-icon :class="kpi.iconColor"><component :is="kpi.icon" /></el-icon>
                </div>
                <span class="text-sm font-medium text-gray-500 dark:text-slate-400 transition-colors">{{ kpi.title }}</span>
              </div>
              
              <div class="mt-4 flex items-baseline gap-2">
                <span class="text-3xl font-bold text-gray-900 dark:text-slate-100 tracking-tight transition-colors">{{ kpi.value }}</span>
                <span class="text-xs text-gray-400 dark:text-slate-500 transition-colors">CNY</span>
              </div>
              
              <div class="mt-2 flex items-center text-xs">
                <span :class="kpi.trend > 0 ? 'text-emerald-500 dark:text-emerald-400' : 'text-rose-500 dark:text-rose-400'" class="flex items-center font-medium">
                  <el-icon class="mr-0.5">
                    <CaretTop v-if="kpi.trend > 0" />
                    <CaretBottom v-else />
                  </el-icon>
                  {{ Math.abs(kpi.trend) }}%
                </span>
                <span class="ml-2 text-gray-400 dark:text-slate-500 transition-colors">较上期</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Dashboard Cards Grid -->
        <div class="grid grid-cols-12 gap-6">
          <el-card
            v-for="card in dashboard.cards"
            :key="card.id"
            shadow="hover"
            class="dashboard-card border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 transition-all duration-300"
            :class="getCardColSpan(card.chart_type)"
          >
            <template #header>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="w-1 h-4 bg-blue-500 rounded-full"></span>
                  <span class="font-semibold text-gray-800 dark:text-slate-200 tracking-wide transition-colors">{{ card.title }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <el-button
                    :icon="Refresh"
                    size="small"
                    circle
                    @click.stop="refreshCard(card.id)"
                    :loading="cardLoadingMap[card.id]"
                    class="!bg-gray-100 dark:!bg-slate-700 !border-gray-200 dark:!border-slate-600 !text-gray-500 dark:!text-slate-300 hover:!bg-gray-200 dark:hover:!bg-slate-600 transition-colors"
                  />
                  <el-button
                    :icon="Delete"
                    size="small"
                    circle
                    @click.stop="handleDeleteCard(card.id)"
                    class="!bg-gray-100 dark:!bg-slate-700 !border-gray-200 dark:!border-slate-600 !text-gray-500 dark:!text-slate-300 hover:!bg-gray-200 dark:hover:!bg-slate-600 transition-colors"
                  />
                </div>
              </div>
            </template>
            
            <div class="h-80">
              <!-- Loading -->
              <div v-if="cardLoadingMap[card.id]" class="h-full flex items-center justify-center">
                <el-icon class="is-loading text-3xl text-slate-400"><Loading /></el-icon>
              </div>
              
              <!-- Error -->
              <div v-else-if="cardErrorMap[card.id]" class="h-full flex items-center justify-center">
                <div class="text-center text-red-400">
                  <el-icon class="text-4xl mb-2"><Warning /></el-icon>
                  <p class="text-sm">{{ cardErrorMap[card.id] }}</p>
                </div>
              </div>
              
              <!-- Chart -->
              <DynamicChart
                v-else-if="cardDataMap[card.id]"
                :chart-type="card.chart_type"
                :data="cardDataMap[card.id]"
              />
              
              <!-- No Data -->
              <div v-else class="h-full flex items-center justify-center text-slate-500">
                <p>暂无数据</p>
              </div>
            </div>
          </el-card>
        </div>
      </template>
    </div>

    <!-- 保存为模板对话框 -->
    <el-dialog
      v-model="showSaveTemplateDialog"
      title="保存为模板"
      width="450px"
      class="dark:bg-slate-800"
    >
      <el-form :model="templateForm" label-position="top">
        <el-form-item label="模板名称" required>
          <el-input v-model="templateForm.name" placeholder="输入模板名称" />
        </el-form-item>
        <el-form-item label="模板描述">
          <el-input v-model="templateForm.description" type="textarea" :rows="3" placeholder="描述这个模板的用途" />
        </el-form-item>
        <el-form-item label="公开模板">
          <el-switch v-model="templateForm.is_public" />
          <span class="ml-2 text-sm text-gray-500">公开后其他用户可以使用此模板</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveTemplateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveAsTemplate" :loading="savingTemplate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Refresh,
  Loading,
  Document,
  Delete,
  Warning,
  CaretTop,
  CaretBottom,
  Money,
  Goods,
  Box,
  TrendCharts,
  FolderAdd
} from '@element-plus/icons-vue'
import {
  getDashboardDetail,
  getCardData,
  deleteCard,
  saveDashboardAsTemplate,
  type Dashboard,
  type CardData
} from '@/api/dashboard'
import DynamicChart from '@/components/Charts/DynamicChart.vue'

const router = useRouter()
const route = useRoute()

const dashboard = ref<Dashboard | null>(null)
const loading = ref(false)
const cardDataMap = reactive<Record<number, CardData>>({})
const cardLoadingMap = reactive<Record<number, boolean>>({})
const cardErrorMap = reactive<Record<number, string>>({})

// UI Controls
const timeRange = ref('week')

// 模板相关状态
const showSaveTemplateDialog = ref(false)
const savingTemplate = ref(false)
const templateForm = reactive({
  name: '',
  description: '',
  is_public: false
})

// Mock KPI Data
const kpiCards = ref([
  {
    title: '总销售额',
    value: '128,430',
    trend: 15.8,
    icon: Money,
    iconBg: 'bg-blue-500/10',
    iconColor: 'text-blue-500'
  },
  {
    title: '采购支出',
    value: '45,200',
    trend: -5.2,
    icon: Goods,
    iconBg: 'bg-indigo-500/10',
    iconColor: 'text-indigo-500'
  },
  {
    title: '库存总值',
    value: '85,600',
    trend: 2.4,
    icon: Box,
    iconBg: 'bg-emerald-500/10',
    iconColor: 'text-emerald-500'
  },
  {
    title: '净利润',
    value: '32,800',
    trend: 12.5,
    icon: TrendCharts,
    iconBg: 'bg-pink-500/10',
    iconColor: 'text-pink-500'
  }
])

// Grid Layout Helper
const getCardColSpan = (chartType: string) => {
  if (['line', 'bar', 'area', 'scatter'].includes(chartType)) {
    return 'col-span-12 lg:col-span-8'
  }
  return 'col-span-12 lg:col-span-4'
}

onMounted(() => {
  loadDashboard()
})

const loadDashboard = async () => {
  const id = parseInt(route.params.id as string)
  if (!id) {
    ElMessage.error('无效的看板ID')
    return
  }
  
  loading.value = true
  try {
    dashboard.value = await getDashboardDetail(id)
    
    // Load data for all cards
    if (dashboard.value.cards.length > 0) {
      await Promise.all(
        dashboard.value.cards.map(card => loadCardData(card.id))
      )
    }
  } catch (error) {
    ElMessage.error('加载看板失败')
  } finally {
    loading.value = false
  }
}

const loadCardData = async (cardId: number) => {
  cardLoadingMap[cardId] = true
  cardErrorMap[cardId] = ''
  
  try {
    const data = await getCardData(cardId)
    cardDataMap[cardId] = data
  } catch (error: any) {
    console.error(`Failed to load card ${cardId}:`, error)
    cardErrorMap[cardId] = error.response?.data?.detail || '加载数据失败'
  } finally {
    cardLoadingMap[cardId] = false
  }
}

const refreshCard = async (cardId: number) => {
  await loadCardData(cardId)
  ElMessage.success('数据已刷新')
}

const refreshAllCards = async () => {
  if (!dashboard.value) return
  
  try {
    await Promise.all(
      dashboard.value.cards.map(card => loadCardData(card.id))
    )
    ElMessage.success('所有数据已刷新')
  } catch (error) {
    ElMessage.error('刷新失败')
  }
}

const handleDeleteCard = async (cardId: number) => {
  try {
    await ElMessageBox.confirm('确定要删除这个卡片吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteCard(cardId)
    ElMessage.success('卡片已删除')
    
    // Reload dashboard
    loadDashboard()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const goBack = () => {
  router.push('/dashboard')
}

/**
 * 保存为模板
 */
const handleSaveAsTemplate = async () => {
  if (!templateForm.name.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }

  if (!dashboard.value) return

  savingTemplate.value = true
  try {
    await saveDashboardAsTemplate(dashboard.value.id, {
      name: templateForm.name,
      description: templateForm.description,
      is_public: templateForm.is_public
    })
    ElMessage.success('模板保存成功')
    showSaveTemplateDialog.value = false
    // 重置表单
    templateForm.name = ''
    templateForm.description = ''
    templateForm.is_public = false
  } catch (error) {
    ElMessage.error('保存模板失败')
  } finally {
    savingTemplate.value = false
  }
}
</script>

<style scoped>
.dashboard-card {
  transition: all 0.3s;
}

.dashboard-card:hover {
  transform: translateY(-2px);
}
</style>
