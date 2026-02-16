<template>
  <div class="flex h-screen bg-gray-50 overflow-hidden">
    <!-- Mobile Header (only visible on small screens) -->
    <header class="md:hidden fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 h-14 flex items-center px-4">
      <!-- Menu Button -->
      <button
        @click="toggleMobileSidebar"
        class="p-2 rounded-lg hover:bg-gray-100"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      <!-- Logo -->
      <router-link to="/" class="flex items-center ml-3">
        <div class="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
          <span class="text-white font-bold text-lg">📈</span>
        </div>
        <h1 class="ml-2 text-base font-bold text-gray-900">Stock Investment</h1>
      </router-link>
    </header>

    <!-- Overlay for mobile sidebar -->
    <div
      v-if="showMobileSidebar"
      @click="closeMobileSidebar"
      class="md:hidden fixed inset-0 bg-black/50 z-40 transition-opacity"
    ></div>

    <!-- Sidebar (responsive) -->
    <aside
      :class="[
        'fixed top-0 bottom-0 z-40 transition-transform duration-300 md:static',
        showMobileSidebar ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
      ]"
    >
      <Sidebar @navigate="closeMobileSidebar" />
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Top Bar (desktop only) -->
      <header class="hidden md:block bg-white border-b border-gray-200 shadow-sm">
        <div class="px-6 py-4">
          <div class="flex items-center justify-between">
            <!-- Breadcrumb / Page Title -->
            <div>
              <h2 class="text-xl font-semibold text-gray-900">{{ pageTitle }}</h2>
              <p v-if="pageDescription" class="text-sm text-gray-500 mt-1">
                {{ pageDescription }}
              </p>
            </div>

            <!-- User Actions -->
            <div class="flex items-center space-x-4">
              <div class="text-sm text-gray-600">
                Welcome, <span class="font-medium text-gray-900">{{ username }}</span>
              </div>
              <button
                @click="handleLogout"
                class="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <!-- Main Content -->
      <main class="flex-1 overflow-y-auto bg-gray-50 pt-14 md:pt-0">
        <div class="container mx-auto px-4 md:px-6 py-4 md:py-6">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RouterView } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import Sidebar from './Sidebar.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const showMobileSidebar = ref(false)

const pageTitle = computed(() => {
  return route.meta?.title || 'Stock Investment System'
})

const pageDescription = computed(() => {
  return route.meta?.description || ''
})

const username = computed(() => authStore.user?.username || 'Guest')

const toggleMobileSidebar = () => {
  showMobileSidebar.value = !showMobileSidebar.value
}

const closeMobileSidebar = () => {
  showMobileSidebar.value = false
}

const handleLogout = () => {
  authStore.clearAuth()
  router.push('/login')
}

// Auto-close sidebar on route change (mobile)
watch(() => route.path, () => {
  closeMobileSidebar()
})
</script>
