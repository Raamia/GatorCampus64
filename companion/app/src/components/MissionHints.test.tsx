// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import HomePage from '../pages/(app)/home'
import { studyFetch } from '../lib/study-api'
import catalog from '../data/mission-catalog.json'
vi.mock('../lib/study-api', () => ({ studyFetch: vi.fn() }))
let host: HTMLDivElement, root: Root
let pending: { resolve: (response: Response) => void; reject: (error: Error) => void; signal: AbortSignal }[]
beforeEach(async () => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  pending = []
  vi.mocked(studyFetch).mockReset().mockImplementation((_path, init) => new Promise((resolve, reject) => {
    pending.push({ resolve, reject, signal: init.signal as AbortSignal })
  }))
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
  await act(() => root.render(<MemoryRouter><HomePage /></MemoryRouter>))
})
afterEach(async () => { await act(() => root.unmount()); host.remove(); vi.unstubAllGlobals() })
async function choose(index: number) { await act(() => host.querySelectorAll<HTMLButtonElement>('.run-mission-select')[index].click()) }
const detail = () => host.querySelector('[aria-label="Selected mission details"]')!.textContent

it('keeps the newest mission hint when an older response finishes last', async () => {
  await choose(0); await choose(1)
  expect(pending[0].signal.aborted).toBe(true)
  expect(pending[1].signal.aborted).toBe(false)
  await act(() => pending[1].resolve(Response.json({ text: 'Newest mission hint' })))
  await act(() => pending[0].resolve(Response.json({ text: 'Obsolete mission hint' })))
  expect(detail()).toContain('Newest mission hint')
  expect(detail()).not.toContain('Obsolete mission hint')
})

it('ignores a late failure and aborts the active request on unmount', async () => {
  await choose(0); await choose(1)
  await act(() => pending[1].resolve(Response.json({ text: 'Current hint' })))
  await act(() => pending[0].reject(new Error('late network failure')))
  expect(detail()).toContain('Current hint')
  await act(() => root.render(<div />))
  expect(pending[1].signal.aborted).toBe(true)
})

it('shows the selected local hint while loading and on an HTTP failure', async () => {
  await choose(0)
  const mission = catalog.missions.find(m => detail()?.includes(m.title))!
  expect(detail()).toContain(mission.hint)
  await act(() => pending[0].resolve(Response.json({ text: 'Upstream error text' }, { status: 503 })))
  expect(detail()).toContain(mission.hint)
  expect(detail()).not.toContain('Upstream error text')
})
