import type { Category, Phrase } from '~/types/speech'

export async function usePhrases() {
  const [categories, phrases] = await Promise.all([
    $fetch<Category[]>('/api/categories'),
    $fetch<Phrase[]>('/api/phrases')
  ])

  return {
    categories,
    phrases,
    byCategory: (category: string) => phrases.filter(phrase => phrase.category === category),
    byId: (id: number) => phrases.find(phrase => phrase.id === id)
  }
}
