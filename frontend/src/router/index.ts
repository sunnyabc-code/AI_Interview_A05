import { createRouter, createWebHistory } from 'vue-router'
import EvaluationReviewView from '@/views/EvaluationReviewView.vue'
import EvaluationAbilityView from '@/views/EvaluationAbilityView.vue'

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
      path: '/interview/:id',
      name: 'interview-session',
      component: () => import('../views/InterviewSessionView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/evaluation',
      name: 'evaluation',
      redirect: '/home?menu=evaluation',
      meta: { requiresAuth: true }
    },
    {
      path: '/evaluation/review',
      name: 'evaluation-review',
      component: EvaluationReviewView,
      meta: { requiresAuth: true }
    },
    {
      path: '/evaluation/ability',
      name: 'evaluation-ability',
      component: EvaluationAbilityView,
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
