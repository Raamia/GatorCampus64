// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import GatorizePage from '../pages/(app)/gatorize'
import { api } from '../lib/gator-api'
import { photoSelectionError } from '../lib/gatorize-photos'
vi.mock('../lib/gator-api', () => ({ api: vi.fn(), finishLogin: vi.fn().mockResolvedValue(true), login: vi.fn(), logout: vi.fn() }))
vi.mock('./GatorAccount', () => ({ default: () => null }))
vi.mock('@google/model-viewer', () => ({}))
let host: HTMLDivElement, root: Root
beforeEach(async () => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  const stored = new Map<string, string>()
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => stored.get(key) ?? null,
    setItem: (key: string, value: string) => { stored.set(key, value) },
    removeItem: (key: string) => { stored.delete(key) },
  })
  vi.mocked(api).mockReset().mockResolvedValue({ characters: [] })
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
  await act(() => root.render(<MemoryRouter><GatorizePage /></MemoryRouter>))
})
afterEach(async () => { await act(() => root.unmount()); host.remove(); vi.unstubAllGlobals() })
async function select(files: File[]) {
  const input = host.querySelector<HTMLInputElement>('input[type=file]')!
  Object.defineProperty(input, 'files', { configurable: true, value: files })
  await act(() => { input.dispatchEvent(new Event('change', { bubbles: true })) })
}
const photo = (name = 'face.png', type = 'image/png') => new File(['fake-photo'], name, { type })

it('shows all five selected files and blocks submission until the user removes an extra', async () => {
  await select(Array.from({ length: 5 }, (_, i) => photo(`${i}.png`)))
  expect(host.querySelectorAll('[aria-label="Selected photos"] li')).toHaveLength(5)
  expect(host.querySelector('[role=alert]')?.textContent).toContain('Remove extra photos')
  await act(() => { host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })) })
  expect(vi.mocked(api).mock.calls.every(([path]) => path !== '/characters')).toBe(true)
  await act(() => host.querySelector<HTMLButtonElement>('[aria-label="Selected photos"] button')!.click())
  expect(host.querySelectorAll('[aria-label="Selected photos"] li')).toHaveLength(4)
  expect(host.querySelector('[role=alert]')).toBeNull()
})

it('advertises JPEG/PNG and immediately explains unsupported selections', async () => {
  expect(host.querySelector('input[type=file]')?.getAttribute('accept')).toBe('image/jpeg,image/png')
  await select([photo('face.webp', 'image/webp')])
  expect(host.querySelector('[role=alert]')?.textContent).toContain('Choose JPEG or PNG')
  await act(() => { host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })) })
  expect(vi.mocked(api).mock.calls.every(([path]) => path !== '/characters')).toBe(true)
  await select([photo('face.jpg', 'image/jpeg')])
  expect(host.querySelector('[role=alert]')).toBeNull()
})

it('accepts supported formats and enforces the existing 8 MiB boundary', () => {
  expect(photoSelectionError([photo(), photo('face.JPG', '')])).toBe('')
  expect(photoSelectionError([new File([new Uint8Array(8 * 1024 * 1024)], 'face.png', { type: 'image/png' })])).toBe('')
  expect(photoSelectionError([new File([new Uint8Array(8 * 1024 * 1024 + 1)], 'face.png', { type: 'image/png' })])).toContain('8 MB')
  expect(photoSelectionError([photo('face.heic', '')])).toContain('JPEG or PNG')
})

it('submits the retained photos once and clears them after successful creation', async () => {
  await select([photo('front.png'), photo('side.png')])
  await act(() => host.querySelector<HTMLInputElement>('input[type=checkbox]')!.click())
  vi.mocked(api).mockResolvedValueOnce({ job_id: 'new-job', character_id: 'new-character', name: 'Pat' })
  await act(() => { host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })) })
  const creates = vi.mocked(api).mock.calls.filter(([path]) => path === '/characters')
  expect(creates).toHaveLength(1)
  const body = creates[0][1]!.body as FormData
  expect(body.getAll('photos').map(file => (file as File).name)).toEqual(['front.png', 'side.png'])
  expect(body.get('consent')).toBe('true')
  expect(localStorage.getItem('sgl-last-job')).toBe('new-job')
  await act(() => Array.from(host.querySelectorAll('button')).find(b => b.textContent === 'Back to my gators')!.click())
  expect(host.querySelector('[aria-label="Selected photos"]')).toBeNull()
  expect(host.querySelector<HTMLInputElement>('input[type=checkbox]')!.checked).toBe(false)
})
