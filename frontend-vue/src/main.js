import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia } from 'pinia'
import App from './App.vue'
import HomePage from './components/HomePage.vue'
import AnalysisPage from './components/AnalysisPage.vue'
import HistoryPage from './components/HistoryPage.vue'
import StatsPage from './components/StatsPage.vue'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomePage },
    { path: '/analysis', component: AnalysisPage },
    { path: '/history', component: HistoryPage },
    { path: '/stats', component: StatsPage }
  ]
})

const pinia = createPinia()
const app = createApp(App)

app.use(router)
app.use(pinia)
app.mount('#app')
