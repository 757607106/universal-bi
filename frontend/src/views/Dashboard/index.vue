<template>
  <div class="h-full flex flex-col bg-transparent">
    <!-- Header -->
    <div class="h-16 border-b border-gray-200 dark:border-slate-700/50 bg-transparent px-6 flex items-center justify-between flex-shrink-0">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-slate-100">我的看板</h2>
      <div class="flex items-center gap-3">
        <el-button @click="showTemplateDialog = true" :icon="FolderOpened" class="!bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-700 !text-gray-600 dark:!text-slate-300 hover:!bg-gray-100 dark:hover:!bg-slate-700">
          从模板创建
        </el-button>
        <el-button type="primary" @click="handleCreateDashboard" :icon="Plus" class="!bg-blue-600 !border-none hover:!bg-blue-500">
          新建看板
        </el-button>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6">
      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center h-64">
        <el-icon class="is-loading text-4xl text-gray-400 dark:text-slate-400"><Loading /></el-icon>
      </div>

      <!-- Empty State -->
      <div v-else-if="dashboards.length === 0" class="flex flex-col items-center justify-center h-64">
        <el-icon class="text-6xl text-gray-300 dark:text-slate-700 mb-4"><DataBoard /></el-icon>
        <p class="text-gray-500 dark:text-slate-400 mb-4">还没有创建看板</p>
        <el-button type="primary" @click="handleCreateDashboard">创建第一个看板</el-button>
      </div>

      <!-- Dashboard Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <el-card
          v-for="dashboard in dashboards"
          :key="dashboard.id"
          shadow="hover"
          class="cursor-pointer transition-all duration-300 bg-white dark:!bg-slate-800 border-gray-200 dark:!border-slate-700 group hover:border-blue-500 dark:hover:!border-blue-500/50"
          @click="goToDashboard(dashboard.id)"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <span class="font-semibold text-gray-900 dark:text-slate-100">{{ dashboard.name }}</span>
              <el-dropdown @command="handleCommand($event, dashboard.id)">
                <el-icon class="cursor-pointer text-gray-400 dark:text-slate-400 hover:text-blue-500"><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu class="bg-white dark:!bg-slate-800 border-gray-200 dark:!border-slate-700">
                    <el-dropdown-item command="delete" :icon="Delete" class="text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
          
          <div class="space-y-3">
            <p v-if="dashboard.description" class="text-sm text-gray-500 dark:text-slate-400">
              {{ dashboard.description }}
            </p>
            
            <div class="flex items-center justify-between text-xs text-gray-400 dark:text-slate-500">
              <div class="flex items-center gap-1">
                <el-icon><Grid /></el-icon>
                <span>{{ dashboard.cards.length }} 个卡片</span>
              </div>
              <span>{{ formatDate(dashboard.updated_at) }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- Create Dashboard Dialog -->
    <el-dialog v-model="createDialogVisible" title="新建看板" width="500px">
      <el-form :model="newDashboard" label-width="80px">
        <el-form-item label="看板名称" required>
          <el-input v-model="newDashboard.name" placeholder="请输入看板名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="newDashboard.description"
            type="textarea"
            :rows="3"
            placeholder="请输入看板描述（可选）"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmCreate" :loading="creating">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 从模板创建对话框 -->
    <el-dialog v-model="showTemplateDialog" title="从模板创建看板" width="600px" class="dark:bg-slate-800">
      <div v-if="loadingTemplates" class="flex items-center justify-center py-8">
        <el-icon class="is-loading text-2xl text-gray-400"><Loading /></el-icon>
      </div>
      <div v-else-if="templates.length === 0" class="text-center py-8 text-gray-500 dark:text-slate-400">
        <el-icon class="text-4xl mb-2"><FolderOpened /></el-icon>
        <p>暂无可用模板</p>
        <p class="text-sm mt-1">在看板详情页可以将看板保存为模板</p>
      </div>
      <div v-else class="space-y-3 max-h-96 overflow-y-auto">
        <div
          v-for="template in templates"
          :key="template.id"
          @click="selectedTemplate = template"
          class="p-4 border rounded-lg cursor-pointer transition-all"
          :class="[
            selectedTemplate?.id === template.id
              ? 'border-blue-500 bg-blue-50 dark:bg-slate-700'
              : 'border-gray-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-slate-600'
          ]"
        >
          <div class="flex items-center justify-between">
            <div>
              <h4 class="font-medium text-gray-900 dark:text-slate-100">{{ template.name }}</h4>
              <p v-if="template.description" class="text-sm text-gray-500 dark:text-slate-400 mt-1">{{ template.description }}</p>
            </div>
            <el-tag v-if="template.is_public" size="small" type="success">公开</el-tag>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showTemplateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateFromTemplate" :loading="creatingFromTemplate" :disabled="!selectedTemplate">
          创建看板
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Loading,
  DataBoard,
  MoreFilled,
  Delete,
  Grid,
  FolderOpened
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
