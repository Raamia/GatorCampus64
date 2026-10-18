// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import SettingsPage from '../pages/(app)/settings'
import { api, login, signup, logout } from '../lib/gator-api'
const state = vi.hoisted(() => ({ session: { loaded: true, signedIn: true, name: 'Ali', email: 'ali@example.test' } }))
vi.mock('../lib/gator-session', () => ({ useGatorSession: () => state.session, refreshGatorSession: vi.fn() }))
vi.mock('../lib/gator-api', () => ({ api: vi.fn(), login: vi.fn(), signup: vi.fn(), logout: vi.fn() }))
let host: HTMLDivElement, root: Root
beforeEach(async () => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  state.session.signedIn = true
  for (const fn of [api, login, signup, logout]) vi.mocked(fn).mockReset().mockResolvedValue({} as never)
  const stored = new Map([['sgl-last-job', 'job'], ['sgl-pending-claim', 'character']])
  vi.stubGlobal('localStorage', { getItem: (key: string) => stored.get(key) ?? null, removeItem: (key: string) => stored.delete(key) })
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
  await act(() => root.render(<SettingsPage />))
})
afterEach(async () => { await act(() => root.unmount()); host.remove(); vi.unstubAllGlobals() })
const button = (text: string) => Array.from(host.querySelectorAll('button')).find(b => b.textContent === text)!
async function confirm() {
  const input = host.querySelector<HTMLInputElement>('[aria-label="Confirm account deletion"]')!
  await act(() => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(input, 'DELETE')
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
}
it('shows the game identity and management controls without any linking workflow', () => {
  expect(host.textContent).toContain('ali@example.test')
  expect(host.textContent).toContain('Revoke game logins')
  expect(host.textContent).not.toContain('Link these accounts')
  expect(button('Delete Gator account').disabled).toBe(true)
  expect(api).not.toHaveBeenCalled()
})
it('requires confirmation and clears saved selections only after successful deletion', async () => {
  await confirm()
  expect(button('Delete Gator account').disabled).toBe(false)
  await act(() => button('Delete Gator account').click())
  expect(api).toHaveBeenCalledWith('/account', expect.objectContaining({ method: 'DELETE', body: '{"confirm":"DELETE"}' }))
  expect(localStorage.getItem('sgl-last-job')).toBeNull()
  expect(localStorage.getItem('sgl-pending-claim')).toBeNull()
  expect(host.textContent).toContain('Gator account deleted')
})
it('preserves saved data and exposes recent-login errors when deletion is refused', async () => {
  vi.mocked(api).mockRejectedValueOnce(new Error('Recent sign-in required'))
  await confirm(); await act(() => button('Delete Gator account').click())
  expect(localStorage.getItem('sgl-last-job')).toBe('job')
  expect(host.textContent).toContain('Recent sign-in required')
  await act(() => button('Sign in again').click())
  expect(login).toHaveBeenCalledWith(true)
})
it('offers separate login and signup when signed out without rendering destructive controls', async () => {
  state.session.signedIn = false
  await act(() => root.render(<SettingsPage />))
  expect(host.textContent).not.toContain('Delete Gator account')
  await act(() => button('Sign up').click()); expect(signup).toHaveBeenCalledOnce()
  await act(() => button('Sign in').click()); expect(login).toHaveBeenCalledOnce()
})
