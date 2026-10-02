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
        <LogoMark
          :size="40"
          label="Dysarthria ASR Tuned Listener"
        />
      </template>
      <template #right>
        <UButton
          to="/labeling"
          block
          color="neutral"
          variant="ghost"
          class="min-h-14 whitespace-normal text-center"
          :aria-current="route.path === '/labeling' ? 'page' : undefined"
        >
          Labeling
        </UButton>

        <UColorModeButton size="xl" />
      </template>
    </UHeader>

    <nav
      aria-label="Hauptnavigation"
      class="mx-auto grid max-w-3xl grid-cols-2 gap-3 px-4 pt-4"
    >
      <UButton
        to="/"
        block
        color="neutral"
        variant="soft"
        class="min-h-14 aria-[current=page]:ring aria-[current=page]:ring-primary/30"
        :aria-current="route.path === '/' ? 'page' : undefined"
      >
        Sprechen
      </UButton>
      <UButton
        to="/training"
        block
        color="neutral"
        variant="soft"
        class="min-h-14 aria-[current=page]:ring aria-[current=page]:ring-primary/30"
        :aria-current="route.path === '/training' ? 'page' : undefined"
      >
        Training
      </UButton>
    </nav>
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
