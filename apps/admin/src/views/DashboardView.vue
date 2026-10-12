<template>
  <div>
    <h2>数据看板</h2>
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :span="6" style="margin-bottom:16px">
        <el-card>
          <div class="num">{{ card.value }}</div>
          <div class="label">{{ card.label }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { get } from '../api/http'

const d = ref<any>({})
onMounted(async () => {
  const r = await get('/admin/dashboard/overview')
  d.value = r.data
})

const cards = computed(() => [
  { label: '注册用户', value: d.value.users ?? '—' },
  { label: '生成总数', value: d.value.works_total ?? '—' },
  { label: '成功 / 失败', value: `${d.value.works_done ?? 0} / ${d.value.works_failed ?? 0}` },
  { label: '在线模板', value: d.value.templates_online ?? '—' },
  { label: '兑换焦耳(J)', value: d.value.joule_sold ?? 0 },
  { label: '待人工审核', value: d.value.pending_review ?? 0 },
])
</script>

<style scoped>
.num { font-size: 28px; font-weight: 700; color: #1b2a4a; }
.label { color: #888; margin-top: 6px; }
</style>
