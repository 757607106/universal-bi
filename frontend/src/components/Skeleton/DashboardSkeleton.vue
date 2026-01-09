<template>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    <div
      v-for="i in count"
      :key="i"
      class="bg-white dark:bg-dark-glass backdrop-blur-md border border-gray-200/50 dark:border-white/5 rounded-2xl p-6 h-[240px] flex flex-col relative overflow-hidden group"
    >
      <!-- Shimmer Effect -->
      <div class="absolute inset-0 animate-shimmer bg-gradient-to-r from-transparent via-white/20 dark:via-white/5 to-transparent z-10 pointer-events-none" style="background-size: 200% 100%"></div>

      <!-- Header -->
      <div class="flex items-start justify-between mb-6">
        <div class="flex items-center gap-3">
          <!-- Icon Placeholder -->
          <div class="w-10 h-10 rounded-xl bg-gray-200 dark:bg-white/10 animate-pulse"></div>
          <div class="space-y-2">
            <!-- Title Placeholder -->
            <div class="h-5 w-32 bg-gray-200 dark:bg-white/10 rounded-md animate-pulse"></div>
            <!-- Date Placeholder -->
            <div class="h-3 w-20 bg-gray-200 dark:bg-white/10 rounded-md animate-pulse"></div>
          </div>
        </div>
        <!-- Menu Icon Placeholder -->
        <div class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-white/5 animate-pulse"></div>
      </div>

      <!-- Description Placeholder -->
      <div class="space-y-2 mb-auto">
        <div class="h-4 w-full bg-gray-100 dark:bg-white/5 rounded-md animate-pulse"></div>
        <div class="h-4 w-2/3 bg-gray-100 dark:bg-white/5 rounded-md animate-pulse"></div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-white/5 mt-4">
        <div class="flex items-center gap-2">
          <div class="w-4 h-4 rounded bg-gray-200 dark:bg-white/10 animate-pulse"></div>
          <div class="h-3 w-16 bg-gray-200 dark:bg-white/10 rounded animate-pulse"></div>
        </div>
        <div class="h-3 w-12 bg-gray-200 dark:bg-white/10 rounded animate-pulse"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  count: {
    type: Number,
    default: 6
  }
})
</script>
