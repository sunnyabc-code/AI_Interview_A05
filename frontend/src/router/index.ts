import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'cover',
      component: () => import('../views/CoverView.vue'),
    },
    {
      path: '/auth',
      name: 'auth',
      component: () => import('../views/AuthView.vue'),
    },
    {
      path: '/home',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/create-interview',
      name: 'create-interview',
      component: () => import('../views/CreateInterviewView.vue'),
      meta: { requiresAuth: true }
    },
  ],
})

router.beforeEach((to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const isAuthenticated = localStorage.getItem('access_token')
  
  if (requiresAuth && !isAuthenticated) {
    next('/auth')
  } else {
    next()
  }
})

export default router
