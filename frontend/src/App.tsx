import { AppShell } from './layout/AppShell.tsx'

export const APP_NAME = 'MotoSphere'
export const APP_TAGLINE = 'The World of Motocross, Connected.'

export function App() {
  return <AppShell name={APP_NAME} tagline={APP_TAGLINE} />
}
