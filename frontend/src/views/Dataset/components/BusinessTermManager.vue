<template>
  <el-dialog
    v-model="dialogVisible"
    title="业务术语管理"
    width="80%"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-tabs v-model="activeTab" class="term-tabs">
      <!-- 业务术语 Tab -->
      <el-tab-pane label="业务术语" name="terms">
        <div class="tab-content">
          <el-alert
            type="info"
            :closable="false"
            class="mb-4"
          >
            <template #title>
              <span>业务术语可以帮助 AI 理解您的业务概念，例如 "高净值客户" = "年消费额 > 100万的客户"</span>
            </template>
          </el-alert>

          <!-- 添加术语表单 -->
          <el-form :model="termForm" :rules="termRules" ref="termFormRef" label-width="80px" class="mb-4">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="术语" prop="term">
                  <el-input v-model="termForm.term" placeholder="例如：高净值客户" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="定义" prop="definition">
                  <el-input v-model="termForm.definition" placeholder="例如：年消费额 > 100万的客户" />
                </el-form-item>
              </el-col>
              <el-col :span="4">
                <el-button type="primary" @click="handleAddTerm" :loading="termLoading">
                  <el-icon class="mr-1"><Plus /></el-icon>
                  添加
                </el-button>
              </el-col>
            </el-row>
          </el-form>

          <!-- 术语列表 -->
          <el-table :data="termList" border stripe v-loading="termListLoading" max-height="300">
            <el-table-column prop="term" label="术语" width="200" />
            <el-table-column prop="definition" label="定义" />
            <el-table-column prop="created_at" label="添加时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="danger" @click="handleDeleteTerm(row)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- QA 对 Tab -->
      <el-tab-pane label="QA 对" name="qa">
        <div class="tab-content">
          <el-alert
            type="info"
            :closable="false"
            class="mb-4"
          >
            <template #title>
              <span>QA 对用于教会 AI 如何将特定问题转化为 SQL 查询，提高查询准确性</span>
            </template>
          </el-alert>

          <!-- 添加 QA 对表单 -->
          <el-form :model="qaForm" :rules="qaRules" ref="qaFormRef" label-width="80px" class="mb-4">
            <el-form-item label="问题" prop="question">
              <el-input v-model="qaForm.question" placeholder="例如：查询上个月的销售额" />
            </el-form-item>
            <el-form-item label="SQL" prop="sql">
              <el-input
                v-model="qaForm.sql"
                type="textarea"
                :rows="4"
                placeholder="例如：SELECT SUM(amount) FROM orders WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleAddQA" :loading="qaLoading">
                <el-icon class="mr-1"><Plus /></el-icon>
                添加 QA 对
              </el-button>
            </el-form-item>
          </el-form>

          <el-divider />

          <!-- 快速添加示例 -->
          <h4 class="text-gray-600 dark:text-slate-400 mb-2">快速添加示例</h4>
          <div class="flex flex-wrap gap-2">
            <el-button 
              v-for="example in qaExamples" 
              :key="example.question"
              size="small"
              @click="fillQAExample(example)"
            >
              {{ example.question }}
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- 文档 Tab -->
      <el-tab-pane label="文档" name="doc">
        <div class="tab-content">
          <el-alert
            type="info"
            :closable="false"
            class="mb-4"
          >
            <template #title>
              <span>文档用于向 AI 提供业务背景、规则说明等上下文信息</span>
            </template>
          </el-alert>

          <!-- 添加文档表单 -->
          <el-form :model="docForm" :rules="docRules" ref="docFormRef" label-width="80px" class="mb-4">
            <el-form-item label="文档内容" prop="content">
              <el-input
                v-model="docForm.content"
                type="textarea"
                :rows="6"
                placeholder="输入业务规则、说明文档等，例如：&#10;公司有三个销售区域：华东、华北、华南&#10;每个区域有独立的销售团队&#10;销售额统计不包含退货订单"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleAddDoc" :loading="docLoading">
                <el-icon class="mr-1"><Plus /></el-icon>
                添加文档
              </el-button>
            </el-form-item>
          </el-form>

          <el-divider />

          <!-- 文档模板 -->
          <h4 class="text-gray-600 dark:text-slate-400 mb-2">文档模板</h4>
          <div class="flex flex-wrap gap-2">
            <el-button 
              v-for="template in docTemplates" 
              :key="template.name"
              size="small"
              @click="fillDocTemplate(template)"
            >
              {{ template.name }}
            </el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import {
  getBusinessTerms,
  addBusinessTerm,
  deleteBusinessTerm,
  trainQAPair,
  trainDocumentation,
  type BusinessTerm
} from '@/api/dataset'

