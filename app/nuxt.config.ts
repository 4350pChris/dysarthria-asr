// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@vite-pwa/nuxt',
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxt/hints',
    '@nuxt/test-utils',
    '@nuxt/a11y'
  ],

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  pwa: {
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
      theme_color: '#0f766e',
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
    },
    workbox: {
      runtimeCaching: [
        {
          urlPattern: /\/api\/(categories|phrases)$/,
          handler: 'NetworkFirst',
          options: {
            cacheName: 'phrases',
            networkTimeoutSeconds: 3,
            expiration: {
              maxEntries: 2,
              maxAgeSeconds: 60 * 60 * 24 * 30
            },
            cacheableResponse: { statuses: [200] }
          }
        }
      ]
    }
  },

  runtimeConfig: {
    apiBase: process.env.NUXT_API_BASE || 'http://127.0.0.1:8000'
  },

  compatibilityDate: '2026-06-30',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  }
})
