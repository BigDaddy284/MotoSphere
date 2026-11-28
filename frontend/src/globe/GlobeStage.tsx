import { useState } from 'react'
import { browserDraws3D } from './drawing.ts'
import styles from './GlobeStage.module.css'

/** What the stage says where the browser gives no 3D picture. */
export const NO_GLOBE = 'The 3D globe cannot be shown in this browser.'

/** Why, and what a person can do about it. */
export const NO_GLOBE_HELP =
  'It needs 3D graphics, which this browser does not offer or has switched off. Try an up-to-date browser, or switch on graphics acceleration (also called hardware acceleration) in the settings of this one.'

/**
 * What the globe stage shows. Where the browser gives no 3D picture it says
 * so, in the place of the globe. Where the browser gives one, the stage is
 * empty: the globe itself is not in the page yet (GLB-002).
 */
export function GlobeStage() {
  // Asked when the stage is first shown and not again: what a browser can
  // draw does not change while the page is open.
  const [draws] = useState(browserDraws3D)

  if (draws) {
    return null
  }
  return (
    <div className={styles.notice}>
      <p className={styles.what}>{NO_GLOBE}</p>
      <p className={styles.help}>{NO_GLOBE_HELP}</p>
    </div>
  )
}
