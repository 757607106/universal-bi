# 前端集成指南 - 智能问答功能升级

## 已完成的组件和 API

### 1. InputSuggestion 组件
- 文件：`src/components/InputSuggestion.vue`
- 功能：实时输入联想
- 用法示例：

```vue
<template>
  <div class="relative">
    <el-input v-model="inputMessage" @focus="showSuggestion = true" />
    <InputSuggestion
      :dataset-id="currentDatasetId"
      :input-value="inputMessage"
      :show="showSuggestion"
      @select="handleSuggestionSelect"
      @close="showSuggestion = false"
    />
  </div>
</template>

<script setup>
import InputSuggestion from '@/components/InputSuggestion.vue'

const showSuggestion = ref(false)
const handleSuggestionSelect = (suggestion) => {
  inputMessage.value = suggestion
  showSuggestion.value = false
}
</script>
```

### 2. API 函数
- 文件：`src/api/chat.ts`
- 新增接口：
  - `suggestInput()` - 输入联想
  - `suggestFollowup()` - 后续推荐问题
  - `exportEnhanced()` - 增强导出
- 扩展类型：
  - `DataInterpretation` - 数据解读
  - `FluctuationAnalysis` - 波动归因
  - `ChatResponse` 已扩展包含新字段

## 需要在 Chat/index.vue 中集成的功能

### 1. 集成输入联想

在输入区域（约第 332 行）：

```vue
<!-- 修改输入区域为相对定位 -->
<div class="p-4 pb-8 bg-transparent flex-shrink-0 flex justify-center z-20">
  <div class="w-full max-w-4xl relative"> <!-- 添加 relative -->
    <div class="bg-white dark:bg-slate-800 rounded-full ...">
      <el-input
        v-model="inputMessage"
        @focus="showSuggestion = true"
        @blur="() => setTimeout(() => showSuggestion = false, 200)"
        ...
      />
      ...
    </div>
    
    <!-- 添加输入联想组件 -->
    <InputSuggestion
      :dataset-id="currentDatasetId"
      :input-value="inputMessage"
      :show="showSuggestion"
      @select="handleSuggestionSelect"
    />
  </div>
</div>
```

在 script 中添加：

```typescript
import InputSuggestion from '@/components/InputSuggestion.vue'

const showSuggestion = ref(false)

const handleSuggestionSelect = (suggestion: string) => {
  inputMessage.value = suggestion
  showSuggestion.value = false
}
```

### 2. 展示数据解读和波动归因

在 AI 消息卡片中（约第 111-325 行），在图表下方添加：

```vue
<!-- 数据解读 -->
<div v-if="msg.dataInterpretation" class="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
  <h4 class="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2 flex items-center gap-2">
    <el-icon><DataAnalysis /></el-icon>
    数据解读
  </h4>
  <p class="text-sm text-gray-700 dark:text-gray-300 mb-2">{{ msg.dataInterpretation.summary }}</p>
  
  <div v-if="msg.dataInterpretation.key_findings && msg.dataInterpretation.key_findings.length > 0" class="mt-2">
    <p class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">关键发现：</p>
    <ul class="text-xs text-gray-600 dark:text-gray-400 space-y-1">
      <li v-for="(finding, idx) in msg.dataInterpretation.key_findings" :key="idx" class="flex items-start gap-1">
        <span>•</span>
        <span>{{ finding }}</span>
      </li>
    </ul>
  </div>
  
  <div v-if="msg.dataInterpretation.quality_score" class="mt-2 text-xs text-gray-500 dark:text-gray-400">
    数据质量评分：{{ msg.dataInterpretation.quality_score }}/100
  </div>
</div>

<!-- 波动归因 -->
<div v-if="msg.fluctuationAnalysis?.has_fluctuation" class="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
  <h4 class="text-sm font-semibold text-amber-900 dark:text-amber-300 mb-2 flex items-center gap-2">
    <el-icon><TrendCharts /></el-icon>
    波动归因分析
  </h4>
  
  <p v-if="msg.fluctuationAnalysis.attribution?.detailed_analysis" class="text-sm text-gray-700 dark:text-gray-300 mb-2">
    {{ msg.fluctuationAnalysis.attribution.detailed_analysis }}
  </p>
  
  <div v-if="msg.fluctuationAnalysis.attribution?.main_factors && msg.fluctuationAnalysis.attribution.main_factors.length > 0" class="mt-2">
    <p class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">主要因素：</p>
    <ul class="text-xs text-gray-600 dark:text-gray-400 space-y-1">
      <li v-for="(factor, idx) in msg.fluctuationAnalysis.attribution.main_factors" :key="idx" class="flex items-start gap-1">
        <span>•</span>
        <span>{{ factor }}</span>
      </li>
    </ul>
  </div>
</div>
```

### 3. 猜你想问功能

在 AI 消息卡片底部（操作按钮区域后）添加：

