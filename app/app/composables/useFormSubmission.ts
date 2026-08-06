import type { FormSubmitEvent } from '@nuxt/ui'

export function useFormSubmission<T extends object>(errorMessage: string) {
  const formErrors = ref<Record<string, string>>({})
  const isSaving = ref(false)

  function clearErrors() {
    formErrors.value = {}
  }

  async function submit<Result>(event: FormSubmitEvent<T>, request: (data: T) => Promise<Result>) {
    if (isSaving.value) return
    clearErrors()
    isSaving.value = true
    try {
      return await request(event.data)
    } catch (error) {
      formErrors.value = apiFormErrors(error, errorMessage)
      return undefined
    } finally {
      isSaving.value = false
    }
  }

  return { clearErrors, formErrors, isSaving, submit }
}
