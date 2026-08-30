<script setup lang="ts">
import type JXG from 'jsxgraph'

const props = defineProps<{
  expression: string
}>()

const graph = ref<HTMLElement>()
const error = ref('')
const isLocked = ref(true)
let board: JXG.Board | undefined
let curve: JXG.GeometryElement | undefined

function zoomIn() {
  board?.zoomIn()
}

function zoomOut() {
  board?.zoomOut()
}

function resetView() {
  board?.setBoundingBox([-10, 10, 10, -10], true)
}

function toggleLock() {
  isLocked.value = !isLocked.value
  if (!board) return
  board.attr.pan.enabled = !isLocked.value
}

async function draw() {
  if (!graph.value) return
  const fn = createGraphFunction(props.expression)
  if (!fn) {
    error.value = 'Bitte gib eine Funktion mit x ein.'
    return
  }

  try {
    const { default: JXG } = await import('jsxgraph')
    if (!board) {
      board = JXG.JSXGraph.initBoard(graph.value, {
        axis: true,
        boundingbox: [-10, 10, 10, -10],
        keepaspectratio: true,
        pan: { enabled: false },
        showCopyright: false,
        showNavigation: false,
        zoom: false
      })
    } else if (curve) {
      board.removeObject(curve)
    }
    curve = board.create('functiongraph', [fn], {
      strokeColor: '#db2777',
      strokeWidth: 3
    })
    error.value = ''
  } catch {
    error.value = 'Diese Funktion kann nicht gezeichnet werden.'
  }
}

watch(() => props.expression, () => {
  void draw()
})
onMounted(() => {
  void draw()
})
onBeforeUnmount(() => curve && board?.removeObject(curve))
</script>

<template>
  <section
    class="space-y-3"
    aria-labelledby="graph-title"
  >
    <h2
      id="graph-title"
      class="text-xl font-bold"
    >
      Graph
    </h2>
    <p
      v-if="error"
      class="font-semibold text-error"
      role="status"
    >
      {{ error }}
    </p>
    <div
      ref="graph"
      class="h-96 w-full rounded-2xl border border-default bg-default"
      :class="{ 'pointer-events-none': isLocked }"
    />
    <div class="grid grid-cols-3 gap-3">
      <UButton
        class="min-h-20 justify-center"
        icon="i-lucide-zoom-out"
        size="xl"
        type="button"
        @click="zoomOut"
      >
        Kleiner
      </UButton>
      <UButton
        class="min-h-20 justify-center"
        icon="i-lucide-rotate-ccw"
        size="xl"
        type="button"
        variant="soft"
        @click="resetView"
      >
        Zurücksetzen
      </UButton>
      <UButton
        class="min-h-20 justify-center"
        icon="i-lucide-zoom-in"
        size="xl"
        type="button"
        @click="zoomIn"
      >
        Größer
      </UButton>
      <UButton
        class="col-span-3 min-h-20 justify-center"
        :icon="isLocked ? 'i-lucide-lock' : 'i-lucide-lock-open'"
        :aria-pressed="isLocked"
        size="xl"
        type="button"
        variant="soft"
        @click="toggleLock"
      >
        {{ isLocked ? 'Graph entsperren' : 'Graph sperren' }}
      </UButton>
    </div>
  </section>
</template>

<style scoped>
.jxgbox {
  overflow: hidden;
  position: relative;
  touch-action: none;
}
</style>
