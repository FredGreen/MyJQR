<template>
  <div class="login-wrap">
    <el-card class="card">
      <h2>🅜 MyJQR · AI 写作</h2>
      <el-tabs v-model="tab">
        <el-tab-pane label="登录" name="login">
          <el-form @keyup.enter="doLogin">
            <el-input v-model="loginForm.email" placeholder="邮箱" size="large" />
            <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" style="margin-top:12px" />
            <el-button type="primary" size="large" style="width:100%;margin-top:16px" :loading="loading" @click="doLogin">登录</el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册（送{{gift}}焦耳）" name="register">
          <el-form @keyup.enter="doRegister">
            <el-input v-model="regForm.email" placeholder="邮箱" size="large" />
            <el-input v-model="regForm.nickname" placeholder="昵称" size="large" style="margin-top:12px" />
            <el-input v-model="regForm.password" type="password" placeholder="密码（≥8位）" size="large" style="margin-top:12px" />
            <el-button type="primary" size="large" style="width:100%;margin-top:16px" :loading="loading" @click="doRegister">注册</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { post } from '../api/http'
import { useAuth } from '../stores/auth'

const tab = ref('login')
const loading = ref(false)
const gift = 100
const router = useRouter()
const auth = useAuth()
const loginForm = reactive({ email: '', password: '' })
const regForm = reactive({ email: '', nickname: '', password: '' })

async function doLogin() {
  loading.value = true
  try {
    const r = await post('/auth/login', loginForm)
    auth.setTokens(r.data.tokens)
    auth.setProfile(r.data.nickname, 0)
    router.push('/market')
  } catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

async function doRegister() {
  loading.value = true
  try {
    const r = await post('/auth/register', regForm)
    auth.setTokens(r.data.tokens)
    ElMessage.success(`注册成功，已赠送 ${gift} 焦耳`)
    router.push('/market')
  } catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}
</script>

<style scoped>
.login-wrap { height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg,#1b2a4a,#2c3e6b); }
.card { width: 400px; }
h2 { margin: 0 0 16px; color: #1b2a4a; }
</style>
