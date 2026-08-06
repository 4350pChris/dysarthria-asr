import type { Category, Phrase } from '~/types/speech'

export function usePhrases() {
  const categories = useFetch<Category[]>('/api/categories', { default: () => [] })
  const phrases = useFetch<Phrase[]>('/api/phrases', { default: () => [] })

  async function refreshPhrases() {
    await phrases.refresh()
  }

  async function refreshAfterCategoryChange() {
    await Promise.all([categories.refresh(), phrases.refresh()])
  }

  return {
    categories: categories.data,
    phrases: phrases.data,
    ready: Promise.all([categories, phrases]),
    byCategory: (category: string) => phrases.data.value.filter(phrase => phrase.category === category),
    byId: (id: number) => phrases.data.value.find(phrase => phrase.id === id),
    refreshAfterCategoryChange,
    refreshPhrases
  }
}
