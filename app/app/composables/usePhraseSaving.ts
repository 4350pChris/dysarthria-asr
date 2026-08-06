type SavePhraseOptions = {
  text: string
  categoryId?: number
  phraseId?: number
}

export function usePhraseSaving() {
  const { loadPhrases } = usePhrases()

  async function savePhrase({ text, categoryId, phraseId }: SavePhraseOptions) {
    const form = new FormData()
    form.append('text', text)

    if (phraseId) {
      await $fetch(`/api/phrases/${phraseId}`, { method: 'PATCH', body: form })
    } else if (categoryId) {
      form.append('category_id', String(categoryId))
      await $fetch('/api/phrases', { method: 'POST', body: form })
    } else {
      throw new Error('Eine Kategorie oder Satz-ID ist erforderlich.')
    }

    await loadPhrases({ force: true })
  }

  return { savePhrase }
}
