<template>
  <div class="modeling-page h-screen flex flex-col bg-gray-50 dark:bg-slate-900">
    <!-- 顶部工具栏 -->
    <div class="toolbar bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <el-button text @click="handleBack" class="!text-gray-600 dark:!text-slate-400">
          <el-icon><ArrowLeft /></el-icon>
          <span class="ml-2">返回</span>
        </el-button>
        <div class="border-l border-gray-300 dark:border-slate-600 h-6"></div>
        <h1 class="text-xl font-bold text-gray-900 dark:text-slate-100">可视化建模</h1>
        <el-tag v-if="currentDataset" type="info" effect="plain" class="!bg-blue-50 dark:!bg-blue-500/10 !border-blue-200 dark:!border-blue-500/50 !text-blue-600 dark:!text-blue-400">
          {{ currentDataset }}
        </el-tag>
      </div>
      
      <div class="flex items-center gap-3">
        <el-button size="small" @click="handleClearCanvas" class="!bg-gray-100 dark:!bg-slate-700 !text-gray-600 dark:!text-slate-300">
          <el-icon><Delete /></el-icon>
          <span class="ml-1">清空画布</span>
        </el-button>
        <el-button size="small" @click="handleAutoLayout" :disabled="nodes.length < 2" class="!bg-gradient-to-r !from-green-500 !to-emerald-600 hover:!from-green-400 hover:!to-emerald-500 !text-white !border-none">
          <el-icon><Rank /></el-icon>
          <span class="ml-1">一键排版</span>
        </el-button>
        <el-button type="primary" size="small" @click="() => handleSave()" :loading="isSaving" class="!bg-blue-600 hover:!bg-blue-500">
          <el-icon><Select /></el-icon>
          <span class="ml-1">保存布局</span>
        </el-button>
      </div>
    </div>

    <!-- 主内容区：三栏布局 -->
    <div class="main-content flex flex-1 overflow-hidden">
      <!-- 左侧：表选择器 (20%) -->
      <div class="left-panel w-1/5 bg-white dark:bg-slate-800 border-r border-gray-200 dark:border-slate-700 flex flex-col">
        <div class="panel-header px-4 py-3 border-b border-gray-200 dark:border-slate-700">
          <h2 class="text-sm font-semibold text-gray-900 dark:text-slate-100 flex items-center gap-2">
            <el-icon><Files /></el-icon>
            <span>数据表</span>
          </h2>
          <el-input 
            v-model="tableSearchKeyword" 
            placeholder="搜索表..." 
            size="small" 
            clearable 
            class="mt-2"
            prefix-icon="Search"
          />
        </div>
        
        <div class="table-list flex-1 overflow-y-auto p-2">
          <div 
            v-for="table in filteredTables" 
            :key="table.name"
            class="table-item bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3 mb-2 cursor-move hover:shadow-md hover:bg-blue-50 dark:hover:bg-blue-500/10 border border-gray-200 dark:border-slate-600 transition-all"
            draggable="true"
            @dragstart="handleDragStart($event, table)"
            @dblclick="handleAddTable(table)"
          >
            <div class="flex items-center gap-2">
              <el-icon class="text-blue-500" :size="16"><Grid /></el-icon>
              <div class="flex-1 min-w-0">
                <div class="text-xs font-medium text-gray-900 dark:text-slate-200 truncate">
                  {{ table.name }}
                </div>
                <div class="text-[10px] text-gray-500 dark:text-slate-400 mt-1">
                  {{ table.fields.length }} 个字段
                </div>
              </div>
            </div>
          </div>
          
          <el-empty v-if="filteredTables.length === 0" description="暂无数据表" :image-size="60" />
        </div>
      </div>

      <!-- 中间：VueFlow 画布区域 (60%) -->
      <div class="canvas-area flex-1 relative">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :node-types="nodeTypes"
          :default-edge-options="defaultEdgeOptions"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @connect="onConnect"
          @drop="handleDrop"
          @dragover.prevent
          @pane-click="onPaneClick"
          class="vue-flow-canvas"
          :connect-on-click="true"
          :snap-to-grid="true"
          :snap-grid="[16, 16]"
        >
          <Background pattern-color="#94a3b8" :gap="16" :size="1" variant="dots" />
          <Controls position="bottom-left" />
          <MiniMap />
        </VueFlow>
        
        <!-- 画布提示 -->
        <div v-if="nodes.length === 0" class="canvas-hint absolute inset-0 flex items-center justify-center pointer-events-none">
          <div class="text-center text-gray-400 dark:text-slate-500">
            <el-icon :size="48" class="mb-4"><Plus /></el-icon>
            <p class="text-sm">拖拽或双击左侧表添加到画布</p>
          </div>
        </div>
      </div>

      <!-- 右侧：属性面板 (20%) -->
      <div class="right-panel w-1/5 bg-white dark:bg-slate-800 border-l border-gray-200 dark:border-slate-700 flex flex-col">
        <div class="panel-header px-4 py-3 border-b border-gray-200 dark:border-slate-700">
          <h2 class="text-sm font-semibold text-gray-900 dark:text-slate-100 flex items-center gap-2">
            <el-icon><Setting /></el-icon>
            <span>属性面板</span>
          </h2>
        </div>
        
        <div class="properties-content flex-1 overflow-y-auto p-4">
          <!-- 选中节点时显示表详情 -->
          <div v-if="selectedNode" class="space-y-4">
            <div class="property-section">
              <h3 class="text-xs font-semibold text-gray-700 dark:text-slate-300 mb-2">表信息</h3>
              <div class="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
                <div class="text-sm font-medium text-gray-900 dark:text-slate-100 mb-2">
                  {{ selectedNode.data.tableName }}
                </div>
                <div class="text-xs text-gray-500 dark:text-slate-400">
                  共 {{ selectedNode.data.fields.length }} 个字段
                </div>
              </div>
            </div>
            
            <div class="property-section">
              <h3 class="text-xs font-semibold text-gray-700 dark:text-slate-300 mb-2">字段列表</h3>
              <div class="space-y-1 max-h-64 overflow-y-auto">
                <div 
                  v-for="field in selectedNode.data.fields" 
                  :key="field.name"
                  class="bg-gray-50 dark:bg-slate-700/50 rounded px-2 py-1.5 text-xs"
                >
                  <div class="flex items-center justify-between">
                    <span class="text-gray-900 dark:text-slate-200 font-medium">{{ field.name }}</span>
                    <span class="text-gray-500 dark:text-slate-400">{{ field.type }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 选中连线时显示关联详情 -->
          <div v-else-if="selectedEdge" class="space-y-4">
            <div class="property-section">
              <h3 class="text-xs font-semibold text-gray-700 dark:text-slate-300 mb-2">关联关系</h3>
              <div class="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
                <div class="text-xs space-y-2">
                  <div class="flex items-center gap-2">
                    <span class="text-gray-500 dark:text-slate-400">源表:</span>
                    <span class="text-gray-900 dark:text-slate-100 font-medium">{{ getNodeLabel(selectedEdge.source) }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="text-gray-500 dark:text-slate-400">目标表:</span>
                    <span class="text-gray-900 dark:text-slate-100 font-medium">{{ getNodeLabel(selectedEdge.target) }}</span>
                  </div>
                  <div v-if="selectedEdge.label" class="flex items-center gap-2">
                    <span class="text-gray-500 dark:text-slate-400">关联字段:</span>
                    <span class="text-blue-600 dark:text-blue-400 font-mono text-[10px]">{{ selectedEdge.label }}</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 编辑连线字段 -->
            <div class="property-section">
              <h3 class="text-xs font-semibold text-gray-700 dark:text-slate-300 mb-2">编辑关联字段</h3>
              <div class="space-y-2">
                <div>
                  <label class="text-xs text-gray-500 dark:text-slate-400 mb-1 block">源表字段</label>
                  <el-select 
                    v-model="editingEdgeSourceCol" 
                    size="small" 
                    class="w-full"
                    placeholder="选择源表字段"
                  >
                    <el-option 
                      v-for="field in getNodeFields(selectedEdge.source)" 
                      :key="field.name" 
                      :label="field.name" 
                      :value="field.name"
                    />
                  </el-select>
                </div>
                <div>
                  <label class="text-xs text-gray-500 dark:text-slate-400 mb-1 block">目标表字段</label>
                  <el-select 
                    v-model="editingEdgeTargetCol" 
                    size="small" 
                    class="w-full"
                    placeholder="选择目标表字段"
                  >
                    <el-option 
                      v-for="field in getNodeFields(selectedEdge.target)" 
                      :key="field.name" 
                      :label="field.name" 
                      :value="field.name"
                    />
                  </el-select>
                </div>
                <el-button type="primary" size="small" @click="handleUpdateEdge" class="w-full mt-2">
                  <el-icon><Check /></el-icon>
                  <span class="ml-1">更新关联</span>
                </el-button>
              </div>
            </div>
            
            <el-button type="danger" size="small" @click="handleDeleteEdge" class="w-full">
              <el-icon><Delete /></el-icon>
              <span class="ml-1">删除关联</span>
            </el-button>
          </div>
          
          <!-- SQL 预览 -->
          <div v-else-if="generatedSQL" class="space-y-4">
            <div class="property-section">
              <h3 class="text-xs font-semibold text-gray-700 dark:text-slate-300 mb-2 flex items-center justify-between">
                <span>SQL 预览</span>
                <el-button size="small" text @click="copySQL">
                  <el-icon><DocumentCopy /></el-icon>
                </el-button>
              </h3>
              <div class="bg-gray-900 dark:bg-slate-950 rounded-lg p-3 max-h-96 overflow-y-auto">
                <pre class="text-xs text-green-400 font-mono whitespace-pre-wrap break-words">{{ generatedSQL }}</pre>
              </div>
            </div>
          </div>
          
          <!-- 未选中任何元素 -->
          <div v-else class="text-center text-gray-400 dark:text-slate-500 mt-8">
            <el-icon :size="32" class="mb-2"><InfoFilled /></el-icon>
            <p class="text-xs">点击节点或连线查看详情</p>
            <p class="text-xs mt-2 text-gray-300 dark:text-slate-600">或使用下方 AI 分析功能</p>
          </div>
        </div>
        
        <!-- 底部操作按钮（始终显示） -->
        <div class="panel-footer p-4 border-t border-gray-200 dark:border-slate-700 space-y-2">
          <el-button 
            type="primary" 
            size="small" 
            @click="handleAutoAnalyze" 
            :disabled="nodes.length < 2"
            :loading="isAnalyzing"
            class="w-full !bg-gradient-to-r !from-purple-600 !to-blue-600 hover:!from-purple-500 hover:!to-blue-500 !border-none"
          >
            <el-icon v-if="!isAnalyzing"><MagicStick /></el-icon>
            <span class="ml-1">🤖 AI 自动分析关联</span>
          </el-button>
          
          <el-button 
            type="success" 
            size="small" 
            @click="handleGenerateWideTable" 
            :disabled="nodes.length === 0 || edges.length === 0"
            class="w-full"
          >
            <el-icon><Check /></el-icon>
            <span class="ml-1">✅ 生成宽表</span>
          </el-button>
          
          <!-- 添加调试信息 -->
          <div class="text-xs text-gray-400 dark:text-slate-500 mt-2 text-center">
            <div>{{ nodes.length }} 个表，{{ edges.length }} 个关联</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 生成宽表 Dialog -->
    <el-dialog
      v-model="wideTableDialogVisible"
      title="生成宽表"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="{ viewName: wideTableName }" label-width="100px">
        <el-form-item label="视图名称" required>
          <div class="flex gap-2">
            <el-input
              v-model="wideTableName"
              placeholder="请输入视图名称，如 sales_analysis"
              maxlength="50"
              show-word-limit
              class="flex-1"
            >
              <template #prepend>v_</template>
            </el-input>
            <el-button 
              type="primary" 
              @click="handleAutoGenerateViewName"
              :icon="MagicStick"
              title="基于表名自动生成"
            >
              一键生成
            </el-button>
          </div>
          <div class="text-xs text-gray-500 dark:text-slate-400 mt-1">
            视图将以 "v_" 开头，只允许字母、数字和下划线
          </div>
        </el-form-item>
        
        <el-form-item label="SQL 预览">
          <div class="flex gap-2 mb-2">
            <el-button 
              size="small" 
              type="primary"
              @click="handleAIOptimizeSQL"
              :loading="isOptimizingSQL"
              :icon="MagicStick"
            >
              <span class="ml-1">🤖 AI 智能优化 SQL</span>
            </el-button>
            <el-button 
              size="small" 
              @click="copySQL"
              :icon="DocumentCopy"
            >
              复制 SQL
            </el-button>
          </div>
          <div class="bg-gray-900 dark:bg-slate-950 rounded p-2 max-h-64 overflow-y-auto">
            <pre class="text-xs text-green-400 font-mono whitespace-pre-wrap">{{ generatedSQL }}</pre>
          </div>
          <div v-if="sqlOptimizationTip" class="text-xs text-blue-500 dark:text-blue-400 mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded">
            <el-icon><InfoFilled /></el-icon>
            <span class="ml-1">{{ sqlOptimizationTip }}</span>
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button @click="wideTableDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleCreateView" :disabled="!wideTableName">
            创建视图
          </el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- 训练进度对话框 -->
    <TrainingProgressDialog
      v-model="progressDialogVisible"
      :dataset-id="currentDatasetId || 0"
      @refresh="() => {}"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, markRaw, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import { 
  ArrowLeft, Delete, Select, Files, Grid, Setting, Plus, 
  InfoFilled, MagicStick, Check, Search, DocumentCopy, Rank 
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import TableNode from './components/TableNode.vue'
import TrainingProgressDialog from '../components/TrainingProgressDialog.vue'
import type { Node, Edge } from '@vue-flow/core'
import { 
  analyzeRelationships, 
  createView, 
  getDbTables,
  updateModelingConfig,
  getDataset,
  trainDataset,
  updateDatasetTables,
  type RelationshipEdge,
  type TableNode as TableNodeType
} from '@/api/dataset'

const router = useRouter()
const route = useRoute()

// VueFlow 相关
const { addNodes, addEdges, removeNodes, removeEdges, findNode, toObject, fromObject, onNodesChange, onEdgesChange } = useVueFlow()

// 注册自定义节点类型
const nodeTypes = {
  tableNode: markRaw(TableNode) as any
}

// 默认连线样式配置
const defaultEdgeOptions = {
  type: 'smoothstep',
  animated: true,
  style: { stroke: '#3b82f6', strokeWidth: 2 }
}

// 数据源
const currentDataset = ref('用户数据集') // 应从路由参数获取
const currentDatasetId = ref<number | null>(null) // Dataset ID
const currentDatasourceId = ref<number>(1) // Datasource ID
const tableSearchKeyword = ref('')
const generatedSQL = ref('') // SQL 预览
const isAnalyzing = ref(false) // AI 分析状态
const wideTableDialogVisible = ref(false) // 宽表 Dialog 显示状态
const wideTableName = ref('') // 宽表名称
const isOptimizingSQL = ref(false) // AI 优化 SQL 状态
const sqlOptimizationTip = ref('') // SQL 优化提示
const isSaving = ref(false) // 保存状态
const hasUnsavedChanges = ref(false) // 是否有未保存的更改
const progressDialogVisible = ref(false) // 训练进度对话框

// 表数据（将从 API 加载）
const availableTables = ref<any[]>([])
const isLoadingTables = ref(false)

// 从路由获取参数
const initFromRoute = async () => {
  // 尝试从路由获取 dataset_id 或 datasource_id
  const datasetId = route.query.dataset_id as string
  const datasourceId = route.query.datasource_id as string
  
  if (datasetId) {
    currentDatasetId.value = parseInt(datasetId)
    // 加载 dataset 信息，获取 datasource_id 和 modeling_config
    await loadDatasetConfig()
  } else if (datasourceId) {
    currentDatasourceId.value = parseInt(datasourceId)
  }
  
  // 加载表列表
  await loadTables()
}

// 加载数据集配置（包括建模数据）
const loadDatasetConfig = async () => {
  if (!currentDatasetId.value) return
  
  try {
    const dataset = await getDataset(currentDatasetId.value)
    console.log('Loaded dataset:', dataset)
    
    // 设置 datasource_id
    if (dataset.datasource_id) {
      currentDatasourceId.value = dataset.datasource_id
    }
    
    // 设置数据集名称
    if (dataset.name) {
      currentDataset.value = dataset.name
    }
    
    // 恢复建模数据
    if (dataset.modeling_config && Object.keys(dataset.modeling_config).length > 0) {
      console.log('Restoring modeling config:', dataset.modeling_config)
      
      // 使用 fromObject 恢复完整状态（包括 viewport）
      try {
        fromObject(dataset.modeling_config)
        console.log('Restored flow state using fromObject')
        
        // 如果有节点，生成 SQL 预览
        if (nodes.value.length > 0) {
          setTimeout(() => {
            generateSQL()
            ElMessage.success('已加载之前的建模配置')
          }, 500)
        }
      } catch (error) {
        console.error('Failed to restore using fromObject, falling back to manual restore:', error)
        
        // 如果 fromObject 失败，使用手动恢复
        if (dataset.modeling_config.nodes && Array.isArray(dataset.modeling_config.nodes)) {
          nodes.value = dataset.modeling_config.nodes.map((n: any) => ({
            id: n.id,
            type: n.type || 'tableNode',
            position: n.position || { x: 0, y: 0 },
            data: n.data
          }))
          console.log('Restored nodes:', nodes.value)
        }
        
        if (dataset.modeling_config.edges && Array.isArray(dataset.modeling_config.edges)) {
          edges.value = dataset.modeling_config.edges.map((e: any) => ({
            id: e.id,
            source: e.source,
            target: e.target,
            label: e.label,
            type: e.type || 'smoothstep',
            animated: e.animated !== false,
            style: e.style || { stroke: '#3b82f6', strokeWidth: 2 },
            data: e.data
          }))
          console.log('Restored edges:', edges.value)
        }
        
        if (nodes.value.length > 0) {
          setTimeout(() => {
            generateSQL()
            ElMessage.success('已加载之前的建模配置')
          }, 500)
        }
      }
    }
  } catch (error: any) {
    console.error('Failed to load dataset config:', error)
    // 不弹出错误提示，静默失败
  }
}

// 加载数据源的表列表
const loadTables = async () => {
  if (!currentDatasourceId.value) {
    console.warn('No datasource_id available')
    return
  }
  
  isLoadingTables.value = true
  try {
    const tables = await getDbTables(currentDatasourceId.value)
    availableTables.value = tables.map((t: any) => ({
      name: t.name,
      fields: t.columns?.map((col: any) => ({
        name: col.name,
        type: col.type
      })) || []
    }))
    console.log('Loaded tables:', availableTables.value)
  } catch (error) {
    console.error('Failed to load tables:', error)
    ElMessage.error('加载表列表失败')
    // 如果加载失败，使用模拟数据
    availableTables.value = mockTables
  } finally {
    isLoadingTables.value = false
  }
}

// 模拟表数据（作为 fallback）
const mockTables = [
  {
    name: 'users',
    fields: [
      { name: 'id', type: 'integer' },
      { name: 'username', type: 'varchar' },
      { name: 'email', type: 'varchar' },
      { name: 'created_at', type: 'timestamp' },
      { name: 'status', type: 'integer' }
    ]
  },
  {
    name: 'orders',
    fields: [
      { name: 'id', type: 'integer' },
      { name: 'user_id', type: 'integer' },
      { name: 'amount', type: 'decimal' },
      { name: 'order_date', type: 'timestamp' },
      { name: 'status', type: 'varchar' }
    ]
  },
  {
    name: 'products',
    fields: [
      { name: 'id', type: 'integer' },
      { name: 'name', type: 'varchar' },
      { name: 'price', type: 'decimal' },
      { name: 'category_id', type: 'integer' },
      { name: 'stock', type: 'integer' }
    ]
  },
  {
    name: 'order_items',
    fields: [
      { name: 'id', type: 'integer' },
      { name: 'order_id', type: 'integer' },
      { name: 'product_id', type: 'integer' },
      { name: 'quantity', type: 'integer' },
      { name: 'price', type: 'decimal' }
    ]
  }
]

// 过滤后的表列表
const filteredTables = computed(() => {
  if (!tableSearchKeyword.value) return availableTables.value
  return availableTables.value.filter(t => 
    t.name.toLowerCase().includes(tableSearchKeyword.value.toLowerCase())
  )
})

// 画布节点和连线
const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])

// 选中的节点和连线
const selectedNode = ref<Node | null>(null)
const selectedEdge = ref<Edge | null>(null)

// 编辑连线的字段
const editingEdgeSourceCol = ref('')
const editingEdgeTargetCol = ref('')

// 监听 selectedEdge 变化，初始化编辑字段
watch(selectedEdge, (newEdge) => {
  if (newEdge) {
    editingEdgeSourceCol.value = newEdge.data?.source_col || ''
    editingEdgeTargetCol.value = newEdge.data?.target_col || ''
  } else {
    editingEdgeSourceCol.value = ''
    editingEdgeTargetCol.value = ''
  }
})

// 拖拽开始
const handleDragStart = (event: DragEvent, table: any) => {
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('application/vueflow', JSON.stringify(table))
  }
}

