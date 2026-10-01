import { createSharedComposable, useIntervalFn } from '@vueuse/core'
import { checkBackendAvailable } from '~/utils/backendAvailable'
import { uploadPendingRecordings } from '~/utils/recordingUploadQueue'

export const useBackendAvailability = createSharedComposable(() => {
  const available = ref(false)
  useIntervalFn(async () => {
    available.value = await checkBackendAvailable()
    if (available.value) void uploadPendingRecordings()
  }, 5000, { immediateCallback: true })
  return available
})
