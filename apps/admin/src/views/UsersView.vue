<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2>用户管理</h2>
      <div style="display:flex;gap:8px">
        <el-input v-model="q" placeholder="搜索邮箱" clearable style="width:240px"
                  @keyup.enter="reload" @clear="reload" />
        <el-button @click="reload">搜索</el-button>
      </div>
    </div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="email" label="邮箱" min-width="200" />
      <el-table-column prop="nickname" label="昵称" width="140" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
            {{ { 1: '正常', 2: '禁用', 3: '注销' }[row.status as 1 | 2 | 3] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="焦耳余额" width="110">
        <template #default="{ row }">{{ row.balance }} J<span v-if="row.frozen">（冻{{ row.frozen }}）</span></template>
      </el-table-column>
      <el-table-column label="作品数" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="viewWorks(row)">{{ row.work_cnt }}</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180" />
    </el-table>
    <el-button v-if="cursor" style="margin-top:12px" @click="loadMore">加载更多</el-button>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '../api/http'

const router = useRouter()
const rows = ref<any[]>([])
const q = ref('')
const cursor = ref(0)

onMounted(reload)

async function reload() {
  cursor.value = 0
  rows.value = []
  await loadMore()
}

async function loadMore() {
  const params = new URLSearchParams()
  if (q.value) params.set('q', q.value)
  if (cursor.value) params.set('cursor', String(cursor.value))
  const r = await get(`/admin/users?${params}`)
  rows.value.push(...r.data.list)
  cursor.value = r.data.cursor
}

function viewWorks(row: any) {
  router.push({ path: '/works', query: { user_id: row.id } })
}
</script>
