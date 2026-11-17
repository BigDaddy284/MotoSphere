import styles from './SectionList.module.css'
import { SECTIONS, type SectionId } from './sections.ts'

interface SectionListProps {
  /** The section the user is in. */
  current: SectionId
  /** Called with the section the user chose. */
  onSelect: (section: SectionId) => void
}

/** The list of sections. Exactly one is marked as the current one. */
export function SectionList({ current, onSelect }: SectionListProps) {
  return (
    <ul className={styles.list}>
      {SECTIONS.map(({ id, label }) => (
        <li key={id}>
          <button
            type="button"
            className={styles.item}
            aria-current={id === current ? 'page' : undefined}
            onClick={() => onSelect(id)}
          >
            {label}
          </button>
        </li>
      ))}
    </ul>
  )
}
