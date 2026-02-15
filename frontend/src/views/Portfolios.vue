<template>
  <div>
    <div class="px-4 py-6 sm:px-0">
        <div class="sm:flex sm:items-center">
          <div class="sm:flex-auto">
            <h1 class="text-2xl font-semibold text-gray-900">Portfolios</h1>
            <p class="mt-2 text-sm text-gray-700">
              Manage your investment accounts and track holdings
            </p>
          </div>
          <div class="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
            <button
              @click="showCreateModal = true"
              class="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              Add Portfolio
            </button>
          </div>
        </div>

        <div v-if="error" class="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {{ error }}
        </div>

        <div v-if="loading" class="mt-8 text-center">
          <p class="text-gray-500">Loading portfolios...</p>
        </div>

        <div v-else-if="portfolios.length === 0" class="mt-8 text-center">
          <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900">No portfolios</h3>
          <p class="mt-1 text-sm text-gray-500">Get started by creating a new portfolio.</p>
        </div>

        <div v-else class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div
            v-for="portfolio in portfolios"
            :key="portfolio.id"
            class="bg-white overflow-hidden shadow rounded-lg"
          >
            <div class="px-4 py-5 sm:p-6">
              <div class="flex items-center justify-between">
                <h3 class="text-lg font-medium text-gray-900">{{ portfolio.name }}</h3>
                <div class="flex space-x-2">
                  <button
                    @click="editPortfolio(portfolio)"
                    class="text-indigo-600 hover:text-indigo-900"
                  >
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    @click="confirmDelete(portfolio)"
                    class="text-red-600 hover:text-red-900"
                  >
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
              <div class="mt-4 space-y-2">
                <div v-if="portfolio.broker" class="text-sm text-gray-500">
                  <span class="font-medium">Broker:</span> {{ portfolio.broker }}
                </div>
                <div v-if="portfolio.accountType" class="flex items-center space-x-2">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                    {{ formatAccountType(portfolio.accountType) }}
                  </span>
                  <span v-if="portfolio.taxDeferred" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Tax Deferred
                  </span>
                  <span v-if="portfolio.taxFree" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    Tax Free
                  </span>
                </div>
                <div v-if="portfolio.contributionLimit" class="text-sm text-gray-500">
                  <span class="font-medium">Contribution Limit:</span> ${{ portfolio.contributionLimit.toLocaleString() }}
                </div>
              </div>
            </div>
          </div>
        </div>
    </div>

    <!-- Create/Edit Modal -->
    <div v-if="showCreateModal || editingPortfolio" class="fixed z-10 inset-0 overflow-y-auto">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="closeModal"></div>
        <div class="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div>
            <h3 class="text-lg font-medium text-gray-900">
              {{ editingPortfolio ? 'Edit Portfolio' : 'Create Portfolio' }}
            </h3>
            <form @submit.prevent="savePortfolio" class="mt-6 space-y-4">
              <div>
                <label for="name" class="block text-sm font-medium text-gray-700">Name *</label>
                <input
                  id="name"
                  v-model="formData.name"
                  type="text"
                  required
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                />
              </div>
              <div>
                <label for="broker" class="block text-sm font-medium text-gray-700">Broker</label>
                <input
                  id="broker"
                  v-model="formData.broker"
                  type="text"
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                />
              </div>
              <div>
                <label for="accountType" class="block text-sm font-medium text-gray-700">Account Type</label>
                <select
                  id="accountType"
                  v-model="formData.accountType"
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                >
                  <option value="">Select type</option>
                  <option value="CASH">Cash</option>
                  <option value="MARGIN">Margin</option>
                  <option value="IRA_TRADITIONAL">IRA Traditional</option>
                  <option value="IRA_ROTH">IRA Roth</option>
                  <option value="401K">401K</option>
                  <option value="TAXABLE">Taxable</option>
                </select>
              </div>
              <div class="flex items-center space-x-6">
                <div class="flex items-center">
                  <input
                    id="taxDeferred"
                    v-model="formData.taxDeferred"
                    type="checkbox"
                    class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <label for="taxDeferred" class="ml-2 block text-sm text-gray-900">
                    Tax Deferred
                  </label>
                </div>
                <div class="flex items-center">
                  <input
                    id="taxFree"
                    v-model="formData.taxFree"
                    type="checkbox"
                    class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <label for="taxFree" class="ml-2 block text-sm text-gray-900">
                    Tax Free
                  </label>
                </div>
              </div>
              <div>
                <label for="contributionLimit" class="block text-sm font-medium text-gray-700">Contribution Limit</label>
                <input
                  id="contributionLimit"
                  v-model.number="formData.contributionLimit"
                  type="number"
                  step="0.01"
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                />
              </div>
              <div class="flex items-center">
                <input
                  id="withdrawalPenalty"
                  v-model="formData.withdrawalPenalty"
                  type="checkbox"
                  class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
                <label for="withdrawalPenalty" class="ml-2 block text-sm text-gray-900">
                  Withdrawal Penalty
                </label>
              </div>
              <div v-if="modalError" class="text-red-600 text-sm">
                {{ modalError }}
              </div>
              <div class="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                <button
                  type="submit"
                  :disabled="saving"
                  class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:col-start-2 sm:text-sm disabled:opacity-50"
                >
                  {{ saving ? 'Saving...' : 'Save' }}
                </button>
                <button
                  type="button"
                  @click="closeModal"
                  class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:col-start-1 sm:text-sm"
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
    <div v-if="deleteConfirmation" class="fixed z-10 inset-0 overflow-y-auto">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="deleteConfirmation = null"></div>
        <div class="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div class="sm:flex sm:items-start">
            <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
              <svg class="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
              <h3 class="text-lg leading-6 font-medium text-gray-900">Delete Portfolio</h3>
              <div class="mt-2">
                <p class="text-sm text-gray-500">
                  Are you sure you want to delete "{{ deleteConfirmation.name }}"? This action cannot be undone.
                </p>
              </div>
            </div>
          </div>
          <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
            <button
              @click="deletePortfolio"
              :disabled="deleting"
              class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
            >
              {{ deleting ? 'Deleting...' : 'Delete' }}
            </button>
            <button
              @click="deleteConfirmation = null"
              class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:w-auto sm:text-sm"
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
import { portfolioAPI } from '../api/portfolio'
const portfolios = ref([])
const loading = ref(false)
const error = ref('')
const showCreateModal = ref(false)
const editingPortfolio = ref(null)
const deleteConfirmation = ref(null)
const saving = ref(false)
const deleting = ref(false)
const modalError = ref('')

