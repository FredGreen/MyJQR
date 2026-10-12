<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2>模板管理</h2>
      <el-button type="primary" @click="openCreate">新建模板</el-button>
    </div>
    <el-table :data="rows" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" width="160" />
      <el-table-column prop="description" label="描述" min-width="240" show-overflow-tooltip />
      <el-table-column prop="workflow_type" label="工作流" width="110" />
      <el-table-column prop="joule_price" label="价格(J)" width="90" />
      <el-table-column prop="use_cnt" label="使用次数" width="100" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ ['草稿', '上线', '下架'][row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="180" />
    </el-table>

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
        <el-form-item label="联网搜索"><el-switch v-model="form.enable_web_search" /></el-form-item>
        <el-form-item label="深度思考"><el-switch v-model="form.enable_think" /></el-form-item>
        <el-form-item label="使用提示"><el-input v-model="form.usage_tips" type="textarea" :rows="2" /></el-form-item>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { get, post, put } from '../api/http'

const rows = ref<any[]>([])
const cats = ref<any[]>([])
const visible = ref(false)
const form = reactive<any>({ category_ids: [], status: 0, joule_price: 1000,
  workflow_type: 'single', enable_web_search: true, enable_think: true, temperature: 0.95,
  model_route: 'default_chat', response_length: 2, usage_example: '' })

onMounted(async () => {
  await load()
  const c = await get('/admin/categories')
  cats.value = c.data.list
})

async function load() {
  const r = await get('/admin/templates?page_size=20')
  rows.value = r.data.list
}

function openCreate() {
  Object.assign(form, { id: null, name: '', description: '', category_ids: [], status: 0,
    joule_price: 1000, workflow_type: 'single', enable_web_search: true, enable_think: true,
    temperature: 0.95, model_route: 'default_chat', response_length: 2,
    usage_example: '', usage_tips: '' })
  visible.value = true
}

async function save() {
  try {
    if (form.id) await put(`/admin/templates/${form.id}`, form)
    else await post('/admin/templates', form)
    ElMessage.success('已保存（新模板记得在数据库或后续版本页发布提示词）')
    visible.value = false
    await load()
  } catch (e: any) { ElMessage.error(e.message) }
}
</script>
