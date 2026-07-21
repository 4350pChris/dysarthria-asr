<script setup lang="ts">
import type { Phrase } from '~/types/speech'

const route = useRoute()
const category = computed(() => decodeURIComponent(String(route.params.category || '')))
const status = ref('')
const formState = reactive({ text: '' })
const editing = ref<Phrase>()
const isSaving = ref(false)
const phraseToDelete = ref<Phrase>()
const isDeleting = ref(false)
const { categories, byCategory, loadPhrases } = usePhrases()

const currentCategory = computed(() => categories.value.find(item => item.name === category.value))
const phrases = computed(() => byCategory(category.value))
const formLabel = computed(() => editing.value ? 'Satz ändern' : 'Neuer Satz')
const submitLabel = computed(() => editing.value ? 'Änderung speichern' : 'Satz hinzufügen')
const isDeleteModalOpen = computed(() => Boolean(phraseToDelete.value))

watch(category, loadData, { immediate: true })

async function loadData() {
  try {
    await loadPhrases()
  } catch {
    status.value = 'Phrasen konnten nicht geladen werden.'
  }
}

function startEdit(phrase: Phrase) {
  editing.value = phrase
  formState.text = phrase.text
  status.value = 'Satz bearbeiten.'
}

function resetForm() {
  editing.value = undefined
  formState.text = ''
}

async function savePhrase() {
  const text = formState.text.trim()
  if (!text || isSaving.value) return
  isSaving.value = true
  const form = new FormData()
  form.append('text', text)
  try {
    if (editing.value) {
      await $fetch(`/api/phrases/${editing.value.id}`, { method: 'PATCH', body: form })
      status.value = 'Satz gespeichert.'
    } else if (currentCategory.value) {
      form.append('category_id', String(currentCategory.value.id))
      await $fetch('/api/phrases', { method: 'POST', body: form })
      status.value = 'Satz hinzugefügt.'
    }
    resetForm()
    await loadPhrases({ force: true })
  } catch {
    status.value = 'Satz konnte nicht gespeichert werden.'
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
    status.value = 'Satz gelöscht.'
    phraseToDelete.value = undefined
    await loadPhrases({ force: true })
  } catch {
    status.value = 'Satz konnte nicht gelöscht werden.'
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <UMain class="min-h-dvh bg-slate-50 px-4 py-5 text-slate-950">
    <UContainer class="max-w-md space-y-5">
      <UButton
        class="min-h-14 rounded-2xl font-extrabold"
        color="neutral"
        icon="i-lucide-arrow-left"
        size="xl"
        to="/phrases"
        variant="ghost"
      >
        Kategorien
      </UButton>

      <header>
        <p class="text-sm font-semibold text-slate-500">
          Satz auswählen
        </p>
        <h1 class="mt-1 text-3xl font-bold tracking-normal">
          {{ category }}
        </h1>
      </header>

      <p
        v-if="status"
        class="text-lg font-semibold text-slate-600"
      >
        {{ status }}
      </p>

      <UForm
        :state="formState"
        class="space-y-3"
        @submit="savePhrase"
      >
        <UFormField :label="formLabel">
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
          <p class="text-xl font-bold leading-snug text-slate-950">
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
    </UContainer>
  </UMain>
</template>
