<template>
  <el-container style="min-height: 100vh">
    <el-aside width="200px" class="aside">
      <div class="logo">🅜 MyJQR</div>
      <el-menu router :default-active="$route.path" class="menu">
        <el-menu-item index="/market">🧩 模板市场</el-menu-item>
        <el-menu-item index="/create">✍️ 开始创作</el-menu-item>
        <el-menu-item index="/works">📚 我的作品</el-menu-item>
        <el-menu-item index="/joule">💰 我的焦耳</el-menu-item>
      </el-menu>
      <div class="user-box">
        <div>{{ auth.nickname || '用户' }}</div>
        <div class="joule">{{ auth.joule }} J</div>
        <el-button size="small" text @click="logout">退出</el-button>
      </div>
    </el-aside>
    <el-main><router-view /></el-main>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import { get } from '../api/http'

const auth = useAuth()
const router = useRouter()

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
</style>
