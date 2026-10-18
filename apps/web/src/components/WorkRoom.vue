<template>
  <div class="workroom">
    <div class="topbar">
      <el-button text @click="$emit('back')">‹ 返回</el-button>
      <span class="w-title">{{ info?.title || '创作中' }}</span>
      <el-tag v-if="info?.template_name" size="small" effect="plain">
        {{ info.template_name }}
      </el-tag>
      <el-tag v-if="aiRate !== null" size="small" :type="aiRate < 50 ? 'success' : 'warning'">
        AI 率 {{ aiRate }}%
      </el-tag>
      <span class="spacer" />
      <el-button text type="primary" :disabled="busy" @click="tplVisible = true">🔄 换模板</el-button>
      <el-button text type="primary" :disabled="busy || editing" @click="startEdit">✏️ 编辑</el-button>
      <el-button text type="primary" :disabled="!displayContent" @click="copyCur">复制</el-button>
    </div>

    <div class="body">
      <!-- 对话区（PC 左栏 / 移动端底部） -->
      <aside class="chat">
        <div ref="msgsEl" class="msgs">
          <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
            <div class="bubble">{{ m.text }}</div>
          </div>
          <div v-if="busy" class="msg assistant">
            <div class="bubble">{{ streamBuf || '…' }}<span class="cursor">▊</span></div>
          </div>
          <div v-if="stageText && busy" class="stage">{{ stageText }}</div>
        </div>
        <div class="composer">
          <div class="quick">
            <span v-for="q in QUICK" :key="q" class="q-chip" @click="inputText = q">{{ q }}</span>
          </div>
          <el-input v-model="inputText" type="textarea" :rows="3" resize="none"
                    placeholder="继续追问，按你的要求修改文章，例如：标题改成悬念式、每段加个案例…" />
          <div class="send-row">
            <el-checkbox v-model="remember" size="small">🧠 记住这个要求</el-checkbox>
            <el-button type="primary" round :loading="sending"
                       :disabled="busy || inputText.trim().length < 2" @click="sendFollowup">
              发送（5J/次）
            </el-button>
          </div>
        </div>
      </aside>

      <!-- 文章区（PC 右栏 / 移动端顶部） -->
      <section class="article">
        <div class="v-bar">
          <div class="v-pills">
            <span v-for="v in versions" :key="v.turn" class="v-pill"
                  :class="{ on: v.turn === viewTurn }" :title="pillTip(v)"
                  @click="viewTurn = v.turn">{{ pillLabel(v) }}</span>
          </div>
          <el-button v-if="viewTurn && viewTurn !== latestTurn" text size="small" type="primary"
                     @click="restore(viewTurn)">恢复此版本</el-button>
        </div>
        <div v-if="info && ['failed', 'banned'].includes(info.status)" class="err-banner">
          作品状态：{{ info.status === 'banned' ? '内容被拦截' : '生成失败' }}，焦耳已退回，可返回重试
        </div>
        <template v-if="editing">
          <div class="edit-hint">✏️ 正在手动编辑，保存后生成新版本（免费），之前的版本都保留、可随时切回；顶部按钮在编辑期间停用</div>
          <el-input v-model="editBuf" type="textarea" class="edit-area" resize="none" />
          <div class="edit-row">
            <el-button @click="editing = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="saveEdit">保存为新版本</el-button>
          </div>
        </template>
        <div v-else class="content">{{ displayContent }}<span v-if="busy && !streamBuf" class="cursor">▊</span></div>
        <div v-if="info?.references?.length" class="refs">
          <b>参考来源：</b>
          <span v-for="r in info.references" :key="r.idx" class="ref">
            [{{ r.idx }}] {{ r.title }}
          </span>
        </div>
      </section>
    </div>

    <!-- 换模板 -->
    <el-dialog v-model="tplVisible" title="换模板重生成" width="640px" top="6vh">
      <p class="dlg-hint">用新模板以当前主题重写整篇，作为新版本保留（按新模板价格计费），原版本可随时切回。</p>
      <div class="tpl-list">
        <div v-for="t in tplOptions" :key="t.template_id" class="tpl-row"
             :class="{ on: pickTid === t.template_id }" @click="pickTid = t.template_id">
          <b>{{ t.name }}</b>
          <span class="d">{{ t.description }}</span>
          <el-tag size="small" type="warning" effect="plain">{{ t.joule_price }}J</el-tag>
        </div>
      </div>
      <template #footer>
        <el-button @click="tplVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!pickTid" :loading="sending" @click="regen">
          用这个模板重写
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { get, post, put } from '../api/http'
import { openSse } from '../api/sse'
import { useAuth } from '../stores/auth'

