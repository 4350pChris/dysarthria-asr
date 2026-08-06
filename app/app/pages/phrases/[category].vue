<script setup lang="ts">
import type { Phrase } from '~/types/speech'

const route = useRoute()

definePageMeta({
  pageHeader: {
    backLabel: 'Kategorien',
    backTo: '/phrases',
    eyebrow: 'Satz auswählen',
    showBack: true,
    titleParam: 'category'
  }
})

const category = computed(() => decodeURIComponent(String(route.params.category || '')))
const phraseToEdit = ref<Phrase>()
const phraseToDelete = ref<Phrase>()
const isDeleting = ref(false)
const { categories, byCategory, refreshPhrases } = usePhrases()

const currentCategory = computed(() => categories.value.find(item => item.name === category.value))
const phrases = computed(() => byCategory(category.value))
const isDeleteModalOpen = computed(() => Boolean(phraseToDelete.value))

function requestDelete(phrase: Phrase) {
  phraseToDelete.value = phrase
}

function closeDeleteModal(isOpen: boolean) {
  if (!isOpen && !isDeleting.value) {
    phraseToDelete.value = undefined
  }
}

function startEdit(phrase: Phrase) {
  phraseToEdit.value = phrase
}

async function confirmDelete() {
  if (!phraseToDelete.value || isDeleting.value) return
  isDeleting.value = true
  try {
    await $fetch(`/api/phrases/${phraseToDelete.value.id}`, { method: 'DELETE' })
    phraseToDelete.value = undefined
    await refreshPhrases()
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <div class="space-y-5">
    <CategoryManagement
      v-if="currentCategory"
      :category="currentCategory"
    />

    <PhraseForm
      v-if="currentCategory"
      v-model:editing="phraseToEdit"
      :current-category="currentCategory"
    />

    <PhraseGrid
      :phrases="phrases"
      @edit="startEdit"
      @delete="requestDelete"
    />

    <UModal
      :open="isDeleteModalOpen"
      title="Satz löschen?"
      description="Dieser Satz wird aus der Liste entfernt."
      :close="false"
      @update:open="closeDeleteModal"
    >
      <template #body>
        <p class="text-xl font-bold leading-snug text-highlighted">
          {{ phraseToDelete?.text }}
        </p>
      </template>

      <template #footer>
        <div class="grid w-full gap-3">
          <UButton
            block
            class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
            color="error"
            icon="i-lucide-trash-2"
            label="Ja, löschen"
            size="xl"
            type="button"
            :loading="isDeleting"
            @click="confirmDelete"
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
            @click="phraseToDelete = undefined"
          />
        </div>
      </template>
    </UModal>
  </div>
</template>
