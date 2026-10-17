<template>
  <div>
    <h2>内容审核（机审可疑队列）</h2>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="#" width="70" />
      <el-table-column prop="biz_type" label="类型" width="100" />
      <el-table-column prop="biz_id" label="业务ID" width="100" />
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" type="success" @click="decide(row.id, 'pass')">放行</el-button>
          <el-button size="small" type="danger" @click="decide(row.id, 'block')">拦截</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                   layout="total, prev, pager, next" background
                   style="margin-top:14px;justify-content:flex-end;flex-wrap:wrap"
                   @current-change="load" />
    <el-empty v-if="!rows.length" description="队列为空" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { get, post } from '../api/http'

const rows = ref<any[]>([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
onMounted(load)

async function load() {
  const r = await get(`/admin/review/queue?page=${page.value}&page_size=${pageSize}`)
  rows.value = r.data.list
  total.value = r.data.total
}

async function decide(id: number, verdict: string) {
  await post(`/admin/review/${id}?verdict=${verdict}`)
  ElMessage.success('已处理')
  await load()
}
</script>
