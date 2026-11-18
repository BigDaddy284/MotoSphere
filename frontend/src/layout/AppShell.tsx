import type { ReactNode } from 'react'
import styles from './AppShell.module.css'
import { useSidePanels } from './useSidePanels.ts'

const SECTIONS_PANEL_ID = 'sections-panel'
const DETAILS_PANEL_ID = 'details-panel'

interface AppShellProps {
  /** The application name, shown as the page's main heading. */
  name: string
  /** One line under the name. */
  tagline: string
  /** Short information shown at the end of the top bar, such as the date. */
  info: ReactNode
  /** What the sections panel shows. */
  sections: ReactNode
}

/**
 * The fixed regions of the screen: a top bar, the sections panel on the left,
 * the globe stage in the centre and the details panel on the right. The stage
 * always gets the largest share of the screen, and takes the room of a side
 * panel that the user closes with its button in the top bar. On a narrow
 * screen the stage has the whole width, and an open panel lies over it.
 */
export function AppShell({ name, tagline, info, sections }: AppShellProps) {
  const { sections: sectionsPanel, details: detailsPanel } = useSidePanels()

  return (
    <div className={styles.shell}>
      <header className={styles.topBar}>
        <button
          type="button"
          className={styles.toggle}
          aria-expanded={sectionsPanel.open}
          aria-controls={SECTIONS_PANEL_ID}
          onClick={sectionsPanel.toggle}
        >
          Sections
        </button>
        <h1 className={styles.name}>{name}</h1>
        <p className={styles.tagline}>{tagline}</p>
        <div className={styles.info}>{info}</div>
        <button
          type="button"
          className={styles.toggle}
          aria-expanded={detailsPanel.open}
          aria-controls={DETAILS_PANEL_ID}
          onClick={detailsPanel.toggle}
        >
          Details
        </button>
      </header>
      <nav
        id={SECTIONS_PANEL_ID}
        className={styles.sections}
        aria-label="Sections"
        hidden={!sectionsPanel.open}
      >
        {sections}
      </nav>
      <main className={styles.stage} aria-label="Globe" />
      <aside
        id={DETAILS_PANEL_ID}
        className={styles.details}
        aria-label="Details"
        hidden={!detailsPanel.open}
      >
        <p className={styles.hint}>Select something on the globe to see its details here.</p>
      </aside>
    </div>
  )
}