const formData = ref({
  name: '',
  broker: '',
  accountType: '',
  taxDeferred: false,
  taxFree: false,
  contributionLimit: null,
  withdrawalPenalty: false
})

const formatAccountType = (type) => {
  const types = {
    'CASH': 'Cash',
    'MARGIN': 'Margin',
    'IRA_TRADITIONAL': 'IRA Traditional',
    'IRA_ROTH': 'IRA Roth',
    '401K': '401K',
    'TAXABLE': 'Taxable'
  }
  return types[type] || type
}

const fetchPortfolios = async () => {
  try {
    loading.value = true
    error.value = ''
    const response = await portfolioAPI.getAll()
    portfolios.value = response.data
  } catch (err) {
    error.value = err.response?.data?.message || 'Failed to load portfolios'
  } finally {
    loading.value = false
  }
}

const editPortfolio = (portfolio) => {
  editingPortfolio.value = portfolio
  formData.value = {
    name: portfolio.name,
    broker: portfolio.broker || '',
    accountType: portfolio.accountType || '',
    taxDeferred: portfolio.taxDeferred || false,
    taxFree: portfolio.taxFree || false,
    contributionLimit: portfolio.contributionLimit || null,
    withdrawalPenalty: portfolio.withdrawalPenalty || false
  }
}

const confirmDelete = (portfolio) => {
  deleteConfirmation.value = portfolio
}

const closeModal = () => {
  showCreateModal.value = false
  editingPortfolio.value = null
  modalError.value = ''
  formData.value = {
    name: '',
    broker: '',
    accountType: '',
    taxDeferred: false,
    taxFree: false,
    contributionLimit: null,
    withdrawalPenalty: false
  }
}

const savePortfolio = async () => {
  try {
    saving.value = true
    modalError.value = ''

    if (editingPortfolio.value) {
      await portfolioAPI.update(editingPortfolio.value.id, formData.value)
    } else {
      await portfolioAPI.create(formData.value)
    }

    closeModal()
    await fetchPortfolios()
  } catch (err) {
    modalError.value = err.response?.data?.message || 'Failed to save portfolio'
  } finally {
    saving.value = false
  }
}

const deletePortfolio = async () => {
  try {
    deleting.value = true
    await portfolioAPI.delete(deleteConfirmation.value.id)
    deleteConfirmation.value = null
    await fetchPortfolios()
  } catch (err) {
    error.value = err.response?.data?.message || 'Failed to delete portfolio'
    deleteConfirmation.value = null
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  fetchPortfolios()
})
</script>
