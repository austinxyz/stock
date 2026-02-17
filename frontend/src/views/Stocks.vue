<template>
  <div>
    <div class="px-4 py-6 sm:px-0">
        <div class="sm:flex sm:items-center">
          <div class="sm:flex-auto">
            <h1 class="text-2xl font-semibold text-gray-900">Stocks</h1>
            <p class="mt-2 text-sm text-gray-700">
              Search and manage stock information
            </p>
          </div>
          <div class="mt-4 sm:mt-0 sm:ml-16 sm:flex-none space-x-3">
            <button
              @click="showManualModal = true"
              class="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
            >
              Add Manually
            </button>
            <button
              @click="showImportModal = true"
              class="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
            >
              Import from Yahoo
            </button>
          </div>
        </div>

        <div class="mt-6">
          <input
            v-model="searchKeyword"
            @input="handleSearch"
            type="text"
            placeholder="Search by symbol or name..."
            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
          />
        </div>

        <div v-if="error" class="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {{ error }}
        </div>

        <div v-if="loading" class="mt-8 text-center">
          <p class="text-gray-500">Loading stocks...</p>
        </div>

        <div v-else-if="stocks.length === 0" class="mt-8 text-center">
          <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900">No stocks found</h3>
          <p class="mt-1 text-sm text-gray-500">Import stocks from Yahoo Finance to get started.</p>
        </div>

        <div v-else class="mt-8 overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
          <table class="min-w-full divide-y divide-gray-300">
            <thead class="bg-gray-50">
              <tr>
                <th class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900">Symbol</th>
                <th class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Name</th>
                <th class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Market</th>
                <th class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Type</th>
                <th class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Sector</th>
                <th class="px-3 py-3.5 text-right text-sm font-semibold text-gray-900">Price</th>
                <th class="relative py-3.5 pl-3 pr-4 sm:pr-6">
                  <span class="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 bg-white">
              <tr v-for="stock in stocks" :key="stock.id">
                <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900">
                  {{ stock.symbol }}
                </td>
                <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                  {{ stock.name }}
                </td>
                <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {{ stock.market }}
                  </span>
                </td>
                <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                  <span :class="[
                    'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                    stock.securityType === 'ETF' ? 'bg-purple-100 text-purple-800' : 'bg-green-100 text-green-800'
                  ]">
                    {{ stock.securityType || 'STOCK' }}
                  </span>
                </td>
                <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                  {{ stock.sector || '-' }}
                </td>
                <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 text-right">
                  -
                </td>
                <td class="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                  <button
                    @click="updatePrice(stock.symbol)"
                    class="text-indigo-600 hover:text-indigo-900 mr-4"
                  >
                    Refresh
                  </button>
                  <button
                    @click="confirmDelete(stock)"
                    class="text-red-600 hover:text-red-900"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
    </div>

    <!-- Manual Add Modal -->
    <div v-if="showManualModal" class="fixed z-50 inset-0 overflow-y-auto">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="closeManualModal"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="relative inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div>
            <h3 class="text-lg font-medium text-gray-900">Add Stock Manually</h3>
            <form @submit.prevent="handleManualAdd" class="mt-6 space-y-4">
              <div>
                <label for="manual-symbol" class="block text-sm font-medium text-gray-700">Symbol *</label>
                <input
                  id="manual-symbol"
                  v-model="manualStock.symbol"
                  type="text"
                  required
                  placeholder="e.g., AAPL"
                  class="mt-1 block w-full rounded-md border border-gray-300 bg-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 uppercase"
                />
              </div>
              <div>
                <label for="manual-name" class="block text-sm font-medium text-gray-700">Name *</label>
                <input
                  id="manual-name"
                  v-model="manualStock.name"
                  type="text"
                  required
                  placeholder="e.g., Apple Inc."
                  class="mt-1 block w-full rounded-md border border-gray-300 bg-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2"
                />
              </div>
              <div>
                <label for="manual-market" class="block text-sm font-medium text-gray-700">Market *</label>
                <select
                  id="manual-market"
                  v-model="manualStock.market"
                  required
                  class="mt-1 block w-full rounded-md border border-gray-300 bg-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2"
                >
                  <option value="">Select Market</option>
                  <option value="US">US</option>
                  <option value="HK">HK</option>
                  <option value="CN">CN</option>
                </select>
              </div>
              <div>
                <label for="manual-type" class="block text-sm font-medium text-gray-700">Type</label>
                <select
                  id="manual-type"
                  v-model="manualStock.securityType"
                  class="mt-1 block w-full rounded-md border border-gray-300 bg-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2"
                >
                  <option value="STOCK">STOCK</option>
                  <option value="ETF">ETF</option>
                </select>
              </div>
              <div>
                <label for="manual-sector" class="block text-sm font-medium text-gray-700">Sector</label>
                <input
                  id="manual-sector"
                  v-model="manualStock.sector"
                  type="text"
                  placeholder="e.g., Technology"
                  class="mt-1 block w-full rounded-md border border-gray-300 bg-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2"
                />
              </div>
              <div>
                <label for="manual-industry" class="block text-sm font-medium text-gray-700">Industry</label>
                <input
                  id="manual-industry"
                  v-model="manualStock.industry"
                  type="text"
                  placeholder="e.g., Consumer Electronics"
                  class="mt-1 block w-full rounded-md border border-gray-300 bg-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2"
                />
              </div>
              <div v-if="manualError" class="text-red-600 text-sm">
                {{ manualError }}
              </div>
              <div class="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3">
                <button
                  type="submit"
                  :disabled="addingManual"
                  class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 sm:col-start-2 sm:text-sm disabled:opacity-50"
                >
                  {{ addingManual ? 'Adding...' : 'Add Stock' }}
                </button>
                <button
                  type="button"
                  @click="closeManualModal"
                  class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 sm:mt-0 sm:col-start-1 sm:text-sm"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- Import Modal -->
    <div v-if="showImportModal" class="fixed z-50 inset-0 overflow-y-auto">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="closeImportModal"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="relative inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div>
            <h3 class="text-lg font-medium text-gray-900">Import Stock from Yahoo Finance</h3>
            <form @submit.prevent="handleImport" class="mt-6 space-y-4">
              <div>
                <label for="symbol" class="block text-sm font-medium text-gray-700">Stock Symbol *</label>
                <input
                  id="symbol"
                  v-model="importSymbol"
                  type="text"
                  required
                  placeholder="e.g., AAPL, TSLA, QQQ"
                  class="mt-1 block w-full rounded-md border border-gray-300 bg-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 uppercase"
                />
                <p class="mt-1 text-xs text-gray-500">
                  Enter the stock symbol as listed on Yahoo Finance
                </p>
              </div>
              <div v-if="importError" class="text-red-600 text-sm">
                {{ importError }}
              </div>
              <div class="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3">
                <button
                  type="submit"
                  :disabled="importing"
                  class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 sm:col-start-2 sm:text-sm disabled:opacity-50"
                >
                  {{ importing ? 'Importing...' : 'Import' }}
                </button>
                <button
                  type="button"
                  @click="closeImportModal"
                  class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 sm:mt-0 sm:col-start-1 sm:text-sm"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="deleteConfirmation" class="fixed z-50 inset-0 overflow-y-auto">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="deleteConfirmation = null"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="relative inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div class="sm:flex sm:items-start">
            <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
              <svg class="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
              <h3 class="text-lg leading-6 font-medium text-gray-900">Delete Stock</h3>
              <div class="mt-2">
                <p class="text-sm text-gray-500">
                  Are you sure you want to delete "{{ deleteConfirmation.symbol }}"? This will also remove it from any holdings.
                </p>
              </div>
            </div>
          </div>
          <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
            <button
              @click="deleteStock"
              :disabled="deleting"
              class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
            >
              {{ deleting ? 'Deleting...' : 'Delete' }}
            </button>
            <button
              @click="deleteConfirmation = null"
              class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 sm:mt-0 sm:w-auto sm:text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { stockAPI } from '../api/stock'
