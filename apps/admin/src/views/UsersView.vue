<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2>用户管理</h2>
      <div style="display:flex;gap:8px">
        <el-input v-model="q" placeholder="搜索邮箱" clearable style="width:240px"
                  @keyup.enter="search" @clear="search" />
        <el-button @click="search">搜索</el-button>
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
    <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                   layout="total, prev, pager, next" background
                   style="margin-top:14px;justify-content:flex-end;flex-wrap:wrap"
                   @current-change="load" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '../api/http'

const router = useRouter()
const rows = ref<any[]>([])
const q = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)

onMounted(load)

async function load() {
  const params = new URLSearchParams({ page: String(page.value), page_size: String(pageSize) })
  if (q.value) params.set('q', q.value)
  const r = await get(`/admin/users?${params}`)
  rows.value = r.data.list
  total.value = r.data.total
}

function search() {
  page.value = 1
  load()
}

function viewWorks(row: any) {
  router.push({ path: '/works', query: { user_id: row.id } })
}
</script>