const props = defineProps<{ workId: number }>()
defineEmits(['back'])
const auth = useAuth()

const QUICK = ['更口语化一些', '更犀利一点', '帮我加个案例', '精简一半', '标题换个角度']
const ROLE_ICON: Record<string, string> = { body: '✨', followup: '💬', regen: '🔄', edit: '✏️' }

const info = ref<any>(null)
const versions = ref<any[]>([])
const messages = ref<{ role: 'user' | 'assistant'; text: string }[]>([])
const inputText = ref('')
const remember = ref(false)
const sending = ref(false)
const busy = ref(false)
const streamBuf = ref('')
const stageText = ref('')
const lastSeq = ref(0)
const viewTurn = ref(0)
const aiRate = ref<number | null>(null)
const editing = ref(false)
const editBuf = ref('')
const saving = ref(false)
const msgsEl = ref<HTMLElement | null>(null)
let abort: AbortController | null = null

// 换模板弹层
const tplVisible = ref(false)
const pickTid = ref(0)
const tplOptions = ref<any[]>([])

const latestTurn = computed(() =>
  versions.value.length ? versions.value[versions.value.length - 1].turn : 0)
const curVersion = computed(() => versions.value.find((v) => v.turn === viewTurn.value))
// 生成/追问/换模板进行中 → 文章区直接显示流式内容；平时显示当前查看的版本
const displayContent = computed(() => {
  if (busy.value) return streamBuf.value
  return curVersion.value?.content ?? ''
})

function pillLabel(v: any): string {
  return `V${v.turn} ${ROLE_ICON[v.role] || ''}`.trim()
}
function pillTip(v: any): string {
  if (v.role === 'regen') return `换模板重写：${v.template_name || ''}`
  return (v.input || '').slice(0, 60)
}
function chatLine(v: any): string {
  if (v.role === 'regen') return `已切换模板「${v.template_name}」重写 → V${v.turn}（${v.word_cnt}字）`
  if (v.role === 'edit') return `${v.input || '手动编辑'} → V${v.turn}（${v.word_cnt}字）`
  return `已按你的要求修改 → V${v.turn}（${v.word_cnt}字）`
}

onMounted(() => load().catch(() => ElMessage.error('作品加载失败，请刷新重试')))
onBeforeUnmount(() => abort?.abort())

async function load() {
  const [d, v] = await Promise.all([
    get(`/works/${props.workId}`),
    get(`/works/${props.workId}/versions`),
  ])
  info.value = d.data
  aiRate.value = d.data.report ? d.data.report.ai_rate : null
  // 同步事件流游标：追问订阅从最新位置续传，避免回放初始生成并在旧 done 处断流
  if (typeof d.data.last_seq === 'number') lastSeq.value = d.data.last_seq
  versions.value = v.data.versions
  if (!viewTurn.value) viewTurn.value = v.data.current_turn || 0
  buildChat()
  if (['generating', 'detecting'].includes(d.data.status)) subscribe(0)
}

// 由版本链重建对话流（刷新/再进后仍能看到完整修改历史）
function buildChat() {
  const msgs: { role: 'user' | 'assistant'; text: string }[] = [{
    role: 'assistant',
    text: versions.value.length
      ? '文章已生成 ✅ 输入修改要求继续打磨，或点右上角换模板换种写法。'
      : '正在生成，稍候…',
  }]
  for (const v of versions.value) {
    if (v.role === 'followup') msgs.push({ role: 'user', text: v.input })
    if (v.role !== 'body') msgs.push({ role: 'assistant', text: chatLine(v) })
  }
  messages.value = msgs
}

