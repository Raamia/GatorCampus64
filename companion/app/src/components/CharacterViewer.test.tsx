// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import CharacterViewer from './CharacterViewer'
vi.mock('@google/model-viewer', () => ({}))
let host: HTMLDivElement, root: Root
beforeEach(() => {
  vi.useFakeTimers()
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(async () => { await act(() => root.unmount()); host.remove(); vi.useRealTimers(); vi.unstubAllGlobals() })
const render = (src = '/model.glb') => act(() => root.render(<CharacterViewer src={src} name="Pat" poster="/front.png" />))

it('keeps a rendered fallback and retries a failed model without reloading the page', async () => {
  await render()
  expect(host.querySelector('img')?.src).toContain('/front.png')
  await act(() => { host.querySelector('model-viewer')!.dispatchEvent(new Event('error')) })
  expect(host.querySelector('model-viewer')).toBeNull()
  expect(host.textContent).toContain('couldn’t load')
  await act(() => host.querySelector('button')!.click())
  expect(host.querySelector('model-viewer')).not.toBeNull()
  await act(() => { host.querySelector('model-viewer')!.dispatchEvent(new Event('load')) })
  expect(host.querySelector('[role=status]')).toBeNull()
  expect(host.querySelector('img')).toBeNull()
})

it('recovers automatically when a new signed URL arrives after an error', async () => {
  await render('/model.glb?old')
  await act(() => { host.querySelector('model-viewer')!.dispatchEvent(new Event('error')) })
  await render('/model.glb?fresh')
  expect(host.querySelector('model-viewer')?.getAttribute('src')).toBe('/model.glb?fresh')
  expect(host.textContent).toContain('Loading your 3D preview')
  await act(() => { host.querySelector('model-viewer')!.dispatchEvent(new Event('load')) })
  expect(host.textContent).not.toContain('couldn’t load')
})

it('offers recovery for a model that never emits a load or error event', async () => {
  await render()
  const expired = host.querySelector('model-viewer')!
  await act(() => vi.advanceTimersByTimeAsync(20_000))
  await act(() => { expired.dispatchEvent(new Event('load')) })
  expect(host.querySelector('button')?.textContent).toBe('Retry 3D preview')
  expect(host.querySelector('img')).not.toBeNull()
})