```vue
<!-- 猜你想问 -->
<div v-if="msg.followupQuestions && msg.followupQuestions.length > 0 && !msg.loading" class="mt-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
  <h4 class="text-sm font-semibold text-purple-900 dark:text-purple-300 mb-3 flex items-center gap-2">
    <el-icon><QuestionFilled /></el-icon>
    猜你想问
  </h4>
  <div class="flex flex-wrap gap-2">
    <el-button
      v-for="(question, idx) in msg.followupQuestions"
      :key="idx"
      size="small"
      plain
      @click="handleFollowupQuestion(question)"
      class="!bg-white dark:!bg-slate-800 !border-purple-200 dark:!border-purple-700 !text-purple-700 dark:!text-purple-300 hover:!bg-purple-50 dark:hover:!bg-purple-900/30"
    >
      {{ question }}
    </el-button>
  </div>
</div>
```

在 script 中添加：

```typescript
const handleFollowupQuestion = (question: string) => {
  inputMessage.value = question
  handleSend()
}
```

### 4. 导出功能

在操作按钮区域添加导出按钮：

```vue
<!-- 导出按钮 -->
<el-dropdown @command="(format: string) => handleExport(msg, format)">
  <el-button
    size="small"
    class="!bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-700 !text-gray-600 dark:!text-slate-300"
  >
    <template #icon>
      <el-icon><Download /></el-icon>
    </template>
    导出
  </el-button>
  <template #dropdown>
    <el-dropdown-menu>
      <el-dropdown-item command="excel">Excel</el-dropdown-item>
      <el-dropdown-item command="excel_with_chart">Excel（含图表）</el-dropdown-item>
      <el-dropdown-item command="pdf">PDF 报告</el-dropdown-item>
      <el-dropdown-item command="csv">CSV</el-dropdown-item>
    </el-dropdown-menu>
  </template>
</el-dropdown>
```

在 script 中添加：

```typescript
import { exportEnhanced } from '@/api/chat'

const handleExport = async (msg: Message, format: string) => {
  if (!msg.chartData?.rows || !msg.chartData?.columns) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  
  try {
    ElMessage.info('正在导出...')
    
    const blob = await exportEnhanced({
      question: msg.question || '',
      sql: msg.sql,
      columns: msg.chartData.columns,
      rows: msg.chartData.rows,
      chart_type: msg.chartType || 'table',
      insight: msg.content,
      data_interpretation: msg.dataInterpretation,
      fluctuation_analysis: msg.fluctuationAnalysis,
      format: format as any
    })
    
    // 下载文件
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    const ext = format === 'pdf' ? 'pdf' : format === 'csv' ? 'csv' : 'xlsx'
    link.download = `分析结果_${Date.now()}.${ext}`
    link.click()
    
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('Export failed:', error)
    ElMessage.error('导出失败')
  }
}
```

### 5. 更新 Message 接口

在 script 中更新 Message 接口：

```typescript
interface Message {
  type: 'user' | 'ai'
  content?: string
  sql?: string
  chartData?: { columns: string[] | null; rows: any[] | null }
  chartType?: string
  alternativeCharts?: string[]
  loading?: boolean
  error?: boolean
  question?: string
  datasetId?: number
  steps?: string[]
  isCached?: boolean
  isSystemError?: boolean
  feedbackGiven?: 'like' | 'dislike'
  regenerating?: boolean
  // 新增字段
  dataInterpretation?: {
    summary: string
    key_findings: string[]
    statistics: Record<string, any>
    quality_score?: number
  }
  fluctuationAnalysis?: {
    has_fluctuation: boolean
    fluctuation_points?: any[]
    attribution?: {
      main_factors?: string[]
      detailed_analysis?: string
    }
    chart_recommendation?: string
  }
  followupQuestions?: string[]
}
```

### 6. 更新 handleSend 函数

在 handleSend 中保存响应的新字段：

```typescript
const response = await sendChat({
  dataset_id: currentDatasetId.value,
  question,
  use_cache: true,
  conversation_history: conversationHistory
})

// ... 现有代码 ...

// 保存新增字段
messages.value[aiMsgIndex].dataInterpretation = response.data_interpretation
messages.value[aiMsgIndex].fluctuationAnalysis = response.fluctuation_analysis
messages.value[aiMsgIndex].followupQuestions = response.followup_questions
```

## 数据集页面快速分析入口

在 `frontend/src/views/Dataset/index.vue` 中，在数据集卡片的操作按钮区域添加：

```vue
<el-button
  size="small"
  @click="handleQuickAnalysis(dataset)"
  class="!bg-green-50 dark:!bg-green-500/10 !border-green-200 dark:!border-green-500/50 !text-green-600 dark:!text-green-400 hover:!bg-green-100 dark:hover:!bg-green-500/20"
>
  <el-icon class="mr-1"><Lightning /></el-icon>
  快速分析
</el-button>
```

在 script 中添加：

```typescript
import { useRouter } from 'vue-router'

const router = useRouter()

const handleQuickAnalysis = (dataset: any) => {
  // 跳转到 Chat 页面并自动选择该数据集
  router.push({
    name: 'Chat',
    query: { dataset_id: dataset.id }
  })
}
```

## 注意事项

1. 确保所有新增的图标已在 imports 中导入
2. 测试暗色模式的样式
3. 添加 lodash-es 依赖：`npm install lodash-es`
4. 所有新功能都有降级处理，不会影响现有功能
5. API 调用失败时会返回空数组或 null，前端需要做好空值判断
