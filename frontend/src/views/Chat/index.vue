<template>
  <div class="h-full flex flex-col bg-transparent relative">
    <!-- Header / Toolbar -->
    <div class="h-16 border-b border-gray-200 dark:border-slate-700/50 bg-white/50 dark:bg-transparent px-6 flex items-center justify-between flex-shrink-0 z-10 transition-colors">
      <div class="flex items-center gap-4">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-slate-100 flex items-center gap-2 transition-colors">
          <el-icon class="text-blue-600 dark:text-cyan-500"><ChatDotRound /></el-icon>
          ChatBI
        </h2>
        
        <!-- 数据源类型选择 -->
        <el-radio-group v-model="sourceType" size="small" @change="handleSourceTypeChange">
          <el-radio-button value="dataset">数据集</el-radio-button>
          <el-radio-button value="datatable">数据表</el-radio-button>
        </el-radio-group>
        
        <!-- 数据集选择器 -->
        <el-select
          v-if="sourceType === 'dataset'"
          v-model="currentDatasetId"
          placeholder="请选择数据集"
          class="w-64"
          :loading="loadingDatasets"
          :effect="'light'"
        >
          <el-option
            v-for="item in datasets"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
        
        <!-- 数据表选择器 -->
        <el-select
          v-else
          v-model="currentDataTableId"
          placeholder="请选择数据表"
          class="w-64"
          :loading="loadingDataTables"
          :effect="'light'"
          filterable
          @change="handleDataTableChange"
        >
          <el-option
            v-for="item in dataTables"
            :key="item.id"
            :label="item.display_name"
            :value="item.id"
          >
            <span class="flex items-center justify-between w-full">
              <span>{{ item.display_name }}</span>
              <div class="flex gap-1">
                <el-tag v-if="item.creation_method === 'excel_upload'" size="small" type="success">上传</el-tag>
                <el-tag v-if="!hasMatchingDataset(item)" size="small" type="warning">无数据集</el-tag>
              </div>
            </span>
          </el-option>
        </el-select>
      </div>
      <el-button @click="clearMessages" plain size="small" class="!bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-700 !text-gray-600 dark:!text-slate-300 hover:!bg-gray-100 dark:hover:!bg-slate-700 !rounded-lg transition-colors">
        <el-icon class="mr-1"><Delete /></el-icon> 清空对话
      </el-button>
    </div>

    <!-- Warning Banner for Missing Dataset -->
    <div 
      v-if="sourceType === 'datatable' && currentDataTableId && dataTables.find(t => t.id === currentDataTableId) && !hasMatchingDataset(dataTables.find(t => t.id === currentDataTableId)!)"
      class="bg-orange-50 dark:bg-orange-900/20 border-b border-orange-200 dark:border-orange-800/50 px-6 py-3 flex-shrink-0"
    >
      <div class="flex items-start gap-3 max-w-5xl mx-auto">
        <el-icon class="text-orange-500 dark:text-orange-400 text-xl flex-shrink-0 mt-0.5"><Warning /></el-icon>
        <div class="flex-1">
          <p class="text-sm text-orange-800 dark:text-orange-300 font-medium">该数据表的数据集正在训练中或尚未创建</p>
          <div class="text-xs text-orange-700 dark:text-orange-400 mt-1.5">
            <p class="mb-1">可能原因：</p>
            <ul class="list-disc ml-5 space-y-0.5">
              <li>数据集正在后台训练中，请稍等 1-2 分钟后刷新页面</li>
              <li>如果是旧数据表，请前往「数据集」页面手动创建并训练数据集</li>
            </ul>
          </div>
        </div>
        <el-button 
          size="small" 
          type="warning" 
          plain
          @click="router.push('/dataset')"
          class="flex-shrink-0"
        >
          前往数据集
        </el-button>
      </div>
    </div>

    <!-- Chat Area -->
    <div class="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth" ref="chatContainer">
      <!-- Empty State -->
      <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center">
        <div class="text-center mb-10">
          <div class="w-20 h-20 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl mx-auto flex items-center justify-center mb-6 shadow-lg shadow-blue-500/20">
            <el-icon class="text-4xl text-white"><DataAnalysis /></el-icon>
          </div>
          <h1 class="text-3xl font-bold text-gray-900 dark:text-slate-100 mb-3 transition-colors">ChatBI 智能分析助手</h1>
          <p class="text-gray-500 dark:text-slate-400 max-w-md mx-auto transition-colors">选择下方推荐指令或直接输入问题，开始探索您的数据价值。</p>
        </div>
        
        <!-- Recommendation Cards -->
        <div class="grid grid-cols-2 gap-4 w-full max-w-3xl">
          <div 
            v-for="(card, index) in recommendCards" 
            :key="index"
            @click="handleCardClick(card)"
            class="group p-5 border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 rounded-xl cursor-pointer transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/10 dark:hover:shadow-[0_0_20px_rgba(6,182,212,0.15)] hover:border-blue-400 dark:hover:border-cyan-500/50 hover:-translate-y-1"
          >
            <div class="flex items-start gap-4">
              <div class="p-3 rounded-lg bg-gray-100 dark:bg-slate-700/50 group-hover:bg-blue-50 dark:group-hover:bg-cyan-500/20 group-hover:text-blue-500 dark:group-hover:text-cyan-400 text-gray-400 dark:text-slate-400 transition-colors">
                <component :is="card.icon" class="w-6 h-6" />
              </div>
              <div>
                <h3 class="font-medium text-gray-900 dark:text-slate-200 mb-1 group-hover:text-blue-600 dark:group-hover:text-cyan-400 transition-colors">{{ card.title }}</h3>
                <p class="text-xs text-gray-500 dark:text-slate-500 leading-relaxed">{{ card.desc }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Messages -->
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['flex gap-5 max-w-5xl mx-auto', msg.type === 'user' ? 'flex-row-reverse' : '']"
      >
        <!-- Avatar -->
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm mt-1 transition-colors"
          :class="msg.type === 'user' ? 'bg-blue-600 text-white shadow-blue-500/20' : 'bg-white dark:bg-slate-800 text-blue-600 dark:text-cyan-400 border border-gray-200 dark:border-slate-700'"
        >
          <el-icon v-if="msg.type === 'user'"><User /></el-icon>
          <el-icon v-else size="20"><Monitor /></el-icon>
        </div>

        <!-- Content -->
        <div class="flex-1 min-w-0 max-w-[85%]">
          <!-- Text Bubble -->
          <div
            :class="[
              'text-sm transition-all relative',
              msg.type === 'user'
                ? 'bg-blue-600 text-white p-4 rounded-3xl rounded-tr-sm shadow-md shadow-blue-500/10'
                : 'bg-white dark:bg-slate-800 text-gray-800 dark:text-slate-200 p-6 rounded-3xl rounded-tl-sm border border-gray-200 dark:border-slate-700 shadow-sm'
            ]"
          >
            <!-- 缓存标识：只在 AI 回复且缓存命中时显示 -->
            <div v-if="msg.type === 'ai' && msg.isCached && !msg.loading" class="absolute top-2 right-2 flex items-center gap-1.5 px-2.5 py-1 bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-900/30 dark:to-amber-900/30 rounded-full border border-yellow-200 dark:border-yellow-700/50 shadow-sm">
              <el-icon class="text-yellow-500 dark:text-yellow-400 text-sm"><Lightning /></el-icon>
              <span class="text-[10px] font-semibold text-yellow-700 dark:text-yellow-400 uppercase tracking-wide">Cached</span>
            </div>
            <div v-if="msg.loading" class="space-y-3">
              <!-- Fake Loading Steps -->
              <div class="flex items-center gap-2 text-gray-500 dark:text-slate-400">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span class="font-medium">{{ currentLoadingStep }}</span>
              </div>
              <div class="space-y-2 pl-6">
                <div v-for="(step, idx) in loadingSteps" :key="idx" class="flex items-center gap-2 text-xs">
                  <el-icon v-if="idx < currentLoadingStepIndex" class="text-emerald-500"><Check /></el-icon>
                  <el-icon v-else-if="idx === currentLoadingStepIndex" class="is-loading text-blue-500"><Loading /></el-icon>
                  <el-icon v-else class="text-gray-400 dark:text-slate-600"><Clock /></el-icon>
                  <span :class="idx <= currentLoadingStepIndex ? 'text-gray-600 dark:text-slate-300' : 'text-gray-400 dark:text-slate-500'">
                    {{ step }}
                  </span>
                </div>
              </div>
            </div>
            
            <div v-else>
              <!-- Error Message (仅显示真正的系统错误) -->
              <div v-if="msg.error && msg.isSystemError" class="flex items-start gap-3 p-4 bg-red-900/20 border border-red-800 rounded-xl">
                <el-icon class="text-red-500 text-xl mt-0.5 flex-shrink-0">
                  <Warning />
                </el-icon>
                <div class="flex-1">
                  <p class="text-sm font-medium text-red-400 mb-1">系统错误</p>
                  <p class="text-sm text-red-300">{{ msg.content }}</p>
                </div>
              </div>

              <!-- Normal Content -->
              <div v-else class="space-y-4">
                <!-- Clarification Request -->
                <div v-if="msg.chartType === 'clarification'" class="space-y-3">
                  <!-- 纯文本消息，自然风格 -->
                  <div class="text-sm text-gray-800 dark:text-slate-100 whitespace-pre-wrap leading-relaxed">
                    {{ msg.content }}
                  </div>
                  
                  <!-- Quick Reply Suggestions -->
                  <div v-if="getClarificationSuggestions(msg.content || '').length > 0" class="space-y-2 pt-2">
                    <p class="text-xs text-gray-500 dark:text-slate-500 font-medium">✨ 快捷回复：</p>
                    <div class="flex flex-wrap gap-2">
                      <el-tag
                        v-for="(suggestion, idx) in getClarificationSuggestions(msg.content || '')"
                        :key="idx"
                        type="info"
                        effect="plain"
                        size="default"
                        class="cursor-pointer !bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-600 !text-gray-600 dark:!text-slate-300 hover:!bg-gray-50 dark:hover:!bg-slate-700 hover:!border-blue-300 dark:hover:!border-slate-500 transition-all duration-200"
                        @click="handleQuickReply(suggestion)"
                      >
                        {{ suggestion }}
                      </el-tag>
                    </div>
                  </div>
                </div>
                
                <!-- Thinking Steps (Real) -->
                <div v-if="msg.steps && msg.steps.length > 0" class="mb-4">
                  <el-collapse class="thinking-steps-collapse border-none" v-model="activeCollapse">
                    <el-collapse-item :name="`step-${index}`">
                      <template #title>
                        <div class="flex items-center gap-2 text-xs py-1 px-2 rounded hover:bg-gray-100 dark:hover:bg-slate-800/50 transition-colors cursor-pointer">
                          <el-icon class="text-blue-500 dark:text-cyan-500"><Operation /></el-icon>
                          <span class="font-medium text-gray-500 dark:text-slate-400">
                            {{ getStepsSummary(msg.steps) }}
                          </span>
                        </div>
                      </template>
                      <div class="space-y-2 text-xs p-3 bg-gray-50 dark:bg-slate-900/50 rounded-lg border border-gray-100 dark:border-slate-800 mt-2">
                        <div
                          v-for="(step, idx) in msg.steps"
                          :key="idx"
                          class="flex items-start gap-2 py-1"
                        >
                          <el-icon
                            :class="getStepIconClass(step)"
                            class="mt-0.5 flex-shrink-0"
                          >
                            <component :is="getStepIcon(step)" />
                          </el-icon>
                          <span
                            :class="getStepTextClass(step)"
                          >
                            {{ step }}
                          </span>
                        </div>
                      </div>
                    </el-collapse-item>
                  </el-collapse>
                </div>

                <p v-if="msg.content && msg.chartType !== 'clarification'" class="whitespace-pre-wrap text-gray-800 dark:text-slate-200 leading-relaxed">{{ msg.content }}</p>
                
                <!-- 结果摘要（仅显示单数据结果） -->
                <div v-if="msg.chartData && msg.chartData.rows && msg.chartData.rows.length === 1 && msg.chartType !== 'clarification'" class="my-4 p-5 bg-gray-50 dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 shadow-inner">
                  <div class="flex items-center gap-2 mb-2">
                    <el-icon class="text-blue-500 dark:text-cyan-500"><CircleCheck /></el-icon>
                    <span class="text-sm font-medium text-gray-500 dark:text-slate-400">查询结果</span>
                  </div>
                  <div class="text-2xl font-bold text-gray-900 dark:text-slate-100">
                    {{ formatSingleResult(msg.chartData) }}
                  </div>
                </div>
                
                <!-- Chart -->
                <div v-if="msg.chartData && msg.chartData.columns && msg.chartData.rows && msg.chartData.rows.length > 0" class="space-y-2">
                  <!-- 图表工具栏 -->
                  <div class="flex items-center justify-between px-2 py-1">
                    <!-- 图表类型切换 -->
                    <div v-if="msg.alternativeCharts && msg.alternativeCharts.length > 0" class="flex items-center gap-2">
                      <span class="text-xs text-gray-500 dark:text-slate-400">切换图表：</span>
                      <el-button
                        v-for="chartType in msg.alternativeCharts"
                        :key="chartType"
                        size="small"
                        :type="msg.chartType === chartType ? 'primary' : 'default'"
                        @click="handleChangeChartType(index, chartType)"
                        class="!text-xs"
                      >
                        {{ getChartTypeName(chartType) }}
                      </el-button>
                    </div>
                    <div v-else></div>
                    
                    <!-- 导出按钮 -->
                    <div class="flex items-center gap-2">
                      <el-dropdown @command="(cmd) => handleExport(msg, cmd)" trigger="click">
                        <el-button size="small" class="!text-xs">
                          <el-icon class="mr-1"><Download /></el-icon>
                          导出数据
                        </el-button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item command="excel">
                              <el-icon><Document /></el-icon>
                              导出为 Excel
                            </el-dropdown-item>
                            <el-dropdown-item command="csv">
                              <el-icon><Document /></el-icon>
                              导出为 CSV
                            </el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                      </el-dropdown>
                    </div>
                  </div>
                  
                  <div class="h-80 w-full bg-white dark:bg-slate-900 rounded-xl p-4 border border-gray-200 dark:border-slate-800 shadow-inner overflow-hidden">
                     <DynamicChart
                       :chart-type="msg.chartType || 'table'"
                       :data="{ columns: msg.chartData.columns, rows: msg.chartData.rows }"
                     />
                  </div>
                  
                  <!-- AI Insight Section (分析师 Agent) -->
                  <div v-if="msg.insight" class="bg-gradient-to-r from-blue-50/50 to-cyan-50/50 dark:from-slate-900/50 dark:to-slate-800/50 rounded-xl p-4 border border-blue-200/50 dark:border-slate-700/50">
                    <div class="flex items-center gap-2 text-blue-600 dark:text-cyan-400 mb-2">
                      <el-icon class="text-lg"><DataAnalysis /></el-icon>
                      <span class="text-xs font-semibold uppercase tracking-wide">智能分析</span>
                    </div>
                    <div class="text-sm text-gray-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                      {{ msg.insight }}
                    </div>
                  </div>
                  
                  <!-- Data Interpretation Section (数据解读) -->
                  <div v-if="msg.dataInterpretation" class="bg-gradient-to-r from-purple-50/50 to-pink-50/50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-xl p-4 border border-purple-200/50 dark:border-purple-700/50">
                    <div class="flex items-center gap-2 text-purple-600 dark:text-purple-400 mb-3">
                      <el-icon class="text-lg"><TrendCharts /></el-icon>
                      <span class="text-xs font-semibold uppercase tracking-wide">数据解读</span>
                    </div>
                    <div class="space-y-2">
                      <p class="text-sm text-gray-700 dark:text-slate-300 leading-relaxed">{{ msg.dataInterpretation.summary }}</p>
                      <div v-if="msg.dataInterpretation.key_findings && msg.dataInterpretation.key_findings.length > 0">
                        <p class="text-xs text-gray-500 dark:text-slate-400 font-medium mb-1">关键发现：</p>
                        <ul class="space-y-1">
                          <li v-for="(finding, idx) in msg.dataInterpretation.key_findings" :key="idx" class="text-sm text-gray-600 dark:text-slate-400 flex items-start gap-2">
                            <span class="text-purple-500 dark:text-purple-400">•</span>
                            <span>{{ finding }}</span>
                          </li>
                        </ul>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Fluctuation Analysis Section (波动归因) -->
                  <div v-if="msg.fluctuationAnalysis && msg.fluctuationAnalysis.has_fluctuation" class="bg-gradient-to-r from-orange-50/50 to-red-50/50 dark:from-orange-900/20 dark:to-red-900/20 rounded-xl p-4 border border-orange-200/50 dark:border-orange-700/50">
                    <div class="flex items-center gap-2 text-orange-600 dark:text-orange-400 mb-3">
                      <el-icon class="text-lg"><Warning /></el-icon>
                      <span class="text-xs font-semibold uppercase tracking-wide">波动归因分析</span>
                    </div>
                    <div class="space-y-2">
                      <div v-if="msg.fluctuationAnalysis.attribution">
                        <p class="text-sm text-gray-700 dark:text-slate-300 leading-relaxed mb-2">
                          {{ msg.fluctuationAnalysis.attribution.detailed_analysis }}
                        </p>
                        <div v-if="msg.fluctuationAnalysis.attribution.main_factors && msg.fluctuationAnalysis.attribution.main_factors.length > 0">
                          <p class="text-xs text-gray-500 dark:text-slate-400 font-medium mb-1">主要因素：</p>
                          <div class="flex flex-wrap gap-2">
                            <el-tag
                              v-for="(factor, idx) in msg.fluctuationAnalysis.attribution.main_factors"
                              :key="idx"
                              type="warning"
                              effect="plain"
                              size="small"
                            >
                              {{ factor }}
                            </el-tag>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Followup Questions Section (猜你想问) -->
                  <div v-if="msg.followupQuestions && msg.followupQuestions.length > 0" class="bg-gradient-to-r from-green-50/50 to-teal-50/50 dark:from-green-900/20 dark:to-teal-900/20 rounded-xl p-4 border border-green-200/50 dark:border-green-700/50">
                    <div class="flex items-center gap-2 text-green-600 dark:text-green-400 mb-3">
                      <el-icon class="text-lg"><QuestionFilled /></el-icon>
                      <span class="text-xs font-semibold uppercase tracking-wide">猜你想问</span>
                    </div>
                    <div class="flex flex-wrap gap-2">
                      <el-tag
                        v-for="(question, idx) in msg.followupQuestions"
                        :key="idx"
                        type="success"
                        effect="plain"
                        size="default"
                        class="cursor-pointer hover:!bg-green-100 dark:hover:!bg-green-900/30 transition-colors"
                        @click="handleFollowupQuestionClick(question)"
                      >
                        {{ question }}
                      </el-tag>
                    </div>
                  </div>
                  
                  <!-- Save to Dashboard Button -->
                  <div class="flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                    <el-button
                      size="small"
                      @click="handleSaveToDashboard(msg, index)"
                      :icon="DocumentAdd"
                      class="!bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-700 !text-gray-600 dark:!text-slate-300 hover:!bg-gray-50 dark:hover:!bg-slate-700 !rounded-md"
                    >
                      保存到看板
                    </el-button>
                  </div>
                </div>

                <!-- SQL Collapse -->
                <el-collapse v-if="msg.sql" class="border-t-0 mt-2">
                  <el-collapse-item name="1">
                    <template #title>
                        <span class="text-xs text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 transition-colors">查看 SQL 详情</span>
                    </template>
                    <div class="bg-gray-50 dark:bg-slate-950 text-gray-600 dark:text-slate-300 p-4 rounded-xl font-mono text-xs overflow-x-auto border border-gray-200 dark:border-slate-800 shadow-inner">
                      {{ msg.sql }}
                    </div>
                    
                    <!-- Feedback Buttons -->
                    <div class="flex items-center gap-3 mt-3 pt-3 border-t border-gray-100 dark:border-slate-800">
                      <span class="text-xs text-gray-400 dark:text-slate-500">结果评价：</span>
                      <div class="flex gap-2">
                        <el-button
                            size="small"
                            :type="msg.feedbackGiven === 'like' ? 'success' : 'default'"
                            :disabled="msg.feedbackGiven !== undefined"
                            @click="handleLikeFeedback(msg, index)"
                            circle
                            class="!bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-700 !text-gray-400 dark:!text-slate-400 hover:!text-green-500 dark:hover:!text-green-400 hover:!border-green-200 dark:hover:!border-green-500/50"
                        >
                            <el-icon><Select /></el-icon>
                        </el-button>
                        <el-button
                            size="small"
                            :type="msg.feedbackGiven === 'dislike' ? 'danger' : 'default'"
                            :disabled="msg.feedbackGiven !== undefined"
                            @click="handleDislikeFeedback(msg, index)"
                            circle
                            class="!bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-700 !text-gray-400 dark:!text-slate-400 hover:!text-red-500 dark:hover:!text-red-400 hover:!border-red-200 dark:hover:!border-red-500/50"
                        >
                            <el-icon><CloseBold /></el-icon>
                        </el-button>
                        <!-- 重新生成按钮 -->
                        <el-button
                            size="small"
                            @click="handleRegenerate(msg, index)"
                            :loading="msg.regenerating"
                            class="!bg-white dark:!bg-slate-800 !border-gray-200 dark:!border-slate-700 !text-gray-400 dark:!text-slate-400 hover:!text-blue-500 dark:hover:!text-cyan-400 hover:!border-blue-200 dark:hover:!border-cyan-500/50"
                        >
                            <template #icon>
                              <el-icon><Refresh /></el-icon>
                            </template>
                            重新生成
                        </el-button>
                      </div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="p-4 pb-8 bg-transparent flex-shrink-0 flex justify-center z-20">
      <div class="w-full max-w-4xl bg-white dark:bg-slate-800 rounded-full shadow-xl dark:shadow-black/50 border border-gray-300 dark:border-slate-700/50 p-2 pl-6 flex items-center gap-4 transition-all hover:border-blue-400 dark:hover:border-slate-600">
        <el-autocomplete
          v-model="inputMessage"
          :placeholder="inputPlaceholder"
          @keyup.enter="handleSend"
          :disabled="!isDataSourceSelected || sending"
          :fetch-suggestions="fetchInputSuggestions"
          :debounce="300"
          :trigger-on-focus="false"
          class="flex-1 custom-chat-input"
          @select="handleSuggestionSelect"
          popper-class="chat-suggestion-popper"
          clearable
        >
          <template #prefix>
            <el-icon class="text-gray-400 dark:text-slate-400"><Search /></el-icon>
          </template>
          <template #default="{ item }">
            <div class="suggestion-item flex items-center gap-2 py-1">
              <el-icon class="text-blue-500 dark:text-cyan-500"><QuestionFilled /></el-icon>
              <span class="text-sm">{{ item.value }}</span>
            </div>
          </template>
        </el-autocomplete>
        <el-button
          type="primary"
          @click="handleSend"
          :loading="sending"
          :disabled="!isDataSourceSelected || !inputMessage.trim()"
          class="!rounded-full px-8 !bg-gradient-to-r !from-blue-600 !to-cyan-600 !border-none hover:!opacity-90 hover:!shadow-lg hover:!shadow-blue-500/20 dark:hover:!shadow-cyan-500/20 transition-all"
        >
          发送
        </el-button>
      </div>
    </div>

    <!-- Save to Dashboard Dialog -->
    <el-dialog
      v-model="saveToDashboardDialog"
      title="保存到看板"
      width="500px"
      class="custom-dialog"
    >
      <el-form label-width="100px">
        <el-form-item label="卡片标题">
          <el-input v-model="cardTitle" placeholder="请输入卡片标题" />
        </el-form-item>
        
        <el-form-item label="选择看板" v-if="!showNewDashboardInput">
          <div class="w-full space-y-2">
            <el-select v-model="selectedDashboardId" placeholder="选择已有看板" class="w-full">
              <el-option
                v-for="dashboard in dashboards"
                :key="dashboard.id"
                :label="dashboard.name"
                :value="dashboard.id"
              />
            </el-select>
            <el-button @click="handleCreateNewDashboard" size="small" class="w-full">
              + 新建看板
            </el-button>
          </div>
        </el-form-item>
        
        <el-form-item label="看板名称" v-if="showNewDashboardInput">
          <el-input v-model="newDashboardName" placeholder="请输入新看板名称" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="handleCancelSave">取消</el-button>
        <el-button type="primary" @click="handleConfirmSave" :loading="savingCard">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- SQL Correction Dialog -->
    <el-dialog
      v-model="sqlCorrectionDialog"
      title="修正 SQL"
      width="700px"
      class="custom-dialog"
    >
      <div class="space-y-4">
        <div>
          <p class="text-sm text-slate-400 mb-2">请修改下方的 SQL 查询，然后提交给 AI 学习：</p>
          <el-input
            v-model="correctedSql"
            type="textarea"
            :rows="10"
            placeholder="输入正确的 SQL..."
            class="font-mono text-sm"
          />
        </div>
        <el-alert
          title="提示"
          type="info"
          :closable="false"
          show-icon
        >
          AI 会学习你提供的正确 SQL，下次遇到类似问题时会更准确。
        </el-alert>
      </div>
      
      <template #footer>
        <el-button @click="handleCancelCorrection">取消</el-button>
        <el-button type="primary" @click="handleSubmitCorrection" :loading="submittingFeedback">
          提交修正
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  User,
  Monitor,
  Delete,
  Search,
  Loading,
  Warning,
  DocumentAdd,
  Check,
  Clock,
  Operation,
  CircleCheck,
  WarningFilled,
  QuestionFilled,
  Select,
  CloseBold,
  TrendCharts,
  PieChart,
  DataLine,
  DataBoard,
  DataAnalysis,
  Lightning,
  Refresh,
  Download,
  Document
} from '@element-plus/icons-vue'
import { getDatasetList, type Dataset } from '@/api/dataset'
import { sendChat, submitFeedback, generateSummary, exportToExcel, exportToCSV, type ConversationMessage, suggestInput } from '@/api/chat'
import { getDashboards, createDashboard, addCardToDashboard, type Dashboard } from '@/api/dashboard'
import { getDataTableList, type DataTable } from '@/api/dataTable'
import DynamicChart from '@/components/Charts/DynamicChart.vue'

