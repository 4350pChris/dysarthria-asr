import type { Category, Phrase } from '~/types/speech'

export function usePhrases() {
  const categories = useState<Category[]>('phrases:categories', () => [])
  const phrases = useState<Phrase[]>('phrases:items', () => [])
  const isLoaded = useState('phrases:is-loaded', () => false)

  async function loadPhrases(options: { force?: boolean } = {}) {
    if (isLoaded.value && !options.force) return

    const [nextCategories, nextPhrases] = await Promise.all([
      $fetch<Category[]>('/api/categories'),
      $fetch<Phrase[]>('/api/phrases')
    ])

    categories.value = nextCategories
    phrases.value = nextPhrases
    isLoaded.value = true
  }

  return {
    categories,
    phrases,
    loadPhrases,
    byCategory: (category: string) => phrases.value.filter(phrase => phrase.category === category),
    byId: (id: number) => phrases.value.find(phrase => phrase.id === id)
  }
}
