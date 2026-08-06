<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'

type ImportFormState = { targetSender: string }

const files = ref<File[] | null>(null)
const formState = reactive<ImportFormState>({ targetSender: '' })
const availableSenders = ref<string[]>([])
const isLoadingSenders = ref(false)
const { clearErrors, formErrors, isSaving, submit } = useFormSubmission<ImportFormState>('WhatsApp-Audios konnten nicht importiert werden.')

const senderOptions = computed(() =>
  availableSenders.value.map(sender => ({ label: sender, value: sender }))
)
const hasArchive = computed(() =>
  files.value?.some(file => file.name.toLowerCase().endsWith('.zip'))
)
const canImport = computed(() =>
  Boolean(files.value?.length) && (!hasArchive.value || Boolean(formState.targetSender))
)

watch(files, async (nextFiles) => {
  clearErrors()
  formState.targetSender = ''
  availableSenders.value = []
  const archive = nextFiles?.find(file => file.name.toLowerCase().endsWith('.zip'))
  if (!archive) return

  isLoadingSenders.value = true
  const form = new FormData()
  form.append('archive', archive)
  try {
    const response = await $fetch<{ senders: string[] }>('/api/labeling/import/senders', {
      method: 'POST',
      body: form
    })
    availableSenders.value = response.senders
  } finally {
    isLoadingSenders.value = false
  }
})
watch(() => formState.targetSender, clearErrors)

async function importFiles(event: FormSubmitEvent<ImportFormState>) {
  const selectedFiles = files.value
  if (!selectedFiles?.length || !canImport.value || isSaving.value) return

  const form = new FormData()
  selectedFiles.forEach(file => form.append('files', file))
  const imported = await submit(event, (data) => {
    form.append('target_sender', data.targetSender.trim())
    return $fetch<{ imported: number }>('/api/labeling/import', {
      method: 'POST',
      body: form
    })
  })
  if (!imported) return
  files.value = null
}
</script>

<template>
  <UForm
    :state="formState"
    class="space-y-3"
    @submit="importFiles"
  >
    <UFormField :error="formErrors.files || formErrors._form">
      <UFileUpload
        v-model="files"
        accept="audio/*,.zip,application/zip"
        class="min-h-48"
        description="WhatsApp-Export-ZIP oder einzelne Audiodateien"
        label="ZIP oder Audios hier ablegen"
        layout="list"
        multiple
        position="inside"
        size="lg"
      />
    </UFormField>
    <UFormField
      v-if="availableSenders.length || isLoadingSenders"
      label="Sprechende Person im WhatsApp-Chat"
      name="targetSender"
      :error="formErrors.target_sender"
    >
      <USelect
        v-model="formState.targetSender"
        class="w-full"
        :items="senderOptions"
        :loading="isLoadingSenders"
        placeholder="Person auswählen"
        size="lg"
      />
    </UFormField>
    <UButton
      block
      class="min-h-14 justify-center font-extrabold"
      color="primary"
      icon="i-lucide-upload"
      size="lg"
      :disabled="!canImport"
      :loading="isSaving"
      type="submit"
    >
      WhatsApp-Audios importieren
    </UButton>
  </UForm>
</template>