// 拖拽到画布
const handleDrop = (event: DragEvent) => {
  const data = event.dataTransfer?.getData('application/vueflow')
  if (!data) return
  
  const table = JSON.parse(data)
  handleAddTable(table, { x: event.clientX - 300, y: event.clientY - 100 })
}

// 添加表到画布
const handleAddTable = (table: any, position?: { x: number; y: number }) => {
  const existingNode = nodes.value.find(n => n.data.tableName === table.name)
  if (existingNode) {
    ElMessage.warning('该表已存在于画布中')
    return
  }
  
  const newNode = {
    id: `node-${Date.now()}`,
    type: 'tableNode',
    position: position || { x: Math.random() * 300 + 50, y: Math.random() * 200 + 50 },
    data: {
      tableName: table.name,
      fields: table.fields,
      selected: false
    }
  }
  
  addNodes([newNode])
  ElMessage.success(`已添加表 ${table.name}`)
}

// 点击节点
const onNodeClick = (event: any) => {
  selectedNode.value = event.node
  selectedEdge.value = null
  
  // 更新所有节点的选中状态
  nodes.value.forEach(n => {
    n.data.selected = n.id === event.node.id
  })
}

// 点击连线
const onEdgeClick = (event: any) => {
  selectedEdge.value = event.edge
  selectedNode.value = null
}

