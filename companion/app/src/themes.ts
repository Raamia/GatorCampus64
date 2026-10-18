/** Theme metadata; runtime values live in styles.css and themes.css. */
export const THEMES = [
  {
    id: 'field',
    label: 'Campus Field',
    description: 'Sky blue, stadium navy, and Gator orange.',
  },
] as const

export type ThemeId = (typeof THEMES)[number]['id']

/** Read the currently active theme id from <html data-theme>. */
export function getActiveTheme(): ThemeId {
  if (typeof document === 'undefined') return 'field'
  const id = document.documentElement.getAttribute('data-theme') as ThemeId | null
  return id ?? 'field'
}

/** Look up a theme entry by id, or fall back to the first theme. */
export function getTheme(id: string) {
  return THEMES.find((t) => t.id === id) ?? THEMES[0]
}
