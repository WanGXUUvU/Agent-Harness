import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/coding'
    },
    {
      path: '/coding',
      name: 'Coding',
      component: () => import('../views/CodingView.vue')
    },
    {
      path: '/assistant',
      redirect: '/coding'
    }
  ]
})

export default router
