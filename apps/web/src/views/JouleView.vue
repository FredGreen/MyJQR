<template>
  <div class="page joule-page">
    <el-row :gutter="16">
      <!-- 余额主卡 -->
      <el-col :xs="24" :md="9">
        <div class="hero">
          <div class="hero-label">💰 可用焦耳</div>
          <div class="hero-num">{{ balance }}<span class="hero-unit">J</span></div>
          <div class="hero-stats">
            <div><span>冻结中</span><b>{{ frozen }} J</b></div>
            <div><span>累计充值/获赠</span><b>{{ earned }} J</b></div>
            <div><span>累计消费</span><b>{{ spent }} J</b></div>
          </div>
        </div>
      </el-col>

      <!-- 兑换 + 说明 -->
      <el-col :xs="24" :md="15">
        <el-card class="redeem-card">
          <b>🎁 兑换码充值</b>
          <p class="hint">输入管理员发放的兑换码，焦耳即时到账</p>
          <div class="redeem-row">
            <el-input v-model="code" placeholder="请输入兑换码" size="large" clearable
                      @keyup.enter="redeem" />
            <el-button type="primary" size="large" :loading="redeeming" @click="redeem">
              立即兑换
            </el-button>
          </div>
          <div class="tips">
            <div>· 焦耳用于支付 AI 创作消耗，生成失败自动全额退回</div>
            <div>· 每次创作前会明确展示本次消耗的焦耳数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 流水 -->
    <el-card class="tx-card">
      <template #header>
        <div class="tx-head">
          <b>📋 流水记录</b>
          <span class="muted">共 {{ txs.length }}{{ hasMore ? '+' : '' }} 条</span>
        </div>
      </template>
      <div v-if="!txs.length" class="empty">暂无流水记录</div>
      <div v-for="t in txs" :key="t.id" class="tx-item">
        <div class="tx-ico" :class="meta(t.biz_type).cls">{{ meta(t.biz_type).ico }}</div>
        <div class="tx-info">
          <div class="tx-title">{{ meta(t.biz_type).label }}</div>
          <div class="tx-remark">{{ t.remark || '—' }}</div>
          <div class="tx-time">{{ fmt(t.created_at) }}</div>
        </div>
        <div class="tx-right">
          <div class="tx-amount" :class="t.amount > 0 ? 'in' : 'out'">
            {{ t.amount > 0 ? '+' : '' }}{{ t.amount }} J
          </div>
          <div class="tx-bal">余额 {{ t.balance_after }} J</div>
        </div>
      </div>
      <div v-if="hasMore" class="more">
        <el-button text :loading="loadingMore" @click="loadMore">加载更多</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { get, post } from '../api/http'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const balance = ref(0)
const frozen = ref(0)
const spent = ref(0)
const earned = ref(0)
const txs = ref<any[]>([])
const hasMore = ref(false)
const loadingMore = ref(false)
const code = ref('')
const redeeming = ref(false)

const META: Record<string, { label: string; ico: string; cls: string }> = {
  generate: { label: '生成消费', ico: '✍️', cls: 'out' },
  refund: { label: '失败退款', ico: '↩️', cls: 'in' },
  redeem: { label: '兑换充值', ico: '🎁', cls: 'in' },
  gift: { label: '新人赠送', ico: '🎈', cls: 'in' },
  adjust: { label: '管理员调整', ico: '⚙️', cls: 'adj' },
}

function meta(type: string) {
  return META[type] || { label: type, ico: '📒', cls: 'adj' }
}

function fmt(s: string): string {
  return (s || '').slice(5, 16)
}

onMounted(load)

async function load() {
  const [b, t] = await Promise.all([get('/joule/me'), get('/joule/transactions?page_size=20')])
  balance.value = b.data.balance
  frozen.value = b.data.frozen
  spent.value = b.data.total_spent
  earned.value = b.data.total_earned
  auth.setProfile(auth.nickname, b.data.balance)
  txs.value = t.data.list
  hasMore.value = t.data.has_more
}

async function loadMore() {
  loadingMore.value = true
  try {
    const cursor = txs.value.length ? txs.value[txs.value.length - 1].id : 0
    const t = await get(`/joule/transactions?page_size=20&cursor=${cursor}`)
    txs.value.push(...t.data.list)
    hasMore.value = t.data.has_more
  } finally { loadingMore.value = false }
}

async function redeem() {
  if (!code.value.trim()) return ElMessage.warning('请输入兑换码')
  redeeming.value = true
  try {
    const r = await post('/joule/redeem', { code: code.value.trim() })
    ElMessage.success(`充值成功 +${r.data.amount} J`)
    code.value = ''
    await load()
  } catch (e: any) { ElMessage.error(e.message) } finally { redeeming.value = false }
}
</script>

<style scoped>
.joule-page { max-width: 1000px; margin: 0 auto; }

.hero {
  background: linear-gradient(135deg, #f59e0b 0%, #f97316 55%, #ea580c 100%);
  border-radius: 12px; color: #fff; padding: 24px;
  box-shadow: 0 8px 20px rgba(234, 88, 12, .25);
  height: 100%; box-sizing: border-box;
}
.hero-label { font-size: 14px; opacity: .9; }
.hero-num { font-size: 44px; font-weight: 800; margin: 8px 0 16px; }
.hero-unit { font-size: 18px; font-weight: 600; margin-left: 6px; opacity: .85; }
.hero-stats { display: flex; gap: 20px; flex-wrap: wrap; border-top: 1px solid rgba(255,255,255,.25); padding-top: 12px; }
.hero-stats div { display: flex; flex-direction: column; gap: 2px; font-size: 12px; opacity: .9; }
.hero-stats b { font-size: 15px; opacity: 1; }

.redeem-card { height: 100%; }
.hint { color: #999; font-size: 13px; margin: 8px 0 12px; }
.redeem-row { display: flex; gap: 10px; }
.tips { margin-top: 14px; color: #aaa; font-size: 12px; line-height: 1.8; }

.tx-card { margin-top: 16px; }
.tx-head { display: flex; justify-content: space-between; align-items: center; }
.muted { color: #999; font-size: 13px; }
.empty { color: #bbb; text-align: center; padding: 40px 0; }
.tx-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 4px; border-bottom: 1px solid #f2f3f5;
}
.tx-item:last-of-type { border-bottom: none; }
.tx-ico {
  width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 17px;
}
.tx-ico.in { background: #e8f6ee; }
.tx-ico.out { background: #fdeeee; }
.tx-ico.adj { background: #f0f1f4; }
.tx-info { flex: 1; min-width: 0; }
.tx-title { font-size: 14px; font-weight: 600; }
.tx-remark { color: #888; font-size: 12px; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tx-time { color: #bbb; font-size: 12px; margin-top: 2px; }
.tx-right { text-align: right; flex-shrink: 0; }
.tx-amount { font-size: 16px; font-weight: 700; }
.tx-amount.in { color: #1b7d46; }
.tx-amount.out { color: #c0392b; }
.tx-bal { color: #bbb; font-size: 12px; margin-top: 2px; }
.more { text-align: center; margin-top: 8px; }

@media (max-width: 768px) {
  .hero { padding: 18px; }
  .hero-num { font-size: 36px; }
  .hero-stats { gap: 14px; }
  .redeem-row { flex-direction: column; }
  .redeem-row .el-button { width: 100%; }
}
</style>
