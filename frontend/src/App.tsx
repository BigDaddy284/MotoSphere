import { useState } from 'react'
import { CurrentDate } from './clock/CurrentDate.tsx'
import { DataStatus } from './data/DataStatus.tsx'
import type { Load } from './globe/Globe.tsx'
import { GlobeStage } from './globe/GlobeStage.tsx'
import { AppShell } from './layout/AppShell.tsx'
import { SectionList } from './navigation/SectionList.tsx'
import { DEFAULT_SECTION, type SectionId } from './navigation/sections.ts'

export const APP_NAME = 'MotoSphere'
export const APP_TAGLINE = 'The World of Motocross, Connected.'

type AppProps = {
  /** How the engine of the globe is loaded. */
  loadTheEngine: Load
}

export function App({ loadTheEngine }: AppProps) {
  const [section, setSection] = useState<SectionId>(DEFAULT_SECTION)

  return (
    <AppShell
      name={APP_NAME}
      tagline={APP_TAGLINE}
      info={
        <>
          <DataStatus />
          <CurrentDate />
        </>
      }
      sections={<SectionList current={section} onSelect={setSection} />}
      stage={<GlobeStage loadTheEngine={loadTheEngine} />}
    />
  )
}
