<template>
  <el-dialog
    v-model="dialogVisible"
    title="已训练数据"
    width="80%"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="training-data-container">
      <!-- 数据统计和筛选 -->
      <div class="flex items-center justify-between mb-4">
        <el-alert
          type="info"
          :closable="false"
          class="flex-1 mr-4"
        >
          <template #title>
            <div class="flex items-center gap-2">
              <el-icon><InfoFilled /></el-icon>
              <span>数据集共包含 <strong>{{ total }}</strong> 条训练数据</span>
            </div>
          </template>
        </el-alert>

        <!-- 类型筛选 -->
        <div class="flex items-center gap-2">
          <span class="text-gray-500 dark:text-slate-400 text-sm">类型筛选：</span>
          <el-radio-group v-model="typeFilter" size="small" @change="handleFilterChange">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="ddl">
              <el-icon class="mr-1"><Grid /></el-icon>
              表结构
            </el-radio-button>
            <el-radio-button value="sql">
              <el-icon class="mr-1"><ChatLineSquare /></el-icon>
              QA对
            </el-radio-button>
            <el-radio-button value="documentation">
              <el-icon class="mr-1"><Document /></el-icon>
              文档
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 数据表格 -->
      <el-table
        v-loading="loading"
        :data="dataList"
        border
        stripe
        max-height="500"
        class="training-data-table"
      >
        <!-- 序号 -->
        <el-table-column
          type="index"
          label="#序号"
          width="80"
          align="center"
          :index="(index) => (currentPage - 1) * pageSize + index + 1"
        />

        <!-- 数据类型 -->
        <el-table-column
          prop="training_data_type"
          label="类型"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              :type="getTypeTag(row.training_data_type)"
              size="small"
            >
              {{ getTypeName(row.training_data_type) }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 问题/描述 -->
        <el-table-column
          label="问题/描述"
          min-width="250"
        >
          <template #default="{ row }">
            <span class="description-text">{{ formatDescription(row) }}</span>
          </template>
        </el-table-column>

        <!-- SQL/内容 -->
        <el-table-column
          label="SQL/内容"
          min-width="350"
        >
          <template #default="{ row }">
            <div class="sql-content">
              <code class="sql-text">{{ formatSqlPreview(row.sql) }}</code>
              <el-button
                v-if="row.sql && row.sql.length > 80"
                link
                type="primary"
                size="small"
                @click="handleViewDetail(row)"
              >
                查看完整内容
              </el-button>
            </div>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column
          label="操作"
          width="80"
          align="center"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click="handleCopySQL(row.sql)"
            >
              <el-icon><CopyDocument /></el-icon>
              复制
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="flex justify-center mt-4">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- SQL 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="详细内容"
      width="70%"
      append-to-body
    >
      <div class="detail-content">
        <div class="mb-4">
          <el-text class="font-bold">问题/描述：</el-text>
          <el-text>{{ currentItem?.question }}</el-text>
        </div>
        <div>
          <el-text class="font-bold mb-2 block">SQL/内容：</el-text>
          <el-input
            v-model="currentItem.sql"
            type="textarea"
            :rows="15"
            readonly
            class="sql-detail"
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleCopySQL(currentItem.sql)">
          <el-icon class="mr-1"><CopyDocument /></el-icon>
          复制SQL
        </el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, CopyDocument, Grid, ChatLineSquare, Document } from '@element-plus/icons-vue'
import { getTrainingData, type TrainingDataItem } from '@/api/dataset'

interface Props {
  modelValue: boolean
  datasetId: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const dialogVisible = ref(false)
const loading = ref(false)
const dataList = ref<TrainingDataItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// 类型筛选
const typeFilter = ref('all')

// 详情对话框
const detailDialogVisible = ref(false)
const currentItem = ref<TrainingDataItem>({
  id: '',
  question: '',
  sql: '',
  training_data_type: 'sql'
})

// 监听 props 变化
watch(() => props.modelValue, (val) => {
  dialogVisible.value = val
  if (val) {
    fetchData()
  }
})

watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
})

