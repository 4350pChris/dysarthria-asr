<script setup lang="ts">
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
    <NuxtPage />
  </UApp>
</template>