// 点击画布空白区域
const onPaneClick = () => {
  selectedNode.value = null
  selectedEdge.value = null
  // 取消所有节点的选中状态
  nodes.value.forEach(n => {
    n.data.selected = false
  })
}

// 手动连线事件处理
const onConnect = (params: any) => {
  console.log('Manual connect:', params)
  
  // 获取源节点和目标节点
  const sourceNode = findNode(params.source)
  const targetNode = findNode(params.target)
  
  if (!sourceNode || !targetNode) {
    ElMessage.error('连线失败：找不到节点')
    return
  }
  
  // 检查是否已存在相同的连线
  const existingEdge = edges.value.find(
    e => (e.source === params.source && e.target === params.target) ||
         (e.source === params.target && e.target === params.source)
  )
  
  if (existingEdge) {
    ElMessage.warning('这两个表已经存在关联')
    return
  }
  
  // 创建新连线，使用默认的 id 字段
  const sourceTableName = sourceNode.data.tableName
  const targetTableName = targetNode.data.tableName
  
  // 尝试智能匹配关联字段
  let sourceCol = 'id'
  let targetCol = 'id'
  
  // 查找常见的外键模式
  const sourceFields = sourceNode.data.fields.map((f: any) => f.name)
  const targetFields = targetNode.data.fields.map((f: any) => f.name)
  
  // 检查 target 是否有 source 表名的外键 (e.g., user_id)
  const sourceTableKey = `${sourceTableName.replace(/^(dim_|fact_|dw_)/, '').replace(/s$/, '')}_id`
  if (targetFields.includes(sourceTableKey)) {
    sourceCol = sourceFields.includes('id') ? 'id' : sourceFields.find((f: string) => f.endsWith('_id')) || 'id'
    targetCol = sourceTableKey
  }
  // 检查 source 是否有 target 表名的外键
  else {
    const targetTableKey = `${targetTableName.replace(/^(dim_|fact_|dw_)/, '').replace(/s$/, '')}_id`
    if (sourceFields.includes(targetTableKey)) {
      sourceCol = targetTableKey
      targetCol = targetFields.includes('id') ? 'id' : targetFields.find((f: string) => f.endsWith('_id')) || 'id'
    }
  }
  
  const newEdge: Edge = {
    id: `e-${params.source}-${params.target}-${Date.now()}`,
    source: params.source,
    target: params.target,
    type: 'smoothstep',
    animated: true,
    label: `${sourceCol} = ${targetCol}`,
    style: { stroke: '#3b82f6', strokeWidth: 2 },
    data: {
      source_col: sourceCol,
      target_col: targetCol,
      type: 'left',
      confidence: 'manual'
    }
  }
  
  addEdges([newEdge])
  ElMessage.success(`已创建关联: ${sourceTableName} → ${targetTableName}`)
  
  // 自动更新 SQL 预览
  generateSQL()
}

