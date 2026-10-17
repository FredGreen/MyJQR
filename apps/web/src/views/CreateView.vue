<template>
  <div class="page">
    <h2>开始创作</h2>

    <!-- ⓪ 未选模板：选择创作方式（不再直接暴露输入框导致报错） -->
    <el-row v-if="phase === 'input' && !tpl" :gutter="16">
      <el-col :xs="24" :sm="12" style="margin-bottom:16px">
        <el-card shadow="hover" class="mode-card free" @click="useFree">
          <div class="mode-ico">🎨</div>
          <div class="mode-name">自由创作</div>
          <div class="mode-desc">不想挑模板？一句话说清想写什么，AI 自选文体与结构自由发挥</div>
          <el-button type="primary" round style="margin-top:14px"
                     :loading="freeLoading">开始自由创作{{ freeTpl ? `（${freeTpl.joule_price} J/次）` : '' }}</el-button>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" style="margin-bottom:16px">
        <el-card shadow="hover" class="mode-card tpl" @click="$router.push('/market')">
          <div class="mode-ico">🧩</div>
          <div class="mode-name">模板创作</div>
          <div class="mode-desc">{{ tplCount ? `${tplCount}+ 个文风模板` : '精选文风模板' }}：故事会、今日选题、种草笔记……挑一个更对味</div>
          <el-button round style="margin-top:14px">去模板市场挑选</el-button>
        </el-card>
      </el-col>
    </el-row>

    <!-- ① 选模板 + 输入 -->
    <el-card v-if="phase === 'input' && tpl" style="max-width:760px">
      <div v-if="tpl" class="tpl-bar">
        <b>{{ tpl.name }}</b>
        <el-tag type="warning" size="small">{{ tpl.joule_price }} J/次</el-tag>
        <span class="muted">{{ tpl.description }}</span>
        <el-button text size="small" @click="$router.push('/market')">换模板</el-button>
      </div>
      <el-input v-model="input" type="textarea" :rows="5" size="large"
                :placeholder="tpl?.workflow_hint || '一句话描述你想写什么，例如：写瑞幸×茅台联名营销分析'" />
      <el-input v-model="material" type="textarea" :rows="3" style="margin-top:10px"
                placeholder="参考素材/你的观点（可选，附素材 AI 味更低）" />
      <div class="opts">
        <el-select v-model="responseLength" style="width:130px">
          <el-option :value="0" label="微篇 ~100字" />
          <el-option :value="1" label="短篇 ~1200字" />
          <el-option :value="2" label="中篇 ~2000字" />
          <el-option :value="3" label="长篇 ~3000字" />
        </el-select>
        <el-switch v-model="enableThink" active-text="深度思考" />
        <el-switch v-model="showRefs" active-text="展示引用" />
      </div>
      <el-button type="primary" size="large" style="margin-top:14px" :loading="starting"
                 @click="start">{{ starting ? '提交中...' : `生成（扣 ${tpl?.joule_price ?? '—'} J）` }}</el-button>
    </el-card>

    <!-- ② 生成过程 -->
    <el-card v-else style="max-width:860px">
      <div class="statusbar">
        <el-tag :type="statusType" size="large">{{ stageText }}</el-tag>
        <span v-if="aiRate !== null" class="report">
          AI 率检测：<b :style="{ color: aiRate < 50 ? '#1b7d46' : '#d4820a' }">{{ aiRate }}%</b>
          （{{ aiLevel }}）
        </span>
      </div>
      <div ref="outputEl" class="output">{{ output }}<span v-if="streaming" class="cursor">▊</span></div>
      <div v-if="references.length" class="refs">
        <b>参考来源：</b>
        <div v-for="(r, i) in references" :key="i" class="ref">[{{ i + 1 }}] {{ r.title }} — {{ r.site_name }}</div>
      </div>
      <div v-if="finished && workId" style="margin-top:16px">
        <el-button @click="copy(output, 'markdown')">复制 Markdown</el-button>
        <el-button @click="copy(plain, '纯文本')">复制纯文本</el-button>
        <el-button type="primary" @click="reset">再写一篇</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { get, post } from '../api/http'
import { openSse } from '../api/sse'
import { useAuth } from '../stores/auth'

const route = useRoute()
const auth = useAuth()

const tpl = ref<any>(null)
const freeTpl = ref<any>(null)
const freeLoading = ref(false)
const tplCount = ref(0)
const input = ref('')
const material = ref('')
const responseLength = ref(2)
const enableThink = ref(true)
const showRefs = ref(true)

