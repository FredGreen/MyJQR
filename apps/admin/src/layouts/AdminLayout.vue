<template>
  <el-container style="min-height: 100vh">
    <!-- 桌面侧栏（<768px 隐藏） -->
    <el-aside width="200px" class="aside desktop-only">
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

    <el-container>
      <!-- 手机顶栏（>=768px 隐藏） -->
      <el-header class="mobile-header" height="52px">
        <el-button text class="burger" @click="drawer = true">☰</el-button>
        <b>🛠 MyJQR 后台</b>
        <el-button size="small" text @click="logout">退出</el-button>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>

    <!-- 手机抽屉菜单 -->
    <el-drawer v-model="drawer" direction="ltr" size="70%" :with-header="false">
      <div class="drawer-logo">🛠 MyJQR 后台</div>
      <el-menu router :default-active="$route.path" @select="drawer = false">
        <el-menu-item index="/dashboard">📊 数据看板</el-menu-item>
        <el-menu-item index="/templates">🧩 模板管理</el-menu-item>
        <el-menu-item index="/users">👥 用户管理</el-menu-item>
        <el-menu-item index="/works">📄 作品列表</el-menu-item>
        <el-menu-item index="/redeem">🎟 兑换码</el-menu-item>
        <el-menu-item index="/review">🛡 内容审核</el-menu-item>
      </el-menu>
    </el-drawer>
  </el-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()
const drawer = ref(false)

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

.mobile-header {
  display: none;
  align-items: center;
  justify-content: space-between;
  background: #1b2a4a;
  color: #fff;
  padding: 0 8px;
}
.drawer-logo { font-weight: 700; padding: 14px 16px; color: #1b2a4a; }

@media (max-width: 768px) {
  .desktop-only { display: none; }
  .mobile-header { display: flex; }
  .mobile-header .burger { color: #fff; font-size: 20px; }
}
</style>
