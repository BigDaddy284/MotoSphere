import type { ReactNode } from 'react'
import styles from './AppShell.module.css'
import { usePanelOpen } from './usePanelOpen.ts'

const SECTIONS_PANEL_ID = 'sections-panel'
const DETAILS_PANEL_ID = 'details-panel'

interface AppShellProps {
  /** The application name, shown as the page's main heading. */
  name: string
  /** One line under the name. */
  tagline: string
  /** What the sections panel shows. */
  sections: ReactNode
}

/**
 * The fixed regions of the screen: a top bar, the sections panel on the left,
 * the globe stage in the centre and the details panel on the right. The stage
 * always gets the largest share of the screen, and takes the room of a side
 * panel that the user closes with its button in the top bar.
 */
export function AppShell({ name, tagline, sections }: AppShellProps) {
  const [sectionsOpen, toggleSections] = usePanelOpen('sections')
  const [detailsOpen, toggleDetails] = usePanelOpen('details')

  return (
    <div className={styles.shell}>
      <header className={styles.topBar}>
        <button
          type="button"
          className={styles.toggle}
          aria-expanded={sectionsOpen}
          aria-controls={SECTIONS_PANEL_ID}
          onClick={toggleSections}
        >
          Sections
        </button>
        <h1 className={styles.name}>{name}</h1>
        <p className={styles.tagline}>{tagline}</p>
        <button
          type="button"
          className={`${styles.toggle} ${styles.toggleEnd}`}
          aria-expanded={detailsOpen}
          aria-controls={DETAILS_PANEL_ID}
          onClick={toggleDetails}
        >
          Details
        </button>
      </header>
      <nav
        id={SECTIONS_PANEL_ID}
        className={styles.sections}
        aria-label="Sections"
        hidden={!sectionsOpen}
      >
        {sections}
      </nav>
      <main className={styles.stage} aria-label="Globe" />
      <aside
        id={DETAILS_PANEL_ID}
        className={styles.details}
        aria-label="Details"
        hidden={!detailsOpen}
      >
        <p className={styles.hint}>Select something on the globe to see its details here.</p>
      </aside>
    </div>
  )
}
