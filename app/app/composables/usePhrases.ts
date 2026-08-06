import type { Category, Phrase } from '~/types/speech'

type PhraseData = {
  categories: Category[]
  phrases: Phrase[]
}

export function usePhrases() {
  const phraseData = useAsyncData<PhraseData>(
    'phrases',
    async () => {
      const [categories, phrases] = await Promise.all([
        $fetch<Category[]>('/api/categories'),
        $fetch<Phrase[]>('/api/phrases')
      ])
      return { categories, phrases }
    },
    {
      dedupe: 'defer',
      default: () => ({ categories: [], phrases: [] })
    }
  )
  const { data } = phraseData

  const categories = computed(() => data.value.categories)
  const phrases = computed(() => data.value.phrases)

  return {
    categories,
    phrases,
    ready: phraseData.then(() => undefined),
    byCategory: (category: string) => phrases.value.filter(phrase => phrase.category === category),
    byId: (id: number) => phrases.value.find(phrase => phrase.id === id)
  }
}
