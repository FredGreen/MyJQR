<template>
  <div class="page">
    <h2>我的焦耳</h2>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card>
          <div class="big">{{ balance }}</div>
          <div class="muted">可用焦耳</div>
          <div class="muted">冻结：{{ frozen }} J ｜ 累计消费：{{ spent }} J</div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card>
          <b>兑换码充值</b>
          <div style="display:flex;gap:10px;margin-top:10px">
            <el-input v-model="code" placeholder="输入兑换码" size="large" />
            <el-button type="primary" size="large" @click="redeem">兑换</el-button>
          </div>
          <div class="muted" style="margin-top:10px">兑换码请联系管理员获取</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top:16px">
      <b>流水记录</b>
      <el-table :data="txs" stripe size="small" style="margin-top:10px">
        <el-table-column prop="id" label="#" width="70" />
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            {{ ({ generate: '生成消费', refund: '退款', redeem: '兑换充值', gift: '赠送', adjust: '调账' } as Record<string, string>)[row.biz_type] || row.biz_type }}
          </template>
        </el-table-column>
        <el-table-column label="变动" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.amount > 0 ? '#1b7d46' : '#c0392b' }">
              {{ row.amount > 0 ? '+' : '' }}{{ row.amount }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="balance_after" label="余额" width="100" />
        <el-table-column prop="remark" label="备注" min-width="160" />
        <el-table-column prop="created_at" label="时间" width="180" />
      </el-table>
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
const txs = ref<any[]>([])
const code = ref('')

onMounted(load)

async function load() {
  const [b, t] = await Promise.all([get('/joule/me'), get('/joule/transactions?page_size=20')])
  balance.value = b.data.balance
  frozen.value = b.data.frozen
  spent.value = b.data.total_spent
  auth.setProfile(auth.nickname, b.data.balance)
  txs.value = t.data.list
}

async function redeem() {
  if (!code.value.trim()) return
  try {
    const r = await post('/joule/redeem', { code: code.value.trim() })
    ElMessage.success(`充值成功 +${r.data.amount} J`)
    code.value = ''
    await load()
  } catch (e: any) { ElMessage.error(e.message) }
}
</script>

<style scoped>
.big { font-size: 40px; font-weight: 700; color: #d4820a; }
.muted { color: #999; font-size: 13px; margin-top: 4px; }
</style>
