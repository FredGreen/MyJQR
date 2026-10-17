<template>
  <div>
    <h2>数据看板</h2>
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :xs="12" :md="8" :lg="4"
              style="margin-bottom:16px">
        <el-card class="stat-card" :body-style="{ padding: '18px' }"
                 :style="{ background: card.bg }">
          <div class="head">
            <span class="ico" :style="{ background: card.color }">{{ card.icon }}</span>
            <span class="label">{{ card.label }}</span>
          </div>
          <div class="num" :style="{ color: card.color }">{{ card.value }}</div>
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
  { label: '注册用户', value: d.value.users ?? '—',
    icon: '👥', color: '#409eff', bg: 'linear-gradient(135deg,#ecf5ff 0%,#f7fbff 100%)' },
  { label: '生成总数', value: d.value.works_total ?? '—',
    icon: '📄', color: '#17a2b8', bg: 'linear-gradient(135deg,#e8f8fa 0%,#f4fcfd 100%)' },
  { label: '成功 / 失败', value: `${d.value.works_done ?? 0} / ${d.value.works_failed ?? 0}`,
    icon: '✅', color: '#1b7d46', bg: 'linear-gradient(135deg,#e8f5ec 0%,#f4fbf6 100%)' },
  { label: '在线模板', value: d.value.templates_online ?? '—',
    icon: '🧩', color: '#722ed1', bg: 'linear-gradient(135deg,#f3ecfd 0%,#faf6ff 100%)' },
  { label: '兑换焦耳(J)', value: d.value.joule_sold ?? 0,
    icon: '💰', color: '#d4820a', bg: 'linear-gradient(135deg,#fdf3e3 0%,#fffaef 100%)' },
  { label: '待人工审核', value: d.value.pending_review ?? 0,
    icon: '🛡', color: (d.value.pending_review ?? 0) > 0 ? '#e64a19' : '#909399',
    bg: (d.value.pending_review ?? 0) > 0
      ? 'linear-gradient(135deg,#fdeceb 0%,#fff7f6 100%)'
      : 'linear-gradient(135deg,#f4f4f5 0,#fafafa 100%)' },
])
</script>

<style scoped>
.stat-card { border: none; box-shadow: 0 2px 8px rgba(27, 42, 74, 0.06); }
.head { display: flex; align-items: center; gap: 8px; }
.ico {
  display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px; border-radius: 8px; font-size: 16px;
  color: #fff;
}
.label { color: #8a94a6; font-size: 13px; }
.num { font-size: 28px; font-weight: 700; margin-top: 10px; }

@media (max-width: 768px) {
  .num { font-size: 22px; }
  .label { font-size: 12px; }
}
</style>
