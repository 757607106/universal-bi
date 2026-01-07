<template>
  <el-dialog
    v-model="dialogVisible"
    title="已训练数据"
    width="80%"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="training-data-container">
      <!-- 数据统计 -->
      <el-alert
        type="info"
        :closable="false"
        class="mb-4"
      >
        <template #title>
          <div class="flex items-center gap-2">
            <el-icon><InfoFilled /></el-icon>
            <span>数据集共包含 <strong>{{ total }}</strong> 条训练数据</span>
          </div>
        </template>
      </el-alert>

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
          label="#"
          width="60"
          :index="(index) => (currentPage - 1) * pageSize + index + 1"
        />

        <!-- 数据类型 -->
        <el-table-column
          prop="training_data_type"
          label="类型"
          width="120"
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
          prop="question"
          label="问题/描述"
          min-width="200"
          show-overflow-tooltip
        />

        <!-- SQL/内容 -->
        <el-table-column
          prop="sql"
          label="SQL/内容"
          min-width="300"
        >
          <template #default="{ row }">
            <div class="sql-content">
              <el-text
                line-clamp="3"
                class="sql-text"
              >
                {{ row.sql }}
              </el-text>
              <el-button
                link
                type="primary"
                size="small"
                @click="handleViewDetail(row)"
                class="mt-1"
              >
                查看详情
              </el-button>
            </div>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column
          label="操作"
          width="100"
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
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, CopyDocument } from '@element-plus/icons-vue'
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
    const res = await getTrainingData(props.datasetId, currentPage.value, pageSize.value)
    dataList.value = res.items
    total.value = res.total
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '获取训练数据失败')
  } finally {
    loading.value = false
  }
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
}
</script>

<style scoped>
.training-data-container {
  padding: 0;
}

.training-data-table {
  width: 100%;
}

.sql-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sql-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #666;
  background-color: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}

.dark .sql-text {
  background-color: #1e293b;
  color: #cbd5e1;
}

.detail-content {
  padding: 16px 0;
}

.sql-detail :deep(textarea) {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}
</style>
