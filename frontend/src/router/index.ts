import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import ForgotPassword from '@/views/ForgotPassword.vue'
import LoadingPage from '@/views/LoadingPage.vue'
import ScenarioList from '@/views/ScenarioList.vue'
import TrainingRoom from '@/views/TrainingRoom.vue'
import ReportDetail from '@/views/ReportDetail.vue'
import Profile from '@/views/Profile.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: Login },
    { path: '/register', component: Register },
    { path: '/forgot-password', component: ForgotPassword },
    { path: '/loading', component: LoadingPage },
    { path: '/scenarios', component: ScenarioList },
    { path: '/training/:sessionId', component: TrainingRoom },
    { path: '/report/:sessionId', component: ReportDetail },
    { path: '/profile', component: Profile },
  ],
})

export default router
