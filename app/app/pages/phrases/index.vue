<script setup lang="ts">
const { categories } = usePhrases()
const speechCommands = useSpeechCommands()
let unregisterCategoryCommands = () => {}

definePageMeta({
  pageHeader: {
    eyebrow: 'Satz auswählen',
    title: 'Wobei brauchst du Hilfe?',
    showBack: true
  }
})

async function openCategory(name: string) {
  await navigateTo(`/phrases/${encodeURIComponent(name)}`)
}

watch(categories, (items) => {
  unregisterCategoryCommands()
  const unregister = items.map(category => speechCommands.register({
    id: `category-${category.id}`,
    label: category.name,
    phrases: [category.name, `kategorie ${category.name}`],
    handler: () => openCategory(category.name)
  }))
  unregisterCategoryCommands = () => unregister.forEach(remove => remove())
}, { immediate: true })

onScopeDispose(() => unregisterCategoryCommands())
</script>

<template>
  <div class="space-y-5">
    <CategoryCreateForm />

    <CategoryGrid :categories="categories" />
  </div>
</template>
