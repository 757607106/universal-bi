<template>
  <el-dialog
    v-model="visible"
    title="新建数据表"
    width="900px"
    :before-close="handleClose"
    :close-on-click-modal="false"
  >
    <el-steps :active="currentStep" align-center class="mb-6">
      <el-step title="选择数据来源" />
      <el-step title="基本信息配置" />
      <el-step title="字段配置" />
    </el-steps>

    <!-- 步骤1: 选择数据来源 -->
    <div v-if="currentStep === 0" class="step-content">
      <el-radio-group v-model="creationMethod" class="method-selection">
        <el-card
          shadow="hover"
          :class="['method-card', { active: creationMethod === 'excel_upload' }]"
          @click="creationMethod = 'excel_upload'"
        >
          <el-radio value="excel_upload" class="mb-2">
            <span class="text-lg font-bold">上传Excel/CSV</span>
          </el-radio>
          <p class="text-gray-500 dark:text-slate-400 text-sm">
            上传本地Excel或CSV文件，系统将自动解析数据并创建数据表
          </p>
          <div v-if="creationMethod === 'excel_upload'" class="mt-4">
            <el-upload
              ref="uploadRef"
              class="upload-demo"
              drag
              :auto-upload="false"
              :on-change="handleFileChange"
              :limit="1"
              accept=".xlsx,.xls,.csv"
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                拖拽文件到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持 .xlsx / .xls / .csv 格式，最大 20MB
                </div>
              </template>
            </el-upload>
            <div v-if="selectedFile" class="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded">
              <div class="flex items-center justify-between">
                <span>{{ selectedFile.name }}</span>
                <el-tag type="info" size="small">{{ formatFileSize(selectedFile.size) }}</el-tag>
              </div>
            </div>
          </div>
        </el-card>

        <el-card
          shadow="hover"
          :class="['method-card', { active: creationMethod === 'datasource_table' }]"
          @click="creationMethod = 'datasource_table'"
        >
          <el-radio value="datasource_table" class="mb-2">
            <span class="text-lg font-bold">从数据源选择</span>
          </el-radio>
          <p class="text-gray-500 dark:text-slate-400 text-sm">
            从已连接的数据源中选择现有表格作为数据表
          </p>
          <div v-if="creationMethod === 'datasource_table'" class="mt-4">
            <el-form-item label="选择数据源">
              <el-select
                v-model="formData.datasource_id"
                placeholder="请选择数据源"
                class="w-full"
                @change="handleDatasourceChange"
              >
                <el-option
                  v-for="ds in datasourceList"
                  :key="ds.id"
                  :label="ds.name"
                  :value="ds.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="选择数据表" v-if="formData.datasource_id">
              <el-select
                v-model="formData.source_table_name"
                placeholder="请选择数据表"
                class="w-full"
                :loading="loadingTables"
                @change="handleTableChange"
              >
                <el-option
                  v-for="table in tableList"
                  :key="table.name"
                  :label="table.name"
                  :value="table.name"
                />
              </el-select>
            </el-form-item>
          </div>
        </el-card>
      </el-radio-group>
    </div>

    <!-- 步骤2: 基本信息配置 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-form :model="formData" label-width="120px">
        <el-form-item label="显示名称" required>
          <el-input
            v-model="formData.display_name"
            placeholder="请输入数据表显示名称"
            maxlength="255"
          />
        </el-form-item>
        <el-form-item label="所属文件夹">
          <el-select
            v-model="formData.folder_id"
            placeholder="请选择文件夹（可选）"
            clearable
            class="w-full"
          >
            <el-option
              v-for="folder in folderList"
              :key="folder.id"
              :label="folder.name"
              :value="folder.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="表备注">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入表备注（选填）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>
    </div>

    <!-- 步骤3: 字段配置 -->
    <div v-if="currentStep === 2" class="step-content">
      <div class="mb-4 flex items-center justify-between">
        <el-checkbox v-model="allSelected" @change="handleSelectAll">全选</el-checkbox>
        <div class="text-sm text-gray-500">
          已选择 {{ selectedFieldsCount }} / {{ formData.fields.length }} 个字段
        </div>
      </div>
      <el-table :data="formData.fields" border max-height="200" class="w-full mb-4">
        <el-table-column type="selection" width="55" :reserve-selection="true">
          <template #default="scope">
            <el-checkbox v-model="scope.row.is_selected" />
          </template>
        </el-table-column>
        <el-table-column prop="field_name" label="字段值" width="150" />
        <el-table-column label="字段中文名" width="150">
          <template #default="scope">
            <el-input v-model="scope.row.field_display_name" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="字段类型" width="120">
          <template #default="scope">
            <el-select v-model="scope.row.field_type" size="small">
              <el-option label="字符" value="text" />
              <el-option label="数值" value="number" />
              <el-option label="时间" value="datetime" />
              <el-option label="地理" value="geo" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="空值展示" width="100">
          <template #default="scope">
            <el-input v-model="scope.row.null_display" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="150">
          <template #default="scope">
            <el-input v-model="scope.row.description" size="small" placeholder="字段备注" />
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 数据预览区域 -->
      <div v-if="formData.preview_data && formData.preview_data.length > 0" class="mt-4">
        <div class="text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">数据预览（前20行）</div>
        <el-table :data="formData.preview_data" border max-height="300" class="w-full" size="small">
          <el-table-column
            v-for="field in formData.fields.filter(f => f.is_selected)"
            :key="field.field_name"
            :prop="field.field_name"
            :label="field.field_display_name"
            min-width="120"
            show-overflow-tooltip
          />
        </el-table>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer flex justify-between">
        <el-button @click="handleClose">取消</el-button>
        <div>
          <el-button v-if="currentStep > 0" @click="currentStep--">上一步</el-button>
          <el-button v-if="currentStep < 2" type="primary" @click="handleNext">
            下一步
          </el-button>
          <el-button
            v-if="currentStep === 2"
            type="primary"
            :loading="submitting"
            @click="handleSubmit"
          >
            确认创建
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import type { Folder, TableField } from '@/api/dataTable'
import { previewExcel, getFolders, createDataTableFromExcel, createDataTableFromDatasource } from '@/api/dataTable'
import { getDataSourceList, getTables } from '@/api/datasource'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'refresh'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const currentStep = ref(0)
const creationMethod = ref<'excel_upload' | 'datasource_table'>('excel_upload')
const selectedFile = ref<File | null>(null)
const datasourceList = ref<any[]>([])
const tableList = ref<any[]>([])
const folderList = ref<Folder[]>([])
const loadingTables = ref(false)
const submitting = ref(false)
const allSelected = ref(true)