// 获取节点标签
const getNodeLabel = (nodeId: string) => {
  const node = findNode(nodeId)
  return node?.data.tableName || nodeId
}

// 获取节点的字段列表
const getNodeFields = (nodeId: string) => {
  const node = findNode(nodeId)
  return node?.data?.fields || []
}

// 更新连线字段
const handleUpdateEdge = () => {
  if (!selectedEdge.value) return
  
  if (!editingEdgeSourceCol.value || !editingEdgeTargetCol.value) {
    ElMessage.warning('请选择源表字段和目标表字段')
    return
  }
  
  // 更新 edge 的数据
  const edgeIndex = edges.value.findIndex(e => e.id === selectedEdge.value!.id)
  if (edgeIndex === -1) return
  
  edges.value[edgeIndex] = {
    ...edges.value[edgeIndex],
    label: `${editingEdgeSourceCol.value} = ${editingEdgeTargetCol.value}`,
    data: {
      ...edges.value[edgeIndex].data,
      source_col: editingEdgeSourceCol.value,
      target_col: editingEdgeTargetCol.value
    }
  }
  
  // 更新 selectedEdge 引用
  selectedEdge.value = edges.value[edgeIndex]
  
  ElMessage.success('关联字段已更新')
  
  // 自动更新 SQL 预览
  generateSQL()
}

