import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import MainLayout from '../components/MainLayout.vue'
import Dashboard from '../views/Dashboard.vue'
import Portfolios from '../views/Portfolios.vue'
import Stocks from '../views/Stocks.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: Dashboard,
        meta: {
          requiresAuth: true,
          title: 'Dashboard',
          description: 'Overview of your investment portfolio'
        }
      },
      {
        path: 'portfolios',
        name: 'Portfolios',
        component: Portfolios,
        meta: {
          requiresAuth: true,
          title: 'Portfolios',
          description: 'Manage your investment accounts'
        }
      },
      {
        path: 'stocks',
        name: 'Stocks',
        component: Stocks,
        meta: {
          requiresAuth: true,
          title: 'Stocks',
          description: 'Browse and import stock information'
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard for authentication
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (!to.meta.requiresAuth && token && (to.name === 'Login' || to.name === 'Register')) {
    next('/')
  } else {
    next()
  }
})

export default router
