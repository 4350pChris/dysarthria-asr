<script setup lang="ts">
const props = defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ reset: [], active: [active: boolean] }>()
const { track } = useUsageAnalytics()
const open = ref(false)
let confirmed = false
watch(open, (value) => {
  emit('active', value)
  if (value) confirmed = false
  else track('text_reset', { outcome: confirmed ? 'confirmed' : 'cancelled' })
}, { flush: 'sync' })

function reset() {
  if (props.disabled) return
  confirmed = true
  open.value = false
  emit('reset')
}
</script>

<template>
  <UButton
    block
    class="min-h-16"
    color="neutral"
    variant="outline"
    size="xl"
    type="button"
    :disabled="disabled"
    @click="open = true"
  >
    Neuer Text
  </UButton>

  <UModal
    v-model:open="open"
    title="Neuer Text?"
    description="Dein Text wird verworfen."
    :close="false"
  >
    <template #footer>
      <div class="grid w-full gap-4">
        <UButton
          block
          class="min-h-20"
          color="neutral"
          variant="outline"
          size="xl"
          type="button"
          @click="open = false"
        >
          Zurück
        </UButton>
        <UButton
          block
          class="min-h-20"
          color="error"
          size="xl"
          type="button"
          :disabled="disabled"
          @click="reset"
        >
          Text verwerfen
        </UButton>
      </div>
    </template>
  </UModal>
</template>
