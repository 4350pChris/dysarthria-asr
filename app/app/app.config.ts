export default defineAppConfig({
  ui: {
    colors: {
      primary: 'rose',
      neutral: 'zinc'
    },
    button: {
      slots: {
        base: 'rounded-2xl font-extrabold'
      },
      variants: {
        size: {
          xl: {
            base: 'min-h-16 text-lg'
          }
        }
      }
    }
  }
})