const formData = ref({
  display_name: '',
  datasource_id: undefined as number | undefined,
  folder_id: undefined as number | undefined,
  description: '',
  source_table_name: '',
  fields: [] as TableField[],
  preview_data: [] as Record<string, any>[]  // 添加预览数据
})

const selectedFieldsCount = computed(() => {
  return formData.value.fields.filter(f => f.is_selected).length
})

watch(visible, async (val) => {
  if (val) {
    await loadInitialData()
  } else {
    resetForm()
  }
})

const loadInitialData = async () => {
  try {
    const [folders, datasources] = await Promise.all([
      getFolders(),
      getDataSourceList()
    ])
    folderList.value = folders
    datasourceList.value = datasources
  } catch (error) {
    console.error('Failed to load initial data:', error)
  }
}

const handleFileChange = async (uploadFile: UploadFile) => {
  if (uploadFile.raw) {
    selectedFile.value = uploadFile.raw
    
    // 自动预览
    try {
      const preview = await previewExcel(uploadFile.raw)
      formData.value.display_name = preview.filename.replace(/\.(xlsx?|csv)$/i, '')
      formData.value.fields = preview.fields.map((field, index) => ({
        field_name: field.field_name,
        field_display_name: field.field_display_name,
        field_type: field.field_type as any,
        date_format: field.field_type === 'datetime' ? 'YYYY-MM-DD' : undefined,
        null_display: '—',
        description: '',
        is_selected: true,
        sort_order: index
      }))
      // 保存预览数据
      formData.value.preview_data = preview.preview_data || []
      
      ElMessage.success('文件解析成功')
    } catch (error: any) {
      ElMessage.error(error.message || '文件解析失败')
      selectedFile.value = null
    }
  }
}

