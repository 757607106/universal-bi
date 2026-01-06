<template>
  <div class="h-full flex flex-col bg-gray-100 dark:bg-gray-950">
    <!-- Header -->
    <div class="h-16 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 flex items-center justify-between flex-shrink-0">
      <div class="flex items-center gap-4">
        <el-button :icon="ArrowLeft" @click="goBack" circle size="small" />
        <div>
          <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ dashboard?.name }}</h2>
          <p v-if="dashboard?.description" class="text-sm text-gray-500">{{ dashboard.description }}</p>
        </div>
      </div>
      
      <div class="flex items-center gap-2">
        <el-button :icon="Refresh" @click="refreshAllCards" size="small">
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6">
      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center h-64">
        <el-icon class="is-loading text-4xl text-gray-400"><Loading /></el-icon>
      </div>

      <!-- Empty State -->
      <div v-else-if="!dashboard || dashboard.cards.length === 0" class="flex flex-col items-center justify-center h-64">
        <el-icon class="text-6xl text-gray-300 dark:text-gray-700 mb-4"><Document /></el-icon>
        <p class="text-gray-500 dark:text-gray-400 mb-4">还没有添加任何卡片</p>
        <p class="text-sm text-gray-400">在智能问答页面生成图表后，点击"保存到看板"添加卡片</p>
      </div>

      <!-- Dashboard Cards Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <el-card
          v-for="card in dashboard.cards"
          :key="card.id"
          shadow="hover"
          class="dashboard-card"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <span class="font-semibold text-gray-900 dark:text-gray-100">{{ card.title }}</span>
              <div class="flex items-center gap-2">
                <el-button
                  :icon="Refresh"
                  size="small"
                  circle
                  @click.stop="refreshCard(card.id)"
                  :loading="cardLoadingMap[card.id]"
                />
                <el-button
                  :icon="Delete"
                  size="small"
                  circle
                  @click.stop="handleDeleteCard(card.id)"
                />
              </div>
            </div>
          </template>
          
          <div class="h-80">
            <!-- Loading -->
            <div v-if="cardLoadingMap[card.id]" class="h-full flex items-center justify-center">
              <el-icon class="is-loading text-3xl text-gray-400"><Loading /></el-icon>
            </div>
            
            <!-- Error -->
            <div v-else-if="cardErrorMap[card.id]" class="h-full flex items-center justify-center">
              <div class="text-center text-red-500">
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
            <div v-else class="h-full flex items-center justify-center text-gray-400">
              <p>暂无数据</p>
            </div>
          </div>
        </el-card>
      </div>
    </div>
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
  Warning
} from '@element-plus/icons-vue'
import {
  getDashboardDetail,
  getCardData,
  deleteCard,
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
</script>

<style scoped>
.dashboard-card {
  transition: all 0.3s;
}

.dashboard-card:hover {
  transform: translateY(-2px);
}
</style>
