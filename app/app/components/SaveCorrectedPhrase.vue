<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { Phrase } from '~/types/speech'

type SavePhraseFormState = {
  category_id?: number
  text: string
}

const props = defineProps<{
  initialText?: string
}>()

const { categories, refreshPhrases } = usePhrases()
const formState = reactive<SavePhraseFormState>({ category_id: undefined, text: '' })
const { clearErrors, formErrors, isSaving, submit } = useFormSubmission<SavePhraseFormState>('Satz konnte nicht gespeichert werden.')
const categoryOptions = computed(() =>
  categories.value.map(category => ({ label: category.name, value: category.id }))
)

watch(
  () => props.initialText,
  () => {
    formState.text = props.initialText || ''
    formState.category_id = undefined
    clearErrors()
  },
  { immediate: true }
)
watch(() => [formState.category_id, formState.text], clearErrors)

async function savePhrase(event: FormSubmitEvent<SavePhraseFormState>) {
  if (!event.data.category_id) {
    formErrors.value = { category_id: 'Wähle eine Kategorie.' }
    return
  }
  const saved = await submit(event, data => $fetch<Phrase>('/api/phrases', {
    method: 'POST',
    body: data
  }))
  if (!saved) return
  await refreshPhrases()
  formState.text = ''
  await navigateTo('/?phrase=' + encodeURIComponent(saved.id))
}
</script>

<template>
  <UForm
    :state="formState"
    class="space-y-5"
    @submit="savePhrase"
  >
    <UFormField
      :error="formErrors.text || formErrors._form"
      label="Dein Satz"
      name="text"
    >
      <UTextarea
        v-model="formState.text"
        class="w-full"
        autoresize
        placeholder="Schreibe deinen Satz hier."
        size="xl"
      />
    </UFormField>

    <UFormField
      :error="formErrors.category_id"
      label="Kategorie"
      name="category_id"
    >
      <USelect
        v-model="formState.category_id"
        class="w-full"
        :content="{
          position: 'item-aligned'
        }"
        :disabled="!categories.length"
        :items="categoryOptions"
        placeholder="Kategorie auswählen"
        size="xl"
        :ui="{
          base: 'text-lg py-4',
          content: 'h-[min(36rem,var(--reka-select-content-available-height,36rem))] max-h-[min(36rem,var(--reka-select-content-available-height,36rem))]',
          item: 'min-h-16 items-center text-xl font-semibold'
        }"
      />
    </UFormField>

    <p
      v-if="!categories.length"
      class="text-lg font-semibold text-toned"
    >
      Bitte lege zuerst eine Kategorie an.
      <UButton
        block
        color="primary"
        icon="i-lucide-plus"
        label="Kategorie hinzufügen"
        size="xl"
        to="/categories"
      />
    </p>

    <UButton
      block
      class="min-h-24 justify-center rounded-2xl text-xl font-extrabold"
      color="primary"
      icon="i-lucide-bookmark-plus"
      label="Satz speichern"
      size="xl"
      type="submit"
      :loading="isSaving"
    />
  </UForm>
</template>
