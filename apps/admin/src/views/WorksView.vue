<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2>作品列表
        <span v-if="filterUser" style="font-size:14px;color:#909399">
          （用户：{{ filterUserLabel }} <el-button link @click="clearFilter">清除筛选</el-button>）
        </span>
        <span v-else-if="filterTemplate" style="font-size:14px;color:#909399">
          （模板：{{ filterTemplateLabel }} <el-button link @click="clearFilter">清除筛选</el-button>）
        </span>
      </h2>
      <el-select v-model="status" placeholder="全部状态" clearable style="width:150px"
                 @change="statusSearch">
        <el-option value="done" label="已完成" />
        <el-option value="failed" label="失败" />
        <el-option value="generating" label="生成中" />
        <el-option value="banned" label="已封禁" />
      </el-select>
    </div>
    <el-table :data="rows" stripe>
      <el-table-column prop="work_id" label="ID" width="70" />
      <el-table-column label="用户" min-width="180">
        <template #default="{ row }">{{ row.user_nickname }}（{{ row.user_email }}）</template>
      </el-table-column>
      <el-table-column prop="template_name" label="模板" width="130" />
      <el-table-column label="标题/主题" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">{{ row.title || row.topic }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="word_cnt" label="字数" width="80" />
      <el-table-column prop="joule_cost" label="消耗(J)" width="85" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row.work_id)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
                   :page-sizes="[10, 20, 30, 50, 100, 500]"
                   layout="total, sizes, prev, pager, next, jumper" background
                   style="margin-top:14px;justify-content:flex-end;flex-wrap:wrap"
                   @size-change="sizeChange" @current-change="load" />

    <el-dialog v-model="detailVisible" title="作品详情" width="760px" top="5vh">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small" style="margin-bottom:12px">
          <el-descriptions-item label="用户">{{ detail.user_nickname }}（{{ detail.user_email }}）</el-descriptions-item>
          <el-descriptions-item label="模板">{{ detail.template_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
          <el-descriptions-item label="字数 / 消耗">{{ detail.word_cnt }} 字 / {{ detail.joule_cost }} J</el-descriptions-item>
          <el-descriptions-item label="模型">{{ detail.model_used || '—' }}</el-descriptions-item>
          <el-descriptions-item label="AI率">{{ detail.report ? `${detail.report.ai_rate}%（${detail.report.level}）` : '—' }}</el-descriptions-item>
          <el-descriptions-item label="主题" :span="2">{{ detail.topic }}</el-descriptions-item>
        </el-descriptions>
        <el-tabs>
          <el-tab-pane label="正文">
            <div class="md-content">{{ detail.content_md || '（无内容）' }}</div>
          </el-tab-pane>
          <el-tab-pane :label="`引用 ${detail.references.length}`">
            <div v-for="r in detail.references" :key="r.idx" style="margin-bottom:6px">
              [{{ r.idx }}] <a :href="r.url" target="_blank" rel="noopener">{{ r.title }}</a>
              <span style="color:#909399">（{{ r.site_name }}）</span>
            </div>
            <div v-if="!detail.references.length" style="color:#909399">无引用</div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get } from '../api/http'

const route = useRoute()
const router = useRouter()
const rows = ref<any[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const status = ref('')
const detailVisible = ref(false)
const detail = ref<any>(null)

const filterUser = computed(() => Number(route.query.user_id) || 0)
const filterTemplate = computed(() => Number(route.query.template_id) || 0)
const filterUserLabel = computed(() => rows.value[0]?.user_email || `#${filterUser.value}`)
const filterTemplateLabel = computed(() => rows.value[0]?.template_name || `#${filterTemplate.value}`)

onMounted(load)

function sizeChange() {
  page.value = 1
  load()
}

async function load() {
  const params = new URLSearchParams({ page: String(page.value), page_size: String(pageSize.value) })
  if (filterUser.value) params.set('user_id', String(filterUser.value))
  if (filterTemplate.value) params.set('template_id', String(filterTemplate.value))
  if (status.value) params.set('status', status.value)
  const r = await get(`/admin/works?${params}`)
  rows.value = r.data.list
  total.value = r.data.total
}

function statusSearch() {
  page.value = 1
  load()
}

function clearFilter() {
  router.replace({ path: '/works' })
  page.value = 1
  load()
}

async function openDetail(id: number) {
  const r = await get(`/admin/works/${id}`)
  detail.value = { ...r.data, references: r.data.references || [] }
  detailVisible.value = true
}

function statusText(s: string) {
  return ({ done: '已完成', failed: '失败', generating: '生成中', detecting: '检测中', banned: '已封禁' } as Record<string, string>)[s] || s
}
function statusType(s: string) {
  return ({ done: 'success', failed: 'danger', generating: 'warning', detecting: 'warning', banned: 'info' } as Record<string, string>)[s] || 'info'
}
</script>

<style scoped>
.md-content { white-space: pre-wrap; line-height: 1.7; max-height: 50vh; overflow: auto; }
</style>
