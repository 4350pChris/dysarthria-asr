<script setup lang="ts">
import type { SpeechMode } from '~/components/SpeechWorkspace.vue'

definePageMeta({
  pageHeader: {
    eyebrow: 'Sprachhilfe',
    title: 'Was möchtest du sagen?'
  }
})

const route = useRoute()
const router = useRouter()

function parseMode(value: unknown): SpeechMode {
  return value === 'math' || value === 'emoji' ? value : 'text'
}

const mode = computed<SpeechMode>({
  get() {
    return parseMode(route.query.mode)
  },
  async set(value) {
    const query = { ...route.query }

    if (value === 'text') {
      delete query.mode
    } else {
      query.mode = value
    }

    await router.replace({ query })
  }
})
</script>

<template>
  <SpeechWorkspace v-model:mode="mode" />
</template>