const handleDatasourceChange = async () => {
  formData.value.source_table_name = ''
  tableList.value = []
  
  if (formData.value.datasource_id) {
    loadingTables.value = true
    try {
      const tables = await getTables(formData.value.datasource_id)
      tableList.value = tables
    } catch (error: any) {
      ElMessage.error(error.message || '获取数据表列表失败')
    } finally {
      loadingTables.value = false
    }
  }
}

const handleTableChange = async () => {
  // 获取表结构并设置字段配置
  const table = tableList.value.find(t => t.name === formData.value.source_table_name)
  if (table && table.columns) {
    formData.value.fields = table.columns.map((col: any, index: number) => ({
      field_name: col.name,
      field_display_name: col.name,
      field_type: inferFieldType(col.type),
      date_format: undefined,
      null_display: '—',
      description: '',
      is_selected: true,
      sort_order: index
    }))
    if (!formData.value.display_name) {
      formData.value.display_name = formData.value.source_table_name
    }
  }
}

const inferFieldType = (sqlType: string): 'text' | 'number' | 'datetime' | 'geo' => {
  const typeStr = sqlType.toLowerCase()
  if (typeStr.includes('int') || typeStr.includes('float') || typeStr.includes('double') || typeStr.includes('decimal')) {
    return 'number'
  }
  if (typeStr.includes('date') || typeStr.includes('time')) {
    return 'datetime'
  }
  return 'text'
}

const handleSelectAll = () => {
  formData.value.fields.forEach(field => {
    field.is_selected = allSelected.value
  })
}

const handleNext = () => {
  if (currentStep.value === 0) {
    if (creationMethod.value === 'excel_upload' && !selectedFile.value) {
      ElMessage.warning('请先上传文件')
      return
    }
    if (creationMethod.value === 'datasource_table' && !formData.value.source_table_name) {
      ElMessage.warning('请选择数据源和数据表')
      return
    }
    if (formData.value.fields.length === 0) {
      ElMessage.warning('未能获取字段信息')
      return
    }
  }
  
  if (currentStep.value === 1) {
    if (!formData.value.display_name.trim()) {
      ElMessage.warning('请输入显示名称')
      return
    }
  }
  
  currentStep.value++
}

const handleSubmit = async () => {
  if (selectedFieldsCount.value === 0) {
    ElMessage.warning('请至少选择一个字段')
    return
  }
  
  submitting.value = true
  try {
    if (creationMethod.value === 'excel_upload' && selectedFile.value) {
      // Excel上传时，datasource_id可选，后端会自动创建上传数据源
      await createDataTableFromExcel(
        formData.value.display_name,
        formData.value.datasource_id || 0,  // 传0表示使用默认上传数据源
        selectedFile.value,
        formData.value.fields.filter(f => f.is_selected),
        formData.value.folder_id,
        formData.value.description
      )
    } else if (creationMethod.value === 'datasource_table') {
      if (!formData.value.datasource_id) {
        ElMessage.error('请选择数据源')
        return
      }
      await createDataTableFromDatasource(
        formData.value.display_name,
        formData.value.datasource_id,
        formData.value.source_table_name,
        formData.value.fields.filter(f => f.is_selected),
        formData.value.folder_id,
        formData.value.description
      )
    }
    
    ElMessage.success('数据表创建成功')
    emit('refresh')
    handleClose()
  } catch (error: any) {
    ElMessage.error(error.message || '创建数据表失败')
  } finally {
    submitting.value = false
  }
}

const handleClose = () => {
  visible.value = false
}

const resetForm = () => {
  currentStep.value = 0
  creationMethod.value = 'excel_upload'
  selectedFile.value = null
  formData.value = {
    display_name: '',
    datasource_id: undefined,
    folder_id: undefined,
    description: '',
    source_table_name: '',
    fields: [],
    preview_data: []
  }
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.step-content {
  min-height: 400px;
  max-height: 600px;
  overflow-y: auto;
}

.method-selection {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  width: 100%;
}

.method-card {
  cursor: pointer;
  transition: all 0.3s;
  padding: 1rem;
}

.method-card.active {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-8);
}

.method-card:hover {
  border-color: var(--el-color-primary);
}

:deep(.el-upload-dragger) {
  padding: 20px;
}
</style>
