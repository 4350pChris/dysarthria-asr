<script setup lang="ts">
const speechCommands = createSpeechCommands()

provideSpeechCommands(speechCommands)

speechCommands.register({
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

useHead({
  meta: [
    { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' }
  ],
  link: [
    { rel: 'icon', href: '/favicon.ico' }
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
  <UApp>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
