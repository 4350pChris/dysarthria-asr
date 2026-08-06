<script setup lang="ts">
const props = defineProps<{
  isRecording: boolean
  isBusy: boolean
}>()

const emit = defineEmits<{
  start: []
  stop: []
}>()

const disabledTimer = ref(false)
const state = computed(() => {
  if (props.isRecording) return 'recording'
  if (props.isBusy) return 'warming'
  return 'idle'
})

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
    :disabled="props.isBusy"
    :ui="{ base: 'flex-col gap-0 ring ring-default hover:ring-primary/50' }"
    @click="toggleRecording(!props.isRecording)"
  >
    <div :class="['record-control-content', `record-control-content--${state}`]">
      <div class="record-logo-stage">
        <LogoMark
          aria-hidden="true"
          class="record-logo record-logo--idle"
          :size="112"
        />
        <LogoSpinner
          aria-hidden="true"
          class="record-logo record-logo--recording"
          label=""
          :size="112"
          variant="compact"
        />
        <LogoSpinner
          aria-hidden="true"
          class="record-logo record-logo--warming"
          label=""
          :size="112"
          speed="warmup"
        />
      </div>

      <div class="record-label">
        <span class="record-copy record-copy--idle text-2xl font-extrabold text-highlighted">
          Aufnehmen
        </span>
        <span class="record-copy record-copy--recording text-2xl font-extrabold text-highlighted">
          Aufnahme läuft
        </span>
        <span class="record-copy record-copy--warming text-2xl font-extrabold text-highlighted">
          Erkennung wird vorbereitet
        </span>
      </div>

      <div class="record-guidance">
        <span class="record-copy record-copy--idle text-base font-semibold text-primary">
          Tippe zum Sprechen
        </span>
        <span class="record-copy record-copy--recording text-base font-semibold text-primary">
          Tippe zum Stoppen
        </span>
        <span class="record-copy record-copy--warming text-base font-semibold text-primary">
          Einen Moment bitte
        </span>
      </div>
    </div>
  </UButton>
</template>

<style scoped>
.record-control-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.record-logo-stage {
  display: grid;
  width: 7rem;
  height: 7rem;
  place-items: center;
}

.record-logo,
.record-copy {
  grid-area: 1 / 1;
  transition: opacity 240ms ease, transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.record-logo--idle,
.record-copy--idle {
  opacity: 1;
  transform: scale(1);
}

.record-logo--recording,
.record-logo--warming,
.record-copy--recording,
.record-copy--warming {
  opacity: 0;
  transform: scale(0.82);
}

.record-label,
.record-guidance {
  display: grid;
  min-width: 100%;
  place-items: center;
}

.record-control-content--recording .record-logo--idle,
.record-control-content--recording .record-copy--idle,
.record-control-content--warming .record-logo--idle,
.record-control-content--warming .record-copy--idle {
  opacity: 0;
  transform: scale(0.82);
}

.record-control-content--recording .record-logo--recording,
.record-control-content--recording .record-copy--recording,
.record-control-content--warming .record-logo--warming,
.record-control-content--warming .record-copy--warming {
  opacity: 1;
  transform: scale(1);
}

@media (prefers-reduced-motion: reduce) {
  .record-logo,
  .record-copy {
    transition: none;
  }
}
</style>
