export function useStartupLogoTransition() {
  const isTargetReady = useState('startup-logo-target-ready', () => false)

  return { isTargetReady }
}
