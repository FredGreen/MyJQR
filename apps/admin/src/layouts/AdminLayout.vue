<template>
  <el-container style="min-height: 100vh">
    <el-aside width="200px" class="aside">
      <div class="logo">🛠 MyJQR 后台</div>
      <el-menu router :default-active="$route.path" class="menu">
        <el-menu-item index="/dashboard">📊 数据看板</el-menu-item>
        <el-menu-item index="/templates">🧩 模板管理</el-menu-item>
        <el-menu-item index="/users">👥 用户管理</el-menu-item>
        <el-menu-item index="/works">📄 作品列表</el-menu-item>
        <el-menu-item index="/redeem">🎟 兑换码</el-menu-item>
        <el-menu-item index="/review">🛡 内容审核</el-menu-item>
      </el-menu>
      <div class="user-box"><el-button size="small" text @click="logout">退出登录</el-button></div>
    </el-aside>
    <el-main><router-view /></el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
function logout() {
  localStorage.removeItem('admin_token')
  router.push('/login')
}
</script>

<style scoped>
.aside { background: #1b2a4a; display: flex; flex-direction: column; }
.logo { color: #fff; font-weight: 700; padding: 20px 16px; }
.menu { border-right: none; flex: 1; background: transparent; }
:deep(.el-menu-item) { color: #cfd6e4; }
:deep(.el-menu-item.is-active) { color: #fff; background: #2c3e6b; }
.user-box { padding: 12px 16px; }
</style>
