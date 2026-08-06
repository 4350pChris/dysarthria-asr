<script setup lang="ts">
defineProps<{
  isRecording: boolean
  isBusy: boolean
}>()

const emit = defineEmits<{
  start: []
  stop: []
}>()

const disabledTimer = ref(false)

function toggleRecording(start: boolean) {
  if (disabledTimer.value) {
    return
  }
  disabledTimer.value = true
  setTimeout(() => {
    disabledTimer.value = false
  }, 2000)
  if (start) {
    emit('start')
  } else {
    emit('stop')
  }
}
</script>

<template>
  <UButton
    class="min-h-60 justify-center rounded-3xl text-center shadow-sm"
    block
    color="neutral"
    size="xl"
    type="button"
    variant="soft"
    :disabled="isBusy"
    :ui="{
      base: isRecording
        ? 'flex-col gap-0 ring-2 ring-primary hover:ring-primary/75'
        : 'flex-col gap-0 ring ring-default hover:ring-primary/50'
    }"
    @click="toggleRecording(!isRecording)"
  >
    <Transition
      mode="out-in"
      name="record-content"
    >
      <div
        v-if="isRecording"
        key="recording"
        class="flex flex-col items-center gap-3"
      >
        <LogoSpinner
          label="Aufnahme läuft"
          :size="92"
          variant="compact"
        />
        <span class="text-2xl font-extrabold text-highlighted">
          Aufnahme läuft
        </span>
        <span class="text-base font-semibold text-primary">
          Tippe zum Stoppen
        </span>
      </div>

      <div
        v-else
        key="idle"
        class="flex flex-col items-center gap-3"
      >
        <LogoSpinner
          v-if="isBusy"
          label="Modell wird vorbereitet"
          :size="76"
          speed="warmup"
        />
        <LogoMark
          v-else
          :size="76"
        />
        <span class="text-2xl font-extrabold text-highlighted">
          {{ isBusy ? 'Erkennung wird vorbereitet' : 'Aufnehmen' }}
        </span>
        <span class="text-base font-semibold text-primary">
          {{ isBusy ? 'Einen Moment bitte' : 'Tippe zum Sprechen' }}
        </span>
      </div>
    </Transition>
  </UButton>
</template>

<style scoped>
.record-content-enter-active,
.record-content-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.record-content-enter-from,
.record-content-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

@media (prefers-reduced-motion: reduce) {
  .record-content-enter-active,
  .record-content-leave-active {
    transition: none;
  }
}
</style>
