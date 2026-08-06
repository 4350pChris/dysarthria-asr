<script setup lang="ts">
const speechCommands = createSpeechCommands()

provideSpeechCommands(speechCommands)

const cleanupSpeechCommands = speechCommands.register({
  id: 'help',
  label: 'Hilfe',
  phrases: ['hilfe', 'befehle'],
  handler: () => {
    speechSynthesis.cancel()
    const labels = [...new Map(
      speechCommands.commands.value
        .filter(command => command.id !== 'help')
        .map(command => [command.id, command.label.toLocaleLowerCase('de-DE')])
    ).values()]
    const utterance = new SpeechSynthesisUtterance(`Du kannst sagen: ${labels.join(', ')}.`)
    utterance.lang = 'de-DE'
    speechSynthesis.speak(utterance)
  }
})

onScopeDispose(cleanupSpeechCommands)

useHead({
  meta: [
    { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
    { name: 'apple-mobile-web-app-capable', content: 'yes' },
    { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
    { name: 'apple-mobile-web-app-title', content: 'Sprechen' }
  ],
  link: [
    { rel: 'icon', href: '/favicon.ico' },
    { rel: 'apple-touch-icon', href: '/apple-touch-icon-180x180.png' }
  ],
  htmlAttrs: {
    lang: 'de'
  }
})

useSeoMeta({
  title: 'Sprechen',
  description: 'Persönliche Sprachhilfe'
})
</script>

<template>
  <VitePwaManifest />
  <UApp>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