function subscribe(fromSeq: number) {
  abort?.abort()
  abort = new AbortController()
  busy.value = true
  streamBuf.value = ''
  openSse(`/api/v1/works/${props.workId}/stream?seq=${fromSeq}`, {
    signal: abort.signal,
    onEvent(event, data) {
      if (typeof data.seq === 'number') lastSeq.value = data.seq
      if (event === 'stage') stageText.value = data.text || ''
      else if (event === 'delta') streamBuf.value += data.text || ''
      else if (event === 'report' && data.phase !== 'before'
               && typeof data.ai_rate === 'number') aiRate.value = data.ai_rate
      else if (event === 'done') finish(data.turn || 0, data.joule_cost || 0)
      else if (event === 'error') fail(data)
    },
    onError() { busy.value = false; stageText.value = '' },
  }).catch(() => { /* abort 或断线，状态由 done/error 兜底 */ })
}

async function finish(turn: number, cost: number) {
  busy.value = false
  streamBuf.value = ''
  stageText.value = ''
  if (cost) auth.joule -= cost
  try {
    const [d, v] = await Promise.all([
      get(`/works/${props.workId}`),
      get(`/works/${props.workId}/versions`),
    ])
    info.value = d.data
    aiRate.value = d.data.report ? d.data.report.ai_rate : null
    if (typeof d.data.last_seq === 'number') lastSeq.value = d.data.last_seq
    versions.value = v.data.versions
    // 完成后由版本链统一重建对话流（初始生成/追问/换模板一致）
    buildChat()
    if (turn) {
      viewTurn.value = turn
    } else {
      viewTurn.value = v.data.current_turn || viewTurn.value
    }
    ElMessage.success('已完成')
  } catch { /* 刷新失败不影响本地状态 */ }
}

function fail(data: any) {
  busy.value = false
  streamBuf.value = ''
  stageText.value = ''
  if (data?.refunded) ElMessage.warning('本次操作失败，焦耳已退回')
  else ElMessage.error(`失败：${data?.code || '未知错误'}`)
  load().catch(() => {})
}

async function sendFollowup() {
  if (busy.value || inputText.value.trim().length < 2) return
  sending.value = true
  try {
    await post(`/works/${props.workId}/followup`, {
      input: inputText.value, remember: remember.value,
    })
    messages.value.push({ role: 'user', text: inputText.value })
    inputText.value = ''
    subscribe(lastSeq.value + 1)
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    sending.value = false
  }
}

async function regen() {
  if (!pickTid.value || busy.value) return
  sending.value = true
  try {
    await post(`/works/${props.workId}/regenerate`, { template_id: pickTid.value })
    tplVisible.value = false
    subscribe(lastSeq.value + 1)
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    sending.value = false
  }
}

function startEdit() {
  editBuf.value = displayContent.value
  editing.value = true
}

