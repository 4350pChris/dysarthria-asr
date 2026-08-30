<script setup lang="ts">
import type JXG from 'jsxgraph'

const props = defineProps<{
  expression: string
}>()

const graph = ref<HTMLElement>()
const error = ref('')
let board: JXG.Board | undefined
let curve: JXG.GeometryElement | undefined

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
        showCopyright: false,
        showNavigation: true
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
    />
  </section>
</template>

<style scoped>
.jxgbox {
  overflow: hidden;
  position: relative;
  touch-action: none;
}
</style>
