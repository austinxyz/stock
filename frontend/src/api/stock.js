import api from './axios'

export const stockAPI = {
  getAll: () => api.get('/stocks'),
  getById: (id) => api.get(`/stocks/${id}`),
  getBySymbol: (symbol) => api.get(`/stocks/symbol/${symbol}`),
  search: (keyword) => api.get('/stocks/search', { params: { keyword } }),
  create: (data) => api.post('/stocks', data),
  importFromYahoo: (symbol) => api.post(`/stocks/import/${symbol}`),
  update: (id, data) => api.put(`/stocks/${id}`, data),
  updatePrice: (symbol) => api.put(`/stocks/price/${symbol}`),
  delete: (id) => api.delete(`/stocks/${id}`)
}
