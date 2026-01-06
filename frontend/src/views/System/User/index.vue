<template>
  <div class="user-management-page">
    <!-- 顶部搜索栏 -->
    <div class="bg-white dark:bg-slate-900 rounded-lg shadow-sm p-6 mb-6">
      <div class="flex items-center justify-between">
        <div class="flex-1 max-w-md">
          <el-input
            v-model="searchQuery"
            placeholder="搜索邮箱或昵称..."
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
            <template #append>
              <el-button :icon="Search" @click="handleSearch">搜索</el-button>
            </template>
          </el-input>
        </div>
        <div class="flex items-center gap-3">
          <el-button :icon="Refresh" @click="loadUserList">刷新</el-button>
        </div>
      </div>
    </div>

    <!-- 用户列表表格 -->
    <div class="bg-white dark:bg-slate-900 rounded-lg shadow-sm">
      <el-table
        v-loading="loading"
        :data="userList"
        stripe
        style="width: 100%"
        :header-cell-style="{ background: '#f8fafc', color: '#475569' }"
      >
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column label="用户" min-width="200">
          <template #default="{ row }">
            <div class="flex items-center gap-3">
              <el-avatar :size="40" class="!bg-blue-100 !text-blue-600">
                {{ getAvatarText(row) }}
              </el-avatar>
              <div class="flex-1 min-w-0">
                <div class="font-medium text-gray-900 dark:text-slate-200 truncate">
                  {{ row.full_name || '未设置' }}
                  <el-tag v-if="row.is_superuser" type="danger" size="small" class="ml-2">
                    超管
                  </el-tag>
                </div>
                <div class="text-xs text-gray-500 dark:text-slate-500 truncate">
                  {{ row.email }}
                </div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_deleted" type="info" size="small">已注销</el-tag>
            <el-tag v-else-if="row.is_active" type="success" size="small">正常</el-tag>
            <el-tag v-else type="warning" size="small">已封禁</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="role" label="角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.role }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="280" align="center" fixed="right">
          <template #default="{ row }">
            <div class="flex items-center justify-center gap-2">
              <!-- 编辑按钮 -->
              <el-button
                v-if="!row.is_deleted"
                size="small"
                :icon="Edit"
                @click="handleEdit(row)"
              >
                编辑
              </el-button>

              <!-- 封禁/解封按钮 -->
              <el-button
                v-if="!row.is_deleted"
                size="small"
                :type="row.is_active ? 'warning' : 'success'"
                :icon="row.is_active ? Lock : Unlock"
                @click="handleToggleStatus(row)"
              >
                {{ row.is_active ? '封禁' : '解封' }}
              </el-button>

              <!-- 注销按钮 -->
              <el-button
                v-if="!row.is_deleted"
                size="small"
                type="danger"
                :icon="Delete"
                @click="handleDelete(row)"
              >
                注销
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="p-6 flex justify-end">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadUserList"
          @current-change="loadUserList"
        />
      </div>
    </div>

    <!-- 编辑用户对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑用户信息"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editFormRules"
        label-width="80px"
      >
        <el-form-item label="邮箱">
          <el-input :value="currentEditUser?.email" disabled />
        </el-form-item>
        
        <el-form-item label="昵称" prop="full_name">
          <el-input
            v-model="editForm.full_name"
            placeholder="请输入用户昵称"
            clearable
          />
        </el-form-item>

        <el-form-item label="角色" prop="role">
          <el-select v-model="editForm.role" placeholder="请选择角色" class="w-full">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>

        <el-form-item label="重置密码" prop="password">
          <el-input
            v-model="editForm.password"
            type="password"
            placeholder="留空则不修改密码"
            clearable
            show-password
          />
        </el-form-item>

        <el-alert
          title="提示：仅用于紧急维护时修改用户信息"
          type="warning"
          :closable="false"
          class="mb-4"
        />
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitEdit">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search, Refresh, Edit, Lock, Unlock, Delete } from '@element-plus/icons-vue'
import {
  getUserList,
  updateUserStatus,
  deleteUser,
  updateUser,
  type SystemUser,
  type UserUpdateByAdmin
} from '@/api/system'

