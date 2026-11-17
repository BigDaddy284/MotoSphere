import styles from './AppShell.module.css'

interface AppShellProps {
  /** The application name, shown as the page's main heading. */
  name: string
  /** One line under the name. */
  tagline: string
}

/**
 * The fixed regions of the screen: a top bar, the sections panel on the left,
 * the globe stage in the centre and the details panel on the right. The stage
 * always gets the largest share of the screen.
 */
export function AppShell({ name, tagline }: AppShellProps) {
  return (
    <div className={styles.shell}>
      <header className={styles.topBar}>
        <h1 className={styles.name}>{name}</h1>
        <p className={styles.tagline}>{tagline}</p>
      </header>
      <nav className={styles.sections} aria-label="Sections" />
      <main className={styles.stage} aria-label="Globe" />
      <aside className={styles.details} aria-label="Details">
        <p className={styles.hint}>Select something on the globe to see its details here.</p>
      </aside>
    </div>
  )
}