// 获取数据
const fetchData = async () => {
  if (!props.datasetId) return

  loading.value = true
  try {
    const res = await getTrainingData(props.datasetId, currentPage.value, pageSize.value, typeFilter.value)
    dataList.value = res.items
    total.value = res.total
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '获取训练数据失败')
  } finally {
    loading.value = false
  }
}

// 类型筛选变化
const handleFilterChange = () => {
  currentPage.value = 1
  fetchData()
}

// 分页处理
const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchData()
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchData()
}

// 获取类型标签
const getTypeTag = (type: string): 'primary' | 'warning' | 'info' => {
  switch (type) {
    case 'sql':
      return 'primary'
    case 'ddl':
      return 'warning'
    case 'documentation':
      return 'info'
    default:
      return 'info'
  }
}

// 获取类型名称
const getTypeName = (type: string) => {
  switch (type) {
    case 'sql':
      return 'QA对'
    case 'ddl':
      return '表结构'
    case 'documentation':
      return '文档'
    default:
      return type
  }
}

// 格式化问题/描述显示
const formatDescription = (row: TrainingDataItem) => {
  const type = row.training_data_type
  const question = row.question || ''
  const sql = row.sql || ''
  
  // 如果后端已经返回了清晰的 question，直接使用
  if (question && !question.startsWith('表结构:') && !question.startsWith('{')) {
    // 表结构类型：在表名后添加说明
    if (type === 'ddl') {
      return `${question} 表结构定义`
    }
    return question
  }
  
  // 后备逻辑：从 sql 中提取信息
  if (type === 'ddl') {
    const tableMatch = sql.match(/CREATE\s+TABLE\s+`?(\w+)`?/i)
    if (tableMatch) {
      return `${tableMatch[1]} 表结构定义`
    }
    return '表结构定义'
  }
  
  if (type === 'sql') {
    return question || '示例查询'
  }
  
  if (type === 'documentation') {
    if (question.length > 50) {
      return question.substring(0, 50) + '...'
    }
    return question || '业务文档'
  }
  
  return question || '-'
}

// 格式化 SQL 预览（简短显示）
const formatSqlPreview = (sql: string) => {
  if (!sql) return '-'
  
  // 如果是 JSON 字符串，尝试解析
  if (sql.startsWith('{')) {
    try {
      const parsed = JSON.parse(sql)
      sql = parsed.sql || sql
    } catch {
      // 解析失败，使用原始字符串
    }
  }
  
  // 移除多余空白，单行显示
  const cleaned = sql.replace(/\s+/g, ' ').trim()
  if (cleaned.length > 80) {
    return cleaned.substring(0, 80) + '...'
  }
  return cleaned
}

// 查看详情
const handleViewDetail = (row: TrainingDataItem) => {
  currentItem.value = row
  detailDialogVisible.value = true
}

// 复制 SQL
const handleCopySQL = async (sql: string) => {
  try {
    await navigator.clipboard.writeText(sql)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 关闭对话框
const handleClose = () => {
  dialogVisible.value = false
  dataList.value = []
  total.value = 0
  currentPage.value = 1
  typeFilter.value = 'all'
}
</script>

<style scoped>
.training-data-container {
  padding: 0;
}

.training-data-table {
  width: 100%;
}

.description-text {
  color: #333;
  font-size: 13px;
}

.dark .description-text {
  color: #e2e8f0;
}

.sql-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sql-text {
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
  color: #1e40af;
  background-color: #f1f5f9;
  padding: 6px 10px;
  border-radius: 4px;
  display: block;
  word-break: break-all;
}

.dark .sql-text {
  background-color: #1e293b;
  color: #93c5fd;
}

.detail-content {
  padding: 16px 0;
}

.sql-detail :deep(textarea) {
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}
</style>
