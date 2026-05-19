import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/HomeStellariaView.vue'),
    meta: { title: '首页' },
  },
  {
    path: '/data',
    name: 'Data',
    component: () => import('../views/DataView.vue'),
    meta: { title: '数据管理' },
  },
  {
    path: '/model',
    name: 'Model',
    component: () => import('../views/ModelView.vue'),
    meta: { title: '表单建模' },
  },
  {
    path: '/results',
    name: 'Results',
    component: () => import('../views/ResultsView.vue'),
    meta: { title: '结果与导出' },
  },
  {
    path: '/home/:topic(product-position|core-value|analysis-flow|trust-export)',
    name: 'HomeKnowledge',
    component: () => import('../views/HomeKnowledgeView.vue'),
    meta: { title: '首页讲解' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} - OpenSEM` : 'OpenSEM'
})

export default router
