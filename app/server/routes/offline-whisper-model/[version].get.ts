import { Readable } from 'node:stream'

export default defineEventHandler(async (event) => {
  const version = getRouterParam(event, 'version')
  const config = useRuntimeConfig()
  if (!config.offlineWhisperModelUrl || version !== config.public.offlineWhisperModelVersion) {
    throw createError({ statusCode: 404, statusMessage: 'Offline model not found.' })
  }

  const response = await fetch(config.offlineWhisperModelUrl, {
    headers: config.offlineWhisperModelToken
      ? { Authorization: `Bearer ${config.offlineWhisperModelToken}` }
      : undefined
  })
  if (!response.ok || !response.body) {
    throw createError({ statusCode: 502, statusMessage: 'Offline model download failed.' })
  }

  setResponseHeader(event, 'Cache-Control', 'private, no-store')
  setResponseHeader(event, 'Content-Length', response.headers.get('content-length') || '')
  setResponseHeader(event, 'Content-Type', 'application/octet-stream')
  return sendStream(event, Readable.fromWeb(response.body))
})
