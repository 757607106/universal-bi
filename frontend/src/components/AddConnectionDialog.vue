<template>
  <el-dialog
    v-model="dialogVisible"
    :title="editData ? '编辑数据库连接' : '添加数据库连接'"
    width="500px"
    :before-close="handleClose"
    class="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800"
  >
    <el-form :model="formData" label-width="80px" class="space-y-4">
      <el-form-item label="连接名称" prop="name">
        <el-input
          v-model="formData.name"
          placeholder="例如：生产环境数据库"
          class="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
        />
      </el-form-item>

      <el-form-item label="数据库类型" prop="type">
        <el-select
          v-model="formData.type"
          class="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100"
        >
          <el-option label="PostgreSQL" value="postgresql" />
          <el-option label="MySQL" value="mysql" />
        </el-select>
      </el-form-item>

      <div class="grid grid-cols-2 gap-4">
        <el-form-item label="主机地址" prop="host">
          <el-input
            v-model="formData.host"
            placeholder="localhost"
            class="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
          />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input
            v-model="formData.port"
            placeholder="5432"
            class="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
          />
        </el-form-item>
      </div>

      <el-form-item label="数据库名称" prop="database_name">
        <el-input
          v-model="formData.database_name"
          placeholder="mydb"
          class="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
        />
      </el-form-item>

      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="formData.username"
          placeholder="admin"
          class="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
        />
      </el-form-item>

      <el-form-item label="密码" prop="password">
        <el-input
          v-model="formData.password"
          type="password"
          placeholder="••••••••"
          class="dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose" class="dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800">
          取消
        </el-button>
        <el-button
          type="success"
          @click="handleTestConnection"
          :loading="testingConnection"
          :disabled="!isFormValid"
          class="bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-500/30 mr-2"
        >
          测试连接
        </el-button>
        <el-button
          type="primary"
          @click="handleSave"
          :loading="saving"
          :disabled="!isFormValid"
          class="bg-[#409EFF] hover:bg-[#3182ce] shadow-lg shadow-blue-500/30"
        >
          {{ editData ? '保存' : '保存连接' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { testConnection, addDataSource, type DataSourceForm } from '../api/datasource'

interface Props {
  modelValue: boolean
  editData?: any
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'save', data: any): void
  (e: 'close'): void
  (e: 'refresh'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const dialogVisible = ref(false)
const testingConnection = ref(false)
const saving = ref(false)
const connectionTested = ref(false)

const formData = ref<DataSourceForm>({
  name: '',
  type: 'postgresql',
  host: '',
  port: 5432,
  database_name: '',
  username: '',
  password: '',
})

const isFormValid = computed(() => {
  return formData.value.name && 
         formData.value.host && 
         formData.value.port && 
         formData.value.database_name && 
         formData.value.username && 
         formData.value.password
})

// 同步 v-model
watch(() => props.modelValue, (newVal) => {
  dialogVisible.value = newVal
  if (newVal) {
    connectionTested.value = false
  }
})

watch(dialogVisible, (newVal) => {
  emit('update:modelValue', newVal)
})

// 当 editData 或 dialogVisible 变化时更新表单数据
watch([() => props.editData, dialogVisible], async ([editData, visible]) => {
  if (visible && editData) {
    formData.value = {
      name: editData.name || '',
      type: editData.type || 'postgresql',
      host: editData.host || '',
      port: Number(editData.port) || 5432,
      database_name: editData.database || '', // 注意：后端模型字段是 database_name，前端显示可能需要适配
      username: editData.username || '',
      password: '', // 编辑时不回显密码
    }
  } else if (visible && !editData) {
    formData.value = {
      name: '',
      type: 'postgresql',
      host: '',
      port: 5432,
      database_name: '',
      username: '',
      password: '',
    }
  }
}, { immediate: true })

const handleTestConnection = async () => {
  testingConnection.value = true
  try {
    const success = await testConnection(formData.value)
    if (success) {
      ElMessage.success('连接成功')
      connectionTested.value = true
    } else {
      ElMessage.error('连接失败，请检查配置')
      connectionTested.value = false
    }
  } catch (error: any) {
    ElMessage.error(error.message || '连接测试出错')
    connectionTested.value = false
  } finally {
    testingConnection.value = false
  }
}

const handleSave = async () => {
  if (!connectionTested.value) {
    // 如果还没测试，先自动测试
    await handleTestConnection()
    if (!connectionTested.value) return
  }
  
  saving.value = true
  try {
    await addDataSource(formData.value)
    ElMessage.success('保存成功')
    emit('save', formData.value)
    handleClose()
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleClose = () => {
  dialogVisible.value = false
  emit('close')
  // 延迟重置表单
  nextTick(() => {
    setTimeout(() => {
      formData.value = {
        name: '',
        type: 'postgresql',
        host: '',
        port: 5432,
        database_name: '',
        username: '',
        password: '',
      }
      connectionTested.value = false
    }, 200)
  })
}
</script>
