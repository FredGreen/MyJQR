<template>
  <el-dialog :model-value="modelValue" title="🧩 选择模板" top="6vh"
             :width="isMobile ? '94%' : '760px'"
             @update:model-value="$emit('update:modelValue', $event)" @open="onOpen">
    <div class="cat-row">
      <div class="cat-chip" :class="{ on: activeCat === 0 }" @click="switchCat(0)">全部模板</div>
      <div v-for="c in categories" :key="c.category_id" class="cat-chip"
           :class="{ on: activeCat === c.category_id }" @click="switchCat(c.category_id)">
        {{ c.name }}
      </div>
    </div>

    <div v-loading="loading" class="grid">
      <div v-for="t in visibleList" :key="t.template_id" class="p-card"
           :class="{ on: pickedId === t.template_id }" @click="pickedId = t.template_id">
        <div class="pc-head">
          <span class="pc-ico">🧩</span>
          <b class="pc-name">{{ t.name }}</b>
          <el-tag size="small" type="warning" effect="plain">{{ t.joule_price }}J</el-tag>
        </div>
        <div class="pc-stats">⭐ {{ Number(t.score).toFixed(1) }} · 🔥 {{ heat(t.stats?.use_cnt || 0) }}人使用</div>
        <div class="pc-desc">{{ t.description }}</div>
        <div v-if="pickedId === t.template_id" class="pc-check">✓</div>
      </div>
      <div v-if="!loading && !visibleList.length" class="empty">该分类暂无模板</div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :disabled="!pickedId" @click="confirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { get } from '../api/http'

// initialTid/initialCatId 为 0 表示不预选（自由创作模式）
const props = withDefaults(defineProps<{
  modelValue: boolean
  initialTid?: number
  initialCatId?: number
}>(), { initialTid: 0, initialCatId: 0 })
const emit = defineEmits(['update:modelValue', 'confirm'])

const isMobile = ref(false)
const mq = window.matchMedia('(max-width: 768px)')
const onMq = (e: MediaQueryListEvent) => { isMobile.value = e.matches }
onMounted(() => { isMobile.value = mq.matches; mq.addEventListener('change', onMq) })
onUnmounted(() => mq.removeEventListener('change', onMq))

const categories = ref<any[]>([])
const activeCat = ref(0)
const loading = ref(false)
const lists = ref<Record<number, any[]>>({})
const pickedId = ref(0)

const visibleList = computed(() => lists.value[activeCat.value] || [])

async function onOpen() {
  if (!categories.value.length) {
    try {
      const r = await get('/template/category/list')
      categories.value = r.data.list || []
    } catch { /* 分类加载失败仍可看全部 */ }
  }
  activeCat.value = props.initialCatId || 0
  pickedId.value = props.initialTid || 0
  await switchCat(activeCat.value)
}

async function switchCat(catId: number) {
  activeCat.value = catId
  if (lists.value[catId]) return
  loading.value = true
  try {
    const r = catId === 0
      ? await get('/template/recommend/list?page_size=20')
      : await get(`/template/list?category_id=${catId}&page_size=20`)
    // 自由创作在创作页有专属卡片，弹框里不重复出现
    lists.value = { ...lists.value, [catId]: (r.data.list || []).filter((t: any) => t.name !== '自由创作') }
  } finally { loading.value = false }
}

function confirm() {
  const t = visibleList.value.find((x: any) => x.template_id === pickedId.value)
  if (!t) return
  emit('confirm', t)
}

function heat(cnt: number): string {
  return cnt >= 10000 ? `${(cnt / 10000).toFixed(1)}万` : String(cnt)
}
</script>

<style scoped>
.cat-row { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 12px; }
.cat-chip {
  flex: 0 0 auto; padding: 5px 14px; border-radius: 14px; background: #f2f3f7;
  color: #555; font-size: 13px; cursor: pointer; user-select: none;
}
.cat-chip.on { background: #409eff; color: #fff; }

.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(215px, 1fr));
  gap: 10px; max-height: 52vh; overflow-y: auto; padding: 2px; min-height: 120px;
}
.p-card {
  background: #fff; border: 1.5px solid #eceef2; border-radius: 10px;
  padding: 12px; cursor: pointer; position: relative; transition: all .15s;
}
.p-card:hover { border-color: #c6e2ff; }
.p-card.on { border-color: #409eff; box-shadow: 0 0 0 3px rgba(64,158,255,.12); }
.pc-head { display: flex; align-items: center; gap: 6px; }
.pc-name { flex: 1; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pc-stats { color: #d4820a; font-size: 12px; margin-top: 6px; }
.pc-desc {
  color: #888; font-size: 12px; line-height: 1.6; margin-top: 6px; height: 38px;
  overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.pc-check {
  position: absolute; right: 8px; bottom: 8px; background: #409eff; color: #fff;
  font-size: 11px; width: 18px; height: 18px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.empty { grid-column: 1 / -1; text-align: center; color: #bbb; padding: 30px 0; }

@media (max-width: 768px) {
  .grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
  .pc-desc { height: 46px; -webkit-line-clamp: 3; }
  .pc-stats { display: none; }
}
</style>
