import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/LoginView.vue') },
    {
      path: '/',
      component: () => import('../layouts/MainLayout.vue'),
      children: [
        { path: '', redirect: '/create' },
        { path: 'market', component: () => import('../views/MarketView.vue') },
        { path: 'create', component: () => import('../views/CreateView.vue') },
        { path: 'works', component: () => import('../views/WorksView.vue') },
        { path: 'joule', component: () => import('../views/JouleView.vue') },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (to.path !== '/login' && !localStorage.getItem('access_token')) return '/login'
})

export default router
