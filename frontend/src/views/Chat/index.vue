<template>
  <div class="h-full flex bg-slate-50 dark:bg-slate-950 relative overflow-hidden transition-colors duration-300">
    <!-- Background Decor -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-blue-400/10 dark:bg-blue-600/10 rounded-full blur-[100px] animate-blob"></div>
      <div class="absolute bottom-[-10%] left-[-5%] w-[500px] h-[500px] bg-cyan-400/10 dark:bg-cyan-600/10 rounded-full blur-[100px] animate-blob animation-delay-2000"></div>
    </div>

    <!-- 会话侧边栏 -->
    <aside class="w-72 flex-shrink-0 flex flex-col border-r border-white/20 dark:border-white/5 bg-white/70 dark:bg-slate-900/70 backdrop-blur-xl z-20 transition-all duration-300">
      <!-- 新建会话按钮 -->
      <div class="p-4 border-b border-white/20 dark:border-white/5">
        <el-button
          type="primary"
          class="w-full !h-10 !rounded-xl !bg-gradient-to-r !from-blue-600 !to-cyan-600 !border-none shadow-lg shadow-blue-500/20 hover:!shadow-blue-500/30 transition-all duration-300"
          @click="handleNewSession"
        >
          <el-icon class="mr-2"><Plus /></el-icon>
          新建会话
        </el-button>
      </div>

      <!-- 会话列表 -->
      <div class="flex-1 overflow-y-auto py-3 px-2 space-y-1 custom-scrollbar">
        <div
          v-for="session in sessions"
          :key="session.id"
          @click="handleSelectSession(session)"
          class="group relative mx-1 px-3 py-3 rounded-xl cursor-pointer transition-all duration-300 border border-transparent"
          :class="[
            currentSessionId === session.id
              ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800/30 shadow-sm'
              : 'hover:bg-white/50 dark:hover:bg-slate-800/50 hover:border-gray-100 dark:hover:border-slate-700/50'
          ]"
        >
          <div class="flex items-center justify-between">
            <div class="flex-1 min-w-0">
              <p 
                class="text-sm font-medium truncate transition-colors duration-300"
                :class="currentSessionId === session.id ? 'text-blue-700 dark:text-blue-400' : 'text-slate-700 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-slate-100'"
              >
                {{ session.title }}
              </p>
              <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">
                {{ formatSessionTime(session.updated_at) }}
              </p>
            </div>
            <el-button
              v-show="currentSessionId === session.id"
              :icon="Delete"
              size="small"
              circle
              class="!bg-white/80 dark:!bg-slate-800/80 !border-transparent !text-slate-400 hover:!text-red-500 hover:!bg-red-50 dark:hover:!bg-red-900/20 transition-all duration-200 opacity-0 group-hover:opacity-100"
              @click.stop="handleDeleteSession(session)"
            />
          </div>
          
          <!-- Active Indicator -->
          <div 
            v-if="currentSessionId === session.id"
            class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gradient-to-b from-blue-500 to-cyan-500 rounded-r-full"
          ></div>
        </div>

        <!-- 空状态 -->
        <div v-if="sessions.length === 0" class="flex flex-col items-center justify-center py-12 text-slate-400 dark:text-slate-500">
          <div class="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-800/50 flex items-center justify-center mb-3">
            <el-icon class="text-2xl"><ChatDotRound /></el-icon>
          </div>
          <p class="text-xs">暂无会话记录</p>
        </div>
      </div>
    </aside>

    <!-- 主聊天区域 -->
    <div class="flex-1 flex flex-col relative min-w-0 z-10">
      <!-- Header / Toolbar -->
      <div class="h-16 px-6 flex items-center justify-between border-b border-white/20 dark:border-white/5 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md z-20 transition-colors">
        <div class="flex items-center gap-6">
          <h2 class="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            ChatBI
          </h2>
          
          <div class="h-6 w-px bg-slate-200 dark:bg-slate-700/50"></div>
          
          <!-- 数据源类型选择 -->
          <div class="flex items-center bg-slate-100 dark:bg-slate-800/50 rounded-lg p-1 border border-slate-200 dark:border-slate-700/50">
            <button
              v-for="type in ['dataset', 'datatable']"
              :key="type"
              @click="sourceType = type as any; handleSourceTypeChange()"
              class="px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200"
              :class="sourceType === type ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'"
            >
              {{ type === 'dataset' ? '数据集' : '数据表' }}
            </button>
          </div>
          
          <!-- 数据集/数据表选择器 -->
          <el-select
            v-if="sourceType === 'dataset'"
            v-model="currentDatasetId"
            placeholder="请选择数据集"
            class="w-64 glass-select"
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
          
          <el-select
            v-else
            v-model="currentDataTableId"
            placeholder="请选择数据表"
            class="w-64 glass-select"
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
                  <el-tag v-if="item.creation_method === 'excel_upload'" size="small" type="success" effect="plain" class="!bg-transparent">上传</el-tag>
                  <el-tag v-if="!hasMatchingDataset(item)" size="small" type="warning" effect="plain" class="!bg-transparent">无数据集</el-tag>
                </div>
              </span>
            </el-option>
          </el-select>
        </div>

        <el-button 
          @click="clearMessages" 
          plain 
          size="small" 
          class="!bg-white/50 dark:!bg-slate-800/50 !backdrop-blur-sm !border-slate-200 dark:!border-slate-700 !text-slate-600 dark:!text-slate-300 hover:!bg-white dark:hover:!bg-slate-700 !rounded-lg transition-all"
        >
          <el-icon class="mr-1"><Delete /></el-icon> 清空对话
        </el-button>
      </div>

      <!-- Warning Banner for Missing Dataset -->
      <transition name="el-fade-in">
        <div 
          v-if="sourceType === 'datatable' && currentDataTableId && dataTables.find(t => t.id === currentDataTableId) && !hasMatchingDataset(dataTables.find(t => t.id === currentDataTableId)!)"
          class="bg-orange-50/90 dark:bg-orange-900/20 backdrop-blur-sm border-b border-orange-200 dark:border-orange-800/50 px-6 py-3 flex-shrink-0 z-10"
        >
          <div class="flex items-start gap-3 max-w-5xl mx-auto">
            <el-icon class="text-orange-500 dark:text-orange-400 text-xl flex-shrink-0 mt-0.5"><Warning /></el-icon>
            <div class="flex-1">
              <p class="text-sm text-orange-800 dark:text-orange-300 font-medium">该数据表的数据集正在训练中或尚未创建</p>
              <div class="text-xs text-orange-700 dark:text-orange-400 mt-1.5 flex gap-4">
                <span>• 数据集正在后台训练中，请稍等 1-2 分钟后刷新页面</span>
                <span>• 需手动创建并训练数据集</span>
              </div>
            </div>
            <el-button 
              size="small" 
              type="warning" 
              plain
              @click="router.push('/dataset')"
              class="flex-shrink-0 !bg-transparent"
            >
              前往数据集
            </el-button>
          </div>
        </div>
      </transition>

      <!-- Chat Area -->
      <div class="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth" ref="chatContainer">
        <!-- Empty State -->
        <transition name="fade">
          <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center">
            <div class="text-center mb-12 animate-fade-in-up">
              <div class="w-24 h-24 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-3xl mx-auto flex items-center justify-center mb-8 shadow-2xl shadow-blue-500/30 rotate-3 hover:rotate-6 transition-transform duration-500">
                <el-icon class="text-5xl text-white"><DataAnalysis /></el-icon>
              </div>
              <h1 class="text-4xl font-bold text-slate-900 dark:text-slate-100 mb-4 tracking-tight">ChatBI 智能分析助手</h1>
              <p class="text-slate-500 dark:text-slate-400 max-w-lg mx-auto text-lg">基于 AI 的自然语言数据分析，让数据洞察触手可及。</p>
            </div>
            
            <!-- Recommendation Cards -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-3xl animate-fade-in-up" style="animation-delay: 0.1s">
              <div 
                v-for="(card, index) in recommendCards" 
                :key="index"
                @click="handleCardClick(card)"
                class="group relative p-5 bg-white/60 dark:bg-slate-800/40 backdrop-blur-sm rounded-2xl cursor-pointer transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/10 dark:hover:shadow-[0_0_20px_rgba(6,182,212,0.15)] border border-white/40 dark:border-white/5 hover:border-blue-400/50 dark:hover:border-cyan-500/50 hover:-translate-y-1 overflow-hidden"
              >
                <!-- Card Glow Effect -->
                <div class="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                
                <div class="flex items-start gap-4 relative z-10">
                  <div class="p-3 rounded-xl bg-slate-100 dark:bg-slate-700/50 group-hover:bg-blue-500 group-hover:text-white dark:group-hover:bg-cyan-500 transition-all duration-300 shadow-sm">
                    <component :is="card.icon" class="w-6 h-6" />
                  </div>
                  <div>
                    <h3 class="font-bold text-slate-800 dark:text-slate-200 mb-1 group-hover:text-blue-600 dark:group-hover:text-cyan-400 transition-colors">{{ card.title }}</h3>
                    <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{{ card.desc }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>

        <!-- Messages -->
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['flex gap-5 max-w-5xl mx-auto animate-slide-up-fade', msg.type === 'user' ? 'flex-row-reverse' : '']"
          :style="{ animationDelay: `${index * 0.05}s` }"
        >
          <!-- Avatar -->
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg mt-1 transition-all duration-300 transform hover:scale-105"
            :class="msg.type === 'user' ? 'bg-gradient-to-br from-blue-600 to-cyan-600 text-white shadow-blue-500/30' : 'bg-white dark:bg-slate-800 text-blue-600 dark:text-cyan-400 border border-slate-200 dark:border-slate-700'"
          >
            <el-icon v-if="msg.type === 'user'"><User /></el-icon>
            <el-icon v-else size="20"><Monitor /></el-icon>
          </div>

          <!-- Content -->
          <div class="flex-1 min-w-0 max-w-[85%]">
            <!-- Text Bubble -->
            <div
              :class="[
                'text-sm transition-all duration-300 relative',
                msg.type === 'user'
                  ? 'bg-gradient-to-br from-blue-600 to-cyan-600 text-white p-4 rounded-2xl rounded-tr-sm shadow-xl shadow-blue-500/20'
                  : 'bg-white/80 dark:bg-slate-800/80 backdrop-blur-md text-slate-800 dark:text-slate-200 p-6 rounded-2xl rounded-tl-sm border border-white/20 dark:border-white/5 shadow-sm hover:shadow-md'
              ]"
            >
              <!-- Cached Badge -->
              <div v-if="msg.type === 'ai' && msg.isCached && !msg.loading" class="absolute top-2 right-2 flex items-center gap-1.5 px-2.5 py-1 bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-900/30 dark:to-amber-900/30 rounded-full border border-yellow-200 dark:border-yellow-700/50 shadow-sm">
                <el-icon class="text-yellow-500 dark:text-yellow-400 text-sm"><Lightning /></el-icon>
                <span class="text-[10px] font-bold text-yellow-700 dark:text-yellow-400 uppercase tracking-wide">Cached</span>
              </div>

              <!-- Loading State -->
              <div v-if="msg.loading" class="space-y-4">
                <div class="flex items-center gap-3 text-slate-500 dark:text-slate-400">
                  <span class="font-medium animate-pulse">{{ currentLoadingStep }}</span>
                </div>
                <!-- Steps List -->
                <div class="space-y-2 pl-1">
                  <div v-for="(step, idx) in loadingSteps" :key="idx" class="flex items-center gap-3 text-xs transition-colors duration-300">
                    <div 
                      class="w-5 h-5 rounded-full flex items-center justify-center border transition-colors duration-300"
                      :class="[
                        idx < currentLoadingStepIndex ? 'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400' :
                        idx === currentLoadingStepIndex ? 'bg-blue-100 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400 animate-pulse' :
                        'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-300 dark:text-slate-600'
                      ]"
                    >
                      <el-icon v-if="idx < currentLoadingStepIndex" class="text-xs"><Check /></el-icon>
                      <el-icon v-else-if="idx === currentLoadingStepIndex" class="text-xs is-loading"><Loading /></el-icon>
                      <span v-else class="text-[10px]">{{ idx + 1 }}</span>
                    </div>
                    <span :class="idx <= currentLoadingStepIndex ? 'text-slate-600 dark:text-slate-300 font-medium' : 'text-slate-400 dark:text-slate-600'">
                      {{ step }}
                    </span>
                  </div>
                </div>
              </div>
              
              <div v-else>
                <!-- System Error -->
                <div v-if="msg.error && msg.isSystemError" class="flex items-start gap-4 p-4 bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/30 rounded-xl">
                  <div class="p-2 bg-red-100 dark:bg-red-900/30 rounded-full text-red-500 flex-shrink-0">
                    <el-icon class="text-lg"><Warning /></el-icon>
                  </div>
                  <div class="flex-1">
                    <p class="text-sm font-bold text-red-800 dark:text-red-300 mb-1">系统错误</p>
                    <p class="text-sm text-red-600 dark:text-red-400 leading-relaxed">{{ msg.content }}</p>
                  </div>
                </div>

                <!-- Normal Content -->
                <div v-else class="space-y-5">
                  <!-- Clarification -->
                  <div v-if="msg.chartType === 'clarification'" class="space-y-4">
                    <div class="text-sm text-slate-800 dark:text-slate-100 whitespace-pre-wrap leading-loose">
                      {{ msg.content }}
                    </div>
                    
                    <!-- Suggestions -->
                    <div v-if="getClarificationSuggestions(msg.content || '').length > 0" class="space-y-2.5">
                      <p class="text-xs text-slate-500 dark:text-slate-500 font-bold uppercase tracking-wider flex items-center gap-1">
                        <el-icon><Lightning /></el-icon> 快捷回复
                      </p>
                      <div class="flex flex-wrap gap-2">
                        <button
                          v-for="(suggestion, idx) in getClarificationSuggestions(msg.content || '')"
                          :key="idx"
                          class="px-3 py-1.5 text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-slate-600 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-200 dark:hover:border-blue-800 hover:text-blue-600 dark:hover:text-blue-400 transition-all duration-200 shadow-sm"
                          @click="handleQuickReply(suggestion)"
                        >
                          {{ suggestion }}
                        </button>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Thinking Steps -->
                  <div v-if="msg.steps && msg.steps.length > 0">
                    <el-collapse class="thinking-steps-collapse border-none" v-model="activeCollapse">
                      <el-collapse-item :name="`step-${index}`">
                        <template #title>
                          <div class="flex items-center gap-2 text-xs py-1.5 px-3 rounded-lg bg-slate-50 dark:bg-slate-900/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer border border-transparent hover:border-slate-200 dark:hover:border-slate-700">
                            <el-icon class="text-blue-500 dark:text-cyan-500"><Operation /></el-icon>
                            <span class="font-medium text-slate-500 dark:text-slate-400">
                              {{ getStepsSummary(msg.steps) }}
                            </span>
                          </div>
                        </template>
                        <div class="space-y-2 text-xs p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-100 dark:border-slate-800 mt-2">
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

                  <p v-if="msg.content && msg.chartType !== 'clarification'" class="whitespace-pre-wrap text-slate-800 dark:text-slate-200 leading-relaxed">{{ msg.content }}</p>
                  
                  <!-- Single Result -->
                  <div v-if="msg.chartData && msg.chartData.rows && msg.chartData.rows.length === 1 && msg.chartType !== 'clarification'" class="p-6 bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm relative overflow-hidden">
                    <div class="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none"></div>
                    <div class="flex items-center gap-2 mb-3 relative z-10">
                      <el-icon class="text-blue-500 dark:text-cyan-500"><CircleCheck /></el-icon>
                      <span class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">查询结果</span>
                    </div>
                    <div class="text-3xl font-bold text-slate-900 dark:text-slate-100 relative z-10 font-mono">
                      {{ formatSingleResult(msg.chartData) }}
                    </div>
                  </div>
                  
                  <!-- Chart -->
                  <div v-if="msg.chartData && msg.chartData.columns && msg.chartData.rows && msg.chartData.rows.length > 0" class="space-y-4">
                    <!-- Chart Toolbar -->
                    <div class="flex items-center justify-between px-1">
                      <!-- Type Switcher -->
                      <div v-if="msg.alternativeCharts && msg.alternativeCharts.length > 0" class="flex items-center gap-2 bg-slate-100 dark:bg-slate-800/50 p-1 rounded-lg">
                        <button
                          v-for="chartType in msg.alternativeCharts"
                          :key="chartType"
                          class="px-2 py-1 text-xs rounded-md transition-all duration-200"
                          :class="msg.chartType === chartType ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm font-medium' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'"
                          @click="handleChangeChartType(index, chartType)"
                        >
                          {{ getChartTypeName(chartType) }}
                        </button>
                      </div>
                      <div v-else></div>
                      
                      <!-- Export -->
                      <el-dropdown @command="(cmd) => handleExport(msg, cmd)" trigger="click">
                        <button class="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-cyan-400 transition-colors">
                          <el-icon><Download /></el-icon>
                          导出
                        </button>
                        <template #dropdown>
                          <el-dropdown-menu class="glass-dropdown">
                            <el-dropdown-item command="excel">
                              <el-icon><Document /></el-icon> Excel
                            </el-dropdown-item>
                            <el-dropdown-item command="csv">
                              <el-icon><Document /></el-icon> CSV
                            </el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                      </el-dropdown>
                    </div>
                    
                    <div class="h-96 w-full bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden">
                       <DynamicChart
                         :chart-type="msg.chartType || 'table'"
                         :data="{ columns: msg.chartData.columns, rows: msg.chartData.rows }"
                       />
                    </div>
                    
                    <!-- AI Insight -->
                    <div v-if="msg.insight" class="bg-gradient-to-r from-blue-50/50 to-cyan-50/50 dark:from-slate-900/50 dark:to-slate-800/50 rounded-xl p-5 border border-blue-100 dark:border-slate-700/50 relative overflow-hidden group">
                      <div class="absolute inset-0 bg-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>
                      <div class="flex items-center gap-2 text-blue-600 dark:text-cyan-400 mb-3 relative z-10">
                        <el-icon class="text-lg"><DataAnalysis /></el-icon>
                        <span class="text-xs font-bold uppercase tracking-wide">智能分析</span>
                      </div>
                      <div class="text-sm text-slate-700 dark:text-slate-300 leading-loose whitespace-pre-wrap relative z-10">
                        {{ msg.insight }}
                      </div>
                    </div>
                    
                    <!-- Data Interpretation -->
                    <div v-if="msg.dataInterpretation" class="bg-gradient-to-r from-purple-50/50 to-pink-50/50 dark:from-purple-900/10 dark:to-pink-900/10 rounded-xl p-5 border border-purple-100 dark:border-purple-800/30">
                      <div class="flex items-center gap-2 text-purple-600 dark:text-purple-400 mb-3">
                        <el-icon class="text-lg"><TrendCharts /></el-icon>
                        <span class="text-xs font-bold uppercase tracking-wide">数据解读</span>
                      </div>
                      <div class="space-y-3">
                        <p class="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{{ msg.dataInterpretation.summary }}</p>
                        <div v-if="msg.dataInterpretation.key_findings && msg.dataInterpretation.key_findings.length > 0">
                          <p class="text-xs text-slate-500 dark:text-slate-500 font-bold mb-2">关键发现</p>
                          <ul class="space-y-2">
                            <li v-for="(finding, idx) in msg.dataInterpretation.key_findings" :key="idx" class="text-sm text-slate-600 dark:text-slate-400 flex items-start gap-2">
                              <span class="text-purple-500 dark:text-purple-400 mt-1.5 w-1.5 h-1.5 rounded-full bg-current flex-shrink-0"></span>
                              <span>{{ finding }}</span>
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>
                    
                    <!-- Fluctuation Analysis -->
                    <div v-if="msg.fluctuationAnalysis && msg.fluctuationAnalysis.has_fluctuation" class="bg-gradient-to-r from-orange-50/50 to-red-50/50 dark:from-orange-900/10 dark:to-red-900/10 rounded-xl p-5 border border-orange-100 dark:border-orange-800/30">
                      <div class="flex items-center gap-2 text-orange-600 dark:text-orange-400 mb-3">
                        <el-icon class="text-lg"><Warning /></el-icon>
                        <span class="text-xs font-bold uppercase tracking-wide">波动归因</span>
                      </div>
                      <div class="space-y-3">
                        <div v-if="msg.fluctuationAnalysis.attribution">
                          <p class="text-sm text-slate-700 dark:text-slate-300 leading-relaxed mb-3">
                            {{ msg.fluctuationAnalysis.attribution.detailed_analysis }}
                          </p>
                          <div v-if="msg.fluctuationAnalysis.attribution.main_factors && msg.fluctuationAnalysis.attribution.main_factors.length > 0">
                            <div class="flex flex-wrap gap-2">
                              <span
                                v-for="(factor, idx) in msg.fluctuationAnalysis.attribution.main_factors"
                                :key="idx"
                                class="px-2 py-1 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 text-xs rounded-md border border-orange-200 dark:border-orange-800/50"
                              >
                                {{ factor }}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <!-- Followup Questions -->
                    <div v-if="msg.followupQuestions && msg.followupQuestions.length > 0" class="bg-gradient-to-r from-emerald-50/50 to-teal-50/50 dark:from-emerald-900/10 dark:to-teal-900/10 rounded-xl p-5 border border-emerald-100 dark:border-emerald-800/30">
                      <div class="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 mb-3">
                        <el-icon class="text-lg"><QuestionFilled /></el-icon>
                        <span class="text-xs font-bold uppercase tracking-wide">猜你想问</span>
                      </div>
                      <div class="flex flex-wrap gap-2">
                        <button
                          v-for="(question, idx) in msg.followupQuestions"
                          :key="idx"
                          class="px-3 py-1.5 text-xs bg-white/50 dark:bg-slate-800/50 border border-emerald-200 dark:border-emerald-800/50 rounded-full text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 transition-colors cursor-pointer text-left"
                          @click="handleFollowupQuestionClick(question)"
                        >
                          {{ question }}
                        </button>
                      </div>
                    </div>
                    
                    <!-- Action Bar -->
                    <div class="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 dark:border-slate-700/50">
                      <!-- Feedback -->
                      <div v-if="msg.sql" class="flex items-center gap-3">
                        <div class="flex gap-1">
                          <button
                              :class="[
                                'p-1.5 rounded-lg transition-colors duration-200',
                                msg.feedbackGiven === 'like' 
                                  ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' 
                                  : 'text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-green-500'
                              ]"
                              :disabled="msg.feedbackGiven !== undefined"
                              @click="handleLikeFeedback(msg, index)"
                              title="有帮助"
                          >
                              <el-icon><Select /></el-icon>
                          </button>
                          <button
                              :class="[
                                'p-1.5 rounded-lg transition-colors duration-200',
                                msg.feedbackGiven === 'dislike' 
                                  ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' 
                                  : 'text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-red-500'
                              ]"
                              :disabled="msg.feedbackGiven !== undefined"
                              @click="handleDislikeFeedback(msg, index)"
                              title="无帮助"
                          >
                              <el-icon><CloseBold /></el-icon>
                          </button>
                          
                          <div class="w-px h-4 bg-slate-200 dark:bg-slate-700 mx-1"></div>

                          <button
                              class="p-1.5 rounded-lg text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-blue-500 transition-colors duration-200"
                              @click="handleRegenerate(msg, index)"
                              :disabled="msg.regenerating"
                              title="重新生成"
                          >
                              <el-icon :class="{'is-loading': msg.regenerating}"><Refresh /></el-icon>
                          </button>
                        </div>
                      </div>
                      <div v-else></div>

                      <!-- Save -->
                      <button
                        v-if="msg.chartData && msg.chartData.columns && msg.chartData.rows && msg.chartData.rows.length > 0"
                        @click="handleSaveToDashboard(msg, index)"
                        class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                      >
                        <el-icon><DocumentAdd /></el-icon>
                        保存到看板
                      </button>
                    </div>
                  </div>

                  <!-- SQL Collapse -->
                  <el-collapse v-if="msg.sql" class="border-t-0 mt-2">
                    <el-collapse-item name="1">
                      <template #title>
                          <span class="text-xs text-slate-400 dark:text-slate-500 hover:text-blue-500 dark:hover:text-cyan-400 transition-colors flex items-center gap-1">
                            <el-icon><DataLine /></el-icon> 查看 SQL 详情
                          </span>
                      </template>
                      <div class="bg-slate-50 dark:bg-slate-950 text-slate-600 dark:text-slate-400 p-4 rounded-xl font-mono text-xs overflow-x-auto border border-slate-200 dark:border-slate-800 shadow-inner my-2">
                        {{ msg.sql }}
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
      <div class="p-6 pb-8 bg-transparent flex-shrink-0 flex justify-center z-20">
        <div class="w-full max-w-4xl bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl rounded-full shadow-2xl shadow-blue-900/5 border border-white/40 dark:border-white/10 p-2 pl-6 flex items-center gap-4 transition-all duration-300 hover:shadow-blue-500/10 hover:border-blue-400/30 dark:hover:border-cyan-500/30">
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
              <el-icon class="text-slate-400 dark:text-slate-500 text-lg"><Search /></el-icon>
            </template>
            <template #default="{ item }">
              <div class="suggestion-item flex items-center gap-2 py-1.5 px-2">
                <el-icon class="text-blue-500 dark:text-cyan-500"><QuestionFilled /></el-icon>
                <span class="text-sm text-slate-700 dark:text-slate-200">{{ item.value }}</span>
              </div>
            </template>
          </el-autocomplete>
          <el-button
            type="primary"
            @click="handleSend"
            :loading="sending"
            :disabled="!isDataSourceSelected || !inputMessage.trim()"
            class="!rounded-full px-8 !h-10 !bg-gradient-to-r !from-blue-600 !to-cyan-600 !border-none hover:!opacity-90 hover:!shadow-lg hover:!shadow-blue-500/20 dark:hover:!shadow-cyan-500/20 transition-all duration-300"
          >
            发送
          </el-button>
        </div>
      </div>

      <!-- Dialogs -->
      <el-dialog
        v-model="saveToDashboardDialog"
        title="保存到看板"
        width="500px"
        class="glass-dialog"
      >
        <el-form label-width="100px" class="mt-4">
          <el-form-item label="卡片标题">
            <el-input v-model="cardTitle" placeholder="请输入卡片标题" />
          </el-form-item>
          
          <el-form-item label="选择看板" v-if="!showNewDashboardInput">
            <div class="w-full space-y-3">
              <el-select v-model="selectedDashboardId" placeholder="选择已有看板" class="w-full">
                <el-option
                  v-for="dashboard in dashboards"
                  :key="dashboard.id"
                  :label="dashboard.name"
                  :value="dashboard.id"
                />
              </el-select>
              <el-button @click="handleCreateNewDashboard" size="small" class="w-full" plain>
                + 新建看板
              </el-button>
            </div>
          </el-form-item>
          
          <el-form-item label="看板名称" v-if="showNewDashboardInput">
            <el-input v-model="newDashboardName" placeholder="请输入新看板名称" />
          </el-form-item>
        </el-form>
        
        <template #footer>
          <div class="dialog-footer">
            <el-button @click="handleCancelSave">取消</el-button>
            <el-button type="primary" @click="handleConfirmSave" :loading="savingCard">
              确定
            </el-button>
          </div>
        </template>
      </el-dialog>

      <el-dialog
        v-model="sqlCorrectionDialog"
        title="修正 SQL"
        width="700px"
        class="glass-dialog"
      >
        <div class="space-y-4">
          <div>
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-2">请修改下方的 SQL 查询，然后提交给 AI 学习：</p>
            <el-input
              v-model="correctedSql"
              type="textarea"
              :rows="10"
              placeholder="输入正确的 SQL..."
              class="font-mono text-sm"
            />
          </div>
          <div class="flex items-start gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-800/30">
            <el-icon class="text-blue-500 mt-0.5"><InfoFilled /></el-icon>
            <p class="text-xs text-blue-700 dark:text-blue-300">AI 会学习你提供的正确 SQL，下次遇到类似问题时会更准确。</p>
          </div>
        </div>
        
        <template #footer>
          <div class="dialog-footer">
            <el-button @click="handleCancelCorrection">取消</el-button>
            <el-button type="primary" @click="handleSubmitCorrection" :loading="submittingFeedback">
              提交修正
            </el-button>
          </div>
        </template>
      </el-dialog>
    </div>
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
  Document,
  Plus,
  InfoFilled
} from '@element-plus/icons-vue'
import { getDatasetList, type Dataset } from '@/api/dataset'
import { sendChat, submitFeedback, generateSummary, exportToExcel, exportToCSV, type ConversationMessage, suggestInput } from '@/api/chat'
import { getDashboards, createDashboard, addCardToDashboard, type Dashboard } from '@/api/dashboard'
import { getDataTableList, type DataTable } from '@/api/dataTable'
import { getSessions, createSession, getSessionDetail, deleteSession, type ChatSession, type ChatSessionDetail } from '@/api/chatSession'
import DynamicChart from '@/components/Charts/DynamicChart.vue'