const route = useRoute()
const router = useRouter()

interface Message {
  type: 'user' | 'ai'
  content?: string
  sql?: string
  chartData?: { columns: string[] | null; rows: any[] | null }  // 允许 columns 和 rows 为 null
  chartType?: string
  alternativeCharts?: string[]  // 备选图表类型
  loading?: boolean
  error?: boolean
  question?: string  // 保存用户问题
  datasetId?: number  // 保存数据集ID
  steps?: string[]  // 执行步骤
  isSystemError?: boolean  // 区分系统错误和业务澄清
  feedbackGiven?: 'like' | 'dislike'  // 反馈状态
  insight?: string  // 分析师 Agent 的业务洞察
  isCached?: boolean  // 是否从缓存读取
  regenerating?: boolean  // 是否正在重新生成
  followupQuestions?: string[]  // 后续推荐问题
  dataInterpretation?: any  // 数据解读
  fluctuationAnalysis?: any  // 波动归因分析
}

const sourceType = ref<'dataset' | 'datatable'>('dataset')
const currentDatasetId = ref<number | undefined>(undefined)
const currentDataTableId = ref<number | undefined>(undefined)
const datasets = ref<Dataset[]>([])
const dataTables = ref<DataTable[]>([])
const loadingDatasets = ref(false)
const loadingDataTables = ref(false)
const messages = ref<Message[]>([])
const inputMessage = ref('')
const sending = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const activeCollapse = ref<string[]>([])

