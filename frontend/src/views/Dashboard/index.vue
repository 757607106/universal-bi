<template>
  <div class="h-full flex flex-col bg-transparent relative">
    <!-- Header -->
    <div class="h-16 border-b border-gray-200/50 dark:border-white/5 px-6 flex items-center justify-between flex-shrink-0 backdrop-blur-sm z-10">
      <div class="flex items-center gap-3">
        <div class="p-2 rounded-lg bg-gradient-to-br from-primary/10 to-cyber-cyan/10 dark:from-primary/20 dark:to-cyber-cyan/20">
          <el-icon class="text-xl text-primary dark:text-primary-glow"><DataBoard /></el-icon>
        </div>
        <div>
          <h2 class="text-lg font-bold text-gray-900 dark:text-slate-100 tracking-tight">我的看板</h2>
          <p class="text-xs text-gray-500 dark:text-slate-400">管理和查看您的数据分析仪表盘</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <el-button @click="showTemplateDialog = true" :icon="FolderOpened" class="!bg-white dark:!bg-white/5 !border-gray-200 dark:!border-white/10 !text-gray-600 dark:!text-slate-300 hover:!bg-gray-50 dark:hover:!bg-white/10 !rounded-xl !h-10 shadow-sm transition-all duration-300 hover:scale-105">
          从模板创建
        </el-button>
        <el-button type="primary" @click="handleCreateDashboard" :icon="Plus" class="!bg-gradient-to-r !from-primary !to-cyber-cyan !border-none !rounded-xl !h-10 !shadow-neon hover:!scale-105 transition-all duration-300">
          新建看板
        </el-button>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6 scroll-smooth">
      <!-- Loading State (Skeleton) -->
      <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="h-48 rounded-2xl bg-white dark:bg-white/5 animate-pulse border border-gray-100 dark:border-white/5"></div>
      </div>

      <!-- Empty State -->
      <div v-else-if="dashboards.length === 0" class="flex flex-col items-center justify-center h-[60vh] animate-fade-in-up">
        <div class="w-24 h-24 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-white/5 dark:to-white/10 flex items-center justify-center mb-6 animate-float">
          <el-icon class="text-5xl text-gray-300 dark:text-slate-600"><DataBoard /></el-icon>
        </div>
        <h3 class="text-xl font-medium text-gray-900 dark:text-slate-200 mb-2">还没有创建看板</h3>
        <p class="text-gray-500 dark:text-slate-400 mb-8 max-w-sm text-center">创建一个新的看板开始可视化您的数据，或者使用预设模板快速开始。</p>
        <el-button type="primary" size="large" @click="handleCreateDashboard" class="!bg-gradient-to-r !from-primary !to-cyber-cyan !border-none !rounded-xl !shadow-neon hover:!scale-105 transition-all duration-300">
          <el-icon class="mr-2"><Plus /></el-icon>
          创建第一个看板
        </el-button>
      </div>

      <!-- Dashboard Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="(dashboard, index) in dashboards"
          :key="dashboard.id"
          class="group relative bg-white dark:bg-dark-glass backdrop-blur-md border border-gray-200/50 dark:border-white/5 rounded-2xl p-6 cursor-pointer transition-all duration-500 hover:border-primary/50 dark:hover:border-primary/50 hover:shadow-lg dark:hover:shadow-[0_0_30px_rgba(59,130,246,0.15)] hover:-translate-y-1"
          :style="{ animationDelay: `${index * 100}ms` }"
          @click="goToDashboard(dashboard.id)"
        >
          <!-- 顶部装饰条 -->
          <div class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary to-cyber-cyan opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-t-2xl"></div>

          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-blue-50 dark:bg-primary/10 flex items-center justify-center text-primary dark:text-primary-glow group-hover:scale-110 transition-transform duration-300">
                <el-icon class="text-xl"><DataBoard /></el-icon>
              </div>
              <div>
                <h3 class="font-bold text-gray-900 dark:text-slate-100 text-lg line-clamp-1 group-hover:text-primary dark:group-hover:text-primary-glow transition-colors">
                  {{ dashboard.name }}
                </h3>
                <span class="text-xs text-gray-400 dark:text-slate-500">{{ formatDate(dashboard.updated_at) }}</span>
              </div>
            </div>
            
            <el-dropdown @command="handleCommand($event, dashboard.id)" @click.stop>
              <button class="p-2 rounded-lg text-gray-400 hover:text-primary hover:bg-gray-100 dark:hover:bg-white/10 transition-all opacity-0 group-hover:opacity-100">
                <el-icon><MoreFilled /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu class="bg-white dark:!bg-slate-800 border-gray-200 dark:!border-slate-700">
                  <el-dropdown-item command="delete" :icon="Delete" class="text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20">删除看板</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          
          <p class="text-sm text-gray-500 dark:text-slate-400 mb-6 line-clamp-2 h-10">
            {{ dashboard.description || '暂无描述' }}
          </p>
          
          <div class="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-white/5">
            <div class="flex items-center gap-2 text-xs text-gray-400 dark:text-slate-500">
              <el-icon><Grid /></el-icon>
              <span>{{ dashboard.cards.length }} 个图表</span>
            </div>
            <div class="flex items-center gap-1 text-xs font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity duration-300 transform translate-x-2 group-hover:translate-x-0">
              <span>进入看板</span>
              <el-icon><ArrowRight /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Dashboard Dialog -->
    <el-dialog 
      v-model="createDialogVisible" 
      title="新建看板" 
      width="500px"
      class="glass-dialog"
      :show-close="false"
    >
      <template #header="{ titleId, titleClass }">
        <div class="flex items-center justify-between border-b border-gray-100 dark:border-white/10 pb-4">
          <h4 :id="titleId" :class="titleClass" class="text-lg font-bold text-gray-900 dark:text-white">新建看板</h4>
          <button @click="createDialogVisible = false" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
            <el-icon class="text-xl"><Close /></el-icon>
          </button>
        </div>
      </template>
      
      <el-form :model="newDashboard" label-position="top" class="mt-4">
        <el-form-item label="看板名称" required>
          <el-input v-model="newDashboard.name" placeholder="请输入看板名称" size="large" class="custom-input" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="newDashboard.description"
            type="textarea"
            :rows="4"
            placeholder="请输入看板描述（可选）"
            class="custom-textarea"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="pt-4 border-t border-gray-100 dark:border-white/10 flex justify-end gap-3">
          <el-button @click="createDialogVisible = false" class="!bg-transparent !border-gray-300 dark:!border-white/20 !text-gray-600 dark:!text-slate-300 hover:!bg-gray-50 dark:hover:!bg-white/5 !rounded-lg">取消</el-button>
          <el-button type="primary" @click="handleConfirmCreate" :loading="creating" class="!bg-gradient-to-r !from-primary !to-cyber-cyan !border-none !rounded-lg !shadow-neon hover:!scale-105 transition-all">
            创建
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 从模板创建对话框 -->
    <el-dialog 
      v-model="showTemplateDialog" 
      title="从模板创建看板" 
      width="800px" 
      class="glass-dialog"
      :show-close="false"
    >
      <template #header="{ titleId, titleClass }">
        <div class="flex items-center justify-between border-b border-gray-100 dark:border-white/10 pb-4">
          <h4 :id="titleId" :class="titleClass" class="text-lg font-bold text-gray-900 dark:text-white">选择模板</h4>
          <button @click="showTemplateDialog = false" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
            <el-icon class="text-xl"><Close /></el-icon>
          </button>
        </div>
      </template>

      <div v-if="loadingTemplates" class="flex flex-col items-center justify-center py-16">
        <div class="w-12 h-12 rounded-full border-4 border-primary/30 border-t-primary animate-spin mb-4"></div>
        <p class="text-gray-500 dark:text-slate-400">加载模板中...</p>
      </div>
      
      <div v-else-if="templates.length === 0" class="text-center py-16 text-gray-500 dark:text-slate-400">
        <div class="w-20 h-20 mx-auto bg-gray-100 dark:bg-white/5 rounded-full flex items-center justify-center mb-4">
          <el-icon class="text-3xl"><FolderOpened /></el-icon>
        </div>
        <p class="text-lg font-medium text-gray-900 dark:text-slate-200">暂无可用模板</p>
        <p class="text-sm mt-2">在看板详情页可以将看板保存为模板</p>
      </div>
      
      <div v-else class="grid grid-cols-2 gap-4 max-h-[500px] overflow-y-auto p-1 custom-scrollbar">
        <div
          v-for="template in templates"
          :key="template.id"
          @click="selectedTemplate = template"
          class="group relative p-5 border rounded-xl cursor-pointer transition-all duration-300"
          :class="[
            selectedTemplate?.id === template.id
              ? 'border-primary bg-primary/5 dark:bg-primary/10 shadow-[0_0_0_2px_rgba(59,130,246,0.2)]'
              : 'border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 hover:border-primary/50 dark:hover:border-primary/50 hover:shadow-lg'
          ]"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="p-2 rounded-lg bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-slate-300 group-hover:text-primary dark:group-hover:text-primary-glow transition-colors">
              <el-icon class="text-xl"><DataBoard /></el-icon>
            </div>
            <div v-if="selectedTemplate?.id === template.id" class="w-5 h-5 rounded-full bg-primary flex items-center justify-center text-white shadow-neon">
              <el-icon class="text-xs"><Check /></el-icon>
            </div>
          </div>
          
          <h4 class="font-bold text-gray-900 dark:text-slate-100 mb-1 group-hover:text-primary dark:group-hover:text-primary-glow transition-colors">{{ template.name }}</h4>
          <p class="text-sm text-gray-500 dark:text-slate-400 line-clamp-2 h-10">{{ template.description || '暂无描述' }}</p>
          
          <div class="mt-4 flex items-center gap-2">
            <el-tag v-if="template.is_public" size="small" effect="dark" class="!bg-green-500/20 !text-green-600 dark:!text-green-400 !border-none">公开</el-tag>
            <el-tag size="small" effect="dark" class="!bg-blue-500/20 !text-blue-600 dark:!text-blue-400 !border-none">系统模板</el-tag>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="pt-4 border-t border-gray-100 dark:border-white/10 flex justify-end gap-3">
          <el-button @click="showTemplateDialog = false" class="!bg-transparent !border-gray-300 dark:!border-white/20 !text-gray-600 dark:!text-slate-300 hover:!bg-gray-50 dark:hover:!bg-white/5 !rounded-lg">取消</el-button>
          <el-button type="primary" @click="handleCreateFromTemplate" :loading="creatingFromTemplate" :disabled="!selectedTemplate" class="!bg-gradient-to-r !from-primary !to-cyber-cyan !border-none !rounded-lg !shadow-neon hover:!scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed">
            创建看板
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import DashboardSkeleton from '@/components/Skeleton/DashboardSkeleton.vue'
import {
  Plus,
  Loading,
  DataBoard,
  MoreFilled,
  Delete,
  Grid,
  FolderOpened,
  ArrowRight,
  Close,
  Check
} from '@element-plus/icons-vue'
import {
  getDashboards,
  createDashboard,
  deleteDashboard,
  getTemplates,
  createDashboardFromTemplate,
  type Dashboard,
  type DashboardTemplateListItem
} from '@/api/dashboard'

