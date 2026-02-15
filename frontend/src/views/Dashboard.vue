<template>
  <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
    <!-- Portfolios Card -->
    <router-link
      to="/portfolios"
      class="bg-white overflow-hidden shadow rounded-lg hover:shadow-md transition-shadow"
    >
      <div class="px-4 py-5 sm:p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-indigo-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">
                Portfolios
              </dt>
              <dd class="text-lg font-semibold text-gray-900">
                Manage Accounts
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </router-link>

    <!-- Stocks Card -->
    <router-link
      to="/stocks"
      class="bg-white overflow-hidden shadow rounded-lg hover:shadow-md transition-shadow"
    >
      <div class="px-4 py-5 sm:p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-green-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">
                Stocks
              </dt>
              <dd class="text-lg font-semibold text-gray-900">
                Browse & Import
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </router-link>

    <!-- Holdings Card (Coming Soon) -->
    <div class="bg-white overflow-hidden shadow rounded-lg opacity-50 cursor-not-allowed">
      <div class="px-4 py-5 sm:p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-gray-400 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">
                Holdings
              </dt>
              <dd class="text-lg font-semibold text-gray-900">
                Coming Soon
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Getting Started Section -->
  <div class="mt-8 bg-white shadow overflow-hidden sm:rounded-lg">
    <div class="px-4 py-5 sm:px-6">
      <h3 class="text-lg leading-6 font-medium text-gray-900">
        Getting Started
      </h3>
      <p class="mt-1 max-w-2xl text-sm text-gray-500">
        Your comprehensive stock investment management system
      </p>
    </div>
    <div class="border-t border-gray-200 px-4 py-5 sm:px-6">
      <dl class="grid grid-cols-1 gap-x-4 gap-y-8 sm:grid-cols-2">
        <div class="sm:col-span-2">
          <dt class="text-sm font-medium text-gray-500">Quick Actions</dt>
          <dd class="mt-1 text-sm text-gray-900">
            <ul class="list-disc pl-5 space-y-1">
              <li>Create your first portfolio to start tracking investments</li>
              <li>Import stocks from Yahoo Finance</li>
              <li>Add holdings to track your stock positions</li>
              <li>Set investment goals for each portfolio</li>
            </ul>
          </dd>
        </div>
      </dl>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const user = computed(() => authStore.user)
</script>