// 计算属性：是否已选择数据源
const isDataSourceSelected = computed(() => {
  if (sourceType.value === 'dataset') {
    return !!currentDatasetId.value
  } else {
    return !!currentDataTableId.value
  }
})

// 计算属性：输入框占位符
const inputPlaceholder = computed(() => {
  if (!isDataSourceSelected.value) {
    return sourceType.value === 'dataset' ? '请先选择数据集...' : '请先选择数据表...'
  }
  
  if (sourceType.value === 'dataset') {
    const dataset = datasets.value.find(d => d.id === currentDatasetId.value)
    return dataset ? `向 ${dataset.name} 提问...` : '请输入您的问题...'
  } else {
    const table = dataTables.value.find(t => t.id === currentDataTableId.value)
    return table ? `查询表 ${table.display_name} 的数据...` : '请输入您的问题...'
  }
})

// Recommendation Cards Data
const recommendCards = [
  {
    title: '销售趋势分析',
    desc: '查看本年度每月的销售额变化趋势',
    icon: TrendCharts,
    query: '按月统计今年的销售额趋势'
  },
  {
    title: '产品类别占比',
    desc: '分析各产品类别的销售占比情况',
    icon: PieChart,
    query: '统计各产品类别的销售额占比'
  },
  {
    title: 'Top 10 客户',
    desc: '找出贡献销售额最高的10位客户',
    icon: DataLine,
    query: '列出销售额最高的10个客户'
  },
  {
    title: '库存状态概览',
    desc: '检查当前库存量较低的产品',
    icon: DataBoard,
    query: '查询库存量少于100的产品'
  }
]

