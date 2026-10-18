<template>
  <div class="page create-page">
    <!-- ② 生成 + 追问改稿工作台 -->
    <WorkRoom v-if="phase === 'run' && workId" :key="workId" :work-id="workId"
              @back="reset" />

    <!-- ① 选择 + 输入 -->
    <template v-else>
      <div class="greet">
        <div>
          <h2>Hi，{{ auth.nickname || '创作者' }} 👋</h2>
          <p class="sub">今天想写点什么？选个文风模板，或让 AI 自由发挥</p>
        </div>
        <div class="greet-actions">
          <el-button class="mem-btn" round @click="memoryOpen = true">🧠 写作记忆</el-button>
          <el-tag class="joule-chip" effect="plain" size="large">💰 {{ auth.joule }} J</el-tag>
        </div>
      </div>

      <!-- 模板横滑卡片流 -->
      <div class="sec-head">
        <b>✨ 创作模板</b>
        <el-button text type="primary" @click="$router.push('/market')">更多模板 ›</el-button>
      </div>
      <div class="strip-wrap">
        <div ref="stripEl" class="tpl-strip">
          <div v-for="t in allCards" :key="t.template_id" class="tpl-card"
               :class="{ on: tpl?.template_id === t.template_id, free: t.isFree }"
               @click="t.isFree ? selectFree(true) : selectTpl(t)">
            <div class="tc-head">
              <span class="tc-ico">{{ t.isFree ? '🎨' : '🧩' }}</span>
              <b class="tc-name">{{ t.name }}</b>
              <el-tag size="small" type="warning" effect="plain">{{ t.joule_price }}J</el-tag>
            </div>
            <div class="tc-stats">
              <template v-if="t.isFree">
                <span>⚡ 原生大模型</span><span>🤖 AI 自选文体</span>
              </template>
              <template v-else>
                <span>⭐ {{ Number(t.score).toFixed(1) }}</span>
                <span>🔥 {{ heat(t.stats?.use_cnt || 0) }}</span>
              </template>
            </div>
            <div class="tc-desc">{{ t.description }}</div>
            <div v-if="tpl?.template_id === t.template_id" class="tc-check">✓ 已选择</div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <el-card class="input-card">
        <div v-if="tpl" class="sel-bar">
          <span>已选：<b>{{ tpl.name }}</b></span>
          <el-tag size="small" type="warning" effect="plain">{{ tpl.joule_price }} J/次</el-tag>
          <el-button text size="small" type="primary" @click="$router.push('/market')">换一个</el-button>
        </div>
        <el-input v-model="input" type="textarea" :rows="4" size="large"
                  :placeholder="tpl?.workflow_hint || '您可以输入一个词或一段素材，例如：瑞幸×茅台联名营销分析'" />
        <el-input v-model="material" type="textarea" :rows="2" class="material"
                  placeholder="＋ 参考素材 / 你的观点（可选，附素材 AI 味更低）" />
        <div class="chips">
          <span class="chip-label">长度</span>
          <el-radio-group v-model="responseLength" size="small">
            <el-radio-button :value="0">微 100字</el-radio-button>
            <el-radio-button :value="1">短 1200</el-radio-button>
            <el-radio-button :value="2">中 2000</el-radio-button>
            <el-radio-button :value="3">长 3000</el-radio-button>
          </el-radio-group>
          <span class="chip-label" :class="{ off: !tpl?.enable_web_search }">🌐 联网</span>
          <el-switch v-model="showRefs" size="small" :disabled="!tpl?.enable_web_search" />
          <span class="chip-label" :class="{ off: !tpl?.enable_think }">🧠 深度思考</span>
          <el-switch v-model="enableThink" size="small" :disabled="!tpl?.enable_think" />
        </div>
        <div class="send-row">
          <span class="price-hint">{{ tpl ? `本次消耗 ${tpl.joule_price} J` : '请先在上方选择模板' }}</span>
          <el-button type="primary" size="large" round :loading="starting"
                     :disabled="!tpl || input.trim().length < 5" @click="start">
            {{ starting ? '提交中…' : '开始创作 ✨' }}
          </el-button>
        </div>
      </el-card>

      <MemoryPanel v-model="memoryOpen" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { get, post } from '../api/http'
