const isVitest = process.env.VITEST === 'true'
const isolationHeaders = {
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Embedder-Policy': 'require-corp'
}

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    ...(!isVitest ? ['@vite-pwa/nuxt'] : []),
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxt/hints',
    '@nuxt/test-utils',
    '@nuxt/a11y',
    '@vueuse/nuxt',
    'nuxt-umami'
  ],

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  routeRules: {
    '/**': {
      headers: isolationHeaders
    }
  },

  vite: {
    server: {
      headers: isolationHeaders
    },
    worker: {
      format: 'es'
    }
  },

  ...(!isVitest
    ? { pwa: {
        registerType: 'prompt',
        manifest: {
          id: '/',
          name: 'Sprechen',
          short_name: 'Sprechen',
          description: 'Persönliche Sprachhilfe',
          lang: 'de',
          start_url: '/',
          scope: '/',
          display: 'standalone',
          background_color: '#ffffff',
          theme_color: '#ec4899',
          icons: [
            {
              src: 'pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png'
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any'
            },
            {
              src: 'maskable-icon-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable'
            }
          ]
        }
      } }
    : {}),

  runtimeConfig: {
    hfToken: '',
    offlineWhisperModelUrl: '',
    public: {
      apiBase: 'http://127.0.0.1:8000',
      offlineWhisperModelVersion: ''
    }
  },

  compatibilityDate: '2026-06-30',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  umami: {
    // Tracking is on by default. Umami still needs a Website ID to send data.
    enabled: true,
    host: 'http://127.0.0.1:3001',
    autoTrack: true,
    ignoreLocalhost: false,
    urlOptions: {
      excludeSearch: true,
      excludeHash: true
    }
  }
})