// Loading Animation State
const loadingSteps = [
  '正在理解问题...',
  '检索业务术语...',
  '生成查询逻辑...',
  '执行 SQL 查询...',
  '处理查询结果...'
]
const currentLoadingStepIndex = ref(0)
const currentLoadingStep = ref(loadingSteps[0])
const loadingProgress = ref(0)  // 添加进度百分比
let loadingInterval: number | null = null

// Dashboard Dialog State
const saveToDashboardDialog = ref(false)
const dashboards = ref<Dashboard[]>([])
const selectedDashboardId = ref<number | undefined>(undefined)
const cardTitle = ref('')
const showNewDashboardInput = ref(false)
const newDashboardName = ref('')
const savingCard = ref(false)
const currentSavingMessage = ref<Message | null>(null)

// Feedback Dialog State
const sqlCorrectionDialog = ref(false)
const correctedSql = ref('')
const submittingFeedback = ref(false)
const currentFeedbackMessage = ref<Message | null>(null)
const currentFeedbackMessageIndex = ref<number>(-1)

onMounted(async () => {
  loadingDatasets.value = true
  loadingDataTables.value = true
  try {
    // 加载数据集
    const res = await getDatasetList()
    console.log('[Chat] All datasets from API:', res.map(d => ({ id: d.id, name: d.name, datasource_id: d.datasource_id, status: d.status })))
    
    datasets.value = res.filter(d => d.status === 'completed')
    console.log('[Chat] Filtered completed datasets:', datasets.value.map(d => ({ id: d.id, name: d.name, datasource_id: d.datasource_id, status: d.status })))
    
    // 加载数据表
    const tables = await getDataTableList()
    dataTables.value = tables.filter(t => t.status === 'active')
    console.log('[Chat] Loaded data tables:', dataTables.value.map(t => ({ id: t.id, name: t.display_name, datasource_id: t.datasource_id })))
    
    // 检查URL参数
    const datasetIdFromQuery = route.query.dataset
    if (datasetIdFromQuery) {
      sourceType.value = 'dataset'
      const datasetId = Number(datasetIdFromQuery)
      
      const allDatasets = await getDatasetList()
      const targetDataset = allDatasets.find(d => d.id === datasetId)
      
      if (targetDataset) {
        const status = targetDataset.status
        if (status === 'completed') {
          currentDatasetId.value = datasetId
          ElMessage.success(`已选择数据集: ${targetDataset.name}`)
        } else if (status === 'training') {
          ElMessage.info({
            message: `数据集 "${targetDataset.name}" 正在训练中，预计1-2分钟完成。训练完成后刷新页面即可使用。`,
            duration: 5000
          })
          if (datasets.value.length > 0) {
            currentDatasetId.value = datasets.value[0].id
          }
        } else {
          ElMessage.warning(`数据集 "${targetDataset.name}" 训练失败或状态异常`)
          if (datasets.value.length > 0) {
            currentDatasetId.value = datasets.value[0].id
          }
        }
      } else {
        if (datasets.value.length > 0) {
          currentDatasetId.value = datasets.value[0].id
        }
        ElMessage.warning('指定的数据集不存在，已选择默认数据集')
      }
    } else if (datasets.value.length > 0) {
      currentDatasetId.value = datasets.value[0].id
    }
  } catch (error) {
    ElMessage.error('Failed to load data sources')
  } finally {
    loadingDatasets.value = false
    loadingDataTables.value = false
  }
})

