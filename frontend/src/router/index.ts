import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
    { path: '/', redirect: '/problems' },
    { path: '/problems', name: 'problems', component: () => import('../views/ProblemListView.vue') },
    { path: '/problems/:id', name: 'problem', component: () => import('../views/ProblemDetailView.vue') },
    { path: '/submissions', name: 'submissions', component: () => import('../views/SubmissionsView.vue') },
  ],
})

// 路由守卫：未登录跳登录页；已登录访问登录页跳题库
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && auth.isLoggedIn) {
    return { path: '/problems' }
  }
})

export default router
