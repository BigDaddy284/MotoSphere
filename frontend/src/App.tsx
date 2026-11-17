import { useState } from 'react'
import { CurrentDate } from './clock/CurrentDate.tsx'
import { AppShell } from './layout/AppShell.tsx'
import { SectionList } from './navigation/SectionList.tsx'
import { DEFAULT_SECTION, type SectionId } from './navigation/sections.ts'

export const APP_NAME = 'MotoSphere'
export const APP_TAGLINE = 'The World of Motocross, Connected.'

export function App() {
  const [section, setSection] = useState<SectionId>(DEFAULT_SECTION)

  return (
    <AppShell
      name={APP_NAME}
      tagline={APP_TAGLINE}
      info={<CurrentDate />}
      sections={<SectionList current={section} onSelect={setSection} />}
    />
  )
}
