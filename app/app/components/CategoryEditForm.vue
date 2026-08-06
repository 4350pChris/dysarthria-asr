<script setup lang="ts">
import type { Category } from '~/types/speech'

const props = defineProps<{
  category: Category
  isSaving: boolean
}>()

const emit = defineEmits<{
  save: [name: string]
  cancel: []
}>()

const name = ref(props.category.name)

watch(() => props.category.name, (categoryName) => {
  name.value = categoryName
})

function save() {
  emit('save', name.value)
}

function cancel() {
  name.value = props.category.name
  emit('cancel')
}
</script>

<template>
  <UForm
    :state="{ name }"
    class="space-y-3"
    @submit="save"
  >
    <UFormField label="Name der Kategorie">
      <UInput
        v-model="name"
        class="w-full"
        size="xl"
      />
    </UFormField>
    <div class="grid gap-3">
      <UButton
        block
        class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
        color="primary"
        icon="i-lucide-save"
        label="Kategorie speichern"
        size="xl"
        type="submit"
        :loading="isSaving"
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
        :disabled="isSaving"
        @click="cancel"
      />
    </div>
  </UForm>
</template>