interface Props {
  modelValue: boolean
  datasetId: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'refresh': []
}>()

const dialogVisible = ref(false)
const activeTab = ref('terms')

// === 业务术语相关 ===
const termFormRef = ref<FormInstance>()
const termForm = reactive({
  term: '',
  definition: ''
})
const termRules: FormRules = {
  term: [{ required: true, message: '请输入术语名称', trigger: 'blur' }],
  definition: [{ required: true, message: '请输入术语定义', trigger: 'blur' }]
}
const termList = ref<BusinessTerm[]>([])
const termLoading = ref(false)
const termListLoading = ref(false)

// === QA 对相关 ===
const qaFormRef = ref<FormInstance>()
const qaForm = reactive({
  question: '',
  sql: ''
})
const qaRules: FormRules = {
  question: [{ required: true, message: '请输入问题', trigger: 'blur' }],
  sql: [{ required: true, message: '请输入对应的 SQL', trigger: 'blur' }]
}
const qaLoading = ref(false)

const qaExamples = [
  { question: '查询总销售额', sql: 'SELECT SUM(amount) as total_sales FROM orders' },
  { question: '统计用户数量', sql: 'SELECT COUNT(*) as user_count FROM users' },
  { question: '查询本月订单', sql: 'SELECT * FROM orders WHERE MONTH(order_date) = MONTH(CURDATE())' }
]

// === 文档相关 ===
const docFormRef = ref<FormInstance>()
const docForm = reactive({
  content: ''
})
const docRules: FormRules = {
  content: [{ required: true, message: '请输入文档内容', trigger: 'blur' }]
}
const docLoading = ref(false)

const docTemplates = [
  { name: '业务规则', content: '业务规则说明：\n1. \n2. \n3. ' },
  { name: '数据字典', content: '数据字典说明：\n字段名：\n含义：\n取值范围：' },
  { name: '计算公式', content: '计算公式说明：\n指标名称：\n计算公式：\n说明：' }
]

// === 监听 ===
watch(() => props.modelValue, (val) => {
  dialogVisible.value = val
  if (val) {
    fetchTermList()
  }
})

watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
})

// === 方法 ===
const fetchTermList = async () => {
  if (!props.datasetId) return
  
  termListLoading.value = true
  try {
    termList.value = await getBusinessTerms(props.datasetId)
  } catch (error) {
    ElMessage.error('获取术语列表失败')
  } finally {
    termListLoading.value = false
  }
}

const handleAddTerm = async () => {
  if (!termFormRef.value) return
  
  await termFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    termLoading.value = true
    try {
      await addBusinessTerm(props.datasetId, {
        term: termForm.term,
        definition: termForm.definition
      })
      ElMessage.success('术语添加成功')
      termForm.term = ''
      termForm.definition = ''
      fetchTermList()
      emit('refresh')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || '添加术语失败')
    } finally {
      termLoading.value = false
    }
  })
}

const handleDeleteTerm = async (row: BusinessTerm) => {
  try {
    await ElMessageBox.confirm(`确定要删除术语 "${row.term}" 吗？`, '确认删除', {
      type: 'warning'
    })
    
    await deleteBusinessTerm(row.id)
    ElMessage.success('术语已删除')
    fetchTermList()
    emit('refresh')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.response?.data?.detail || '删除失败')
    }
  }
}

const handleAddQA = async () => {
  if (!qaFormRef.value) return
  
  await qaFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    qaLoading.value = true
    try {
      await trainQAPair(props.datasetId, {
        question: qaForm.question,
        sql: qaForm.sql
      })
      ElMessage.success('QA 对添加成功')
      qaForm.question = ''
      qaForm.sql = ''
      emit('refresh')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || '添加 QA 对失败')
    } finally {
      qaLoading.value = false
    }
  })
}

const fillQAExample = (example: typeof qaExamples[0]) => {
  qaForm.question = example.question
  qaForm.sql = example.sql
}

const handleAddDoc = async () => {
  if (!docFormRef.value) return
  
  await docFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    docLoading.value = true
    try {
      await trainDocumentation(props.datasetId, {
        content: docForm.content
      })
      ElMessage.success('文档添加成功')
      docForm.content = ''
      emit('refresh')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || '添加文档失败')
    } finally {
      docLoading.value = false
    }
  })
}

const fillDocTemplate = (template: typeof docTemplates[0]) => {
  docForm.content = template.content
}

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

const handleClose = () => {
  dialogVisible.value = false
}
</script>

<style scoped>
.term-tabs {
  min-height: 450px;
}

.tab-content {
  padding: 16px 0;
}
</style>
