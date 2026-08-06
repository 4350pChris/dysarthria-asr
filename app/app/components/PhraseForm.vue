<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { Category, Phrase } from '~/types/speech'

type PhraseFormState = { text: string }

const props = defineProps<{
  currentCategory: Category | undefined
}>()

const formState = reactive<PhraseFormState>({ text: '' })

const editing = defineModel<Phrase | undefined>('editing', { required: true })

const { refreshPhrases } = usePhrases()
const { clearErrors, formErrors, isSaving, submit }
  = useFormSubmission<PhraseFormState>('Satz konnte nicht gespeichert werden.')
const formLabel = computed(() =>
  editing.value ? 'Satz ändern' : 'Neuer Satz'
)
const submitLabel = computed(() =>
  editing.value ? 'Änderung speichern' : 'Satz hinzufügen'
)

function resetForm() {
  editing.value = undefined
  formState.text = ''
  clearErrors()
}

watch(editing, (newEditing) => {
  const newText = newEditing?.text || ''
  formState.text = newText
  clearErrors()
})

watch(() => formState.text, clearErrors)

async function savePhrase(event: FormSubmitEvent<PhraseFormState>) {
  const phraseId = editing.value?.id
  const categoryId = props.currentCategory?.id
  if (!phraseId && !categoryId) {
    formErrors.value = { text: 'Diese Kategorie gibt es nicht mehr.' }
    return
  }
  const saved = await submit(event, data => phraseId
    ? $fetch<Phrase>(`/api/phrases/${phraseId}`, { method: 'PATCH', body: data })
    : $fetch<Phrase>('/api/phrases', { method: 'POST', body: { ...data, category_id: categoryId } })
  )
  if (!saved) return
  await refreshPhrases()
  resetForm()
}
</script>

<template>
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
        :disabled="!formState.text.trim()"
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
        :disabled="!formState.text.trim()"
        icon="i-lucide-x"
        label="Abbrechen"
        size="xl"
        type="button"
        variant="subtle"
        @click="resetForm"
      />
    </div>
  </UForm>
</template>
