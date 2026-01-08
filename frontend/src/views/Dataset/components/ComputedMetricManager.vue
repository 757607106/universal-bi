<template>
  <el-dialog
    v-model="visible"
    title="计算指标管理"
    width="900px"
    :before-close="handleClose"
  >
    <div class="metric-manager">
      <!-- 添加新指标表单 -->
      <el-card class="mb-4">
        <template #header>
          <div class="flex items-center justify-between">
            <span class="font-bold">添加新指标</span>
            <el-button 
              v-if="!showAddForm" 
              type="primary" 
              size="small" 
              @click="showAddForm = true"
            >
              <el-icon class="mr-1"><Plus /></el-icon>
              新建指标
            </el-button>
          </div>
        </template>

        <el-form 
          v-if="showAddForm" 
          :model="newMetric" 
          label-width="100px"
          @submit.prevent="handleAdd"
        >
          <el-form-item label="指标名称" required>
            <el-input 
              v-model="newMetric.name" 
              placeholder="例如：客单价、毛利率"
              clearable
            />
          </el-form-item>

          <el-form-item label="计算公式" required>
            <el-input
              v-model="newMetric.formula"
              type="textarea"
              :rows="3"
              placeholder="SQL 表达式，例如：SUM(gmv) / COUNT(DISTINCT user_id)"
            />
            <div class="text-xs text-gray-500 mt-1">
              提示：使用标准 SQL 表达式，可以包含聚合函数、字段引用等
            </div>
          </el-form-item>

          <el-form-item label="业务口径">
            <el-input
              v-model="newMetric.description"
              type="textarea"
              :rows="3"
              placeholder="描述该指标的业务含义和使用场景，例如：统计周期内，平均每个付费用户的消费金额"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="handleAdd" :loading="adding">
              保存
            </el-button>
            <el-button @click="cancelAdd">取消</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 已有指标列表 -->
      <el-card>
        <template #header>
          <div class="flex items-center justify-between">
            <span class="font-bold">已有指标（{{ metrics.length }}）</span>
            <el-button 
              type="info" 
              size="small" 
              plain
              @click="fetchMetrics"
              :loading="loading"
            >
              <el-icon class="mr-1"><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>

        <div v-if="loading && metrics.length === 0" class="text-center py-8 text-gray-500">
          <el-icon class="is-loading text-2xl"><Loading /></el-icon>
          <div class="mt-2">加载中...</div>
        </div>

        <el-empty v-else-if="metrics.length === 0" description="暂无计算指标" />

        <div v-else class="space-y-3">
          <el-card
            v-for="metric in metrics"
            :key="metric.id"
            shadow="hover"
            class="metric-item"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-2">
                  <el-tag type="success" effect="dark" size="small">
                    <el-icon class="mr-1"><TrendCharts /></el-icon>
                    指标
                  </el-tag>
                  <span class="font-bold text-lg">{{ metric.name }}</span>
                </div>

                <div class="mb-2">
                  <div class="text-sm text-gray-500 mb-1">计算公式：</div>
                  <el-input
                    :model-value="metric.formula"
                    type="textarea"
                    :rows="2"
                    readonly
                    class="font-mono text-sm"
                  />
                </div>

                <div v-if="metric.description" class="mb-2">
                  <div class="text-sm text-gray-500 mb-1">业务口径：</div>
                  <div class="text-sm text-gray-700 bg-gray-50 p-2 rounded">
                    {{ metric.description }}
                  </div>
                </div>

                <div class="text-xs text-gray-400">
                  创建时间：{{ formatDate(metric.created_at) }}
                </div>
              </div>

              <div class="ml-4 flex flex-col gap-2">
                <el-button 
                  type="primary" 
                  size="small" 
                  plain
                  @click="handleEdit(metric)"
                >
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button 
                  type="danger" 
                  size="small" 
                  plain
                  @click="handleDelete(metric)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </el-card>
        </div>
      </el-card>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑指标"
      width="600px"
      append-to-body
    >
      <el-form :model="editingMetric" label-width="100px">
        <el-form-item label="指标名称" required>
          <el-input v-model="editingMetric.name" />
        </el-form-item>

        <el-form-item label="计算公式" required>
          <el-input
            v-model="editingMetric.formula"
            type="textarea"
            :rows="3"
          />
        </el-form-item>

        <el-form-item label="业务口径">
          <el-input
            v-model="editingMetric.description"
            type="textarea"
            :rows="3"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdate" :loading="updating">
          保存
        </el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Loading, Edit, Delete, TrendCharts } from '@element-plus/icons-vue'
