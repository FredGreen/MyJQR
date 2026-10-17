<template>
  <div class="wrap">
    <el-card class="card">
      <h2>🛠 MyJQR 管理后台</h2>
      <el-input v-model="username" placeholder="用户名" size="large" />
      <el-input v-model="password" type="password" placeholder="密码" size="large" style="margin-top:12px" @keyup.enter="login" />
      <el-button type="primary" size="large" style="width:100%;margin-top:16px" :loading="loading" @click="login">登录</el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { post } from '../api/http'

const username = ref('')
const password = ref('')
const loading = ref(false)
const router = useRouter()

async function login() {
  loading.value = true
  try {
    const r = await post('/admin/login', { username: username.value, password: password.value })
    localStorage.setItem('admin_token', r.data.access_token)
    router.push('/dashboard')
  } catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}
</script>

<style scoped>
.wrap { height: 100vh; display: flex; align-items: center; justify-content: center; background: #1b2a4a; }
.card { width: 380px; }
</style>
