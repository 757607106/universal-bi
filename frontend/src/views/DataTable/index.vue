<template>
  <div class="h-full overflow-auto bg-transparent p-8">
    <div class="max-w-7xl mx-auto">
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-3xl font-bold mb-2 text-gray-900 dark:text-slate-100">数据表管理</h1>
          <p class="text-gray-500 dark:text-slate-400">管理和组织您的数据表，支持Excel上传和数据源表选择</p>
        </div>
        <div class="flex gap-3">
          <el-button @click="folderManagerVisible = true" class="bg-purple-600 shadow-lg shadow-purple-500/30 hover:bg-purple-500 border-none text-white">
            <el-icon class="mr-2"><Folder /></el-icon>
            文件夹管理
          </el-button>
          <el-button type="primary" @click="createDialogVisible = true" class="bg-blue-600 shadow-lg shadow-blue-500/30 hover:bg-blue-500 border-none">
            <el-icon class="mr-2"><Plus /></el-icon>
            新建数据表
          </el-button>
        </div>
      </div>

      <!-- 数据表列表 -->
      <div>
        <!-- 文件夹过滤 -->
          <div class="mb-4 flex items-center gap-2">
            <span class="text-sm text-gray-500">筛选：</span>
            <el-select
              v-model="selectedFolderId"
              placeholder="全部文件夹"
              clearable
              class="w-48"
              @change="loadDataTables"
            >
              <el-option label="全部文件夹" :value="undefined" />
              <el-option label="未分类" :value="null" />
              <el-option
                v-for="folder in folders"
                :key="folder.id"
                :label="folder.name"
                :value="folder.id"
              />
            </el-select>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索数据表名称"
              clearable
              class="w-64"
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>

          <!-- 数据表列表 -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <el-card
              v-for="table in filteredTables"
              :key="table.id"
              class="hover:shadow-lg transition-all duration-300 border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 group hover:border-blue-500 dark:hover:border-blue-500/50"
            >
              <template #header>
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <el-icon class="text-blue-500" :size="20">
                      <component :is="getMethodIcon(table.creation_method)" />
                    </el-icon>
                    <span class="font-bold text-gray-900 dark:text-slate-100 truncate">{{ table.display_name }}</span>
                  </div>
                  <el-tag :type="table.status === 'active' ? 'success' : 'info'" effect="dark" size="small">
                    {{ table.status === 'active' ? '活跃' : '归档' }}
                  </el-tag>
                </div>
              </template>

              <div class="space-y-3">
                <div class="flex items-center justify-between text-sm">
                  <span class="text-gray-500 dark:text-slate-400">建表方式</span>
                  <span class="text-gray-900 dark:text-slate-200">
                    {{ table.creation_method === 'excel_upload' ? 'Excel上传' : '数据源表' }}
                  </span>
                </div>

                <div class="flex items-center justify-between text-sm">
                  <span class="text-gray-500 dark:text-slate-400">行数/列数</span>
                  <span class="font-medium text-gray-900 dark:text-slate-200">
                    {{ table.row_count.toLocaleString() }} / {{ table.column_count }}
                  </span>
                </div>

                <div class="flex items-center justify-between text-sm">
                  <span class="text-gray-500 dark:text-slate-400">创建时间</span>
                  <span class="text-gray-600 dark:text-slate-300">{{ formatDate(table.created_at) }}</span>
                </div>

                <div v-if="table.description" class="text-sm text-gray-600 dark:text-slate-400 line-clamp-2">
                  {{ table.description }}
                </div>

                <div class="pt-3 border-t border-gray-200 dark:border-slate-700 flex items-center justify-between">
                  <el-button size="small" @click="handleView(table)" class="!bg-blue-50 dark:!bg-blue-500/10 !border-blue-200 dark:!border-blue-500/50 !text-blue-600 dark:!text-blue-400">
                    <el-icon class="mr-1"><View /></el-icon>
                    查看
                  </el-button>

                  <el-dropdown trigger="click" @command="(cmd: string) => handleAction(cmd, table)">
                    <el-button size="small" class="!bg-gray-100 dark:!bg-slate-700 hover:!bg-gray-200 dark:hover:!bg-slate-600 !border-gray-200 dark:!border-slate-600">
                      <el-icon><More /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="edit">
                          <el-icon><Edit /></el-icon>
                          编辑
                        </el-dropdown-item>
                        <el-dropdown-item command="chat">
                          <el-icon><ChatDotRound /></el-icon>
                          智能问答
                        </el-dropdown-item>
                        <el-dropdown-item command="delete" divided>
                          <el-icon class="text-red-500"><Delete /></el-icon>
                          <span class="text-red-500">删除</span>
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
            </el-card>
          </div>

          <el-empty v-if="filteredTables.length === 0" description="暂无数据表">
            <el-button type="primary" @click="createDialogVisible = true">
              <el-icon class="mr-1"><Plus /></el-icon>
              创建数据表
            </el-button>
          </el-empty>
      </div>

      <!-- 创建数据表对话框 -->
      <CreateDataTableDialog
        v-model="createDialogVisible"
        @refresh="loadDataTables"
      />

      <!-- 文件夹管理对话框 -->
      <FolderManager
        v-model="folderManagerVisible"
        @refresh="loadFolders"
      />

      <!-- 查看数据表对话框 -->
      <el-dialog
        v-model="viewDialogVisible"
        :title="currentTable?.display_name"
        width="90%"
        top="5vh"
      >
        <div v-if="currentTable">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="显示名称">{{ currentTable.display_name }}</el-descriptions-item>
            <el-descriptions-item label="物理表名">{{ currentTable.physical_table_name }}</el-descriptions-item>
            <el-descriptions-item label="建表方式">
              {{ currentTable.creation_method === 'excel_upload' ? 'Excel上传' : '数据源表' }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="currentTable.status === 'active' ? 'success' : 'info'">
                {{ currentTable.status === 'active' ? '活跃' : '归档' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="行数">{{ currentTable.row_count.toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="列数">{{ currentTable.column_count }}</el-descriptions-item>
            <el-descriptions-item label="创建时间" :span="2">{{ formatDate(currentTable.created_at) }}</el-descriptions-item>
            <el-descriptions-item v-if="currentTable.description" label="备注" :span="2">
              {{ currentTable.description }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="mt-6">
            <h3 class="text-lg font-bold mb-3">数据预览</h3>
            <el-table :data="previewData" border max-height="400" v-loading="loadingPreview">
              <el-table-column
                v-for="col in previewColumns"
                :key="col.field_name"
                :prop="col.field_name"
                :label="col.field_display_name"
                min-width="120"
              >
                <template #header>
                  <div>
                    <div>{{ col.field_display_name }}</div>
                    <div class="text-xs text-gray-400">{{ col.field_type }}</div>
                  </div>
                </template>
              </el-table-column>
            </el-table>
            <div class="mt-3 flex justify-end">
              <el-pagination
                v-model:current-page="previewPage"
                :page-size="20"
                :total="currentTable.row_count"
                layout="prev, pager, next"
                @current-change="loadPreviewData"
              />
            </div>
          </div>
        </div>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Folder,
  Search,
  View,
  Edit,
  Delete,
  More,
  ChatDotRound,
  Upload,
  Connection
} from '@element-plus/icons-vue'
import type { DataTable, Folder as FolderType, TableField } from '@/api/dataTable'
import { getDataTableList, deleteDataTable, getFolders, queryDataTable } from '@/api/dataTable'
import CreateDataTableDialog from './components/CreateDataTableDialog.vue'
import FolderManager from './components/FolderManager.vue'

const router = useRouter()
const dataTableList = ref<DataTable[]>([])
const folders = ref<FolderType[]>([])
const selectedFolderId = ref<number | null | undefined>(undefined)
const searchKeyword = ref('')
const createDialogVisible = ref(false)
const folderManagerVisible = ref(false)
const viewDialogVisible = ref(false)
const currentTable = ref<DataTable | null>(null)
const previewData = ref<any[]>([])
const previewColumns = ref<TableField[]>([])
const previewPage = ref(1)
const loadingPreview = ref(false)

const filteredTables = computed(() => {
  let list = dataTableList.value
  
  // 按搜索关键词过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    list = list.filter(t =>
      t.display_name.toLowerCase().includes(keyword) ||
      t.physical_table_name.toLowerCase().includes(keyword)
    )
  }
  
  return list
})

onMounted(() => {
  loadDataTables()
  loadFolders()
})

const loadDataTables = async () => {
  try {
    dataTableList.value = await getDataTableList(selectedFolderId.value)
  } catch (error: any) {
    ElMessage.error(error.message || '获取数据表列表失败')
  }
}

const loadFolders = async () => {
  try {
    folders.value = await getFolders()
  } catch (error: any) {
    console.error('Failed to load folders:', error)
  }
}

const handleSearch = () => {
  // 搜索在computed中实现
}

const handleView = async (table: DataTable) => {
  currentTable.value = table
  viewDialogVisible.value = true
  previewPage.value = 1
  await loadPreviewData()
}

const loadPreviewData = async () => {
  if (!currentTable.value) return
  
  loadingPreview.value = true
  try {
    const result = await queryDataTable(currentTable.value.id, previewPage.value, 20)
    previewData.value = result.data
    previewColumns.value = result.columns
  } catch (error: any) {
    ElMessage.error(error.message || '加载数据预览失败')
  } finally {
    loadingPreview.value = false
  }
}

const handleAction = async (command: string, table: DataTable) => {
  switch (command) {
    case 'edit':
      // TODO: 实现编辑功能
      ElMessage.info('编辑功能待实现')
      break
    case 'chat':
      router.push({
        name: 'chat',
        query: { data_table_id: table.id }
      })
      break
    case 'delete':
      await handleDelete(table)
      break
  }
}

const handleDelete = async (table: DataTable) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据表"${table.display_name}"吗？此操作将删除物理表，无法恢复！`,
      '警告',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )
    
    await deleteDataTable(table.id)
    ElMessage.success('数据表已删除')
    await loadDataTables()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const getMethodIcon = (method: string) => {
  return method === 'excel_upload' ? Upload : Connection
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
