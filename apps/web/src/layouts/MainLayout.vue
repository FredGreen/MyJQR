<template>
  <el-container style="min-height: 100vh" class="layout">
    <!-- 桌面侧栏（<768px 隐藏） -->
    <el-aside width="200px" class="aside desktop-only">
      <div class="logo">🅜 MyJQR</div>
      <el-menu router :default-active="$route.path" class="menu">
        <el-menu-item index="/create">✍️ 开始创作</el-menu-item>
        <el-menu-item index="/market">🧩 模板市场</el-menu-item>
        <el-menu-item index="/works">📚 我的作品</el-menu-item>
        <el-menu-item index="/joule">💰 我的焦耳</el-menu-item>
      </el-menu>
      <div class="user-box">
        <div>{{ auth.nickname || '用户' }}</div>
        <div class="joule">{{ auth.joule }} J</div>
        <el-button size="small" text @click="logout">退出</el-button>
      </div>
    </el-aside>

    <el-container>
      <!-- 手机顶栏：昵称 + 余额 + 退出 -->
      <el-header class="mobile-header" height="48px">
        <b>🅜 {{ auth.nickname || 'MyJQR' }}</b>
        <span class="m-joule">{{ auth.joule }} J</span>
        <el-button size="small" text @click="logout">退出</el-button>
      </el-header>
      <el-main class="main"><router-view /></el-main>
    </el-container>

    <!-- 手机底部导航 -->
    <nav class="bottom-nav">
      <router-link v-for="n in navs" :key="n.to" :to="n.to" class="bn-item"
                   :class="{ on: $route.path === n.to }">
        <span class="bn-ico">{{ n.ico }}</span><span>{{ n.label }}</span>
      </router-link>
    </nav>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import { get } from '../api/http'

const auth = useAuth()
const router = useRouter()
const navs = [
  { to: '/create', ico: '✍️', label: '创作' },
  { to: '/market', ico: '🧩', label: '市场' },
  { to: '/works', ico: '📚', label: '作品' },
  { to: '/joule', ico: '💰', label: '焦耳' },
]

onMounted(async () => {
  try {
    const r = await get('/auth/me')
    auth.setProfile(r.data.nickname, r.data.joule.balance)
  } catch { /* 401 已自动跳登录 */ }
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.aside { background: #fff; border-right: 1px solid #eee; display: flex; flex-direction: column; }
.logo { font-size: 20px; font-weight: 700; padding: 20px 16px; color: #1b2a4a; }
.menu { border-right: none; flex: 1; }
.user-box { padding: 16px; border-top: 1px solid #eee; font-size: 13px; }
.joule { color: #d4820a; margin: 4px 0; }

.mobile-header {
  display: none;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #eee;
  padding: 0 12px;
}
.m-joule { color: #d4820a; font-size: 14px; margin-left: auto; margin-right: 8px; }

.bottom-nav { display: none; }

@media (max-width: 768px) {
  .desktop-only { display: none; }
  .mobile-header { display: flex; }
  .main { padding: 12px 12px calc(64px + env(safe-area-inset-bottom)); }
  .bottom-nav {
    display: flex;
    position: fixed;
    left: 0; right: 0; bottom: 0;
    background: #fff;
    border-top: 1px solid #eee;
    padding-bottom: env(safe-area-inset-bottom);
    z-index: 100;
  }
  .bn-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 8px 0 6px;
    font-size: 12px;
    color: #909399;
    text-decoration: none;
  }
  .bn-item.on { color: #1b2a4a; font-weight: 600; }
  .bn-ico { font-size: 20px; line-height: 1; }
}
</style>
