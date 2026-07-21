import type { Category, Phrase } from '~/types/speech'

export async function usePhrases() {
  const config = useRuntimeConfig()
  const [categories, phrases] = await Promise.all([
    $fetch<Category[]>(`${config.public.apiBase}/api/categories`),
    $fetch<Phrase[]>(`${config.public.apiBase}/api/phrases`)
  ])

  return {
    categories,
    phrases,
    byCategory: (category: string) => phrases.filter(phrase => phrase.category === category),
    byId: (id: number) => phrases.find(phrase => phrase.id === id)
  }
}