async function saveEdit() {
  if (!editBuf.value.trim()) return
  saving.value = true
  try {
    const r = await put(`/works/${props.workId}/content`, { content_md: editBuf.value })
    editing.value = false
    ElMessage.success(`已保存为 V${r.data.turn}`)
    await load()
    viewTurn.value = r.data.turn
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function restore(turn: number) {
  const v = versions.value.find((x) => x.turn === turn)
  if (!v) return
  try {
    const r = await post(`/works/${props.workId}/segments/${v.segment_id}/restore`)
    ElMessage.success(`已把 V${turn} 恢复为最新版（V${r.data.turn}）`)
    await load()
    viewTurn.value = r.data.turn
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

function copyCur() {
  if (!displayContent.value) return
  navigator.clipboard.writeText(displayContent.value)
  ElMessage.success('已复制全文')
}

watch(tplVisible, async (open) => {
  if (!open) return
  pickTid.value = 0
  try {
    const r = await get('/template/recommend/list?page_size=50')
    let list: any[] = r.data.list || []
    try {
      const f = await get('/template/free-creation')
      if (f.data?.template_id !== info.value?.template_id) list = [f.data, ...list]
    } catch { /* 自由创作兜底失败忽略 */ }
    const seen = new Set<number>()
    tplOptions.value = list.filter((t) => {
      if (!t.template_id || t.template_id === info.value?.template_id
          || seen.has(t.template_id)) return false
      seen.add(t.template_id)
      return true
    })
  } catch (e: any) {
    ElMessage.error(e.message)
  }
})

watch([() => messages.value.length, streamBuf], () => {
  nextTick(() => msgsEl.value?.scrollTo({ top: msgsEl.value.scrollHeight }))
})
</script>

<style scoped>
.workroom {
  display: flex; flex-direction: column;
  height: calc(100vh - 170px); min-height: 500px;
}

.topbar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  background: #fff; border: 1px solid #eceef2; border-radius: 12px;
  padding: 8px 14px; margin-bottom: 12px;
}
.w-title { font-weight: 600; font-size: 15px; max-width: 320px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.spacer { flex: 1; }

.body { flex: 1; display: flex; gap: 12px; min-height: 0; }

.chat {
  flex: 0 0 360px; display: flex; flex-direction: column;
  background: #fff; border: 1px solid #eceef2; border-radius: 12px; overflow: hidden;
}
.msgs { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.msg { display: flex; }
.msg.user { justify-content: flex-end; }
.bubble {
  max-width: 86%; padding: 8px 12px; border-radius: 12px; font-size: 14px;
  line-height: 1.7; white-space: pre-wrap; word-break: break-word;
}
.msg.user .bubble { background: #409eff; color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: #f4f6fa; border-bottom-left-radius: 4px; }
.stage { color: #999; font-size: 12px; text-align: center; }
.cursor { animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0 } }

.composer { border-top: 1px solid #f0f2f5; padding: 10px 12px; }
.quick { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.q-chip { font-size: 12px; color: #666; background: #f4f6fa; border-radius: 12px;
  padding: 3px 10px; cursor: pointer; }
.q-chip:hover { color: #409eff; background: #ecf5ff; }
.send-row { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }

.article {
  flex: 1; display: flex; flex-direction: column; min-width: 0;
  background: #fff; border: 1px solid #eceef2; border-radius: 12px; padding: 14px 16px;
}
.v-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.v-pills { display: flex; gap: 6px; overflow-x: auto; flex: 1; }
.v-pill { flex: 0 0 auto; font-size: 12px; padding: 3px 10px; border-radius: 12px;
  background: #f4f6fa; color: #666; cursor: pointer; white-space: nowrap; }
.v-pill.on { background: #409eff; color: #fff; }
.err-banner { background: #fef0f0; color: #f56c6c; font-size: 13px;
  padding: 10px 12px; border-radius: 8px; margin-bottom: 10px; }
.content { flex: 1; overflow-y: auto; white-space: pre-wrap; font-size: 15px; line-height: 1.9; }
/* 编辑态：编辑框吃掉剩余空间，保存/取消永远固定在可视区内 */
.edit-hint { color: #999; font-size: 12px; margin-bottom: 8px; }
.edit-area { flex: 1; min-height: 140px; }
.edit-area :deep(textarea) { height: 100%; resize: none; }
.edit-row { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; flex: 0 0 auto; }
.refs { margin-top: 10px; font-size: 12px; color: #999; }
.ref { margin-right: 8px; }

.dlg-hint { color: #999; font-size: 13px; margin: 0 0 12px; line-height: 1.6; }
.tpl-list { max-height: 380px; overflow-y: auto; }
.tpl-row { display: flex; align-items: center; gap: 10px; padding: 10px 12px;
  border: 1.5px solid #eceef2; border-radius: 10px; margin-bottom: 8px; cursor: pointer; }
.tpl-row.on { border-color: #409eff; background: #ecf5ff; }
.tpl-row .d { flex: 1; color: #999; font-size: 12px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; }

/* 移动端：上下分屏 —— 上方文章、下方追问 */
@media (max-width: 768px) {
  .workroom { height: calc(100vh - 120px); min-height: 460px; }
  .body { flex-direction: column; }
  .article { order: 0; flex: 1; min-height: 0; padding: 10px 12px; }
  .chat { order: 1; flex: 0 0 44%; }
  .w-title { max-width: 150px; }
}
</style>
