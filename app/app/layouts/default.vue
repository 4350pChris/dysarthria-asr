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
  action?: HeaderAction
}

const route = useRoute()
const speechCommands = useSpeechCommands()
useBackendAvailability()
const header = computed(() => route.meta.pageHeader as PageHeader)
const title = computed(() => {
  if (header.value.titleParam) {
    return decodeURIComponent(
      String(route.params[header.value.titleParam] || '')
    )
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
  <div class="min-h-dvh bg-default">
    <UHeader
      title="Dysarthria ASR"
      :toggle="false"
      :ui="{
        container: 'max-w-3xl px-4'
      }"
    >
      <template #left>
        <UButton
          v-if="header.showBack"
          class="min-h-14"
          color="neutral"
          icon="i-lucide-arrow-left"
          size="xl"
          :to="header.backTo || '/'"
          variant="ghost"
        >
          {{ header.backLabel || "Zurück" }}
        </UButton>
        <LogoLockup :mark-size="40" />
      </template>
      <template #right>
        <UColorModeButton size="xl" />
      </template>
    </UHeader>

    <section class="px-4 pt-4">
      <UContainer class="max-w-3xl space-y-4 pb-5">
        <div>
          <p class="text-sm font-semibold text-muted">
            {{ header.eyebrow }}
          </p>
          <h1 class="mt-1 text-3xl font-bold tracking-normal">
            {{ title }}
          </h1>
        </div>
        <UButton
          v-if="header.action"
          class="min-h-12"
          color="primary"
          :icon="header.action.icon"
          size="lg"
          :to="header.action.to"
        >
          {{ header.action.label }}
        </UButton>
      </UContainer>
    </section>

    <UMain class="min-h-dvh px-4 pb-5 text-highlighted">
      <UContainer
        class="max-w-3xl flex min-h-[calc(100dvh-2.5rem)] flex-col space-y-5"
      >
        <PwaInstallHint />
        <PwaUpdatePrompt />

        <slot />
      </UContainer>
    </UMain>
  </div>
</template>
