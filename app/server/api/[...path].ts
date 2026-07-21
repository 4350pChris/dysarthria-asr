export default defineEventHandler((event) => {
  const path = getRouterParam(event, 'path')
  const { apiBase } = useRuntimeConfig()

  return proxyRequest(event, `${apiBase}/api/${path}`)
})
