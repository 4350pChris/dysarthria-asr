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
const formState = reactive({ text: '' })
const formErrors = ref<Record<string, string>>({})
const editing = ref<Phrase>()
const isSaving = ref(false)
const phraseToDelete = ref<Phrase>()
const isDeleting = ref(false)
const { categories, byCategory, refreshPhrases } = usePhrases()
const { savePhrase: persistPhrase } = usePhraseSaving()

const currentCategory = computed(() => categories.value.find(item => item.name === category.value))
const phrases = computed(() => byCategory(category.value))
const formLabel = computed(() => editing.value ? 'Satz ändern' : 'Neuer Satz')
const submitLabel = computed(() => editing.value ? 'Änderung speichern' : 'Satz hinzufügen')
const isDeleteModalOpen = computed(() => Boolean(phraseToDelete.value))

function startEdit(phrase: Phrase) {
  editing.value = phrase
  formState.text = phrase.text
  formErrors.value = {}
}

function resetForm() {
  editing.value = undefined
  formState.text = ''
  formErrors.value = {}
}

watch(() => formState.text, () => formErrors.value = {})

async function savePhrase() {
  const text = formState.text.trim()
  if (!text || isSaving.value) return
  if (!editing.value && !currentCategory.value) {
    formErrors.value = { text: 'Diese Kategorie gibt es nicht mehr.' }
    return
  }
  formErrors.value = {}
  isSaving.value = true
  try {
    await persistPhrase({
      text,
      categoryId: currentCategory.value?.id,
      phraseId: editing.value?.id
    })
    resetForm()
  } catch (error) {
    formErrors.value = apiFormErrors(error, 'Satz konnte nicht gespeichert werden.')
  } finally {
    isSaving.value = false
  }
}

function requestDelete(phrase: Phrase) {
  phraseToDelete.value = phrase
}

function closeDeleteModal(isOpen: boolean) {
  if (!isOpen && !isDeleting.value) {
    phraseToDelete.value = undefined
  }
}

async function confirmDelete() {
  if (!phraseToDelete.value || isDeleting.value) return
  isDeleting.value = true
  try {
    await $fetch(`/api/phrases/${phraseToDelete.value.id}`, { method: 'DELETE' })
    phraseToDelete.value = undefined
    await refreshPhrases()
  } catch (error) {
    formErrors.value = apiFormErrors(error, 'Satz konnte nicht gelöscht werden.')
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

    <UForm
      :state="formState"
      class="space-y-3"
      @submit="savePhrase"
    >
      <UFormField
        :error="formErrors.text || formErrors._form"
        :label="formLabel"
      >
        <UTextarea
          v-model="formState.text"
          class="w-full"
          autoresize
          placeholder="z. B. Ich möchte Anna anrufen."
          size="xl"
        />
      </UFormField>
      <div class="grid gap-3">
        <UButton
          class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
          block
          color="primary"
          icon="i-lucide-save"
          size="xl"
          type="submit"
          :label="submitLabel"
          :loading="isSaving"
        />
        <UButton
          class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
          block
          color="neutral"
          icon="i-lucide-x"
          label="Abbrechen"
          size="xl"
          type="button"
          variant="subtle"
          @click="resetForm"
        />
      </div>
    </UForm>

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
