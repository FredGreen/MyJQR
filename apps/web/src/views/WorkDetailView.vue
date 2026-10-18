<template>
  <WorkRoom v-if="id" :work-id="id" @back="$router.push('/works')" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import WorkRoom from '../components/WorkRoom.vue'

defineOptions({ name: 'WorkDetailView' })
const route = useRoute()
const id = computed(() => Number(route.params.id) || 0)
</script>