const stocks = ref([])
const loading = ref(false)
const error = ref('')
const searchKeyword = ref('')
const showImportModal = ref(false)
const importSymbol = ref('')
const importing = ref(false)
const importError = ref('')
const showManualModal = ref(false)
const manualStock = ref({
  symbol: '',
  name: '',
  market: '',
  securityType: 'STOCK',
  sector: '',
  industry: ''
})
const addingManual = ref(false)
const manualError = ref('')
const deleteConfirmation = ref(null)
const deleting = ref(false)

const formatPrice = (price, currency) => {
  const formatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
  return formatter.format(price)
}

const fetchStocks = async () => {
  try {
    loading.value = true
    error.value = ''
    const response = await stockAPI.getAll()
    stocks.value = response.data
  } catch (err) {
    error.value = err.response?.data?.message || 'Failed to load stocks'
  } finally {
    loading.value = false
  }
}

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    await fetchStocks()
    return
  }

  try {
    loading.value = true
    error.value = ''
    const response = await stockAPI.search(searchKeyword.value)
    stocks.value = response.data
  } catch (err) {
    error.value = err.response?.data?.message || 'Search failed'
  } finally {
    loading.value = false
  }
}

const closeImportModal = () => {
  showImportModal.value = false
  importSymbol.value = ''
  importError.value = ''
}

const closeManualModal = () => {
  showManualModal.value = false
  manualStock.value = {
    symbol: '',
    name: '',
    market: '',
    securityType: 'STOCK',
    sector: '',
    industry: ''
  }
  manualError.value = ''
}

const handleImport = async () => {
  try {
    importing.value = true
    importError.value = ''
    await stockAPI.importFromYahoo(importSymbol.value.toUpperCase())
    closeImportModal()
    await fetchStocks()
  } catch (err) {
    importError.value = err.response?.data?.message || 'Failed to import stock'
  } finally {
    importing.value = false
  }
}

const handleManualAdd = async () => {
  try {
    addingManual.value = true
    manualError.value = ''
    await stockAPI.create({
      ...manualStock.value,
      symbol: manualStock.value.symbol.toUpperCase()
    })
    closeManualModal()
    await fetchStocks()
  } catch (err) {
    manualError.value = err.response?.data?.message || 'Failed to add stock'
  } finally {
    addingManual.value = false
  }
}

const updatePrice = async (symbol) => {
  try {
    await stockAPI.updatePrice(symbol)
    await fetchStocks()
  } catch (err) {
    error.value = `Failed to update price for ${symbol}`
  }
}

const confirmDelete = (stock) => {
  deleteConfirmation.value = stock
}

const deleteStock = async () => {
  try {
    deleting.value = true
    await stockAPI.delete(deleteConfirmation.value.id)
    deleteConfirmation.value = null
    await fetchStocks()
  } catch (err) {
    error.value = err.response?.data?.message || 'Failed to delete stock'
    deleteConfirmation.value = null
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  fetchStocks()
})
</script>
