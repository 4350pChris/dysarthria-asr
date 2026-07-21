<script setup lang="ts">
import type { Phrase } from '~/types/speech'

defineProps<{
  phrases: Phrase[]
}>()

defineEmits<{
  edit: [phrase: Phrase]
  delete: [phrase: Phrase]
}>()
</script>

<template>
  <div class="grid gap-3">
    <UCard
      v-for="phrase in phrases"
      :key="phrase.id"
    >
      <p class="text-xl font-bold leading-snug text-slate-950">
        {{ phrase.text }}
      </p>
      <div class="mt-4 grid grid-cols-3 gap-2">
        <UButton
          class="min-h-14 justify-center rounded-2xl font-extrabold"
          color="primary"
          icon="i-lucide-volume-2"
          :to="{ path: '/', query: { phrase: phrase.number } }"
        >
          Sagen
        </UButton>
        <UButton
          class="min-h-14 justify-center rounded-2xl font-extrabold"
          color="neutral"
          icon="i-lucide-pencil"
          type="button"
          variant="subtle"
          @click="$emit('edit', phrase)"
        >
          Ändern
        </UButton>
        <UButton
          class="min-h-14 justify-center rounded-2xl font-extrabold"
          color="error"
          icon="i-lucide-trash-2"
          type="button"
          variant="subtle"
          @click="$emit('delete', phrase)"
        >
          Löschen
        </UButton>
      </div>
    </UCard>
  </div>
</template>
