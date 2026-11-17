/** The application's sections, in the order they are listed. */
export const SECTIONS = [
  { id: 'explore', label: 'Explore' },
  { id: 'events', label: 'Events' },
  { id: 'tracks', label: 'Tracks' },
  { id: 'championships', label: 'Championships' },
  { id: 'riders', label: 'Riders' },
  { id: 'teams', label: 'Teams' },
  { id: 'results', label: 'Results' },
  { id: 'news', label: 'News' },
  { id: 'statistics', label: 'Statistics' },
] as const

export type SectionId = (typeof SECTIONS)[number]['id']

/** The section shown when the application starts. */
export const DEFAULT_SECTION: SectionId = 'explore'
