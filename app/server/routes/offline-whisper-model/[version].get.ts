export default defineEventHandler(async (event) => {
  const version = getRouterParam(event, 'version')
  const config = useRuntimeConfig()
  if (!config.offlineWhisperModelUrl || version !== config.public.offlineWhisperModelVersion) {
    throw createError({ statusCode: 404, statusMessage: 'Offline model not found.' })
  }

  const response = await fetch(config.offlineWhisperModelUrl, {
    headers: config.hfToken
      ? { Authorization: `Bearer ${config.hfToken}` }
      : undefined
  })
  if (!response.ok || !response.body) {
    throw createError({ statusCode: 502, statusMessage: 'Offline model download failed.' })
  }

  setResponseHeader(event, 'Cache-Control', 'private, no-store')
  const contentLength = response.headers.get('content-length')
  if (contentLength) setResponseHeader(event, 'Content-Length', Number(contentLength))
  setResponseHeader(event, 'Content-Type', 'application/octet-stream')
  return sendStream(event, response.body)
})
