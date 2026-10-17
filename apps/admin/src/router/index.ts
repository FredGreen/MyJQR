import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes: [
    { path: '/login', component: () => import('../views/LoginView.vue') },
    {
      path: '/',
      component: () => import('../layouts/AdminLayout.vue'),
      children: [
        // base 已是 /admin/，路由内部路径不要再带前缀（写了会拼成 /admin/admin/* 导致空白页）
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', component: () => import('../views/DashboardView.vue') },
        { path: 'templates', component: () => import('../views/TemplatesView.vue') },
        { path: 'redeem', component: () => import('../views/RedeemView.vue') },
        { path: 'review', component: () => import('../views/ReviewView.vue') },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (to.path !== '/login' && !localStorage.getItem('admin_token')) return '/login'
})

export default router
