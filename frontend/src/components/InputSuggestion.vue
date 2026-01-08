<template>
  <div v-if="showSuggestions && suggestions.length > 0" class="input-suggestion-container">
    <div class="suggestion-list">
      <div
        v-for="(suggestion, index) in suggestions"
        :key="index"
        class="suggestion-item"
        @click="handleSelect(suggestion)"
      >
        <el-icon class="suggestion-icon"><Search /></el-icon>
        <span class="suggestion-text">{{ suggestion }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { debounce } from 'lodash-es'
import { suggestInput } from '@/api/chat'

const props = defineProps<{
  datasetId: number | null
  inputValue: string
  show: boolean
}>()

const emit = defineEmits<{
  select: [suggestion: string]
  close: []
}>()

const suggestions = ref<string[]>([])
const loading = ref(false)
const showSuggestions = ref(false)

// 监听输入值变化
watch(() => props.inputValue, debounce(async (newValue: string) => {
  if (!props.datasetId || !newValue || newValue.length < 1) {
    suggestions.value = []
    showSuggestions.value = false
    return
  }
  
  if (!props.show) {
    return
  }
  
  try {
    loading.value = true
    const response = await suggestInput({
      dataset_id: props.datasetId,
      partial_input: newValue,
      limit: 5
    })
    
    suggestions.value = response.suggestions || []
    showSuggestions.value = suggestions.value.length > 0
  } catch (error) {
    console.error('Failed to fetch suggestions:', error)
    suggestions.value = []
    showSuggestions.value = false
  } finally {
    loading.value = false
  }
}, 300))

// 监听 show 属性变化
watch(() => props.show, (newShow) => {
  if (!newShow) {
    showSuggestions.value = false
  }
})

const handleSelect = (suggestion: string) => {
  emit('select', suggestion)
  showSuggestions.value = false
}
</script>

<style scoped>
.input-suggestion-container {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 1000;
  margin-top: 4px;
}

.suggestion-list {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-height: 300px;
  overflow-y: auto;
}

.dark .suggestion-list {
  background: #1e293b;
  border-color: #334155;
}

.suggestion-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 1px solid #f3f4f6;
}

.dark .suggestion-item {
  border-bottom-color: #334155;
}

.suggestion-item:last-child {
  border-bottom: none;
}

.suggestion-item:hover {
  background: #f9fafb;
}

.dark .suggestion-item:hover {
  background: #334155;
}

.suggestion-icon {
  color: #9ca3af;
  margin-right: 8px;
  font-size: 16px;
  flex-shrink: 0;
}

.suggestion-text {
  color: #374151;
  font-size: 14px;
  flex: 1;
}

.dark .suggestion-text {
  color: #e2e8f0;
}
</style>
