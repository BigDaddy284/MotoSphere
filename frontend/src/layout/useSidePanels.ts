import { useState } from 'react'
import { useNarrowScreen } from './narrowScreen.ts'
import { type PanelName, usePanelOpen } from './usePanelOpen.ts'

interface SidePanel {
  open: boolean
  /** Closes the panel when it is open, and opens it when it is closed. */
  toggle: () => void
}

/**
 * The two side panels: whether each is open, and how to close or open it.
 *
 * On a wide screen the panels stand beside the globe stage. Each starts open
 * and has its own choice, remembered for the session.
 *
 * On a narrow screen an open panel covers the stage. Both start closed, so
 * that the page opens with the globe in view; at most one is open; and
 * nothing is remembered, so loading the page again shows the globe.
 */
export function useSidePanels(): Record<PanelName, SidePanel> {
  const narrow = useNarrowScreen()
  const [sectionsOpen, toggleSections] = usePanelOpen('sections')
  const [detailsOpen, toggleDetails] = usePanelOpen('details')
  const [openOnNarrow, setOpenOnNarrow] = useState<PanelName | null>(null)

  if (!narrow) {
    return {
      sections: { open: sectionsOpen, toggle: toggleSections },
      details: { open: detailsOpen, toggle: toggleDetails },
    }
  }

  function onNarrow(name: PanelName): SidePanel {
    const open = openOnNarrow === name
    return {
      open,
      toggle: () => {
        setOpenOnNarrow(open ? null : name)
      },
    }
  }
  return { sections: onNarrow('sections'), details: onNarrow('details') }
}
