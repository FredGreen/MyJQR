<template>
  <div class="page works-page">
    <h2>我的作品</h2>

    <!-- 桌面：表格 -->
    <el-table :data="works" stripe class="desk-table">
      <el-table-column prop="work_id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" min-width="240" />
      <el-table-column prop="topic" label="主题" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="typeOf(row.status)" size="small">{{ labelOf(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="word_cnt" label="字数" width="90" />
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" @click="open(row.work_id)">
            {{ row.status === 'done' ? '查看 / 修改' : '查看' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 手机：卡片列表 -->
    <div class="m-list">
      <div v-for="w in works" :key="w.work_id" class="m-card" @click="open(w.work_id)">
        <div class="m-top">
          <div class="m-title">{{ w.title || '(未命名)' }}</div>
          <el-tag :type="typeOf(w.status)" size="small">{{ labelOf(w.status) }}</el-tag>
        </div>
        <div class="m-topic">{{ w.topic }}</div>
        <div class="m-foot">
          <span>{{ w.word_cnt || 0 }} 字</span>
          <span>{{ fmt(w.created_at) }}</span>
        </div>
      </div>
      <div v-if="!works.length" class="m-empty">还没有作品，去创作第一篇吧 ✍️</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '../api/http'

const router = useRouter()
const works = ref<any[]>([])

const STATUS: Record<string, { label: string; type: string }> = {
  done: { label: '完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
  banned: { label: '拦截', type: 'danger' },
  generating: { label: '生成中', type: 'info' },
}

function labelOf(s: string) { return STATUS[s]?.label || s }
function typeOf(s: string) { return STATUS[s]?.type || 'info' }
function fmt(s: string) { return (s || '').slice(5, 16) }

onMounted(async () => {
  const r = await get('/works?page_size=20')
  works.value = r.data.list
})

function open(id: number) {
  router.push(`/work/${id}`)
}
</script>

<style scoped>
.works-page { max-width: 1000px; margin: 0 auto; }

.m-list { display: none; }

@media (max-width: 768px) {
  .desk-table { display: none; }
  .m-list { display: block; }
  .m-card {
    background: #fff; border: 1px solid #eceef2; border-radius: 10px;
    padding: 12px 14px; margin-bottom: 10px; cursor: pointer;
  }
  .m-card:active { background: #f7f8fa; }
  .m-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .m-title { font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .m-topic { color: #888; font-size: 12px; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .m-foot { display: flex; justify-content: space-between; color: #bbb; font-size: 12px; margin-top: 6px; }
  .m-empty { text-align: center; color: #bbb; padding: 40px 0; }
}
</style>