const phase = ref<'input' | 'run'>('input')
const starting = ref(false)
const streaming = ref(false)
const stageText = ref('准备中...')
const output = ref('')
const workId = ref<number | null>(null)
const finished = ref(false)
const aiRate = ref<number | null>(null)
const aiLevel = ref('')
const references = ref<any[]>([])

const statusType = computed(() =>
  finished.value ? 'success' : streaming.value ? 'primary' : 'info')
const plain = computed(() => output.value.replace(/[#*`>\-\[\]]/g, ''))

onMounted(async () => {
  // 兜底模式信息（无论是否带模板进来都预取，点击卡片零等待）
  get('/template/free-creation').then(r => { freeTpl.value = r.data }).catch(() => {})
  get('/template/recommend/list?page_size=1').then(r => { tplCount.value = r.data.total }).catch(() => {})
  const tid = route.query.template_id
  if (!tid) return
  const r = await get(`/template/detail?template_id=${tid}`)
  tpl.value = r.data
  if (r.data.name === '降AI率') {
    tpl.value.workflow_hint = '把需要降 AI 率的全文直接粘贴到这里'
  }
  responseLength.value = r.data.response_length || 2
})

async function useFree() {
  freeLoading.value = true
  try {
    const r = await get('/template/free-creation')
    freeTpl.value = r.data
    tpl.value = { ...r.data, enable_web_search: false, enable_think: true }
    responseLength.value = r.data.response_length || 2
  } catch (e: any) {
    ElMessage.error(e.message || '自由创作暂不可用，请选择模板')
  } finally { freeLoading.value = false }
}

async function start() {
  if (input.value.trim().length < 5) return ElMessage.warning('请至少输入 5 个字')
  if (!tpl.value) return ElMessage.warning('请先选择创作方式：自由创作或挑选模板')
  starting.value = true
  try {
    const r = await post('/works/generate', {
      template_id: tpl.value.template_id, input: input.value,
      response_length: responseLength.value, enable_think: enableThink.value,
      show_references: showRefs.value, material: material.value,
    })
    workId.value = r.data.work_id
    phase.value = 'run'
    await openSse(`/api/v1/works/${workId.value}/stream?seq=0`, {
      onEvent(event, data) {
        if (event === 'stage') stageText.value = data.text
        else if (event === 'delta') { streaming.value = true; output.value += data.text; stageText.value = '正在撰写...' }
        else if (event === 'search_end' && data.references) references.value = data.references
        else if (event === 'report' && data.phase !== 'before') { aiRate.value = data.ai_rate; aiLevel.value = data.level }
        else if (event === 'done') { finished.value = true; streaming.value = false; stageText.value = '完成 ✅'; auth.joule -= r.data.joule_cost }
        else if (event === 'error') {
          finished.value = true; streaming.value = false
          stageText.value = `失败：${data.code}`
          if (data.refunded) { ElMessage.warning('生成失败，焦耳已退回'); auth.joule = auth.joule }
        }
      },
      onError: (e) => { stageText.value = '连接中断，请刷新查看结果' },
    })
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally { starting.value = false }
}

function copy(text: string, label: string) {
  navigator.clipboard.writeText(text)
  ElMessage.success(`已复制${label}`)
}

function reset() {
  phase.value = 'input'; output.value = ''; finished.value = false
  aiRate.value = null; references.value = []; stageText.value = '准备中...'
}
</script>

<style scoped>
.tpl-bar { margin-bottom: 12px; display: flex; gap: 10px; align-items: center; }
.muted { color: #999; font-size: 13px; flex: 1; }
.mode-card { cursor: pointer; text-align: center; padding: 28px 18px; border: 1.5px solid transparent; }
.mode-card:hover { transform: translateY(-2px); }
.mode-card.free { background: linear-gradient(160deg,#f0f7ff 0%,#fdf6ec 100%); }
.mode-card.tpl { background: linear-gradient(160deg,#f6f1fd 0%,#eefaf3 100%); }
.mode-ico { font-size: 40px; }
.mode-name { font-size: 20px; font-weight: 700; margin-top: 10px; color: #1b2a4a; }
.mode-desc { color: #888; font-size: 13px; margin-top: 8px; line-height: 1.7; }
.opts { margin-top: 12px; display: flex; gap: 24px; align-items: center; flex-wrap: wrap; }
.statusbar { display: flex; justify-content: space-between; margin-bottom:  12px; flex-wrap: wrap; gap: 8px; }
.output { white-space: pre-wrap; font-size: 15px; line-height: 1.9; min-height: 300px;
  background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #eee; }
.cursor { animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0 } }
.refs { margin-top: 12px; font-size: 12px; color: #888; }
.ref { margin: 2px 0; }
</style>
