export default defineAppConfig({
  ui: {
    colors: {
      primary: 'rose',
      neutral: 'zinc'
    },
    button: {
      slots: {
        base: 'rounded-2xl font-extrabold disabled:opacity-100 aria-disabled:opacity-100'
      },
      variants: {
        size: {
          xl: {
            base: 'min-h-16 text-lg'
          }
        }
      },
      compoundVariants: [{
        color: 'primary',
        variant: 'solid',
        class: 'text-inverted bg-primary-700 hover:bg-primary-800 active:bg-primary-800 disabled:bg-primary-700 aria-disabled:bg-primary-700 outline-primary-700/25 focus-visible:outline-3 dark:text-primary-100'
      }, {
        color: 'primary',
        variant: 'soft',
        class: 'text-primary-800 bg-primary-100 hover:bg-primary-200 active:bg-primary-200 disabled:bg-primary-100 aria-disabled:bg-primary-100 outline-primary-700/25 focus-visible:outline-3 dark:text-primary-100 dark:bg-primary-900/60 dark:disabled:bg-primary-900/60 dark:aria-disabled:bg-primary-900/60 dark:hover:bg-primary-900/80 dark:active:bg-primary-900/80'
      }]
    }
  }
})
