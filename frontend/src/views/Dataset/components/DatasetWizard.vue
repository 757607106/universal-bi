<template>
  <el-dialog
    v-model="dialogVisible"
    title="新建数据集"
    width="800px"
    :before-close="handleClose"
    :close-on-click-modal="false"
  >
    <el-steps :active="activeStep" finish-status="success" simple class="mb-6">
      <el-step title="基本信息" />
      <el-step title="选择数据表" />
    </el-steps>

    <!-- Step 1: 基本信息 -->
    <div v-show="activeStep === 0" class="py-4 px-8">
      <el-form :model="form" label-width="100px">
        <el-form-item label="数据集名称" required>
          <el-input v-model="form.name" placeholder="请输入数据集名称（如：销售数据分析）" />
        </el-form-item>
        <el-form-item label="数据源" required>
          <el-select v-model="form.datasource_id" placeholder="请选择数据源" class="w-full">
            <el-option
              v-for="item in dataSources"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <!-- Step 2: 选择数据表 -->
    <div v-show="activeStep === 1" class="py-4">
      <div v-if="loadingTables" class="flex justify-center py-8">
        <el-icon class="is-loading text-3xl text-gray-400 dark:text-slate-400"><Loading /></el-icon>
      </div>
      <el-transfer
        v-else
        v-model="selectedTables"
        :data="tableList"
        :titles="['可用表', '已选表']"
        filterable
        filter-placeholder="搜索表名"
        class="flex justify-center"
      >
        <template #default="{ option }">
          <span>{{ option.label }}</span>
        </template>
      </el-transfer>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button v-if="activeStep === 0" type="primary" @click="nextStep" :disabled="!form.name || !form.datasource_id">
          下一步
        </el-button>
        <el-button v-if="activeStep === 1" @click="prevStep">上一步</el-button>
        <el-button
          v-if="activeStep === 1"
          type="primary"
          @click="handleSaveAndModeling"
          :loading="saving"
          :disabled="selectedTables.length === 0"
        >
          保存并建模
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { getDataSourceList, type DataSource } from '@/api/datasource'
import { createDataset, updateDatasetTables, trainDataset, getDbTables } from '@/api/dataset'

interface Props {
  modelValue: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'refresh'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
const router = useRouter()

const dialogVisible = ref(false)
const activeStep = ref(0)
const saving = ref(false)
const loadingTables = ref(false)

const form = ref({
  name: '',
  datasource_id: undefined as number | undefined,
})
const createdDatasetId = ref<number | null>(null)

const dataSources = ref<DataSource[]>([])
const tableList = ref<{ key: string; label: string }[]>([])
const selectedTables = ref<string[]>([])

// 同步 v-model
watch(() => props.modelValue, (newVal) => {
  dialogVisible.value = newVal
  if (newVal) {
    resetForm()
    fetchDataSources()
  }
})

watch(dialogVisible, (newVal) => {
  emit('update:modelValue', newVal)
})

const fetchDataSources = async () => {
  try {
    dataSources.value = await getDataSourceList()
  } catch (error) {
    ElMessage.error('获取数据源列表失败')
  }
}

const fetchTables = async (datasourceId: number) => {
  loadingTables.value = true
  try {
    const tables = await getDbTables(datasourceId)
    // 后端返回的是 TableInfo[] 包含 name 和 columns
    tableList.value = tables.map((t) => ({ key: t.name, label: t.name }))
  } catch (error) {
    ElMessage.error('获取数据表失败')
  } finally {
    loadingTables.value = false
  }
}

const resetForm = () => {
  activeStep.value = 0
  form.value = { name: '', datasource_id: undefined }
  createdDatasetId.value = null
  selectedTables.value = []
  tableList.value = []
}

const handleClose = () => {
  dialogVisible.value = false
}

const nextStep = async () => {
  if (activeStep.value === 0) {
    if (!form.value.name || !form.value.datasource_id) return
    
    // 如果尚未创建数据集，则先创建
    if (!createdDatasetId.value) {
      saving.value = true
      try {
        const dataset = await createDataset({
          name: form.value.name,
          datasource_id: form.value.datasource_id
        })
        createdDatasetId.value = dataset.id
        // 加载表
        await fetchTables(form.value.datasource_id)
        activeStep.value = 1
      } catch (error) {
        ElMessage.error('创建数据集失败')
      } finally {
        saving.value = false
      }
    } else {
      // 已经创建过，直接下一步（可能是回退后再点下一步）
      // 检查数据源是否变更，如果变更需要重新获取表（暂不支持修改数据源，简化逻辑）
      activeStep.value = 1
    }
  }
}

const prevStep = () => {
  if (activeStep.value > 0) {
    activeStep.value--
  }
}

const handleSaveAndModeling = async () => {
  if (!createdDatasetId.value) return
  
  saving.value = true
  try {
    // 1. 更新表配置
    await updateDatasetTables(createdDatasetId.value, selectedTables.value)
    
    ElMessage.success('数据集创建成功，即将进入可视化建模')
    emit('refresh')
    handleClose()
    
    // 2. 跳转到可视化建模页面
    router.push(`/datasets/modeling/${createdDatasetId.value}`)
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
:deep(.el-transfer-panel) {
  width: 300px;
}
</style>
