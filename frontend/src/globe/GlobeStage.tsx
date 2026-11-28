import { useState } from 'react'
import { browserDraws3D } from './drawing.ts'
import { Globe, type Load } from './Globe.tsx'
import styles from './GlobeStage.module.css'

/** What the stage says where the browser gives no 3D picture. */
export const NO_GLOBE = 'The 3D globe cannot be shown in this browser.'

/** Why, and what a person can do about it. */
export const NO_GLOBE_HELP =
  'It needs 3D graphics, which this browser does not offer or has switched off. Try an up-to-date browser, or switch on graphics acceleration (also called hardware acceleration) in the settings of this one.'

type GlobeStageProps = {
  /** How the engine of the globe is loaded. It is asked only where the browser can draw. */
  loadTheEngine: Load
}

/**
 * What the globe stage shows. Where the browser gives no 3D picture it says
 * so, in the place of the globe, and the engine is not loaded. Where the
 * browser gives one, the stage shows the globe, which fills it, and marks
 * it as busy until the engine has drawn its first complete picture.
 */
export function GlobeStage({ loadTheEngine }: GlobeStageProps) {
  // Asked when the stage is first shown and not again: what a browser can
  // draw does not change while the page is open.
  const [draws] = useState(browserDraws3D)
  const [drawn, setDrawn] = useState(false)

  if (draws) {
    return (
      <div className={styles.globe} aria-busy={!drawn}>
        <Globe
          load={loadTheEngine}
          onDrawn={() => {
            setDrawn(true)
          }}
          // What a person is told when the globe cannot be shown is GLB-004.
          // Until then the failure goes where every failure of the page goes
          // that nothing has caught: to the browser, which reports it.
          onFailed={reportError}
        />
      </div>
    )
  }
  return (
    <div className={styles.notice}>
      <p className={styles.what}>{NO_GLOBE}</p>
      <p className={styles.help}>{NO_GLOBE_HELP}</p>
    </div>
  )
}
