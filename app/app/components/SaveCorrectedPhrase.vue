<script setup lang="ts">
import type { Category, Suggestion } from '~/types/speech'

const props = defineProps<{
  selected?: Suggestion
}>()

const { categories } = usePhrases()
const { savePhrase: persistPhrase } = usePhraseSaving()
const correctedText = ref('')
const selectedCategory = ref<Category>()
const isSaveModalOpen = ref(false)
const isSaving = ref(false)
const status = ref('')

watch(
  () => props.selected?.id,
  () => {
    correctedText.value = props.selected?.text || ''
    selectedCategory.value = undefined
    status.value = ''
  },
  { immediate: true }
)

function openSaveModal() {
  if (!correctedText.value.trim()) return
  selectedCategory.value = undefined
  isSaveModalOpen.value = true
}

async function savePhrase() {
  const text = correctedText.value.trim()
  if (!text || !selectedCategory.value || isSaving.value) return
  isSaving.value = true
  try {
    await persistPhrase({
      text,
      categoryId: selectedCategory.value.id
    })
    status.value = `Gespeichert in: ${selectedCategory.value.name}.`
    isSaveModalOpen.value = false
  } catch {
    status.value = 'Satz konnte nicht gespeichert werden.'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="space-y-3 rounded-3xl bg-elevated p-4">
    <UFormField label="Satz korrigieren">
      <UTextarea
        v-model="correctedText"
        class="w-full"
        autoresize
        size="xl"
      />
    </UFormField>
    <p
      v-if="status"
      class="text-lg font-semibold text-toned"
    >
      {{ status }}
    </p>
    <UButton
      block
      class="min-h-20 justify-center rounded-2xl text-lg font-extrabold"
      color="primary"
      icon="i-lucide-bookmark-plus"
      label="Als eigenen Satz speichern"
      size="xl"
      type="button"
      :disabled="!correctedText.trim()"
      @click="openSaveModal"
    />

    <UModal
      v-model:open="isSaveModalOpen"
      title="Kategorie wählen"
      description="Wähle zuerst eine Kategorie. Danach speicherst du den Satz."
    >
      <template #body>
        <div class="space-y-3">
          <UButton
            v-for="category in categories"
            :key="category.id"
            block
            class="min-h-20 justify-start rounded-2xl text-left text-xl font-extrabold"
            color="neutral"
            type="button"
            variant="subtle"
            :class="selectedCategory?.id === category.id ? 'ring-4 ring-primary/20 border-primary' : ''"
            @click="selectedCategory = category"
          >
            {{ category.name }}
          </UButton>
          <p
            v-if="!categories.length"
            class="text-lg font-semibold text-toned"
          >
            Bitte lege zuerst eine Kategorie an.
          </p>
        </div>
      </template>

      <template #footer>
        <div class="grid w-full gap-3">
          <UButton
            block
            class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
            color="primary"
            icon="i-lucide-save"
            :label="selectedCategory ? `In ${selectedCategory.name} speichern` : 'Kategorie wählen'"
            size="xl"
            type="button"
            :disabled="!selectedCategory"
            :loading="isSaving"
            @click="savePhrase"
          />
          <UButton
            block
            class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
            color="neutral"
            icon="i-lucide-x"
            label="Abbrechen"
            size="xl"
            type="button"
            variant="subtle"
            @click="isSaveModalOpen = false"
          />
        </div>
      </template>
    </UModal>
  </section>
</template>
