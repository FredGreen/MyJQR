<template>
  <div class="page">
    <h2>模板市场</h2>
    <div class="cats">
      <el-tag v-for="c in categories" :key="c.category_id" size="large"
              :effect="activeCat === c.category_id ? 'dark' : 'plain'"
              style="cursor:pointer;margin:0 8px 8px 0"
              @click="selectCat(c.category_id)">{{ c.name }}</el-tag>
    </div>

    <el-row :gutter="16">
      <el-col v-for="t in templates" :key="t.template_id" :span="8" style="margin-bottom:16px">
        <el-card shadow="hover" style="cursor:pointer" @click="openDetail(t)">
          <div class="tname">{{ t.name }} <el-tag size="small" type="warning">{{ t.joule_price }}J</el-tag></div>
          <div class="tdesc">{{ t.description }}</div>
          <div class="tmeta">
            <span>⭐ {{ t.score }}</span>
            <span>{{ t.stats.use_cnt }} 次使用</span>
            <span v-if="t.enable_web_search">🌐 联网</span>
            <span v-if="t.enable_think">🧠 深度</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="detailVisible" :title="detail?.name" width="640px">
      <template v-if="detail">
        <p><b>描述：</b>{{ detail.description }}</p>
        <p><b>分类：</b><el-tag v-for="c in detail.categories" :key="c" size="small" style="margin-right:6px">{{ c }}</el-tag></p>
        <p><b>价格：</b>{{ detail.joule_price }} 焦耳/次</p>
        <p v-if="detail.usage_tips"><b>使用提示：</b>{{ detail.usage_tips }}</p>
        <el-button type="primary" size="large" @click="useTemplate(detail)">用这个模板创作 →</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '../api/http'

const router = useRouter()
const categories = ref<any[]>([])
const templates = ref<any[]>([])
const activeCat = ref<number | null>(null)
const detailVisible = ref(false)
const detail = ref<any>(null)

onMounted(async () => {
  const c = await get('/template/category/list')
  categories.value = c.data.list
  const r = await get('/template/recommend/list?page_size=20')
  templates.value = r.data.list
})

async function selectCat(cid: number) {
  activeCat.value = cid
  const r = await get(`/template/list?category_id=${cid}&page_size=20`)
  templates.value = r.data.list
}

async function openDetail(t: any) {
  const r = await get(`/template/detail?template_id=${t.template_id}`)
  detail.value = r.data
  detailVisible.value = true
}

function useTemplate(t: any) {
  router.push({ path: '/create', query: { template_id: t.template_id } })
}
</script>

<style scoped>
.tname { font-size: 17px; font-weight: 600; }
.tdesc { color: #666; margin: 10px 0; min-height: 40px; }
.tmeta { color: #999; font-size: 12px; display: flex; gap: 14px; }
.cats { margin-bottom: 20px; }
</style>
