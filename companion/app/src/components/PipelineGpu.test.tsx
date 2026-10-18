import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { PipelineGpu } from './PipelineGpu'
import { parseSnapshot, type PipelineSnapshot } from '../lib/pipeline-status'

const observed = '2026-10-18T12:00:00Z'
const now = Date.parse(observed)
const snapshot: PipelineSnapshot = { observed_at: observed, jobs: [], gpu: [{
  id: '0123456789ab', observed_at: observed, available: true,
  gpus: [{ index: 0, utilization_gpu_pct: 0, memory_used_mib: 12288, memory_total_mib: 16384 }],
}] }
const render = (value: PipelineSnapshot | null = snapshot, failed = false, time = now) => renderToStaticMarkup(<PipelineGpu snapshot={value} failed={failed} now={time} />)

describe('GPU measurements', () => {
  it('shows real idle zero and reserved memory without requiring a running job', () => {
    const html = render()
    expect(html).toContain('Reporting')
    expect(html).toContain('0%')
    expect(html).toContain('12.0 GiB')
    expect(html).toContain('16.0 GiB')
    expect(html).toContain('value="12288"')
    expect(html).toContain('2026-10-18 12:00:00 UTC')
  })
  it('marks a stale worker even when the API snapshot is fresh', () => {
    const freshApi = { ...snapshot, observed_at: new Date(now + 40_000).toISOString() }
    expect(render(freshApi, false, now + 40_000)).toContain('Stale · last reported')
    expect(render(snapshot, true)).toContain('readings are frozen')
    expect(render(snapshot, false, now + 40_000)).not.toContain('>Reporting<')
  })
  it('distinguishes unavailable metrics, missing reports and loading', () => {
    expect(render(null)).toContain('Loading GPU measurements')
    expect(render(null, true)).toContain('Retrying automatically')
    expect(render({ ...snapshot, gpu: [] })).toContain('No GPU measurements reported')
    const unknown = { ...snapshot, gpu: [{ ...snapshot.gpu[0], gpus: [{ index: 0, utilization_gpu_pct: null, memory_used_mib: null, memory_total_mib: null }] }] }
    expect(render(unknown)).toContain('Unavailable')
    expect(render(unknown)).not.toContain('<meter')
    expect(render(unknown)).not.toContain('0%')
    expect(render({ ...snapshot, gpu: [{ ...snapshot.gpu[0], available: false, gpus: [] }] })).toContain('worker could not read GPU metrics')
  })
  it('projects only public fields and tolerates older APIs', () => {
    expect(parseSnapshot({ ...snapshot, gpu: snapshot.gpu.map(g => ({ ...g, hostname: 'private', gpus: g.gpus.map(d => ({ ...d, serial: 'private' })) })) })).toEqual(snapshot)
    expect(parseSnapshot({ observed_at: observed, jobs: [] }).gpu).toEqual([])
  })
  it('rejects malformed and impossible metrics instead of displaying false values', () => {
    for (const patch of [{ utilization_gpu_pct: 101 }, { utilization_gpu_pct: true }, { memory_used_mib: 20000 }, { memory_total_mib: 0 }, { memory_total_mib: Infinity }, { index: -1 }]) {
      expect(() => parseSnapshot({ ...snapshot, gpu: [{ ...snapshot.gpu[0], gpus: [{ ...snapshot.gpu[0].gpus[0], ...patch }] }] })).toThrow()
    }
    expect(() => parseSnapshot({ ...snapshot, gpu: [{ ...snapshot.gpu[0], available: false }] })).toThrow()
  })
})