import { useAuth } from '../stores/auth'
import MemoryPanel from '../components/MemoryPanel.vue'
import WorkRoom from '../components/WorkRoom.vue'

defineOptions({ name: 'CreateView' })

const route = useRoute()
const auth = useAuth()

const tpl = ref<any>(null)
const freeTpl = ref<any>(null)
const recommend = ref<any[]>([])
const selectedTid = ref(0)
const stripEl = ref<HTMLElement | null>(null)
const allCards = computed(() => {
  const free = freeTpl.value
    ? [{ template_id: freeTpl.value.template_id, name: freeTpl.value.name,
        description: freeTpl.value.description, joule_price: freeTpl.value.joule_price,
        isFree: true }]
    : []
  const list = recommend.value
    .filter((t: any) => t.name !== '自由创作' && t.template_id !== freeTpl.value?.template_id)
    .map((t: any) => ({ ...t, isFree: false }))
  const cards = [...free, ...list]
  // 选中的卡永远排第一位，保证用户一眼看到 ✓已选择
  const i = cards.findIndex((c: any) => c.template_id === selectedTid.value)
  if (i > 0) return [cards[i], ...cards.slice(0, i), ...cards.slice(i + 1)]
  return cards
})
const input = ref('')
const material = ref('')
const responseLength = ref(2)
const enableThink = ref(true)
const showRefs = ref(true)

const phase = ref<'input' | 'run'>('input')
const starting = ref(false)
const workId = ref<number | null>(null)
const memoryOpen = ref(false)

function heat(cnt: number): string {
  return cnt >= 10000 ? `${(cnt / 10000).toFixed(1)}万人使用` : `${cnt}人使用`
}

onMounted(async () => {
  try {
    const f = await get('/template/free-creation')
    freeTpl.value = f.data
  } catch { /* 自由创作卡缺失不影响主流程 */ }
  // 初始选中：URL 带入（市场跳转）> 服务端记住的上次选择 > 后端默认（今日选题）
  let initTid = 0
  let saveIt = false
  try {
    const p = await get('/template/preference')
    initTid = p.data.template_id || 0
  } catch { /* 无偏好也能进 */ }
  const qtid = Number(route.query.template_id) || 0
  if (qtid) { initTid = qtid; saveIt = true }
  try {
    const r = await get('/template/recommend/list?page_size=20')
    recommend.value = r.data.list
  } catch { /* 列表失败不影响选中 */ }
  if (initTid) await applySelection(initTid, saveIt)
})

// 选中变化 → 卡片已重排到第一位，横滑条滚回开头让用户看到 ✓已选择
watch(selectedTid, () => {
  nextTick(() => stripEl.value?.scrollTo({ left: 0, behavior: 'smooth' }))
})

// 页面被 KeepAlive 缓存后仍要响应市场带入的模板（输入内容不清空）
watch(() => route.query.template_id, async (nv, ov) => {
  const tid = Number(nv) || 0
  if (tid && tid !== Number(ov)) await applySelection(tid, true)
})

async function applySelection(tid: number, save = false) {
  if (freeTpl.value && tid === freeTpl.value.template_id) {
    await selectFree(save)
  } else {
    await selectById(tid, save)
  }
}

async function selectById(tid: number, save = false) {
  try {
    const r = await get(`/template/detail?template_id=${tid}`)
    tpl.value = r.data
    selectedTid.value = tid
    responseLength.value = r.data.response_length || 2
    if (r.data.name === '降AI率') tpl.value.workflow_hint = '把需要降 AI 率的全文直接粘贴到这里'
    // 不在推荐列表里（如市场深处模板）→ 用详情数据补一张卡，置顶展示
    if (!recommend.value.some((t: any) => t.template_id === tid)) {
      recommend.value.unshift(r.data)
    }
    if (save) post('/template/preference', { template_id: tid }).catch(() => {})
  } catch (e: any) { ElMessage.error(e.message) }
}

async function selectTpl(t: any) {
  if (tpl.value?.template_id === t.template_id) return
  await applySelection(t.template_id, true)
}