// 数据状态
const loading = ref(false)
const submitting = ref(false)
const searchQuery = ref('')
const userList = ref<SystemUser[]>([])

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 编辑对话框
const editDialogVisible = ref(false)
const editFormRef = ref<FormInstance>()
const currentEditUser = ref<SystemUser | null>(null)
const editForm = reactive<UserUpdateByAdmin>({
  full_name: '',
  password: '',
  role: ''
})

const editFormRules: FormRules = {
  password: [
    { min: 6, message: '密码长度至少为6位', trigger: 'blur' }
  ]
}

/**
 * 获取头像文字
 */
const getAvatarText = (user: SystemUser) => {
  if (user.full_name) {
    return user.full_name.substring(0, 2).toUpperCase()
  }
  return user.email.substring(0, 2).toUpperCase()
}

/**
 * 加载用户列表
 */
const loadUserList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      search: searchQuery.value || undefined
    }
    const res = await getUserList(params)
    userList.value = res.users
    pagination.total = res.total
  } catch (error) {
    console.error('加载用户列表失败:', error)
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

/**
 * 搜索用户
 */
const handleSearch = () => {
  pagination.page = 1
  loadUserList()
}

/**
 * 编辑用户
 */
const handleEdit = (user: SystemUser) => {
  currentEditUser.value = user
  editForm.full_name = user.full_name || ''
  editForm.password = ''
  editForm.role = user.role
  editDialogVisible.value = true
}

/**
 * 提交编辑
 */
const handleSubmitEdit = async () => {
  if (!editFormRef.value || !currentEditUser.value) return

  await editFormRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      // 只提交有值的字段
      const data: UserUpdateByAdmin = {}
      if (editForm.full_name) data.full_name = editForm.full_name
      if (editForm.password) data.password = editForm.password
      if (editForm.role) data.role = editForm.role

      if (Object.keys(data).length === 0) {
        ElMessage.warning('请至少修改一项')
        return
      }

      if (currentEditUser.value) {
        await updateUser(currentEditUser.value.id, data)
        ElMessage.success('修改成功')
        editDialogVisible.value = false
        loadUserList()
      }
    } catch (error: any) {
      console.error('修改用户失败:', error)
      ElMessage.error(error.response?.data?.detail || '修改用户失败')
    } finally {
      submitting.value = false
    }
  })
}

/**
 * 切换用户状态（封禁/解封）
 */
const handleToggleStatus = async (user: SystemUser) => {
  const action = user.is_active ? '封禁' : '解封'
  const confirmText = user.is_active
    ? `确定要封禁用户 "${user.email}" 吗？封禁后该用户将无法登录系统。`
    : `确定要解封用户 "${user.email}" 吗？`

  try {
    await ElMessageBox.confirm(confirmText, `${action}用户`, {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await updateUserStatus(user.id, { is_active: !user.is_active })
    ElMessage.success(`${action}成功`)
    loadUserList()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error(`${action}用户失败:`, error)
      ElMessage.error(error.response?.data?.detail || `${action}用户失败`)
    }
  }
}

/**
 * 注销用户（软删除）
 */
const handleDelete = async (user: SystemUser) => {
  try {
    await ElMessageBox.confirm(
      `确定要注销用户 "${user.email}" 吗？此操作将：\n1. 将用户标记为已删除\n2. 禁止用户登录\n3. 不会删除用户的历史数据`,
      '注销用户',
      {
        confirmButtonText: '确定注销',
        cancelButtonText: '取消',
        type: 'error',
        dangerouslyUseHTMLString: false
      }
    )

    await deleteUser(user.id)
    ElMessage.success('注销成功')
    loadUserList()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('注销用户失败:', error)
      ElMessage.error(error.response?.data?.detail || '注销用户失败')
    }
  }
}

// 页面加载时获取用户列表
onMounted(() => {
  loadUserList()
})
</script>

<style scoped>
.user-management-page {
  padding: 0;
}

:deep(.el-table) {
  --el-table-border-color: #e2e8f0;
}

:deep(.dark .el-table) {
  --el-table-border-color: #334155;
  --el-table-bg-color: #0f172a;
  --el-table-tr-bg-color: #0f172a;
  --el-table-row-hover-bg-color: #1e293b;
}

:deep(.el-pagination) {
  --el-pagination-bg-color: transparent;
}
</style>
