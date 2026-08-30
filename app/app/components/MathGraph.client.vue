<script setup lang="ts">
import JXG from 'jsxgraph'

type AxisKey = 'x' | 'y'

type AxisThemeAttributes = {
  strokeColor: string
  highlightStrokeColor: string
  ticks: {
    strokeColor: string
    highlightStrokeColor: string
    drawLabels: true
    labelColor: string
    label: {
      strokeColor: string
      highlightStrokeColor: string
    }
  }
}

const props = defineProps<{
  expression: string
}>()

const graph = ref<HTMLElement>()
const error = ref('')
const isLocked = ref(true)
const colorMode = useColorMode()
let board: JXG.Board | undefined
let curve: JXG.GeometryElement | undefined

function getGraphTheme() {
  if (!graph.value) {
    return {
      axisColor: '#7a2d57',
      labelColor: '#9d5a75'
    }
  }

  const styles = getComputedStyle(graph.value)

  return {
    axisColor:
      styles.getPropertyValue('--ui-border-accented').trim() || '#7a2d57',
    labelColor: styles.getPropertyValue('--ui-text-muted').trim() || '#9d5a75'
  }
}

function getAxisAttributes(): Record<AxisKey, AxisThemeAttributes> {
  const { axisColor, labelColor } = getGraphTheme()

  const attributes = {
    strokeColor: axisColor,
    highlightStrokeColor: axisColor,
    ticks: {
      strokeColor: axisColor,
      highlightStrokeColor: axisColor,
      drawLabels: true,
      labelColor,
      label: {
        strokeColor: labelColor,
        highlightStrokeColor: labelColor
      }
    }
  } satisfies AxisThemeAttributes

  return {
    x: attributes,
    y: attributes
  }
}

function getBoardAxis(axis: AxisKey): JXG.Axis | undefined {
  return board?.defaultAxes[axis] as unknown as JXG.Axis | undefined
}

function applyBoardTheme() {
  if (!board) return

  const axisAttributes = getAxisAttributes()

  for (const axisKey of ['x', 'y'] as const) {
    const axis = getBoardAxis(axisKey)
    if (!axis) continue

    const attributes = axisAttributes[axisKey]
    axis.setAttribute({
      strokeColor: attributes.strokeColor,
      highlightStrokeColor: attributes.highlightStrokeColor
    })
    axis.defaultTicks.setAttribute(attributes.ticks)
  }

  board.update()
}

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

function draw() {
  if (!graph.value) return
  const fn = createGraphFunction(props.expression)
  if (!fn) {
    error.value = 'Bitte gib eine Funktion mit x ein.'
    return
  }

  try {
    if (!board) {
      board = JXG.JSXGraph.initBoard(graph.value, {
        axis: true,
        boundingbox: [-10, 10, 10, -10],
        defaultAxes: getAxisAttributes(),
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

watch(
  () => props.expression,
  () => {
    draw()
  }
)

watch(
  () => colorMode.value,
  () => {
    applyBoardTheme()
  }
)

onMounted(() => {
  draw()
})

onBeforeUnmount(() => {
  if (curve && board) {
    board.removeObject(curve)
  }
})
</script>

<template>
  <section
    class="space-y-3"
    aria-labelledby="graph-title"
  >
    <h2
      id="graph-title"
      class="sr-only"
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
        block
        class="min-h-20"
        icon="i-lucide-zoom-out"
        size="xl"
        type="button"
        @click="zoomOut"
      >
        <span class="max-md:sr-only">Kleiner</span>
      </UButton>
      <UButton
        block
        class="min-h-20"
        icon="i-lucide-rotate-ccw"
        size="xl"
        type="button"
        variant="soft"
        @click="resetView"
      >
        <span class="max-md:sr-only">Zurücksetzen</span>
      </UButton>
      <UButton
        block
        icon="i-lucide-zoom-in"
        size="xl"
        type="button"
        @click="zoomIn"
      >
        <span class="max-md:sr-only">Größer</span>
      </UButton>
      <UButton
        block
        class="col-span-3 min-h-20"
        :icon="isLocked ? 'i-lucide-lock' : 'i-lucide-lock-open'"
        :aria-pressed="isLocked"
        size="xl"
        type="button"
        variant="soft"
        @click="toggleLock"
      >
        {{ isLocked ? "Graph entsperren" : "Graph sperren" }}
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
