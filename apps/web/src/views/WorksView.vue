<template>
  <div class="page">
    <h2>我的作品</h2>
    <el-table :data="works" stripe>
      <el-table-column prop="work_id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" min-width="240" />
      <el-table-column prop="topic" label="主题" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'done' ? 'success' : row.status === 'failed' ? 'danger' : 'info'" size="small">
            {{ ({ done: '完成', failed: '失败', banned: '拦截', generating: '生成中' } as Record<string, string>)[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="word_cnt" label="字数" width="90" />
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button size="small" @click="open(row.work_id)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="detail?.title" width="760px" top="5vh">
      <template v-if="detail">
        <div class="meta">
          <el-tag v-if="detail.report" :type="detail.report.ai_rate < 50 ? 'success' : 'warning'">
            AI 率 {{ detail.report.ai_rate }}%（{{ detail.report.level }}）
          </el-tag>
          <el-tag type="info">{{ detail.model_used }}</el-tag>
          <el-tag type="warning">{{ detail.joule_cost }} J</el-tag>
        </div>
        <div class="content">{{ detail.content_md }}</div>
        <div v-if="detail.references?.length" class="refs">
          <b>参考来源：</b>
          <div v-for="r in detail.references" :key="r.idx">[{{ r.idx }}] {{ r.title }}</div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { get } from '../api/http'

const works = ref<any[]>([])
const visible = ref(false)
const detail = ref<any>(null)

onMounted(async () => {
  const r = await get('/works?page_size=20')
  works.value = r.data.list
})

async function open(id: number) {
  const r = await get(`/works/${id}`)
  detail.value = r.data
  visible.value = true
}
</script>

<style scoped>
.meta { margin-bottom: 12px; display: flex; gap: 8px; }
.content { white-space: pre-wrap; line-height: 1.9; max-height: 60vh; overflow: auto; background: #fff; padding: 16px; border: 1px solid #eee; border-radius: 8px; }
.refs { margin-top: 12px; font-size: 12px; color: #888; }
</style>
