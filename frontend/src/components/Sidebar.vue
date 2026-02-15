<template>
  <aside class="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
    <!-- Logo/Brand -->
    <div class="p-6 border-b border-gray-200">
      <router-link to="/" class="flex items-center space-x-2">
        <div class="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
          <span class="text-white font-bold text-lg">📈</span>
        </div>
        <div>
          <h1 class="text-lg font-bold text-gray-900">Stock Investment</h1>
          <p class="text-xs text-gray-500">Portfolio Manager</p>
        </div>
      </router-link>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto p-4 space-y-2">
      <!-- Dashboard -->
      <router-link
        to="/"
        class="nav-item"
        :class="isActive('/')"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
        <span>Dashboard</span>
      </router-link>

      <!-- Portfolio Management -->
      <div class="space-y-1 mt-6">
        <div class="nav-section-title">Portfolio</div>
        <router-link
          to="/portfolios"
          class="nav-item"
          :class="isActive('/portfolios')"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
          </svg>
          <span>Portfolios</span>
        </router-link>
        <div class="nav-item nav-item-disabled">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <span>Holdings</span>
          <span class="ml-auto text-xs text-gray-400">Soon</span>
        </div>
      </div>

      <!-- Stock Market -->
      <div class="space-y-1 mt-6">
        <div class="nav-section-title">Market</div>
        <router-link
          to="/stocks"
          class="nav-item"
          :class="isActive('/stocks')"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <span>Stocks</span>
        </router-link>
        <div class="nav-item nav-item-disabled">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
          <span>Screening</span>
          <span class="ml-auto text-xs text-gray-400">Soon</span>
        </div>
      </div>

      <!-- Strategy & Backtesting -->
      <div class="space-y-1 mt-6">
        <div class="nav-section-title">Strategy</div>
        <div class="nav-item nav-item-disabled">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          <span>Strategies</span>
          <span class="ml-auto text-xs text-gray-400">Soon</span>
        </div>
        <div class="nav-item nav-item-disabled">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
          <span>Backtesting</span>
          <span class="ml-auto text-xs text-gray-400">Soon</span>
        </div>
        <div class="nav-item nav-item-disabled">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Simulation</span>
          <span class="ml-auto text-xs text-gray-400">Soon</span>
        </div>
      </div>
    </nav>

    <!-- Footer -->
    <div class="p-4 border-t border-gray-200">
      <div class="text-xs text-gray-500">
        <p>v1.0.0</p>
        <p>© 2025 Stock Investment</p>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const emit = defineEmits(['navigate'])
const route = useRoute()

const isActive = (path) => {
  // Exact match for home
  if (path === '/') {
    return route.path === '/'
      ? 'bg-indigo-50 text-indigo-600'
      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
  }
  // Prefix match for other routes
  return route.path.startsWith(path)
    ? 'bg-indigo-50 text-indigo-600'
    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
}
</script>

<style scoped>
.nav-item {
  @apply flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer;
}

.nav-item-disabled {
  @apply opacity-50 cursor-not-allowed;
  pointer-events: none;
}

.nav-section-title {
  @apply px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider;
}
</style>
