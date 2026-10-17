<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2>模板管理</h2>
      <el-button type="primary" @click="openCreate">新建模板</el-button>
    </div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" width="160" />
      <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
      <el-table-column prop="workflow_type" label="工作流" width="100" />
      <el-table-column prop="joule_price" label="价格(J)" width="90" />
      <el-table-column label="使用次数" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="viewWorks(row)">{{ row.use_cnt }}</el-button>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ ['草稿', '上线', '下架'][row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="170" />
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
                   :page-sizes="[10, 20, 30, 50, 100, 500]"
                   layout="total, sizes, prev, pager, next, jumper" background
                   style="margin-top:14px;justify-content:flex-end;flex-wrap:wrap"
                   @size-change="sizeChange" @current-change="load" />

    <el-dialog v-model="visible" :title="form.id ? '编辑模板' : '新建模板'" width="680px">
      <el-form label-width="100px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category_ids" multiple placeholder="可多选">
            <el-option v-for="c in cats" :key="c.category_id" :value="c.category_id" :label="c.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="工作流">
          <el-select v-model="form.workflow_type" style="width:200px">
            <el-option value="single" label="single 单篇生成" />
            <el-option value="de_ai" label="de_ai 降AI率" />
          </el-select>
        </el-form-item>
        <el-form-item label="价格(J)"><el-input-number v-model="form.joule_price" :min="0" :step="100" /></el-form-item>
        <el-form-item label="默认长度档">
          <el-select v-model="form.response_length" style="width:200px">
            <el-option :value="0" label="微篇 ~100字" />
            <el-option :value="1" label="短篇 ~1200字" />
            <el-option :value="2" label="中篇 ~2000字" />
            <el-option :value="3" label="长篇 ~3000字" />
          </el-select>
        </el-form-item>
        <el-form-item label="联网搜索"><el-switch v-model="form.enable_web_search" /></el-form-item>
        <el-form-item label="深度思考"><el-switch v-model="form.enable_think" /></el-form-item>
        <el-form-item label="使用提示"><el-input v-model="form.usage_tips" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="提示词">
          <div style="width:100%">
            <el-input v-model="form.system_prompt" type="textarea" :rows="6"
                      placeholder="系统提示词（≥10 字生效）：人设/任务/风格/要求。留空=不修改现有提示词；改动后保存会自动生成新版本并发布" />
            <el-input v-model="form.user_prompt_template" type="textarea" :rows="2" style="margin-top:6px"
                      placeholder="用户提示词模板（可选）：可用 {topic} {material} {length} 占位" />
          </div>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio :value="0">草稿</el-radio><el-radio :value="1">上线</el-radio><el-radio :value="2">下架</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="模板详情" width="720px" top="5vh">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small" style="margin-bottom:12px">
          <el-descriptions-item label="ID / 状态">{{ detail.id }} /
            <el-tag :type="detail.status === 1 ? 'success' : 'info'" size="small">
              {{ ['草稿', '上线', '下架'][detail.status] }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="工作流 / 路由">{{ detail.workflow_type }} / {{ detail.model_route }}</el-descriptions-item>
          <el-descriptions-item label="价格">{{ detail.joule_price }} J</el-descriptions-item>
          <el-descriptions-item label="参数">温度 {{ detail.temperature }}｜长度档 {{ detail.response_length }}｜
            联网 {{ detail.enable_web_search ? '开' : '关' }}｜思考 {{ detail.enable_think ? '开' : '关' }}</el-descriptions-item>
          <el-descriptions-item label="使用 / 用户数">
            <el-button link type="primary" @click="viewWorks({ id: detail.id })">{{ detail.stats.use_cnt }} 次</el-button>
            / {{ detail.stats.user_cnt }} 人
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ detail.updated_at }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ detail.description || '—' }}</el-descriptions-item>
          <el-descriptions-item label="使用示例" :span="2">{{ detail.usage_example || '—' }}</el-descriptions-item>
        </el-descriptions>
        <el-tabs>
          <el-tab-pane :label="`当前提示词 v${detail.prompt?.version ?? '-'}`">
            <div v-if="detail.prompt" class="md-content">
              <div style="color:#909399;margin-bottom:6px">system_prompt：</div>
              <div class="prompt-box">{{ detail.prompt.system_prompt }}</div>
              <div style="color:#909399;margin:8px 0 6px">user_prompt_template：</div>
              <div class="prompt-box">{{ detail.prompt.user_prompt_template }}</div>
            </div>
            <div v-else style="color:#f56c6c">该模板没有已发布的提示词版本</div>
          </el-tab-pane>
          <el-tab-pane :label="`版本历史 ${detail.prompt_versions.length}`">
            <el-table :data="detail.prompt_versions" size="small">
              <el-table-column prop="version" label="版本" width="80" />
              <el-table-column label="发布状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.published === 1 ? 'success' : 'info'" size="small">
                    {{ row.published === 1 ? '已发布' : '未发布' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { get, post, put } from '../api/http'

const router = useRouter()
const rows = ref<any[]>([])
const cats = ref<any[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const visible = ref(false)
const detailVisible = ref(false)
const detail = ref<any>(null)
const form = reactive<any>({ category_ids: [], status: 0, joule_price: 1000,
  workflow_type: 'single', enable_web_search: true, enable_think: true, temperature: 0.95,
  model_route: 'default_chat', response_length: 2, usage_example: '' })

onMounted(async () => {
  await load()
  const c = await get('/admin/categories')
  cats.value = c.data.list
})

function sizeChange() {
  page.value = 1
  load()
}

async function load() {
  const r = await get(`/admin/templates?page=${page.value}&page_size=${pageSize.value}`)
  rows.value = r.data.list
  total.value = r.data.total
}

function openCreate() {
  Object.assign(form, { id: null, name: '', description: '', category_ids: [], status: 0,
    joule_price: 1000, workflow_type: 'single', enable_web_search: true, enable_think: true,
    temperature: 0.95, model_route: 'default_chat', response_length: 2,
    usage_example: '', usage_tips: '', system_prompt: '', user_prompt_template: '' })
  visible.value = true
}

async function openEdit(row: any) {
  // 拉全量字段（列表接口只含展示字段，编辑需完整数据 + 分类挂载）
  const r = await get(`/admin/templates/${row.id}`)
  const d = r.data
  Object.assign(form, {
    id: d.id, name: d.name, description: d.description, category_ids: d.category_ids,
    status: d.status, joule_price: d.joule_price, workflow_type: d.workflow_type,
    enable_web_search: d.enable_web_search, enable_think: d.enable_think,
    temperature: d.temperature, model_route: d.model_route,
    response_length: d.response_length, usage_example: d.usage_example, usage_tips: d.usage_tips,
    system_prompt: d.prompt?.system_prompt || '',
    user_prompt_template: d.prompt?.user_prompt_template || '',
  })
  visible.value = true
}

async function openDetail(row: any) {
  const r = await get(`/admin/templates/${row.id}`)
  detail.value = r.data
  detailVisible.value = true
}

async function save() {
  try {
    if (form.id) await put(`/admin/templates/${form.id}`, form)
    else await post('/admin/templates', form)
    ElMessage.success(form.system_prompt ? '已保存，提示词变更已自动发布' : '已保存（未填提示词的模板无法被用户生成）')
    visible.value = false
    await load()
  } catch (e: any) { ElMessage.error(e.message) }
}

function viewWorks(row: any) {
  router.push({ path: '/works', query: { template_id: row.id } })
}
</script>

<style scoped>
.md-content { white-space: pre-wrap; line-height: 1.6; max-height: 45vh; overflow: auto; }
.prompt-box { background: #f5f7fa; padding: 10px; border-radius: 4px; white-space: pre-wrap; }
</style>
