<template>
  <el-drawer
    v-model="visible"
    title="数据预览"
    size="80%"
    :with-header="true"
    :before-close="handleClose"
    class="data-preview-drawer"
  >
    <div class="flex h-full gap-4">
      <!-- 连接错误提示 -->
      <div v-if="connectionError" class="w-full flex items-center justify-center">
        <div class="text-center max-w-md">
          <el-icon class="text-6xl text-orange-500 mb-4"><WarningFilled /></el-icon>
          <h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">连接失败</h3>
          <p class="text-gray-600 dark:text-gray-400 mb-6">{{ connectionError }}</p>
          <el-button type="primary" @click="handleReconnect">
            <el-icon class="mr-1"><Refresh /></el-icon>
            重新连接
          </el-button>
        </div>
      </div>

      <!-- 正常内容 -->
      <template v-else>
        <!-- 左侧表名列表 -->
        <div class="w-64 flex flex-col border-r border-gray-200 dark:border-gray-800 pr-4">
          <el-input
            v-model="searchTable"
            placeholder="搜索表名..."
            class="mb-4"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <div v-loading="loadingTables" class="flex-1 overflow-y-auto">
            <ul class="space-y-1">
              <li
                v-for="table in filteredTables"
                :key="table"
                @click="handleTableClick(table)"
                :class="[
                  'px-3 py-2 rounded-md cursor-pointer text-sm transition-colors',
                  currentTable === table
                    ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 font-medium'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                ]"
              >
                <div class="flex items-center">
                  <el-icon class="mr-2"><List /></el-icon>
                  <span class="truncate" :title="table">{{ table }}</span>
                </div>
              </li>
            </ul>
            <div v-if="filteredTables.length === 0 && !loadingTables" class="text-center text-gray-400 text-sm py-4">
              无匹配表名
            </div>
          </div>
        </div>

        <!-- 右侧数据预览 -->
        <div class="flex-1 flex flex-col overflow-hidden">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">
              {{ currentTable ? `当前预览: ${currentTable}` : '请选择左侧表名进行预览' }}
            </h3>
            <el-tag v-if="currentTable" size="small" type="info">只显示前 100 行</el-tag>
          </div>

          <div class="flex-1 overflow-hidden relative border border-gray-200 dark:border-gray-800 rounded-lg">
            <el-table
              v-if="currentTable"
              v-loading="loadingData"
              :data="tableData"
              height="100%"
              style="width: 100%"
              border
              stripe
            >
              <el-table-column
                v-for="col in tableColumns"
                :key="col.prop"
                :prop="col.prop"
                :label="col.label"
                min-width="120"
                show-overflow-tooltip
              />
            </el-table>
            <div v-else class="h-full flex items-center justify-center text-gray-400">
              <el-empty description="暂无数据预览" />
            </div>
          </div>
        </div>
      </template>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Search, List, WarningFilled, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getTables, previewTable, type TableInfo } from '../api/datasource'

const props = defineProps<{
  modelValue: boolean
  datasourceId: number | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'reconnect', datasourceId: number): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loadingTables = ref(false)
const loadingData = ref(false)
const tablesInfo = ref<TableInfo[]>([])
const searchTable = ref('')
const currentTable = ref('')
const tableColumns = ref<{ prop: string, label: string }[]>([])
const tableData = ref<any[]>([])
const connectionError = ref('')

// 计算属性：从 TableInfo 中提取表名列表
const tables = computed(() => tablesInfo.value.map(t => t.name))

const filteredTables = computed(() => {
  if (!searchTable.value) return tables.value
  return tables.value.filter(t => t.toLowerCase().includes(searchTable.value.toLowerCase()))
})

// 监听弹窗打开，加载表列表
watch(() => props.modelValue, async (val) => {
  if (val && props.datasourceId) {
    connectionError.value = ''
    await fetchTables()
    // 重置状态
    currentTable.value = ''
    tableData.value = []
    tableColumns.value = []
    searchTable.value = ''
  }
})

const fetchTables = async () => {
  if (!props.datasourceId) return

  loadingTables.value = true
  connectionError.value = ''
  try {
    tablesInfo.value = await getTables(props.datasourceId)
    console.log('Loaded tables info:', tablesInfo.value)
    // 如果有表，默认选中第一个
    if (tablesInfo.value.length > 0) {
      handleTableClick(tablesInfo.value[0].name)
    }
  } catch (error: any) {
    console.error('Error getting tables:', error)
    // 显示后端返回的详细错误信息
    const errorMessage = error.response?.data?.detail || error.message || '获取表列表失败'
    connectionError.value = errorMessage
  } finally {
    loadingTables.value = false
  }
}

const handleTableClick = async (tableName: string) => {
  if (currentTable.value === tableName) return
  if (!props.datasourceId) return

  currentTable.value = tableName
  loadingData.value = true

  try {
    console.log('Fetching data for table:', tableName)
    const data = await previewTable(props.datasourceId, tableName)
    tableColumns.value = data.columns
    tableData.value = data.rows
  } catch (error: any) {
    console.error(`Error getting data for ${tableName}:`, error)
    ElMessage.error(`获取表 ${tableName} 数据失败`)
    tableColumns.value = []
    tableData.value = []
  } finally {
    loadingData.value = false
  }
}

const handleReconnect = () => {
  if (props.datasourceId) {
    visible.value = false
    emit('reconnect', props.datasourceId)
  }
}

const handleClose = () => {
  visible.value = false
}
</script>

<style scoped>
/* 可以在这里添加一些特定的样式调整 */
:deep(.el-drawer__body) {
  padding: 20px;
  overflow: hidden; /* 防止双重滚动条 */
}
</style>