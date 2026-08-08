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
const { isTargetReady } = useStartupLogoTransition()
const state = computed(() => {
  if (props.isRecording) return 'recording'
  if (props.isBusy) return 'warming'
  return 'idle'
})

const copy = computed(() => ({
  idle: {
    title: 'Aufnehmen',
    guidance: 'Tippe zum Sprechen'
  },
  recording: {
    title: 'Aufnahme läuft',
    guidance: 'Tippe zum Stoppen'
  },
  warming: {
    title: 'Erkennung wird vorbereitet',
    guidance: 'Einen Moment bitte'
  }
})[state.value])

function toggleRecording() {
  if (disabledTimer.value) {
    return
  }
  disabledTimer.value = true
  setTimeout(() => {
    disabledTimer.value = false
  }, 2000)
  if (!props.isRecording) {
    emit('start')
  } else {
    emit('stop')
  }
}
</script>

<template>
  <slot
    :is-busy="props.isBusy"
    :is-recording="props.isRecording"
    :toggle="toggleRecording"
  >
    <UButton
      class="min-h-60 justify-center rounded-3xl text-center shadow-sm"
      block
      color="neutral"
      size="xl"
      type="button"
      variant="soft"
      :disabled="props.isBusy"
      :ui="{ base: 'flex-col gap-0 ring ring-default hover:ring-primary/50' }"
      @click="toggleRecording"
    >
      <div class="flex flex-col items-center gap-3">
        <div
          data-startup-logo-target
          class="grid size-28 place-items-center"
          :class="{ 'opacity-0': !isTargetReady }"
        >
          <LogoMark
            aria-hidden="true"
            :size="112"
            :state="state"
          />
        </div>

        <div class="grid min-w-full place-items-center">
          <Transition name="record-copy">
            <div
              :key="state"
              class="col-start-1 row-start-1 flex flex-col items-center gap-3"
            >
              <span class="min-h-8 text-2xl font-extrabold text-highlighted">
                {{ copy.title }}
              </span>

              <span class="min-h-6 text-base font-semibold text-muted">
                {{ copy.guidance }}
              </span>
            </div>
          </Transition>
        </div>
      </div>
    </UButton>
  </slot>
</template>

<style scoped>
.record-copy-enter-active,
.record-copy-leave-active {
  @apply transition-opacity duration-200 motion-reduce:transition-none;
}

.record-copy-enter-from,
.record-copy-leave-to {
  @apply opacity-0;
}
</style>