// 删除连线
const handleDeleteEdge = () => {
  if (selectedEdge.value) {
    removeEdges([selectedEdge.value.id])
    ElMessage.success('已删除关联')
    selectedEdge.value = null
    // 自动更新 SQL 预览
    generateSQL()
  }
}

// 清空画布
const handleClearCanvas = async () => {
  try {
    await ElMessageBox.confirm('确定清空画布吗？此操作不可恢复。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    nodes.value = []
    edges.value = []
    selectedNode.value = null
    selectedEdge.value = null
    ElMessage.success('画布已清空')
  } catch {
    // 取消操作
  }
}

// 一键排版 - 自动整理节点布局
const handleAutoLayout = () => {
  if (nodes.value.length < 2) {
    ElMessage.warning('请至少添加两个表')
    return
  }
  
  const loading = ElLoading.service({
    lock: true,
    text: '正在自动排版...',
    background: 'rgba(0, 0, 0, 0.7)'
  })
  
  try {
    // Dagre 布局算法 - 层次化布局
    const nodeWidth = 220 // 节点宽度
    const nodeHeight = 180 // 节点高度
    const horizontalGap = 150 // 水平间距
    const verticalGap = 100 // 垂直间距
    
    // 构建图的邻接表
    const graph = new Map<string, Set<string>>()
    const inDegree = new Map<string, number>()
    
    // 初始化
    nodes.value.forEach(node => {
      graph.set(node.id, new Set())
      inDegree.set(node.id, 0)
    })
    
    // 构建邻接表和入度
    edges.value.forEach(edge => {
      const sourceId = edge.source
      const targetId = edge.target
      graph.get(sourceId)?.add(targetId)
      inDegree.set(targetId, (inDegree.get(targetId) || 0) + 1)
    })
    
    // 拓扑排序分层
    const layers: string[][] = []
    const queue: string[] = []
    const visited = new Set<string>()
    
    // 找到所有入度为 0 的节点（根节点）
    inDegree.forEach((degree, nodeId) => {
      if (degree === 0) {
        queue.push(nodeId)
      }
    })
    
    // 如果没有根节点（可能有环），随机选择一个起始节点
    if (queue.length === 0) {
      queue.push(nodes.value[0].id)
    }
    
    // BFS 分层
    while (queue.length > 0) {
      const currentLayer: string[] = []
      const nextQueue: string[] = []
      
      queue.forEach(nodeId => {
        if (visited.has(nodeId)) return
        visited.add(nodeId)
        currentLayer.push(nodeId)
        
        // 将子节点加入下一层
        graph.get(nodeId)?.forEach(childId => {
          if (!visited.has(childId)) {
            nextQueue.push(childId)
          }
        })
      })
      
      if (currentLayer.length > 0) {
        layers.push(currentLayer)
      }
      
      queue.length = 0
      queue.push(...nextQueue)
      
      // 防止死循环
      if (layers.length > nodes.value.length) break
    }
    
    // 添加未访问的节点（孤立节点）
    const unvisitedNodes = nodes.value.filter(n => !visited.has(n.id))
    if (unvisitedNodes.length > 0) {
      layers.push(unvisitedNodes.map(n => n.id))
    }
    
    // 计算每层的布局
    let currentY = 50 // 起始 Y 坐标
    const updatedNodes = [...nodes.value]
    
    layers.forEach((layer, layerIndex) => {
      const layerWidth = layer.length * (nodeWidth + horizontalGap) - horizontalGap
      const startX = Math.max(50, (window.innerWidth * 0.6 - layerWidth) / 2) // 居中
      
      layer.forEach((nodeId, index) => {
        const nodeIndex = updatedNodes.findIndex(n => n.id === nodeId)
        if (nodeIndex !== -1) {
          updatedNodes[nodeIndex] = {
            ...updatedNodes[nodeIndex],
            position: {
              x: startX + index * (nodeWidth + horizontalGap),
              y: currentY
            }
          }
        }
      })
      
      currentY += nodeHeight + verticalGap
    })
    
    // 应用新的布局
    nodes.value = updatedNodes
    
    ElMessage.success('排版完成')
  } catch (error) {
    console.error('自动排版失败:', error)
    ElMessage.error('自动排版失败')
  } finally {
    loading.close()
  }
}

// AI 自动分析关联
const handleAutoAnalyze = async () => {
  if (nodes.value.length < 2) {
    ElMessage.warning('请至少添加两个表')
    return
  }
  
  // 检查是否有 datasource_id
  if (!currentDatasourceId.value) {
    ElMessage.error('未找到数据源 ID，无法进行 AI 分析')
    return
  }
  
  isAnalyzing.value = true
  const loading = ElLoading.service({
    lock: true,
    text: '🤖 AI 正在分析表关联关系...',
    background: 'rgba(0, 0, 0, 0.7)'
  })
  
  try {
    // 获取画布上所有表名
    const tableNames = nodes.value.map(n => n.data.tableName)
    
    console.log('=== AI Analysis Debug ===')
    console.log('Table names to analyze:', tableNames)
    console.log('Datasource ID:', currentDatasourceId.value)
    console.log('Current nodes:', nodes.value)
    
    // 调用 AI 分析接口
    const result = await analyzeRelationships({
      datasource_id: currentDatasourceId.value,
      table_names: tableNames
    })
    
    console.log('AI Response:', result)
    console.log('Edges from backend:', result.edges)
    console.log('Nodes from backend:', result.nodes)
    
    // 清空现有连线
    edges.value = []
    
    // 添加 AI 分析出的连线
    if (result.edges && result.edges.length > 0) {
      // **关键修复**：后端返回的 source/target 是表名，需要转换为 Node ID
      const newEdges: Edge[] = result.edges.map((edge: RelationshipEdge, index: number) => {
        // 找到对应的 node
        const sourceNode = nodes.value.find(n => n.data.tableName === edge.source)
        const targetNode = nodes.value.find(n => n.data.tableName === edge.target)
        
        console.log(`Processing edge ${index}:`, {
          edgeSource: edge.source,
          edgeTarget: edge.target,
          foundSourceNode: sourceNode?.id,
          foundTargetNode: targetNode?.id
        })
        
        if (!sourceNode || !targetNode) {
          console.warn(`Cannot find nodes for edge:`, edge)
          return null
        }
        
        // **正确的连线格式**
        const edgeObject = {
          id: `e-${edge.source}-${edge.target}-${index}`, // 唯一 ID
          source: sourceNode.id, // 必须是 Node 的 ID，不是表名
          target: targetNode.id, // 必须是 Node 的 ID，不是表名
          label: `${edge.source_col} = ${edge.target_col}`, // 连线上显示的文字
          type: 'smoothstep', // 连线样式：阶梯线
          animated: true, // 动画效果
          style: { 
            stroke: edge.confidence === 'high' ? '#10b981' : edge.confidence === 'medium' ? '#3b82f6' : '#6b7280',
            strokeWidth: 2 
          },
          data: {
            source_col: edge.source_col,
            target_col: edge.target_col,
            type: edge.type,
            confidence: edge.confidence
          }
        }
        
        console.log(`Created edge object:`, edgeObject)
        return edgeObject
      }).filter(e => e !== null) as Edge[]
      
      console.log('Final edges to add:', newEdges)
      
      // 应用到画布
      addEdges(newEdges)
      
      console.log('Edges after addEdges:', edges.value)
      
      ElMessage.success(`✅ AI 分析完成，发现 ${newEdges.length} 个关联关系`)
      
      // 生成 SQL 预览
      generateSQL()
      
      // AI 分析后自动保存
      if (currentDatasetId.value && newEdges.length > 0) {
        setTimeout(async () => {
          await handleSave(true) // 静默保存，不显示提示
          console.log('AI 分析结果已自动保存')
        }, 1000)
      }
      
      // 提示用户调整位置
      if (newEdges.length > 0) {
        setTimeout(() => {
          ElMessage.info('连线已创建，如果节点重叠请手动调整位置')
        }, 1000)
      }
    } else {
      console.log('No edges found in response')
      ElMessage.info('未发现明显的关联关系')
    }
  } catch (error: any) {
    console.error('AI 分析失败:', error)
    console.error('Error details:', error.response?.data || error.message)
    ElMessage.error(error.message || 'AI 分析失败，请稍后重试')
  } finally {
    loading.close()
    isAnalyzing.value = false
  }
}

// 生成 SQL 预览 - 明确列出字段并去重
const generateSQL = () => {
  if (nodes.value.length === 0) {
    generatedSQL.value = ''
    return
  }
  
  // 为每个表创建别名映射
  const tableAliases = new Map<string, string>()
  const usedAliases = new Set<string>()
  
  nodes.value.forEach(node => {
    const tableName = node.data.tableName
    // 生成别名：去除前缀后取首字母，确保唯一
    let alias = tableName.replace(/^(dim_|fact_|dw_|ods_|dwd_|dws_|ads_)/i, '')
      .split('_')
      .map((part: string) => part[0])
      .join('')
      .toLowerCase()
    
    // 如果别名已存在，添加数字后缀
    let finalAlias = alias
    let counter = 1
    while (usedAliases.has(finalAlias)) {
      finalAlias = `${alias}${counter}`
      counter++
    }
    
    usedAliases.add(finalAlias)
    tableAliases.set(tableName, finalAlias)
  })
  
  // 如果没有连线，只显示第一个表的所有字段
  if (edges.value.length === 0) {
    const firstNode = nodes.value[0]
    const firstTable = firstNode.data.tableName
    const firstAlias = tableAliases.get(firstTable)!
    const fields = firstNode.data.fields.map((f: any) => `${firstAlias}.${f.name}`).join(',\n  ')
    generatedSQL.value = `SELECT \n  ${fields}\nFROM ${firstTable} ${firstAlias}\nLIMIT 100;`
    return
  }
  
  // ========== 关键修复：先构建 JOIN 子句，确定哪些表会被包含 ==========
  const firstNode = nodes.value[0]
  const firstTable = firstNode.data.tableName
  const firstAlias = tableAliases.get(firstTable)!
  
  // 已处理的表（会出现在 FROM/JOIN 子句中的表）
  const processedTables = new Set([firstTable])
  const pendingEdges = [...edges.value]
  const joinClauses: string[] = []
  
  // 循环处理所有 edge
  let maxIterations = pendingEdges.length * 2
  let iterations = 0
  
  while (pendingEdges.length > 0 && iterations < maxIterations) {
    iterations++
    let progressMade = false
    
    for (let i = pendingEdges.length - 1; i >= 0; i--) {
      const edge = pendingEdges[i]
      const sourceTable = getNodeLabel(edge.source)
      const targetTable = getNodeLabel(edge.target)
      
      let joinTable = ''
      let joinTableAlias = ''
      let joinCondition = ''
      
      if (processedTables.has(sourceTable) && !processedTables.has(targetTable)) {
        joinTable = targetTable
        joinTableAlias = tableAliases.get(targetTable)!
        const sourceAlias = tableAliases.get(sourceTable)!
        joinCondition = `${sourceAlias}.${edge.data?.source_col || 'id'} = ${joinTableAlias}.${edge.data?.target_col || 'id'}`
        processedTables.add(targetTable)
        progressMade = true
      } else if (processedTables.has(targetTable) && !processedTables.has(sourceTable)) {
        joinTable = sourceTable
        joinTableAlias = tableAliases.get(sourceTable)!
        const targetAlias = tableAliases.get(targetTable)!
        joinCondition = `${targetAlias}.${edge.data?.target_col || 'id'} = ${joinTableAlias}.${edge.data?.source_col || 'id'}`
        processedTables.add(sourceTable)
        progressMade = true
      } else if (processedTables.has(sourceTable) && processedTables.has(targetTable)) {
        // 两个表都已处理，跳过此 edge
        pendingEdges.splice(i, 1)
        progressMade = true
        continue
      } else {
        // 两个表都未处理，暂时跳过
        continue
      }
      
      if (joinTable && joinCondition) {
        const joinType = edge.data?.type === 'inner' ? 'INNER JOIN' : 'LEFT JOIN'
        joinClauses.push(`${joinType} ${joinTable} ${joinTableAlias} ON ${joinCondition}`)
        pendingEdges.splice(i, 1)
      }
    }
    
    if (!progressMade) {
      console.warn('SQL generation stalled. Remaining edges:', pendingEdges)
      // 如果有未处理的边且无法继续，说明存在孤立的子图
      // 警告用户但继续生成 SQL
      if (pendingEdges.length > 0) {
        ElMessage.warning('部分表未连接到主表，将被排除在 SQL 之外')
      }
      break
    }
  }
  
  // ========== 只为已处理的表生成字段列表 ==========
  const allFields: string[] = []
  const seenColumns = new Set<string>()
  const columnCounts = new Map<string, number>()
  
  // 第一遍：只统计已处理表的列名出现次数
  nodes.value.forEach(node => {
    const tableName = node.data.tableName
    if (!processedTables.has(tableName)) {
      return  // 跳过未连接的表
    }
    node.data.fields.forEach((field: any) => {
      columnCounts.set(field.name, (columnCounts.get(field.name) || 0) + 1)
    })
  })
  
  // 第二遍：只为已处理的表生成字段
  nodes.value.forEach(node => {
    const tableName = node.data.tableName
    if (!processedTables.has(tableName)) {
      return  // 跳过未连接的表
    }
    
    const alias = tableAliases.get(tableName)!
    
    node.data.fields.forEach((field: any) => {
      const fullField = `${alias}.${field.name}`
      if (seenColumns.has(fullField)) {
        return
      }
      seenColumns.add(fullField)
      
      // 如果列名在多个表中出现，添加表别名前缀
      if (columnCounts.get(field.name)! > 1) {
        allFields.push(`${fullField} AS ${alias}_${field.name}`)
      } else {
        allFields.push(fullField)
      }
    })
  })
  
  // 构建最终 SQL
  const selectClause = allFields.join(',\n  ')
  let sql = `SELECT \n  ${selectClause}\nFROM ${firstTable} ${firstAlias}`
  
  if (joinClauses.length > 0) {
    sql += '\n' + joinClauses.join('\n')
  }
  
  generatedSQL.value = sql
}

// 复制 SQL
const copySQL = async () => {
  try {
    await navigator.clipboard.writeText(generatedSQL.value)
    ElMessage.success('SQL 已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

// 监听 edges 变化，自动更新 SQL 预览
watch(() => edges.value.length, () => {
  if (edges.value.length > 0 && !selectedNode.value && !selectedEdge.value) {
    generateSQL()
  }
}, { deep: true })

// 生成宽表
const handleGenerateWideTable = () => {
  if (nodes.value.length === 0) {
    ElMessage.warning('请先添加表到画布')
    return
  }
  
  if (edges.value.length === 0) {
    ElMessage.warning('请先使用 AI 分析或手动创建表关联')
    return
  }
  
  // 生成 SQL
  generateSQL()
  
  // 打开 Dialog
  wideTableDialogVisible.value = true
  wideTableName.value = ''
}

// 创建视图
const handleCreateView = async () => {
  if (!wideTableName.value) {
    ElMessage.warning('请输入视图名称')
    return
  }
  
  // 验证视图名称格式
  const viewNamePattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/
  if (!viewNamePattern.test(wideTableName.value)) {
    ElMessage.error('视图名称格式不正确，只允许字母、数字和下划线')
    return
  }
  
  const loading = ElLoading.service({
    lock: true,
    text: '正在创建视图...',
    background: 'rgba(0, 0, 0, 0.7)'
  })
  
  try {
    // 提取 SQL（移除 LIMIT 子句）
    let sql = generatedSQL.value.replace(/\s*LIMIT\s+\d+\s*;?\s*$/i, '')
    
    console.log('=== Creating View Debug ===')
    console.log('Datasource ID:', currentDatasourceId.value)
    console.log('View Name:', `v_${wideTableName.value}`)
    console.log('SQL:', sql)
    
    await createView({
      datasource_id: currentDatasourceId.value,
      view_name: `v_${wideTableName.value}`,
      sql: sql
    })
    
   wideTableDialogVisible.value = false
    
    // 提示是否训练
    await ElMessageBox.confirm(
      `宽表 v_${wideTableName.value} 已创建成功!\n\n是否立即将该视图添加到数据集并开始训练?`,
      '创建成功',
      {
        confirmButtonText: '立即训练',
        cancelButtonText: '稍后再说',
        type: 'success'
      }
    )
    
    // 用户点击了"立即训练"
    if (!currentDatasetId.value) {
      ElMessage.warning('未找到数据集ID，无法开始训练')
      router.push('/datasets')
      return
    }
    
    // 更新数据集表配置（添加新创建的视图）
    try {
      // 获取当前数据集的表配置
      const dataset = await getDataset(currentDatasetId.value)
      const currentTables = dataset.schema_config || []
      const viewName = `v_${wideTableName.value}`
      
      // 如果视图不在列表中，添加进去
      if (!currentTables.includes(viewName)) {
        currentTables.push(viewName)
        await updateDatasetTables(currentDatasetId.value, currentTables)
      }
      
      // 触发训练
      await trainDataset(currentDatasetId.value)
      ElMessage.success('已触发训练')
      
      // 打开训练进度对话框
      progressDialogVisible.value = true
      
    } catch (error: any) {
      console.error('训练失败:', error)
      ElMessage.error(error?.message || '触发训练失败')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('创建视图失败:', error)
      ElMessage.error(error.message || '创建视图失败')
    }
  } finally {
    loading.close()
  }
}

// 一键生成视图名称
const handleAutoGenerateViewName = () => {
  if (nodes.value.length === 0) {
    ElMessage.warning('请先添加表到画布')
    return
  }
  
  // 获取画布上的表名
  const tableNames = nodes.value.map(n => n.data.tableName)
  
  // 生成规则：
  // 1. 如果只有 1-2 个表，直接使用表名
  // 2. 如果有 3+ 个表，使用前 2 个 + 时间戳
  // 3. 移除表前缀 (dim_, fact_, etc.)
  
  const cleanTableNames = tableNames.map(name => {
    // 移除常见前缀
    return name.replace(/^(dim_|fact_|dw_|ods_|dwd_|dws_|ads_)/i, '')
  })
  
  let viewName = ''
  
  if (cleanTableNames.length === 1) {
    viewName = cleanTableNames[0]
  } else if (cleanTableNames.length === 2) {
    viewName = `${cleanTableNames[0]}_${cleanTableNames[1]}`
  } else {
    // 取前 2 个表名 + 时间戳
    const timestamp = Date.now().toString().slice(-6)
    viewName = `${cleanTableNames[0]}_${cleanTableNames[1]}_${timestamp}`
  }
  
  // 确保符合命名规范（只允许字母、数字、下划线）
  viewName = viewName.replace(/[^a-zA-Z0-9_]/g, '_').toLowerCase()
  
  // 限制长度（除去 v_ 前缀后最长 45 个字符）
  if (viewName.length > 45) {
    viewName = viewName.substring(0, 45)
  }
  
  wideTableName.value = viewName
  ElMessage.success('视图名称已自动生成')
}

// AI 智能优化 SQL
const handleAIOptimizeSQL = async () => {
  if (!generatedSQL.value) {
    ElMessage.warning('请先生成 SQL')
    return
  }
  
  isOptimizingSQL.value = true
  sqlOptimizationTip.value = ''
  
  try {
    // 暂时使用本地优化逻辑（后续可接入后端 AI）
    ElMessage.info('🤖 AI 正在分析并优化 SQL...')
    
    // 模拟 AI 处理延迟
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // 智能优化逻辑：
    // 1. 分析当前 SQL
    const currentSQL = generatedSQL.value
    
    // 2. 检查是否使用 SELECT *
    if (currentSQL.includes('SELECT *')) {
      // 收集所有表的字段
      const allFields: string[] = []
      const tableAliasMap = new Map<string, string>()
      
      nodes.value.forEach(node => {
        const tableName = node.data.tableName
        const alias = tableName.replace(/^(dim_|fact_|dw_|ods_|dwd_|dws_|ads_)/i, '')
          .split('_')
          .map((part: string) => part[0])
          .join('')
          .toLowerCase()
        
        tableAliasMap.set(tableName, alias)
        
        // 添加所有字段（带别名）
        node.data.fields.forEach((field: any) => {
          allFields.push(`${alias}.${field.name}`)
        })
      })
      
      // 3. 生成优化后的 SQL（明确列举字段）
      const selectClause = allFields.join(',\n  ')
      const optimizedSQL = currentSQL.replace(
        'SELECT *',
        `SELECT \n  ${selectClause}`
      )
      
      generatedSQL.value = optimizedSQL
      sqlOptimizationTip.value = `✅ 已优化：将 SELECT * 替换为明确列举的 ${allFields.length} 个字段，提升查询性能并避免列名冲突`
      
      ElMessage.success('🎉 SQL 已智能优化！')
    } else {
      ElMessage.info('当前 SQL 已经是优化的形式')
      sqlOptimizationTip.value = '✅ 当前 SQL 已经明确指定了字段，无需进一步优化'
    }
  } catch (error: any) {
    console.error('AI 优化 SQL 失败:', error)
    ElMessage.error('优化失败，请稍后重试')
  } finally {
    isOptimizingSQL.value = false
  }
}

// 保存模型
const handleSave = async (isAutoSave = false) => {
  if (!currentDatasetId.value) {
    if (!isAutoSave) {
      ElMessage.error('未找到数据集 ID，无法保存')
    }
    return
  }
  
  isSaving.value = true
  
  const loading = isAutoSave ? null : ElLoading.service({
    lock: true,
    text: '正在保存建模配置...',
    background: 'rgba(0, 0, 0, 0.7)'
  })
  
  try {
    // 使用 VueFlow 的 toObject() 获取完整状态（包括 viewport）
    const flowObject = toObject()
    
    // 准备保存数据
    const modelingConfig = {
      nodes: flowObject.nodes.map(n => ({
        id: n.id,
        type: n.type,
        position: n.position,
        data: n.data
      })),
      edges: flowObject.edges.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        type: e.type,
        animated: e.animated,
        style: e.style,
        data: e.data
      })),
      viewport: flowObject.viewport // 保存视口位置和缩放
    }
    
    console.log('Saving modeling config:', modelingConfig)
    
    await updateModelingConfig(currentDatasetId.value, modelingConfig)
    
    hasUnsavedChanges.value = false
    
    if (!isAutoSave) {
      ElMessage.success('建模配置已保存')
    }
  } catch (error: any) {
    console.error('保存失败:', error)
    if (!isAutoSave) {
      ElMessage.error(error?.message || '保存失败')
    }
  } finally {
    isSaving.value = false
    loading?.close()
  }
}

// 返回
const handleBack = () => {
  router.back()
}

// 自动保存防抖计时器
let autoSaveTimer: number | null = null
const AUTO_SAVE_DELAY = 5000 // 5秒后自动保存

// 监听画布变化并触发自动保存
const scheduleAutoSave = () => {
  if (!currentDatasetId.value) return
  
  hasUnsavedChanges.value = true
  
  // 清除之前的计时器
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }
  
  // 设置新的计时器
  autoSaveTimer = setTimeout(async () => {
    if (hasUnsavedChanges.value) {
      await handleSave(true)
      console.log('自动保存完成')
    }
  }, AUTO_SAVE_DELAY)
}

// 页面加载时初始化
initFromRoute()

// 监听节点和连线的变化
onMounted(() => {
  // 监听节点变化
  onNodesChange(() => {
    scheduleAutoSave()
  })
  
  // 监听连线变化
  onEdgesChange(() => {
    scheduleAutoSave()
  })
  
  console.log('已启用自动保存（变化后 5 秒自动保存）')
})

// 清理计时器
onUnmounted(() => {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }
})
</script>

<style scoped>
.modeling-page {
  font-family: 'Inter', system-ui, sans-serif;
}

.vue-flow-canvas {
  background-color: rgb(249 250 251);
}

.dark .vue-flow-canvas {
  background-color: rgb(15 23 42);
}

/* 自定义滚动条 */
.table-list::-webkit-scrollbar,
.properties-content::-webkit-scrollbar {
  width: 6px;
}

.table-list::-webkit-scrollbar-thumb,
.properties-content::-webkit-scrollbar-thumb {
  background-color: rgba(156, 163, 175, 0.5);
  border-radius: 3px;
}

.dark .table-list::-webkit-scrollbar-thumb,
.dark .properties-content::-webkit-scrollbar-thumb {
  background-color: rgba(100, 116, 139, 0.5);
}
</style>
