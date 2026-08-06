<script setup lang="ts">
type HeaderAction = {
  to: string
  label: string
  icon: string
}

type PageHeader = {
  eyebrow: string
  title?: string
  titleParam?: string
  backTo?: string
  backLabel?: string
  showBack?: boolean
  wide?: boolean
  action?: HeaderAction
}

const route = useRoute()
const speechCommands = useSpeechCommands()
const header = computed(() => route.meta.pageHeader as PageHeader)
const title = computed(() => {
  if (header.value.titleParam) {
    return decodeURIComponent(String(route.params[header.value.titleParam] || ''))
  }
  return header.value.title || ''
})

useSpeechCommand({
  id: 'back',
  label: 'Zurück',
  phrases: ['zurück', 'zurueck', 'zurückgehen'],
  handler: async () => {
    if (!header.value.showBack) {
      speechCommands.status.value = 'Du bist auf der Startseite.'
      return
    }
    await navigateTo(header.value.backTo || '/')
  }
})
</script>

<template>
  <UMain class="min-h-dvh bg-default px-4 py-5 text-highlighted">
    <UContainer
      :class="[
        header.wide ? 'max-w-3xl' : 'max-w-md',
        'flex min-h-[calc(100dvh-2.5rem)] flex-col space-y-5'
      ]"
    >
      <div
        v-if="header.showBack || header.action"
        class="flex items-center justify-between gap-3"
      >
        <UButton
          v-if="header.showBack"
          class="min-h-14 rounded-2xl font-extrabold"
          color="neutral"
          icon="i-lucide-arrow-left"
          size="xl"
          :to="header.backTo || '/'"
          variant="ghost"
        >
          {{ header.backLabel || 'Zurück' }}
        </UButton>
        <UButton
          v-if="header.action"
          class="min-h-12 font-extrabold"
          color="primary"
          :icon="header.action.icon"
          size="lg"
          :to="header.action.to"
        >
          {{ header.action.label }}
        </UButton>
      </div>

      <header>
        <p class="text-sm font-semibold text-muted">
          {{ header.eyebrow }}
        </p>
        <h1 class="mt-1 text-3xl font-bold tracking-normal">
          {{ title }}
        </h1>
      </header>

      <PwaInstallHint />
      <PwaUpdatePrompt />

      <slot />
    </UContainer>
  </UMain>
</template>
