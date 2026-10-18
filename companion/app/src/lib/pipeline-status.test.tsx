import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { duration, fetchPipelineStatus, parseSnapshot, snapshotStale, type PipelineSnapshot } from './pipeline-status'
import { PipelineResults } from '../pages/pipeline'

const snapshot: PipelineSnapshot = { observed_at: '2026-10-17T12:00:00+00:00', jobs: [
  { id: '0123456789ab', state: 'build', step: 'build', elapsed_seconds: 65, steps: [
    { step: 'spec', seconds: 2.3, running: false }, { step: 'build', seconds: 62.7, running: true },
  ] },
] }
afterEach(() => vi.unstubAllGlobals())

describe('anonymous pipeline status', () => {
  it('fetches without credentials or auth headers', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(snapshot)))
    vi.stubGlobal('fetch', fetcher)
    const signal = new AbortController().signal
    expect(await fetchPipelineStatus(signal)).toEqual(snapshot)
    expect(fetcher).toHaveBeenCalledWith('https://api.gatorcamp.us/pipeline/status', { credentials: 'omit', signal })
  })
  it('never renders upstream error bodies', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private email', { status: 503 })))
    await expect(fetchPipelineStatus(new AbortController().signal)).rejects.toThrow('Pipeline status unavailable')
  })
  it('projects safe fields and rejects malformed status', () => {
    expect(parseSnapshot({ ...snapshot, account: 'private', jobs: snapshot.jobs.map(job => ({ ...job, photo: 'secret-url' })) })).toEqual(snapshot)
    for (const fields of [{ state: 'private-name' }, { id: 'account-id' }, { elapsed_seconds: -1 }]) {
      expect(() => parseSnapshot({ ...snapshot, jobs: [{ ...snapshot.jobs[0], ...fields }] })).toThrow()
    }
    expect(() => parseSnapshot({ ...snapshot, observed_at: 'broken' })).toThrow()
  })
  it('flags old observations and formats measured timings', () => {
    const observed = Date.parse(snapshot.observed_at)
    expect(snapshotStale(snapshot, observed + 20_000)).toBe(false)
    expect(snapshotStale(snapshot, observed + 31_000)).toBe(true)
    expect(duration(65)).toBe('1m 5s')
    expect(duration(0)).toBe('0.0s')
    expect(duration(null)).toBe('Unavailable')
  })
  it('renders loading, empty, failed and stale states honestly', () => {
    const render = (value: PipelineSnapshot | null, failed = false, stale = false) => renderToStaticMarkup(<PipelineResults snapshot={value} failed={failed} stale={stale} />)
    expect(render(null)).toContain('Loading pipeline status')
    expect(render({ ...snapshot, jobs: [] })).toContain('No jobs yet')
    expect(render(null, true)).toContain('Retrying automatically')
    expect(render(snapshot, true)).toContain('timings are frozen')
    expect(render(snapshot, false, true)).toContain('snapshot is stale')
    expect(render(snapshot)).toContain('in progress at snapshot')
    expect(render(snapshot)).toContain('1m 2s')
    const failed = { ...snapshot, jobs: [{ ...snapshot.jobs[0], state: 'failed', steps: [] }] }
    expect(render(failed)).toContain('Stopped at build')
    expect(render(failed)).toContain('Step timings unavailable')
  })
})