const route = useRoute()
const router = useRouter()

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
  isSystemError?: boolean
  feedbackGiven?: 'like' | 'dislike'
  insight?: string
  isCached?: boolean
  regenerating?: boolean
  followupQuestions?: string[]
  dataInterpretation?: any
  fluctuationAnalysis?: any
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

// 会话管理相关状态
const sessions = ref<ChatSession[]>([])
const currentSessionId = ref<number | undefined>(undefined)
const loadingSessions = ref(false)

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
const loadingProgress = ref(0)
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
  loadingSessions.value = true
  try {
    // 加载数据集
    const res = await getDatasetList()
    datasets.value = res.filter(d => d.status === 'completed')

    // 加载数据表
    const tables = await getDataTableList()
    dataTables.value = tables.filter(t => t.status === 'active')

    // 加载会话列表
    try {
      sessions.value = await getSessions()
    } catch (e) {
      console.warn('[Chat] Failed to load sessions:', e)
    }

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
    loadingSessions.value = false
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
    loadingProgress.value = Math.min(90, (currentLoadingStepIndex.value / loadingSteps.length) * 100)
  }, 2000)
}

const stopLoadingAnimation = () => {
  if (loadingInterval) {
    clearInterval(loadingInterval)
    loadingInterval = null
  }
  loadingProgress.value = 100
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

  messages.value.push({ type: 'user', content: question })
  inputMessage.value = ''
  scrollToBottom()

  const aiMsgIndex = messages.value.length
  messages.value.push({ type: 'ai', loading: true })
  sending.value = true
  startLoadingAnimation()
  scrollToBottom()

  try {
    const conversationHistory: ConversationMessage[] = []
    const historicalMessages = messages.value.slice(0, -2)
    const recentMessages = historicalMessages.slice(-6)

    for (const msg of recentMessages) {
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
    
    let datasetId = currentDatasetId.value
    let dataTableId = undefined
    
    if (sourceType.value === 'datatable' && currentDataTableId.value) {
      const selectedTable = dataTables.value.find(t => t.id === currentDataTableId.value)
      if (selectedTable) {
        const matchingDataset = datasets.value.find(d => {
          const hasCorrectDatasource = d.datasource_id !== null && 
                                       d.datasource_id === selectedTable.datasource_id
          const isCompleted = d.status === 'completed'
          const containsTable = d.schema_config?.includes(selectedTable.physical_name)
          return hasCorrectDatasource && isCompleted && containsTable
        })
        
        if (!matchingDataset) {
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
      }
    }
    
    const res = await sendChat({
      dataset_id: datasetId!,
      question: question,
      conversation_history: conversationHistory.length > 0 ? conversationHistory : undefined,
      data_table_id: dataTableId,
      session_id: currentSessionId.value
    })

    const chartData = (res.columns && res.rows) ? {
      columns: res.columns,
      rows: res.rows
    } : undefined
    
    messages.value[aiMsgIndex] = {
      type: 'ai',
      loading: false,
      content: res.answer_text || undefined,
      sql: res.sql || undefined,
      chartData: chartData,
      chartType: res.chart_type,
      alternativeCharts: res.alternative_charts || [],
      question: question,
      datasetId: sourceType.value === 'dataset' ? currentDatasetId.value : datasetId,
      steps: res.steps,
      error: false,
      isSystemError: false,
      insight: res.insight,
      isCached: res.is_cached || res.from_cache || false,
      followupQuestions: res.followup_questions || [],
      dataInterpretation: res.data_interpretation,
      fluctuationAnalysis: res.fluctuation_analysis
    }
  } catch (error: any) {
    console.error(error)
    
    if (error.message && error.message.includes('No trained dataset')) {
      messages.value[aiMsgIndex] = {
        type: 'ai',
        loading: false,
        error: true,
        isSystemError: false,
        content: '该数据表所属的数据源没有已训练的数据集。\n\n请前往"数据集"页面，选择对应的数据源创建并训练数据集后再使用。'
      }
    } else {
      const statusCode = error.response?.status
      const isServerError = statusCode && statusCode >= 500
      
      let errorMessage = error.response?.data?.detail || '抱歉，处理您的问题时出现了错误。请稍后重试。'
      
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
    stopLoadingAnimation()
    sending.value = false
    scrollToBottom()
  }
}

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
    return 'text-slate-400'
  } else {
    return 'text-slate-500 dark:text-slate-400'
  }
}

const handleSaveToDashboard = async (msg: Message, index: number) => {
  currentSavingMessage.value = msg
  cardTitle.value = msg.question || '未命名图表'
  
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

const getClarificationSuggestions = (content: string): string[] => {
  if (!content) return []
  const suggestions: string[] = []
  
  if (content.includes('还是')) {
    const parts = content.split('还是')
    for (const part of parts) {
      const quotedMatch = part.match(/["「](.*?)["」]/)
      if (quotedMatch && quotedMatch[1] && quotedMatch[1].length < 30) {
        suggestions.push(quotedMatch[1].trim())
        continue
      }
      const termMatch = part.match(/(个数|总数|金额|数量|订单|客户|用户|消费|销售|按.{1,4}分组|按.{1,4}统计)/)
      if (termMatch && termMatch[1] && termMatch[1].length < 20) {
        suggestions.push(termMatch[1].trim())
      }
    }
  }
  
  if (content.includes('或')) {
    const parts = content.split('或')
    for (const part of parts) {
      const quotedMatch = part.match(/["「](.*?)["」]/)
      if (quotedMatch && quotedMatch[1] && quotedMatch[1].length < 30) {
        suggestions.push(quotedMatch[1].trim())
      }
    }
  }
  
  const listMatches = content.match(/[\d一二三四五][\.、]\s*([^\d一二三四五\.、\n]{2,20})/g)
  if (listMatches) {
    for (const match of listMatches) {
      const cleanMatch = match.replace(/^[\d一二三四五][\.、]\s*/, '').trim()
      if (cleanMatch.length >= 2 && cleanMatch.length <= 20) {
        suggestions.push(cleanMatch)
      }
    }
  }
  
  const contentLower = content.toLowerCase()
  if (contentLower.includes('时间') || contentLower.includes('日期') || contentLower.includes('周期') || contentLower.includes('范围')) {
    if (suggestions.length < 3) {
      suggestions.push('最近 7 天', '最近 30 天', '本月')
    }
  }
  if (contentLower.includes('分组') || contentLower.includes('统计') || contentLower.includes('维度')) {
    if (suggestions.length < 3) {
      suggestions.push('按日统计', '按月统计', '按类型分组')
    }
  }
  if (contentLower.includes('客户') || contentLower.includes('用户')) {
    if (suggestions.length < 3) {
      suggestions.push('VIP 客户', '普通客户', '所有客户')
    }
  }
  if (contentLower.includes('订单')) {
    if (suggestions.length < 3) {
      suggestions.push('已完成订单', '待处理订单', '所有订单')
    }
  }
  
  if (suggestions.length === 0) {
    return [
      '显示最近 30 天的数据',
      '按月统计',
      '查询所有类型'
    ]
  }
  
  return [...new Set(suggestions)].slice(0, 5)
}

const handleQuickReply = (suggestion: string) => {
  if (sourceType.value === 'dataset' && !currentDatasetId.value) {
    ElMessage.warning('请先选择一个数据集')
    return
  }
  if (sourceType.value === 'datatable' && !currentDataTableId.value) {
    ElMessage.warning('请先选择一个数据表')
    return
  }
  
  const lastUserMessage = messages.value.filter(m => m.type === 'user').pop()
  if (!lastUserMessage) return
  
  const enhancedQuestion = `${lastUserMessage.content}，${suggestion}`
  inputMessage.value = enhancedQuestion
  
  nextTick(() => {
    const inputEl = document.querySelector('.custom-chat-input input') as HTMLInputElement
    if (inputEl) {
      inputEl.focus()
    }
  })
}

const formatSingleResult = (chartData: { columns: string[] | null; rows: any[] | null }) => {
  if (!chartData.rows || chartData.rows.length !== 1 || !chartData.columns) {
    return ''
  }
  
  const row = chartData.rows[0]
  const parts: string[] = []
  
  chartData.columns.forEach((col, index) => {
    const value = row[col]
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

const handleChangeChartType = (msgIndex: number, newChartType: string) => {
  if (messages.value[msgIndex]) {
    messages.value[msgIndex].chartType = newChartType
  }
}

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
  
  currentFeedbackMessage.value = msg
  currentFeedbackMessageIndex.value = index
  correctedSql.value = msg.sql
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
      messages.value[currentFeedbackMessageIndex.value].feedbackGiven = 'dislike'
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

const handleRegenerate = async (msg: Message, index: number) => {
  if (!msg.question || !msg.datasetId) {
    ElMessage.warning('无法重新生成，缺少必要信息')
    return
  }

  messages.value[index].regenerating = true

  try {
    const conversationHistory: ConversationMessage[] = []
    const historicalMessages = messages.value.slice(0, index - 1)
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

    const res = await sendChat({
      dataset_id: msg.datasetId,
      question: msg.question,
      use_cache: false,
      conversation_history: conversationHistory.length > 0 ? conversationHistory : undefined
    })
    
    const chartData = (res.columns && res.rows) ? {
      columns: res.columns,
      rows: res.rows
    } : undefined
    
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
      isCached: false,
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

const fetchInputSuggestions = async (queryString: string, callback: (suggestions: any[]) => void) => {
  if (sourceType.value === 'datatable') {
    callback([])
    return
  }
  
  if (!currentDatasetId.value) {
    callback([])
    return
  }
  
  if (!queryString || queryString.trim().length < 2) {
    callback([])
    return
  }

  try {
    const res = await suggestInput({
      dataset_id: currentDatasetId.value,
      partial_input: queryString.trim(),
      limit: 5
    })
    
    const suggestions = res.suggestions.map(s => ({ value: s }))
    callback(suggestions)
  } catch (error: any) {
    console.error('[Input Suggest] Error:', error)
    callback([])
  }
}

const handleSuggestionSelect = (item: any) => {
  inputMessage.value = item.value
}

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

const handleSourceTypeChange = () => {
  currentDatasetId.value = undefined
  currentDataTableId.value = undefined
  messages.value = []
  
  if (sourceType.value === 'dataset' && datasets.value.length > 0) {
    currentDatasetId.value = datasets.value[0].id
  } else if (sourceType.value === 'datatable' && dataTables.value.length > 0) {
    const firstValidTable = dataTables.value.find(t => hasMatchingDataset(t))
    if (firstValidTable) {
      currentDataTableId.value = firstValidTable.id
    } else if (dataTables.value.length > 0) {
      currentDataTableId.value = dataTables.value[0].id
    }
  }
}

const hasMatchingDataset = (table: DataTable): boolean => {
  return datasets.value.some(d => 
    d.datasource_id !== null && 
    d.datasource_id === table.datasource_id && 
    d.status === 'completed'
  )
}

const handleDataTableChange = (tableId: number) => {
  const selectedTable = dataTables.value.find(t => t.id === tableId)
  if (selectedTable && !hasMatchingDataset(selectedTable)) {
    ElMessage.warning({
      message: `该数据表所属的数据源没有已训练的数据集，查询可能失败。请先在"数据集"页面创建并训练数据集。`,
      duration: 5000
    })
  }
  messages.value = []
}

const formatSessionTime = (dateStr: string): string => {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else if (diffDays === 1) {
    return '昨天'
  } else if (diffDays < 7) {
    return `${diffDays}天前`
  } else {
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }
}

const handleNewSession = async () => {
  try {
    const datasetId = sourceType.value === 'dataset' ? currentDatasetId.value : undefined
    const newSession = await createSession({ dataset_id: datasetId })
    sessions.value.unshift(newSession)
    currentSessionId.value = newSession.id
    messages.value = []
    ElMessage.success('新会话已创建')
  } catch (error) {
    console.error('[Chat] Failed to create session:', error)
    ElMessage.error('创建会话失败')
  }
}

const handleSelectSession = async (session: ChatSession) => {
  if (currentSessionId.value === session.id) return

  currentSessionId.value = session.id
  messages.value = []

  try {
    const detail = await getSessionDetail(session.id)

    if (detail.dataset_id) {
      const hasDataset = datasets.value.some(d => d.id === detail.dataset_id)
      if (hasDataset) {
        sourceType.value = 'dataset'
        currentDatasetId.value = detail.dataset_id
      }
    }

    for (const msg of detail.messages) {
      if (msg.role === 'user') {
        messages.value.push({
          type: 'user',
          content: msg.question || ''
        })
      } else if (msg.role === 'assistant') {
        messages.value.push({
          type: 'ai',
          content: msg.answer || undefined,
          sql: msg.sql || undefined,
          chartData: msg.chart_data || undefined,
          chartType: msg.chart_type || undefined,
          insight: msg.insight || undefined,
          question: msg.question || undefined,
          datasetId: detail.dataset_id || undefined
        })
      }
    }

    scrollToBottom()
  } catch (error) {
    console.error('[Chat] Failed to load session:', error)
    ElMessage.error('加载会话失败')
  }
}

const handleDeleteSession = async (session: ChatSession) => {
  try {
    await deleteSession(session.id)
    sessions.value = sessions.value.filter(s => s.id !== session.id)

    if (currentSessionId.value === session.id) {
      currentSessionId.value = undefined
      messages.value = []
    }

    ElMessage.success('会话已删除')
  } catch (error) {
    console.error('[Chat] Failed to delete session:', error)
    ElMessage.error('删除会话失败')
  }
}

const refreshSessions = async () => {
  try {
    sessions.value = await getSessions()
  } catch (error) {
    console.warn('[Chat] Failed to refresh sessions:', error)
  }
}
</script>

<style scoped>
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
  color: #1e293b !important;
  font-size: 1rem;
}

.dark .custom-chat-input :deep(.el-input__inner) {
  color: #e2e8f0 !important;
}

.custom-chat-input :deep(.el-input__inner::placeholder) {
  color: #94a3b8;
}

/* Glass Components */
.glass-select :deep(.el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.5) !important;
  backdrop-filter: blur(8px);
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.dark .glass-select :deep(.el-input__wrapper) {
  background-color: rgba(30, 41, 59, 0.5) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.glass-dialog :deep(.el-dialog) {
  background-color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 24px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.dark .glass-dialog :deep(.el-dialog) {
  background-color: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.glass-dialog :deep(.el-dialog__header) {
  margin-right: 0;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  padding: 20px 24px;
}

.dark .glass-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

/* Custom Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.2);
  border-radius: 4px;
}

.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.4);
}

/* Animations */
@keyframes blob {
  0% { transform: translate(0px, 0px) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
  100% { transform: translate(0px, 0px) scale(1); }
}

.animate-blob {
  animation: blob 7s infinite;
}

.animation-delay-2000 {
  animation-delay: 2s;
}

@keyframes slideUpFade {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-slide-up-fade {
  animation: slideUpFade 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translate3d(0, 30px, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
</style>

<style>
/* Global styles for autocomplete popper */
.chat-suggestion-popper.el-popper {
  background: rgba(255, 255, 255, 0.9) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  border-radius: 16px !important;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
  padding: 8px !important;
}

.dark .chat-suggestion-popper.el-popper {
  background: rgba(30, 41, 59, 0.9) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

.chat-suggestion-popper .el-autocomplete-suggestion__list {
  padding: 0 !important;
}

.chat-suggestion-popper .el-autocomplete-suggestion__item {
  border-radius: 8px;
  margin-bottom: 2px;
}

.chat-suggestion-popper .el-autocomplete-suggestion__item:hover {
  background-color: rgba(59, 130, 246, 0.1) !important;
}

.glass-dropdown .el-dropdown-menu {
  background: rgba(255, 255, 255, 0.9) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  border-radius: 12px !important;
  padding: 6px !important;
}

.dark .glass-dropdown .el-dropdown-menu {
  background: rgba(30, 41, 59, 0.9) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

.glass-dropdown .el-dropdown-menu__item {
  border-radius: 8px;
  margin-bottom: 2px;
}

.glass-dropdown .el-dropdown-menu__item:hover {
  background-color: rgba(59, 130, 246, 0.1) !important;
  color: #3b82f6 !important;
}
</style>