onUnmounted(() => {
  if (loadingInterval) {
    clearInterval(loadingInterval)
  }
})

const handleCardClick = (card: typeof recommendCards[0]) => {
  if (!currentDatasetId.value) {
    ElMessage.warning('请先选择一个数据集')
    return
  }
  inputMessage.value = card.query
  handleSend()
}

const startLoadingAnimation = () => {
  currentLoadingStepIndex.value = 0
  currentLoadingStep.value = loadingSteps[0]
  loadingProgress.value = 0
  
  loadingInterval = window.setInterval(() => {
    currentLoadingStepIndex.value = (currentLoadingStepIndex.value + 1) % loadingSteps.length
    currentLoadingStep.value = loadingSteps[currentLoadingStepIndex.value]
    // 更新进度条，最多到 90%，留 10% 给最终处理
    loadingProgress.value = Math.min(90, (currentLoadingStepIndex.value / loadingSteps.length) * 100)
  }, 2000)  // 每 2 秒更新一次
}

const stopLoadingAnimation = () => {
  if (loadingInterval) {
    clearInterval(loadingInterval)
    loadingInterval = null
  }
  loadingProgress.value = 100  // 完成时设置为 100%
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const clearMessages = () => {
  messages.value = []
}

const handleSend = async () => {
  // 验证数据源选择
  if (sourceType.value === 'dataset' && !currentDatasetId.value) {
    ElMessage.warning('请先选择一个数据集')
    return
  }
  if (sourceType.value === 'datatable' && !currentDataTableId.value) {
    ElMessage.warning('请先选择一个数据表')
    return
  }
  
  const question = inputMessage.value.trim()
  if (!question) return

  // 1. Add User Message
  messages.value.push({ type: 'user', content: question })
  inputMessage.value = ''
  scrollToBottom()

  // 2. Add AI Loading Placeholder
  const aiMsgIndex = messages.value.length
  messages.value.push({ type: 'ai', loading: true })
  sending.value = true
  startLoadingAnimation()  // 启动加载动画
  scrollToBottom()

  try {
    // 3. 构建对话历史（最近3轮，排除当前正在发送的消息）
    const conversationHistory: ConversationMessage[] = []
    // 排除最后两条消息（当前用户消息和 AI loading 占位符）
    const historicalMessages = messages.value.slice(0, -2)
    // 取最近6条历史消息（3轮对话）
    const recentMessages = historicalMessages.slice(-6)

    for (const msg of recentMessages) {
      // 只包含有实际内容的消息，排除 loading 和 error 状态
      if (msg.type === 'user' && msg.content && !msg.loading) {
        conversationHistory.push({
          role: 'user',
          content: msg.content
        })
      } else if (msg.type === 'ai' && msg.content && !msg.loading && !msg.error) {
        conversationHistory.push({
          role: 'assistant',
          content: msg.content
        })
      }
    }
    
    // 4. Call API with conversation history
    // 如果选择的是数据表，需要获取对应的数据集ID
    let datasetId = currentDatasetId.value
    let dataTableId = undefined
    
    if (sourceType.value === 'datatable' && currentDataTableId.value) {
      const selectedTable = dataTables.value.find(t => t.id === currentDataTableId.value)
      if (selectedTable) {
        console.log('[Chat] Selected table:', selectedTable.display_name, 'datasource_id:', selectedTable.datasource_id)
        console.log('[Chat] Available datasets:', datasets.value.map(d => ({ 
          id: d.id, 
          name: d.name, 
          datasource_id: d.datasource_id, 
          status: d.status 
        })))
        
        // 查找使用相同数据源的已训练数据集
        const matchingDataset = datasets.value.find(d => {
          const isMatching = d.datasource_id !== null && 
                            d.datasource_id === selectedTable.datasource_id && 
                            d.status === 'completed'
          console.log(`[Chat] Checking dataset "${d.name}" (datasource_id: ${d.datasource_id}, status: ${d.status}) - Match: ${isMatching}`)
          return isMatching
        })
        
        console.log('[Chat] Matching dataset:', matchingDataset)
        
        if (!matchingDataset) {
          // 检查是否存在该数据源的数据集但状态不是 completed
          const allDatasets = await getDatasetList()
          const incompleteDataset = allDatasets.find(d => d.datasource_id === selectedTable.datasource_id)
          
          let errorMsg = ''
          if (incompleteDataset) {
            if (incompleteDataset.status === 'training') {
              errorMsg = `该数据表所属的数据源的数据集"${incompleteDataset.name}"正在训练中，请等待训练完成后再使用。`
            } else if (incompleteDataset.status === 'failed') {
              errorMsg = `该数据表所属的数据源的数据集"${incompleteDataset.name}"训练失败，请前往"数据集"页面重新训练。`
            } else if (incompleteDataset.status === 'pending') {
              errorMsg = `该数据表所属的数据源的数据集"${incompleteDataset.name}"尚未开始训练，请前往"数据集"页面点击"训练"按钮。`
            } else {
              errorMsg = `该数据表所属的数据源的数据集"${incompleteDataset.name}"状态异常（${incompleteDataset.status}），请检查数据集配置。`
            }
          } else {
            errorMsg = `该数据表所属的数据源（ID: ${selectedTable.datasource_id}）没有对应的数据集。\n\n请前往"数据集"页面，创建并训练该数据源的数据集。`
          }
          
          ElMessage.error(errorMsg)
          throw new Error('No trained dataset found for this data table')
        }
        
        datasetId = matchingDataset.id
        dataTableId = currentDataTableId.value
        
        console.log('[Chat] ✓ Using dataset', matchingDataset.name, '(ID:', matchingDataset.id, ') for table', selectedTable.display_name)
      }
    }
    
    const res = await sendChat({
      dataset_id: datasetId!,
      question: question,
      conversation_history: conversationHistory.length > 0 ? conversationHistory : undefined,
      data_table_id: dataTableId
    })

    // 4. Update AI Message (保存问题和数据集ID)
    const isClarification = res.chart_type === 'clarification'
    
    // 直接使用后端返回的 columns 和 rows
    const chartData = (res.columns && res.rows) ? {
      columns: res.columns,
      rows: res.rows
    } : undefined
    
    // Debug: 输出数据结构
    console.log('[Chat Debug] API Response:', {
      has_columns: !!res.columns,
      has_rows: !!res.rows,
      rows_length: res.rows?.length,
      chartData: chartData,
      chart_type: res.chart_type
    })
    
    messages.value[aiMsgIndex] = {
      type: 'ai',
      loading: false,
      content: res.answer_text || undefined,
      sql: res.sql || undefined,
      chartData: chartData,
      chartType: res.chart_type,
      alternativeCharts: res.alternative_charts || [],  // 备选图表类型
      question: question,
      datasetId: sourceType.value === 'dataset' ? currentDatasetId.value : datasetId,
      steps: res.steps,
      error: false,
      isSystemError: false,
      insight: res.insight,  // 直接使用后端同步返回的分析
      isCached: res.is_cached || res.from_cache || false,  // 缓存标识
      followupQuestions: res.followup_questions || [],  // 后续推荐问题
      dataInterpretation: res.data_interpretation,  // 数据解读
      fluctuationAnalysis: res.fluctuation_analysis  // 波动归因分析
    }
  } catch (error: any) {
    console.error(error)
    
    // 如果是数据集不存在的错误，给出更友好的提示
    if (error.message && error.message.includes('No trained dataset')) {
      messages.value[aiMsgIndex] = {
        type: 'ai',
        loading: false,
        error: true,
        isSystemError: false,
        content: '该数据表所属的数据源没有已训练的数据集。\n\n请前往"数据集"页面，选择对应的数据源创建并训练数据集后再使用。'
      }
    } else {
      // 区分 HTTP 错误类型
      const statusCode = error.response?.status
      const isServerError = statusCode && statusCode >= 500
      
      let errorMessage = error.response?.data?.detail || '抱歉，处理您的问题时出现了错误。请稍后重试。'
      
      // 如果是 404 错误，可能是数据集不存在
      if (statusCode === 404 && errorMessage.includes('Dataset')) {
        errorMessage = '数据集不存在或无权访问。\n\n如果您选择的是数据表模式，请确保对应数据源已创建并训练了数据集。'
      }
      
      messages.value[aiMsgIndex] = {
        type: 'ai',
        loading: false,
        error: true,
        isSystemError: isServerError,
        content: errorMessage
      }
    }
  } finally {
    stopLoadingAnimation()  // 停止加载动画
    sending.value = false
    scrollToBottom()
  }
}

// Step Analysis Helpers
const getStepsSummary = (steps: string[]) => {
  const hasError = steps.some(s => s.includes('失败') || s.includes('出错'))
  const hasCorrection = steps.some(s => s.includes('修正') || s.includes('自动修复'))
  const hasMultiRound = steps.some(s => s.includes('多轮推理') || s.includes('中间 SQL'))
  
  if (hasMultiRound) {
    return 'AI 进行了多轮推理 🧠'
  } else if (hasCorrection) {
    return 'AI 已自动修正 SQL 并生成结果 ✨'
  } else if (hasError) {
    return '查看执行详情 (含警告)'
  } else {
    return '查看执行步骤 ✓'
  }
}

const getStepIcon = (step: string) => {
  if (step.includes('失败') || step.includes('出错')) {
    return WarningFilled
  } else if (step.includes('成功') || step.includes('已修正')) {
    return CircleCheck
  } else {
    return Clock
  }
}

const getStepIconClass = (step: string) => {
  if (step.includes('失败') || step.includes('出错')) {
    return 'text-orange-500'
  } else if (step.includes('成功') || step.includes('已修正')) {
    return 'text-green-500'
  } else {
    return 'text-blue-500'
  }
}

const getStepTextClass = (step: string) => {
  if (step.includes('失败') || step.includes('出错')) {
    return 'text-gray-400'
  } else {
    return 'text-gray-300'
  }
}

// Save to Dashboard
const handleSaveToDashboard = async (msg: Message, index: number) => {
  currentSavingMessage.value = msg
  cardTitle.value = msg.question || '未命名图表'
  
  // Load dashboards
  try {
    dashboards.value = await getDashboards()
  } catch (error) {
    ElMessage.error('加载看板列表失败')
    return
  }
  
  saveToDashboardDialog.value = true
}

const handleCreateNewDashboard = () => {
  showNewDashboardInput.value = true
}

const handleConfirmSave = async () => {
  if (!currentSavingMessage.value) return
  
  let targetDashboardId = selectedDashboardId.value
  
  // Create new dashboard if needed
  if (showNewDashboardInput.value && newDashboardName.value.trim()) {
    try {
      const newDashboard = await createDashboard(newDashboardName.value.trim())
      targetDashboardId = newDashboard.id
      ElMessage.success('看板创建成功')
    } catch (error) {
      ElMessage.error('创建看板失败')
      return
    }
  }
  
  if (!targetDashboardId) {
    ElMessage.warning('请选择或创建一个看板')
    return
  }
  
  if (!cardTitle.value.trim()) {
    ElMessage.warning('请输入卡片标题')
    return
  }
  
  // Save card
  savingCard.value = true
  try {
    await addCardToDashboard(targetDashboardId, {
      title: cardTitle.value.trim(),
      dataset_id: currentSavingMessage.value.datasetId!,
      sql: currentSavingMessage.value.sql!,
      chart_type: currentSavingMessage.value.chartType || 'table'
    })
    
    ElMessage.success('已保存到看板')
    saveToDashboardDialog.value = false
    
    // Reset state
    selectedDashboardId.value = undefined
    showNewDashboardInput.value = false
    newDashboardName.value = ''
    currentSavingMessage.value = null
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingCard.value = false
  }
}

const handleCancelSave = () => {
  saveToDashboardDialog.value = false
  selectedDashboardId.value = undefined
  showNewDashboardInput.value = false
  newDashboardName.value = ''
  currentSavingMessage.value = null
}

// Clarification Helpers
const getClarificationSuggestions = (content: string): string[] => {
  if (!content) return []
  
  // 尝试从 AI 回复中提取建议
  const suggestions: string[] = []
  
  // 1. 检测是否包含"还是"分隔的选项（最优先，直接来自AI的建议）
  if (content.includes('还是')) {
    const parts = content.split('还是')
    for (const part of parts) {
      // 提取""或「」包裹的内容
      const quotedMatch = part.match(/["「](.*?)["」]/)
      if (quotedMatch && quotedMatch[1] && quotedMatch[1].length < 30) {
        suggestions.push(quotedMatch[1].trim())
        continue
      }
      
      // 提取常见的业务术语
      const termMatch = part.match(/(个数|总数|金额|数量|订单|客户|用户|消费|销售|按.{1,4}分组|按.{1,4}统计)/)
      if (termMatch && termMatch[1] && termMatch[1].length < 20) {
        suggestions.push(termMatch[1].trim())
      }
    }
  }
  
  // 2. 检测是否包含"或"分隔的选项
  if (content.includes('或')) {
    const parts = content.split('或')
    for (const part of parts) {
      const quotedMatch = part.match(/["「](.*?)["」]/)
      if (quotedMatch && quotedMatch[1] && quotedMatch[1].length < 30) {
        suggestions.push(quotedMatch[1].trim())
      }
    }
  }
  
  // 3. 检测是否包含列表式的选项（如："1. 选项A  2. 选项B"）
  const listMatches = content.match(/[\d一二三四五][\.、]\s*([^\d一二三四五\.、\n]{2,20})/g)
  if (listMatches) {
    for (const match of listMatches) {
      const cleanMatch = match.replace(/^[\d一二三四五][\.、]\s*/, '').trim()
      if (cleanMatch.length >= 2 && cleanMatch.length <= 20) {
        suggestions.push(cleanMatch)
      }
    }
  }
  
  // 4. 根据关键词提供智能建议
  const contentLower = content.toLowerCase()
  
  // 时间相关
  if (contentLower.includes('时间') || contentLower.includes('日期') || contentLower.includes('周期') || contentLower.includes('范围')) {
    if (suggestions.length < 3) {
      suggestions.push('最近 7 天', '最近 30 天', '本月')
    }
  }
  
  // 统计维度相关
  if (contentLower.includes('分组') || contentLower.includes('统计') || contentLower.includes('维度')) {
    if (suggestions.length < 3) {
      suggestions.push('按日统计', '按月统计', '按类型分组')
    }
  }
  
  // 客户相关
  if (contentLower.includes('客户') || contentLower.includes('用户')) {
    if (suggestions.length < 3) {
      suggestions.push('VIP 客户', '普通客户', '所有客户')
    }
  }
  
  // 订单相关
  if (contentLower.includes('订单')) {
    if (suggestions.length < 3) {
      suggestions.push('已完成订单', '待处理订单', '所有订单')
    }
  }
  
  // 5. 如果仍然没有提取到建议，返回通用默认建议
  if (suggestions.length === 0) {
    return [
      '显示最近 30 天的数据',
      '按月统计',
      '查询所有类型'
    ]
  }
  
  // 去重并限制数量
  return [...new Set(suggestions)].slice(0, 5)
}

const handleQuickReply = (suggestion: string) => {
  // 检查是否已选择数据源（支持数据集和数据表两种模式）
  if (sourceType.value === 'dataset' && !currentDatasetId.value) {
    ElMessage.warning('请先选择一个数据集')
    return
  }
  if (sourceType.value === 'datatable' && !currentDataTableId.value) {
    ElMessage.warning('请先选择一个数据表')
    return
  }
  
  // 获取上一个用户问题
  const lastUserMessage = messages.value.filter(m => m.type === 'user').pop()
  if (!lastUserMessage) return
  
  // 组合原始问题和建议
  const enhancedQuestion = `${lastUserMessage.content}，${suggestion}`
  
  // 自动填充到输入框
  inputMessage.value = enhancedQuestion
  
  // 聚焦到输入框
  nextTick(() => {
    const inputEl = document.querySelector('.el-input__inner') as HTMLInputElement
    if (inputEl) {
      inputEl.focus()
    }
  })
}

// Format single result for better display
const formatSingleResult = (chartData: { columns: string[] | null; rows: any[] | null }) => {
  if (!chartData.rows || chartData.rows.length !== 1 || !chartData.columns) {
    return ''
  }
  
  const row = chartData.rows[0]
  const parts: string[] = []
  
  chartData.columns.forEach((col, index) => {
    const value = row[col]
    
    // 格式化数值
    if (typeof value === 'number') {
      if (Number.isInteger(value)) {
        parts.push(`${col}: ${value.toLocaleString()}`)
      } else {
        parts.push(`${col}: ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
      }
    } else {
      parts.push(`${col}: ${value}`)
    }
  })
  
  return parts.join(' | ')
}

// 图表类型切换
const handleChangeChartType = (msgIndex: number, newChartType: string) => {
  if (messages.value[msgIndex]) {
    messages.value[msgIndex].chartType = newChartType
  }
}

// 图表类型名称映射
const getChartTypeName = (chartType: string): string => {
  const nameMap: Record<string, string> = {
    'line': '折线图',
    'bar': '柱状图',
    'pie': '饼图',
    'table': '表格',
    'scatter': '散点图',
    'area': '面积图'
  }
  return nameMap[chartType] || chartType
}

// 导出数据
const handleExport = async (msg: Message, format: string) => {
  if (!msg.chartData || !msg.chartData.columns || !msg.chartData.rows || !msg.datasetId) {
    ElMessage.warning('无可导出的数据')
    return
  }
  
  try {
    const exportData = {
      dataset_id: msg.datasetId,
      question: msg.question || '查询结果',
      columns: msg.chartData.columns,
      rows: msg.chartData.rows
    }
    
    let blob: Blob
    let filename: string
    
    if (format === 'excel') {
      ElMessage.info('正在生成 Excel 文件...')
      blob = await exportToExcel(exportData)
      filename = `${msg.question?.slice(0, 20) || '查询结果'}_${new Date().getTime()}.xlsx`
    } else if (format === 'csv') {
      ElMessage.info('正在生成 CSV 文件...')
      blob = await exportToCSV(exportData)
      filename = `${msg.question?.slice(0, 20) || '查询结果'}_${new Date().getTime()}.csv`
    } else {
      ElMessage.error('不支持的导出格式')
      return
    }
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功！')
  } catch (error: any) {
    console.error('Export failed:', error)
    ElMessage.error(error.response?.data?.detail || '导出失败，请重试')
  }
}

// Feedback Handlers
const handleLikeFeedback = async (msg: Message, index: number) => {
  if (!msg.sql || !msg.question || !msg.datasetId) {
    ElMessage.warning('无法提交反馈，缺少必要信息')
    return
  }
  
  submittingFeedback.value = true
  
  try {
    const response = await submitFeedback({
      dataset_id: msg.datasetId,
      question: msg.question,
      sql: msg.sql,
      rating: 1
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      // 标记为已反馈
      messages.value[index].feedbackGiven = 'like'
    } else {
      ElMessage.warning(response.message)
    }
  } catch (error: any) {
    console.error(error)
    ElMessage.error('反馈提交失败')
  } finally {
    submittingFeedback.value = false
  }
}

const handleDislikeFeedback = (msg: Message, index: number) => {
  if (!msg.sql || !msg.question || !msg.datasetId) {
    ElMessage.warning('无法提交反馈，缺少必要信息')
    return
  }
  
  // 打开 SQL 修正对话框
  currentFeedbackMessage.value = msg
  currentFeedbackMessageIndex.value = index
  correctedSql.value = msg.sql  // 预填充当前 SQL
  sqlCorrectionDialog.value = true
}

const handleCancelCorrection = () => {
  sqlCorrectionDialog.value = false
  correctedSql.value = ''
  currentFeedbackMessage.value = null
  currentFeedbackMessageIndex.value = -1
}

const handleSubmitCorrection = async () => {
  if (!currentFeedbackMessage.value || currentFeedbackMessageIndex.value === -1) {
    return
  }
  
  if (!correctedSql.value.trim()) {
    ElMessage.warning('请输入修正后的 SQL')
    return
  }
  
  submittingFeedback.value = true
  
  try {
    const response = await submitFeedback({
      dataset_id: currentFeedbackMessage.value.datasetId!,
      question: currentFeedbackMessage.value.question!,
      sql: correctedSql.value.trim(),
      rating: -1
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      // 标记为已反馈
      messages.value[currentFeedbackMessageIndex.value].feedbackGiven = 'dislike'
      // 关闭对话框
      handleCancelCorrection()
    } else {
      ElMessage.warning(response.message)
    }
  } catch (error: any) {
    console.error(error)
    ElMessage.error('修正提交失败')
  } finally {
    submittingFeedback.value = false
  }
}

// 重新生成处理
const handleRegenerate = async (msg: Message, index: number) => {
  if (!msg.question || !msg.datasetId) {
    ElMessage.warning('无法重新生成，缺少必要信息')
    return
  }

  // 设置重新生成状态
  messages.value[index].regenerating = true

  try {
    // 构建对话历史（获取该消息之前的历史）
    const conversationHistory: ConversationMessage[] = []
    // 获取该消息之前的所有消息（不包括当前消息及其对应的用户问题）
    const historicalMessages = messages.value.slice(0, index - 1)
    // 取最近6条历史消息（3轮对话）
    const recentMessages = historicalMessages.slice(-6)

    for (const histMsg of recentMessages) {
      if (histMsg.type === 'user' && histMsg.content && !histMsg.loading) {
        conversationHistory.push({
          role: 'user',
          content: histMsg.content
        })
      } else if (histMsg.type === 'ai' && histMsg.content && !histMsg.loading && !histMsg.error) {
        conversationHistory.push({
          role: 'assistant',
          content: histMsg.content
        })
      }
    }

    // 调用 API，设置 use_cache = false 强制刷新
    const res = await sendChat({
      dataset_id: msg.datasetId,
      question: msg.question,
      use_cache: false,  // 关键：禁用缓存
      conversation_history: conversationHistory.length > 0 ? conversationHistory : undefined
    })
    
    const isClarification = res.chart_type === 'clarification'
    
    const chartData = (res.columns && res.rows) ? {
      columns: res.columns,
      rows: res.rows
    } : undefined
    
    // 更新消息
    messages.value[index] = {
      type: 'ai',
      loading: false,
      content: res.answer_text || undefined,
      sql: res.sql || undefined,
      chartData: chartData,
      chartType: res.chart_type,
      question: msg.question,
      datasetId: msg.datasetId,
      steps: res.steps,
      error: false,
      isSystemError: false,
      insight: res.insight,
      isCached: false,  // 重新生成的不会是缓存结果
      regenerating: false,
      followupQuestions: res.followup_questions,
      dataInterpretation: res.data_interpretation,
      fluctuationAnalysis: res.fluctuation_analysis
    }
    
    ElMessage.success('已重新生成')
    scrollToBottom()
  } catch (error: any) {
    console.error(error)
    ElMessage.error('重新生成失败')
    messages.value[index].regenerating = false
  }
}

// ========== 输入联想相关函数 ==========

/**
 * 输入联想 - 获取问题建议
 */
const fetchInputSuggestions = async (queryString: string, callback: (suggestions: any[]) => void) => {
  console.log('[Input Suggest] Triggered with:', queryString, 'sourceType:', sourceType.value, 'datasetId:', currentDatasetId.value)
  
  // 数据表模式暂不支持输入联想（因为需要 dataset_id）
  if (sourceType.value === 'datatable') {
    console.log('[Input Suggest] Skipped: datatable mode')
    callback([])
    return
  }
  
  if (!currentDatasetId.value) {
    console.log('[Input Suggest] Skipped: no dataset selected')
    callback([])
    return
  }
  
  if (!queryString || queryString.trim().length < 2) {
    console.log('[Input Suggest] Skipped: query too short')
    callback([])
    return
  }

  try {
    console.log('[Input Suggest] Calling API with dataset_id:', currentDatasetId.value, 'partial_input:', queryString.trim())
    const res = await suggestInput({
      dataset_id: currentDatasetId.value,
      partial_input: queryString.trim(),
      limit: 5
    })
    
    console.log('[Input Suggest] API Response:', res)
    
    // 转换为 el-autocomplete 需要的格式
    const suggestions = res.suggestions.map(s => ({ value: s }))
    console.log('[Input Suggest] Formatted suggestions:', suggestions)
    
    // 如果有建议，显示提示
    if (suggestions.length > 0) {
      console.log('[Input Suggest] ✓ Returning', suggestions.length, 'suggestions')
    } else {
      console.log('[Input Suggest] ⚠ No suggestions returned from API')
    }
    
    callback(suggestions)
  } catch (error: any) {
    console.error('[Input Suggest] Error:', error)
    console.error('[Input Suggest] Error details:', error.response?.data || error.message)
    callback([])
  }
}

/**
 * 处理联想建议选择
 */
const handleSuggestionSelect = (item: any) => {
  inputMessage.value = item.value
  // 不自动发送，让用户确认
}

/**
 * 处理后续问题点击
 */
const handleFollowupQuestionClick = (question: string) => {
  if (sourceType.value === 'dataset' && !currentDatasetId.value) {
    ElMessage.warning('请先选择一个数据集')
    return
  }
  if (sourceType.value === 'datatable' && !currentDataTableId.value) {
    ElMessage.warning('请先选择一个数据表')
    return
  }
  inputMessage.value = question
  handleSend()
}

/**
 * 切换数据源类型
 */
const handleSourceTypeChange = () => {
  // 清空当前选择和对话历史
  currentDatasetId.value = undefined
  currentDataTableId.value = undefined
  messages.value = []
  
  // 自动选择第一个可用项
  if (sourceType.value === 'dataset' && datasets.value.length > 0) {
    currentDatasetId.value = datasets.value[0].id
  } else if (sourceType.value === 'datatable' && dataTables.value.length > 0) {
    // 选择第一个有对应数据集的数据表
    const firstValidTable = dataTables.value.find(t => hasMatchingDataset(t))
    if (firstValidTable) {
      currentDataTableId.value = firstValidTable.id
    } else if (dataTables.value.length > 0) {
      // 如果没有有效的，还是选第一个，但会在发送时提示
      currentDataTableId.value = dataTables.value[0].id
    }
  }
}

/**
 * 检查数据表是否有对应的已训练数据集
 */
const hasMatchingDataset = (table: DataTable): boolean => {
  return datasets.value.some(d => 
    d.datasource_id !== null && 
    d.datasource_id === table.datasource_id && 
    d.status === 'completed'
  )
}

/**
 * 处理数据表切换
 */
const handleDataTableChange = (tableId: number) => {
  const selectedTable = dataTables.value.find(t => t.id === tableId)
  if (selectedTable && !hasMatchingDataset(selectedTable)) {
    ElMessage.warning({
      message: `该数据表所属的数据源没有已训练的数据集，查询可能失败。请先在"数据集"页面创建并训练数据集。`,
      duration: 5000
    })
  }
  // 清空对话历史
  messages.value = []
}
</script>

<style scoped>
/* Thinking Steps Collapse Custom Styling */
.thinking-steps-collapse :deep(.el-collapse-item__header) {
  padding: 0;
  background-color: transparent;
  border: none;
  font-size: 13px;
  height: auto;
  line-height: normal;
}

.thinking-steps-collapse :deep(.el-collapse-item__arrow) {
  margin: 0 0 0 8px;
}

.thinking-steps-collapse :deep(.el-collapse-item__content) {
  padding-bottom: 0;
}

.thinking-steps-collapse :deep(.el-collapse-item__wrap) {
  border: none;
  background-color: transparent;
}

/* Custom Input Styling */
.custom-chat-input :deep(.el-input__wrapper) {
  background-color: transparent !important;
  box-shadow: none !important;
  padding-left: 0;
}

.custom-chat-input :deep(.el-input__inner) {
  color: #e2e8f0 !important;
  font-size: 1rem;
}

.custom-chat-input :deep(.el-input__inner::placeholder) {
  color: #64748b;
}

/* Custom Dialog Dark Mode */
.custom-dialog :deep(.el-dialog) {
  background-color: #1e293b;
  border: 1px solid #334155;
}

.custom-dialog :deep(.el-dialog__title) {
  color: #f1f5f9;
}

.custom-dialog :deep(.el-dialog__body) {
  color: #cbd5e1;
}

/* Autocomplete Suggestion Popper */
.chat-suggestion-popper {
  z-index: 9999 !important;
}

.suggestion-item {
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.suggestion-item:hover {
  background-color: #f0f9ff;
}
</style>

<style>
/* Global styles for autocomplete popper (需要非 scoped) */
.chat-suggestion-popper.el-popper {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  max-width: 600px;
}

.chat-suggestion-popper .el-autocomplete-suggestion__list {
  padding: 4px;
}

.chat-suggestion-popper .el-autocomplete-suggestion__wrap {
  max-height: 300px;
}
</style>
