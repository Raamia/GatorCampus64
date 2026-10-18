import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { pollJob } from './job-polling'
beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

it('backs off transient failures and returns to three seconds after recovery', async () => {
  const request = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ state: 'build' })
  const onJob = vi.fn(), onError = vi.fn()
  const stop = pollJob({ initial: { state: 'queued' }, request, onJob, onError })
  await vi.advanceTimersByTimeAsync(3000)
  expect(onError).toHaveBeenCalledOnce()
  await vi.advanceTimersByTimeAsync(5999)
  expect(request).toHaveBeenCalledTimes(1)
  await vi.advanceTimersByTimeAsync(1)
  expect(onJob).toHaveBeenCalledOnce()
  await vi.advanceTimersByTimeAsync(3000)
  expect(request).toHaveBeenCalledTimes(3)
  stop()
  expect(vi.getTimerCount()).toBe(0)
})

it('bounds hung reads, aborts them, and ignores their late results', async () => {
  let late!: (job: { state: string }) => void
  const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { late = resolve }))
    .mockResolvedValue({ state: 'build' })
  const onJob = vi.fn(), onError = vi.fn()
  const stop = pollJob({ initial: { state: 'queued' }, request, onJob, onError })
  await vi.advanceTimersByTimeAsync(18_000)
  expect(request.mock.calls[0][0].aborted).toBe(true)
  expect(onError.mock.calls[0][0].message).toContain('timed out')
  late({ state: 'ready' })
  await vi.advanceTimersByTimeAsync(6000)
  expect(onJob).toHaveBeenCalledExactlyOnceWith({ state: 'build' })
  stop()
})

it('cancels pending work when the selected job changes or the page unmounts', async () => {
  let resolve!: (job: { state: string }) => void
  const request = vi.fn().mockImplementation(() => new Promise(done => { resolve = done }))
  const onJob = vi.fn(), onError = vi.fn()
  const stop = pollJob({ initial: { state: 'build' }, request, onJob, onError })
  await vi.advanceTimersByTimeAsync(3000)
  stop()
  expect(request.mock.calls[0][0].aborted).toBe(true)
  resolve({ state: 'ready' })
  await vi.advanceTimersByTimeAsync(60_000)
  expect(onJob).not.toHaveBeenCalled()
  expect(onError).not.toHaveBeenCalled()
  expect(request).toHaveBeenCalledOnce()
})

it('keeps ready deployment checks at 30 seconds and stops failed jobs', async () => {
  const request = vi.fn().mockResolvedValueOnce({ state: 'ready' }).mockResolvedValueOnce({ state: 'failed' })
  const stop = pollJob({ initial: { state: 'build' }, request, onJob: vi.fn(), onError: vi.fn() })
  await vi.advanceTimersByTimeAsync(3000)
  await vi.advanceTimersByTimeAsync(29_999)
  expect(request).toHaveBeenCalledOnce()
  await vi.advanceTimersByTimeAsync(1)
  expect(request).toHaveBeenCalledTimes(2)
  await vi.advanceTimersByTimeAsync(60_000)
  expect(request).toHaveBeenCalledTimes(2)
  stop()
})
