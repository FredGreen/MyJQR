<template>
  <div>
    <h2>兑换码管理</h2>
    <el-card style="max-width:560px">
      <b>批量生成</b>
      <div style="display:flex;gap:10px;margin-top:10px;align-items:center">
        <el-input-number v-model="amount" :min="100" :step="100" placeholder="面额(J)" />
        <el-input-number v-model="count" :min="1" :max="500" placeholder="数量" />
        <el-button type="primary" @click="gen">生成</el-button>
      </div>
      <div v-if="codes.length" style="margin-top:14px">
        <el-text type="info">批次 {{ batchNo }}，共 {{ codes.length }} 张：</el-text>
        <div class="codes">{{ codes.join('\n') }}</div>
        <el-button size="small" style="margin-top:8px" @click="copyAll">复制全部</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { post } from '../api/http'

const amount = ref(1000)
const count = ref(10)
const codes = ref<string[]>([])
const batchNo = ref('')

async function gen() {
  const r = await post('/admin/redeem-codes/batch', { amount: amount.value, count: count.value })
  codes.value = r.data.codes
  batchNo.value = r.data.batch_no
}

function copyAll() {
  navigator.clipboard.writeText(codes.value.join('\n'))
  ElMessage.success('已复制')
}
</script>

<style scoped>
.codes { white-space: pre-wrap; background: #fafafa; padding: 12px; border-radius: 6px;
  margin-top: 8px; font-family: monospace; max-height: 300px; overflow: auto; }
</style>