const router = useRouter()

const dashboards = ref<Dashboard[]>([])
const loading = ref(false)
const createDialogVisible = ref(false)
const creating = ref(false)
const newDashboard = ref({
  name: '',
  description: ''
})

// 模板相关状态
const showTemplateDialog = ref(false)
const loadingTemplates = ref(false)
const templates = ref<DashboardTemplateListItem[]>([])
const selectedTemplate = ref<DashboardTemplateListItem | null>(null)
const creatingFromTemplate = ref(false)

onMounted(() => {
  loadDashboards()
})

const loadDashboards = async () => {
  loading.value = true
  try {
    dashboards.value = await getDashboards()
  } catch (error) {
    ElMessage.error('加载看板列表失败')
  } finally {
    loading.value = false
  }
}

const handleCreateDashboard = () => {
  newDashboard.value = { name: '', description: '' }
  createDialogVisible.value = true
}

const handleConfirmCreate = async () => {
  if (!newDashboard.value.name.trim()) {
    ElMessage.warning('请输入看板名称')
    return
  }
  
  creating.value = true
  try {
    const dashboard = await createDashboard(
      newDashboard.value.name.trim(),
      newDashboard.value.description.trim() || undefined
    )
    ElMessage.success('看板创建成功')
    createDialogVisible.value = false
    
    // Navigate to new dashboard
    router.push(`/dashboard/${dashboard.id}`)
  } catch (error) {
    ElMessage.error('创建看板失败')
  } finally {
    creating.value = false
  }
}

