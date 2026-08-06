<script setup lang="ts">
const files = ref<File[] | null>(null)
const formState = reactive({ targetSender: '' })
const availableSenders = ref<string[]>([])
const isLoadingSenders = ref(false)
const isBusy = ref(false)

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

async function importFiles() {
  const selectedFiles = files.value
  if (!selectedFiles?.length || !canImport.value || isBusy.value) return

  isBusy.value = true
  const form = new FormData()
  selectedFiles.forEach(file => form.append('files', file))
  form.append('target_sender', formState.targetSender.trim())

  try {
    await $fetch('/api/labeling/import', {
      method: 'POST',
      body: form
    })
    files.value = null
  } finally {
    isBusy.value = false
  }
}
</script>

<template>
  <UForm
    :state="formState"
    class="space-y-3"
    @submit="importFiles"
  >
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
    <UFormField
      v-if="availableSenders.length || isLoadingSenders"
      label="Sprechende Person im WhatsApp-Chat"
      name="targetSender"
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
      :loading="isBusy"
      type="submit"
    >
      WhatsApp-Audios importieren
    </UButton>
  </UForm>
</template>
