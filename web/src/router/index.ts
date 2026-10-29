import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import FlowspecView from '../views/FlowspecView.vue'
import PrefixInventoryView from '../views/PrefixInventoryView.vue'
import PseudoRibsView from '../views/PseudoRibsView.vue'
import AnnouncementsView from '../views/AnnouncementsView.vue'
import PeersView from '../views/PeersView.vue'
import SettingsView from '../views/SettingsView.vue'
import LoginView from '../views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true },
    },
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true },
    },
    {
      path: '/flowspec',
      name: 'flowspec',
      component: FlowspecView,
      meta: { requiresAuth: true },
    },
    {
      path: '/prefixes',
      name: 'prefixes',
      component: PrefixInventoryView,
      meta: { requiresAuth: true },
    },
    {
      path: '/pseudo-ribs',
      name: 'pseudo-ribs',
      component: PseudoRibsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/announcements',
      name: 'announcements',
      component: AnnouncementsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/peers',
      name: 'peers',
      component: PeersView,
      meta: { requiresAuth: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { requiresAuth: true },
    },
  ],
})

// Navigation Guard: Protect routes and redirect unauthenticated users
router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')

  if (to.meta.requiresAuth && !token) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.meta.guestOnly && token) {
    return { path: '/' }
  }
})

export default router
