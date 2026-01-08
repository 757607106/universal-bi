<template>
  <el-dialog
    v-model="visible"
    title="文件夹管理"
    width="500px"
    :before-close="handleClose"
  >
    <div class="folder-list">
      <div class="mb-4">
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          新建文件夹
        </el-button>
      </div>

      <el-table :data="folders" border>
        <el-table-column prop="name" label="文件夹名称" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button link type="primary" size="small" @click="handleEdit(scope.row)">
              重命名
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(scope.row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="folders.length === 0" description="暂无文件夹" />
    </div>

    <!-- 新建/编辑文件夹对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingFolder ? '重命名文件夹' : '新建文件夹'"
      width="400px"
      append-to-body
    >
      <el-form :model="folderForm" label-width="80px">
        <el-form-item label="文件夹名">
          <el-input
            v-model="folderForm.name"
            placeholder="请输入文件夹名称"
            maxlength="255"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { Folder } from '@/api/dataTable'
import { getFolders, createFolder, updateFolder, deleteFolder } from '@/api/dataTable'

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

const folders = ref<Folder[]>([])
const dialogVisible = ref(false)
const editingFolder = ref<Folder | null>(null)
const submitting = ref(false)
const folderForm = ref({
  name: ''
})

watch(visible, async (val) => {
  if (val) {
    await loadFolders()
  }
})

const loadFolders = async () => {
  try {
    folders.value = await getFolders()
  } catch (error: any) {
    ElMessage.error(error.message || '获取文件夹列表失败')
  }
}

const showCreateDialog = () => {
  editingFolder.value = null
  folderForm.value.name = ''
  dialogVisible.value = true
}

const handleEdit = (folder: Folder) => {
  editingFolder.value = folder
  folderForm.value.name = folder.name
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!folderForm.value.name.trim()) {
    ElMessage.warning('请输入文件夹名称')
    return
  }

  submitting.value = true
  try {
    if (editingFolder.value) {
      await updateFolder(editingFolder.value.id, { name: folderForm.value.name })
      ElMessage.success('文件夹重命名成功')
    } else {
      await createFolder({ name: folderForm.value.name })
      ElMessage.success('文件夹创建成功')
    }
    
    dialogVisible.value = false
    await loadFolders()
    emit('refresh')
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (folder: Folder) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除文件夹"${folder.name}"吗？删除后无法恢复。`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    )
    
    await deleteFolder(folder.id)
    ElMessage.success('文件夹已删除')
    await loadFolders()
    emit('refresh')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleClose = () => {
  visible.value = false
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<style scoped>
.folder-list {
  min-height: 300px;
}
</style>