async function selectFree(save = false) {
  if (tpl.value?.template_id === freeTpl.value?.template_id) return
  try {
    const r = await get('/template/free-creation')
    freeTpl.value = r.data
    tpl.value = { ...r.data, enable_web_search: false, enable_think: true }
    selectedTid.value = r.data.template_id
    responseLength.value = r.data.response_length || 2
    showRefs.value = false
    if (save) post('/template/preference', { template_id: r.data.template_id }).catch(() => {})
  } catch (e: any) { ElMessage.error(e.message || '自由创作暂不可用') }
}

async function start() {
  if (input.value.trim().length < 5) return ElMessage.warning('请至少输入 5 个字')
  if (!tpl.value) return ElMessage.warning('请先选择创作模板')
  starting.value = true
  try {
    const r = await post('/works/generate', {
      template_id: tpl.value.template_id, input: input.value,
      response_length: responseLength.value, enable_think: enableThink.value,
      show_references: showRefs.value, material: material.value,
    })
    workId.value = r.data.work_id
    phase.value = 'run'
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally { starting.value = false }
}

// 返回输入页：输入内容与选中模板全部保留（KeepAlive + 本组件状态）
function reset() {
  phase.value = 'input'
  workId.value = null
}
</script>

<style scoped>
.create-page { max-width: 1000px; margin: 0 auto; }

.greet { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.greet h2 { margin: 4px 0; font-size: 24px; }
.sub { color: #999; margin: 4px 0 0; font-size: 14px; }
.greet-actions { display: flex; align-items: center; gap: 10px; }
.joule-chip { color: #d4820a; font-weight: 600; }

.sec-head { display: flex; justify-content: space-between; align-items: center; margin: 18px 0 10px; }
.sec-head b { font-size: 16px; }

.strip-wrap { position: relative; }
.strip-wrap::after {
  content: ''; position: absolute; right: 0; top: 0; bottom: 10px; width: 36px;
  background: linear-gradient(90deg, rgba(245, 246, 248, 0), #f5f6f8);
  pointer-events: none;
}
.tpl-strip {
  display: flex; gap: 12px; overflow-x: auto; padding: 4px 2px 12px;
  scroll-snap-type: x mandatory;
}
.tpl-strip::-webkit-scrollbar { height: 4px; }
.tpl-strip::-webkit-scrollbar-track { background: transparent; }
.tpl-strip::-webkit-scrollbar-thumb { background: transparent; border-radius: 2px; }
.strip-wrap:hover .tpl-strip::-webkit-scrollbar-thumb { background: #dfe3ea; }
.tpl-card {
  flex: 0 0 250px; height: 148px; scroll-snap-align: start; cursor: pointer;
  background: #fff; border: 1.5px solid #eceef2; border-radius: 12px; padding: 14px;
  position: relative; overflow: hidden; transition: all .15s;
}
.tpl-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(27,42,74,.08); }
.tpl-card.on { border-color: #409eff; box-shadow: 0 0 0 3px rgba(64,158,255,.12); }
.tpl-card.free { background: linear-gradient(150deg,#f2f8ff 0%,#fdf6ec 100%); }
.tc-head { display: flex; align-items: center; gap: 6px; }
.tc-ico { font-size: 18px; }
.tc-name { flex: 1; font-size: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tc-stats { color: #d4820a; font-size: 12px; display: flex; gap: 12px; margin-top: 8px; }
.tc-desc { color: #888; font-size: 12px; line-height: 1.6; margin-top: 6px; height: 38px;
  overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.tc-check {
  position: absolute; right: 10px; bottom: 10px;
  background: #409eff; color: #fff; font-size: 11px;
  padding: 2px 8px; border-radius: 10px;
}

.input-card { max-width: 860px; }
.sel-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; font-size: 14px; }
.sel-bar .el-button { margin-left: auto; }
.material { margin-top: 10px; }
.chips { display: flex; align-items: center; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
.chip-label { color: #666; font-size: 13px; }
.chip-label.off { color: #c0c4cc; }
.send-row { display: flex; justify-content: space-between; align-items: center; margin-top: 14px; }
.price-hint { color: #999; font-size: 13px; }

@media (max-width: 768px) {
  .tpl-card { flex: 0 0 78%; }
  .send-row .el-button { flex: 1; }
  .greet-actions .mem-btn { padding: 8px 12px; }
}
</style>