const goToDashboard = (id: number) => {
  router.push(`/dashboard/${id}`)
}

const handleCommand = async (command: string, dashboardId: number) => {
  if (command === 'delete') {
    try {
      await ElMessageBox.confirm('确定要删除这个看板吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      
      await deleteDashboard(dashboardId)
      ElMessage.success('看板已删除')
      loadDashboards()
    } catch (error: any) {
      if (error !== 'cancel') {
        ElMessage.error('删除失败')
      }
    }
  }
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`

  return date.toLocaleDateString('zh-CN')
}

/**
 * 加载模板列表
 */
const loadTemplates = async () => {
  loadingTemplates.value = true
  try {
    templates.value = await getTemplates()
  } catch (error) {
    ElMessage.error('加载模板失败')
  } finally {
    loadingTemplates.value = false
  }
}

/**
 * 打开模板对话框时加载模板
 */
import { watch } from 'vue'
watch(showTemplateDialog, (val) => {
  if (val) {
    selectedTemplate.value = null
    loadTemplates()
  }
})

/**
 * 从模板创建看板
 */
const handleCreateFromTemplate = async () => {
  if (!selectedTemplate.value) return

  creatingFromTemplate.value = true
  try {
    const dashboard = await createDashboardFromTemplate(selectedTemplate.value.id)
    ElMessage.success('看板创建成功')
    showTemplateDialog.value = false
    router.push(`/dashboard/${dashboard.id}`)
  } catch (error) {
    ElMessage.error('创建看板失败')
  } finally {
    creatingFromTemplate.value = false
  }
}
</script>

<style scoped>
.glass-dialog :deep(.el-dialog) {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  padding: 24px;
}

.dark .glass-dialog :deep(.el-dialog) {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.glass-dialog :deep(.el-dialog__header) {
  margin: 0;
  padding: 0;
}

.glass-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.glass-dialog :deep(.el-dialog__footer) {
  padding: 0;
}

/* Custom Input Styles */
:deep(.custom-input .el-input__wrapper) {
  background-color: rgba(243, 244, 246, 0.5) !important;
  box-shadow: none !important;
  border: 1px solid rgba(229, 231, 235, 1);
  border-radius: 12px;
  padding: 8px 12px;
  transition: all 0.3s;
}

:deep(.dark .custom-input .el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.05) !important;
  border-color: rgba(255, 255, 255, 0.1);
}

:deep(.custom-input .el-input__wrapper.is-focus) {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
  background-color: white !important;
}

:deep(.dark .custom-input .el-input__wrapper.is-focus) {
  background-color: rgba(255, 255, 255, 0.1) !important;
}

:deep(.custom-textarea .el-textarea__inner) {
  background-color: rgba(243, 244, 246, 0.5) !important;
  box-shadow: none !important;
  border: 1px solid rgba(229, 231, 235, 1);
  border-radius: 12px;
  padding: 12px;
  transition: all 0.3s;
}

:deep(.dark .custom-textarea .el-textarea__inner) {
  background-color: rgba(255, 255, 255, 0.05) !important;
  border-color: rgba(255, 255, 255, 0.1);
  color: white;
}

:deep(.custom-textarea .el-textarea__inner:focus) {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
  background-color: white !important;
}

:deep(.dark .custom-textarea .el-textarea__inner:focus) {
  background-color: rgba(255, 255, 255, 0.1) !important;
}

.animate-fade-in-up {
  animation: fadeInUp 0.5s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