import {
  getComputedMetrics,
  createComputedMetric,
  updateComputedMetric,
  deleteComputedMetric,
  type ComputedMetric,
  type ComputedMetricCreate
} from '@/api/dataset'

const props = defineProps<{
  modelValue: boolean
  datasetId: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'refresh'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const metrics = ref<ComputedMetric[]>([])
const loading = ref(false)
const showAddForm = ref(false)
const adding = ref(false)
const updating = ref(false)
const editDialogVisible = ref(false)

const newMetric = ref<ComputedMetricCreate>({
  name: '',
  formula: '',
  description: ''
})

const editingMetric = ref<Partial<ComputedMetric>>({
  id: 0,
  name: '',
  formula: '',
  description: ''
})

// 获取指标列表
const fetchMetrics = async () => {
  if (!props.datasetId) return

  loading.value = true
  try {
    metrics.value = await getComputedMetrics(props.datasetId)
  } catch (error: any) {
    ElMessage.error(error.message || '获取指标列表失败')
  } finally {
    loading.value = false
  }
}

// 添加指标
const handleAdd = async () => {
  if (!newMetric.value.name || !newMetric.value.formula) {
    ElMessage.warning('请填写指标名称和计算公式')
    return
  }

  adding.value = true
  try {
    await createComputedMetric(props.datasetId, newMetric.value)
    ElMessage.success('指标已添加并训练到 AI')
    
    // 重置表单
    newMetric.value = {
      name: '',
      formula: '',
      description: ''
    }
    showAddForm.value = false
    
    // 刷新列表
    fetchMetrics()
  } catch (error: any) {
    ElMessage.error(error.message || '添加指标失败')
  } finally {
    adding.value = false
  }
}

// 取消添加
const cancelAdd = () => {
  newMetric.value = {
    name: '',
    formula: '',
    description: ''
  }
  showAddForm.value = false
}

// 编辑指标
const handleEdit = (metric: ComputedMetric) => {
  editingMetric.value = { ...metric }
  editDialogVisible.value = true
}

// 更新指标
const handleUpdate = async () => {
  if (!editingMetric.value.name || !editingMetric.value.formula) {
    ElMessage.warning('请填写指标名称和计算公式')
    return
  }

  updating.value = true
  try {
    await updateComputedMetric(
      props.datasetId,
      editingMetric.value.id!,
      {
        name: editingMetric.value.name,
        formula: editingMetric.value.formula,
        description: editingMetric.value.description
      }
    )
    ElMessage.success('指标已更新')
    editDialogVisible.value = false
    fetchMetrics()
  } catch (error: any) {
    ElMessage.error(error.message || '更新指标失败')
  } finally {
    updating.value = false
  }
}

// 删除指标
const handleDelete = async (metric: ComputedMetric) => {
  try {
    await ElMessageBox.confirm(
      `确认删除指标 "${metric.name}" 吗？删除后将无法恢复。`,
      '删除确认',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteComputedMetric(props.datasetId, metric.id)
    ElMessage.success('指标已删除')
    fetchMetrics()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除指标失败')
    }
  }
}

// 格式化日期
const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 关闭对话框
const handleClose = () => {
  showAddForm.value = false
  editDialogVisible.value = false
  visible.value = false
}

// 监听datasetId变化
watch(() => props.datasetId, (newId) => {
  if (newId && visible.value) {
    fetchMetrics()
  }
})

// 监听对话框打开
watch(visible, (newVal) => {
  if (newVal && props.datasetId) {
    fetchMetrics()
  }
})
</script>

<style scoped>
.metric-manager {
  max-height: 70vh;
  overflow-y: auto;
}

.metric-item {
  transition: all 0.3s ease;
}

.metric-item:hover {
  transform: translateY(-2px);
}
</style>

