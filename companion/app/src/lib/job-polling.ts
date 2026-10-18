/** One non-overlapping polling loop per selected job. Never retries a creation request. */
export function pollJob<T extends { state: string }>({ initial, request, onJob, onError }: {
  initial: T
  request: (signal: AbortSignal) => Promise<T>
  onJob: (job: T) => void
  onError: (error: Error) => void
}): () => void {
  let active = true
  let current = initial
  let failures = 0
  let next: ReturnType<typeof setTimeout> | undefined
  let deadline: ReturnType<typeof setTimeout> | undefined
  let controller: AbortController | undefined
  function schedule() {
    if (!active || current.state === 'failed') return
    next = setTimeout(() => { void refresh() }, current.state === 'ready' ? 30_000 : Math.min(30_000, 3000 * (failures + 1)))
  }
  async function refresh() {
    controller = new AbortController()
    try {
      const timeout = new Promise<never>((_, reject) => {
        deadline = setTimeout(() => {
          reject(new Error('Status update timed out. Your build continues; retrying automatically.'))
          controller?.abort()
        }, 15_000)
      })
      const job = await Promise.race([request(controller.signal), timeout])
      if (!active) return
      current = job
      failures = 0
      onJob(job)
    } catch (error) {
      if (!active) return
      failures++
      onError(error instanceof Error ? error : new Error('Status updates unavailable. Retrying automatically.'))
    } finally {
      clearTimeout(deadline)
      schedule()
    }
  }
  schedule()
  return () => { active = false; clearTimeout(next); clearTimeout(deadline); controller?.abort() }
}
