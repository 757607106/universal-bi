<template>
  <div class="h-full overflow-auto bg-gray-50 dark:bg-gray-950">
    <div class="max-w-7xl mx-auto p-8">
      <div class="mb-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-3xl font-bold mb-2 text-gray-900 dark:text-gray-100 tracking-tight">数据连接</h1>
          <p class="text-gray-600 dark:text-gray-400">管理您的数据库连接和数据源配置</p>
        </div>
        <div class="flex items-center gap-4 w-full md:w-auto">
          <div class="relative flex-1 md:w-64 group">
            <el-input
              v-model="searchTerm"
              placeholder="搜索连接..."
              clearable
              class="w-full !rounded-xl transition-all duration-300"
            >
              <template #prefix>
                <el-icon class="text-gray-400 group-hover:text-blue-500 transition-colors"><Search /></el-icon>
              </template>
            </el-input>
          </div>
          <el-button
            type="primary"
            class="!rounded-xl !px-6 !py-5 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/40 transition-all duration-300 transform hover:-translate-y-0.5"
            @click="handleAddClick"
          >
            <el-icon class="w-4 h-4 mr-2"><Plus /></el-icon>
            添加连接
          </el-button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <ConnectionCard
          v-for="conn in filteredConnections"
          :key="conn.id"
          v-bind="conn"
          @edit="handleEdit(conn)"
          @delete="handleDeleteClick(conn.id)"
          @click="handleCardClick(conn.id)"
          class="h-full cursor-pointer"
        />
      </div>

      <div v-if="filteredConnections.length === 0" class="text-center py-12 text-gray-400 dark:text-gray-600">
        <p>未找到匹配的连接</p>
      </div>
    </div>

    <AddConnectionDialog
      v-model="dialogOpen"
      :edit-data="editingConnection"
      @save="handleSave"
      @close="handleDialogClose"
    />

    <DeleteConfirmDialog
      v-model="deleteDialogOpen"
      title="删除数据库连接"
      :description="`确定要删除 ${deletingConnection?.name || ''} 吗？此操作无法撤销。`"
      @confirm="handleDeleteConfirm"
    />

    <DataPreviewDrawer
      v-model="previewDrawerOpen"
      :datasource-id="previewDataSourceId"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Plus, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ConnectionCard from './ConnectionCard.vue'
import AddConnectionDialog from './AddConnectionDialog.vue'
import DeleteConfirmDialog from './DeleteConfirmDialog.vue'
import DataPreviewDrawer from './DataPreviewDrawer.vue'
import { getDataSourceList, deleteDataSource, type DataSource } from '../api/datasource'

interface DataSourceWithStatus extends DataSource {
  status: '已连接' | '未连接'
  lastSync: string
  database?: string
}

const connections = ref<DataSourceWithStatus[]>([])
const searchTerm = ref('')
const dialogOpen = ref(false)
const deleteDialogOpen = ref(false)
const previewDrawerOpen = ref(false)
const editingConnection = ref<DataSource | null>(null)
const deletingId = ref<number | null>(null)
const previewDataSourceId = ref<number | null>(null)

const filteredConnections = computed(() =>
  connections.value.filter(conn =>
    conn.name.toLowerCase().includes(searchTerm.value.toLowerCase()) ||
    conn.type.toLowerCase().includes(searchTerm.value.toLowerCase())
  )
)

const deletingConnection = computed(() =>
  connections.value.find(c => c.id === deletingId.value)
)

const fetchConnections = async () => {
  try {
    const data = await getDataSourceList()
    // 适配后端数据到前端显示格式
    connections.value = data.map(item => ({
      ...item,
      // 后端没有 status 和 lastSync，暂时 mock
      status: '已连接',
      lastSync: '刚刚',
      database: item.database_name // 兼容前端组件字段名
    }))
  } catch (error) {
    ElMessage.error('获取连接列表失败')
  }
}

onMounted(() => {
  fetchConnections()
})

const handleAddClick = () => {
  editingConnection.value = null
  dialogOpen.value = true
}

const handleEdit = (connection: DataSource) => {
  editingConnection.value = connection
  dialogOpen.value = true
}

const handleSave = () => {
  // 保存成功后刷新列表
  fetchConnections()
}

const handleDialogClose = () => {
  dialogOpen.value = false
}

const handleDeleteClick = (id: number) => {
  deletingId.value = id
  deleteDialogOpen.value = true
}

const handleCardClick = (id: number) => {
  previewDataSourceId.value = id
  previewDrawerOpen.value = true
}

const handleDeleteConfirm = async () => {
  if (deletingId.value) {
    try {
      await deleteDataSource(deletingId.value)
      ElMessage.success('数据库连接已删除')
      await fetchConnections()
    } catch (error) {
      ElMessage.error('删除失败')
    }
    deleteDialogOpen.value = false
    deletingId.value = null
  }
}
</script>
