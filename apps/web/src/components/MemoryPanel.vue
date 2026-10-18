<template>
  <el-dialog :model-value="modelValue" title="🧠 我的写作记忆" width="620px" top="6vh"
             @update:model-value="$emit('update:modelValue', $event)" @open="load">
    <el-tabs v-model="tab">
      <el-tab-pane label="全局偏好" name="global">
        <p class="hint">跨模板长期有效的写作偏好，每次创作都会生效，不随作品或模板重置。</p>
        <el-input v-model="globalText" type="textarea" :rows="7" maxlength="1000" show-word-limit
                  placeholder="例如：多用短句、口语化表达；爱用生活化的比喻；结尾常留互动问题" />
        <div class="row">
          <el-button type="primary" :loading="saving" @click="save('global', 0, globalText)">
            保存全局偏好
          </el-button>
        </div>
      </el-tab-pane>
      <el-tab-pane label="分类通用" name="category">
        <p class="hint">某一分类下多个模板共用的风格要求，使用该分类的模板创作时会一起加载。</p>
        <el-select v-model="catId" placeholder="选择分类" style="width: 100%" @change="onCatChange">
          <el-option v-for="c in categories" :key="c.category_id" :label="c.name"
                     :value="c.category_id" />
        </el-select>
        <el-input v-model="catText" type="textarea" :rows="6" maxlength="1000" show-word-limit
                  placeholder="该分类下的通用要求…" style="margin-top: 10px" />
        <div class="row">
          <el-button type="primary" :disabled="!catId" :loading="saving"
                     @click="save('category', catId!, catText)">保存分类偏好</el-button>
        </div>
      </el-tab-pane>
      <el-tab-pane label="模板专属" name="template">
        <p class="hint">单个模板下的专属要求（个性化 Skill）。创作页追问时勾选「记住这个要求」也会自动沉淀到这里。</p>
        <el-select v-model="tplId" filterable placeholder="选择模板" style="width: 100%"
                   @change="onTplChange">
          <el-option v-for="t in templateOptions" :key="t.template_id" :label="t.name"
                     :value="t.template_id" />
        </el-select>
        <el-input v-model="tplText" type="textarea" :rows="6" maxlength="1000" show-word-limit
                  placeholder="该模板的专属要求…" style="margin-top: 10px" />
        <div class="row">
          <el-button type="primary" :disabled="!tplId" :loading="saving"
                     @click="save('template', tplId!, tplText)">保存模板要求</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { get, put } from '../api/http'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits(['update:modelValue'])

const tab = ref('global')
const saving = ref(false)
const globalText = ref('')
const categories = ref<any[]>([])
const catId = ref<number | null>(null)
const catText = ref('')
const templateOptions = ref<any[]>([])
const tplId = ref<number | null>(null)
const tplText = ref('')

async function load() {
  try {
    const o = (await get('/memory/overview')).data
    globalText.value = o.global || ''
    categories.value = o.categories || []
    const saved = o.templates || []
    // 下拉 = 已有记忆的模板 + 推荐列表（去重），保证能找到所有可选模板
    const extra: any[] = []
    try {
      const r = await get('/template/recommend/list?page_size=50')
      for (const t of r.data.list) {
        if (!saved.some((s: any) => s.template_id === t.template_id)) extra.push(t)
      }
    } catch { /* 推荐失败不影响已保存模板 */ }
    templateOptions.value = [...saved, ...extra]
  } catch (e: any) {
    ElMessage.error(e.message)
    emit('update:modelValue', false)
  }
}

function onCatChange() {
  const c = categories.value.find((x) => x.category_id === catId.value)
  catText.value = c?.content || ''
}

function onTplChange() {
  const t = templateOptions.value.find((x) => x.template_id === tplId.value)
  tplText.value = t?.content || ''
}

async function save(scope: string, scopeId: number, content: string) {
  saving.value = true
  try {
    await put('/memory', { scope, scope_id: scopeId, content })
    ElMessage.success('记忆已保存，下次创作即生效')
    await load()
    if (scope === 'category') onCatChange()
    if (scope === 'template') onTplChange()
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.hint { color: #999; font-size: 13px; margin: 0 0 10px; line-height: 1.6; }
.row { margin-top: 10px; display: flex; justify-content: flex-end; }
</style>
