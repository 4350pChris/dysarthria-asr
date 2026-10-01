export async function checkBackendAvailable(): Promise<boolean> {
  try {
    const response = await fetch('/api/health', {
      cache: 'no-store',
      signal: AbortSignal.timeout(1500)
    })
    return response.ok && (await response.json()).status === 'ok'
  } catch {
    return false
  }
}
