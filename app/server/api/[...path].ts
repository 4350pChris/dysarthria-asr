export default defineEventHandler((event) => {
  const path = getRouterParam(event, 'path')
  const { apiBase } = useRuntimeConfig()
  const query = getRequestURL(event).search

  return proxyRequest(event, `${apiBase}/api/${path}${query}`)
})
