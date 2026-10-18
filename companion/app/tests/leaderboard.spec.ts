import { test, expect } from '@playwright/test'
import { captureConsoleErrors } from './helpers/errors'

/**
 * /leaderboard smoke coverage. A fresh dev DeepSpace room has no
 * verified_runs yet, so these exercise the real "nothing verified yet" empty
 * state rather than seeded data - the ranking logic itself (tie-breaks,
 * filtering, player-tag formatting) is covered at the unit level in
 * src/lib/leaderboard.test.ts and src/server/ingest-routes.test.ts.
 */
test.describe('Leaderboard page', () => {
  test('loads with no JS errors and shows the verified board', async ({ page }) => {
    const errors = captureConsoleErrors(page)
    await page.goto('/leaderboard')
    await expect(page.getByTestId('app-navigation')).toBeVisible({ timeout: 15000 })
    await expect(page.getByRole('heading', { name: 'Leaderboards' })).toBeVisible()
    await expect(page.getByText('VERIFIED', { exact: true })).toBeVisible()
    expect(errors).toEqual([])
  })

  test('shows the empty-board message when a mission has no verified runs', async ({ page }) => {
    await page.goto('/leaderboard')
    await expect(page.getByText(/No verified runs yet/i)).toBeVisible({ timeout: 15000 })
  })

  test('switching mission tabs changes the selected board', async ({ page }) => {
    await page.goto('/leaderboard')
    const tabs = page.locator('.lb-mission')
    await expect(tabs.first()).toBeVisible({ timeout: 15000 })
    const count = await tabs.count()
    test.skip(count < 2, 'mission catalog has fewer than two missions to switch between')
    await expect(tabs.first()).toHaveClass(/is-selected/)
    await tabs.nth(1).click()
    await expect(tabs.nth(1)).toHaveClass(/is-selected/)
    await expect(tabs.first()).not.toHaveClass(/is-selected/)
  })

  test('offline runs are hidden behind sign-in, not shown as verified', async ({ page }) => {
    await page.goto('/leaderboard')
    await expect(page.getByText('OFFLINE', { exact: false })).toBeVisible()
    await expect(page.getByText(/Sign in to see runs synced/i)).toBeVisible()
  })
})
