export function usePwaUpdateSafety() {
  const isSafeToUpdate = useState('pwa-update-safe', () => true)

  return { isSafeToUpdate }
}
