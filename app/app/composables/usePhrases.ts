import type { Phrase } from '~/types/speech'

export async function usePhrases() {
  const config = useRuntimeConfig()
  const phrases = await $fetch<Phrase[]>(`${config.public.apiBase}/api/phrases`)
  const categories = [...new Set(phrases.map(phrase => phrase.category))]

  return {
    categories,
    phrases,
    byCategory: (category: string) => phrases.filter(phrase => phrase.category === category),
    byNumber: (number: string) => phrases.find(phrase => phrase.number === number)
  }
}
