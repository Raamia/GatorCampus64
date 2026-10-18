import config from './gator-config.json'

export type StepTiming = { step: string; seconds: number | null; running: boolean }
export type PipelineJob = { id: string; state: string; step: string | null; elapsed_seconds: number | null; steps: StepTiming[] }
export type GpuDevice = { index: number; utilization_gpu_pct: number | null; memory_used_mib: number | null; memory_total_mib: number | null }
export type GpuReading = { id: string; observed_at: string; available: boolean; gpus: GpuDevice[] }
export type PipelineSnapshot = { observed_at: string; jobs: PipelineJob[]; gpu: GpuReading[] }
const steps = ['queued', 'spec', 'face', 'build', 'export', 'validate', 'preview', 'store']
const states = [...steps.filter(step => step !== 'store'), 'ready', 'failed', 'unknown']
const seconds = (value: unknown): value is number | null => value === null || (typeof value === 'number' && Number.isFinite(value) && value >= 0)
const object = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null

const metric = (value: unknown, maximum: number): value is number | null => seconds(value) && (value === null || value <= maximum)

function parseGpuDevice(device: unknown): GpuDevice {
  if (!object(device)
    || typeof device.index !== 'number' || !Number.isInteger(device.index) || device.index < 0 || device.index > 15
    || !metric(device.utilization_gpu_pct, 100)
    || !metric(device.memory_used_mib, 1_048_576)
    || !metric(device.memory_total_mib, 1_048_576) || device.memory_total_mib === 0
    || (device.memory_used_mib !== null && device.memory_total_mib !== null && device.memory_used_mib > device.memory_total_mib)) {
    throw new Error('Invalid GPU metrics')
  }
  return { index: device.index, utilization_gpu_pct: device.utilization_gpu_pct, memory_used_mib: device.memory_used_mib, memory_total_mib: device.memory_total_mib }
}

/** Validate and project only operational fields, even if a future API adds others. */
export function parseSnapshot(value: unknown): PipelineSnapshot {
  if (!object(value) || typeof value.observed_at !== 'string' || !Number.isFinite(Date.parse(value.observed_at)) || !Array.isArray(value.jobs) || value.jobs.length > 12) throw new Error('Invalid pipeline status')
  const jobs = value.jobs.map((job: unknown): PipelineJob => {
    if (!object(job) || typeof job.id !== 'string' || !/^[a-f0-9]{12}$/.test(job.id) || typeof job.state !== 'string' || !states.includes(job.state) || !(job.step === null || (typeof job.step === 'string' && [...steps, 'ready'].includes(job.step))) || !seconds(job.elapsed_seconds) || !Array.isArray(job.steps) || job.steps.length > 64) throw new Error('Invalid pipeline job')
    const timings = job.steps.map((entry: unknown): StepTiming => {
      if (!object(entry) || typeof entry.step !== 'string' || !steps.includes(entry.step) || !seconds(entry.seconds) || typeof entry.running !== 'boolean') throw new Error('Invalid pipeline timing')
      return { step: entry.step, seconds: entry.seconds, running: entry.running }
    })
    return { id: job.id, state: job.state, step: job.step, elapsed_seconds: job.elapsed_seconds, steps: timings }
  })
  // An older API can still serve job timings during the staged rollout.
  const rawGpu = value.gpu ?? []
  if (!Array.isArray(rawGpu) || rawGpu.length > 8) throw new Error('Invalid GPU status')
  const gpu = rawGpu.map((reading: unknown): GpuReading => {
    if (!object(reading) || typeof reading.id !== 'string' || !/^[a-f0-9]{12}$/.test(reading.id) || typeof reading.observed_at !== 'string' || !Number.isFinite(Date.parse(reading.observed_at)) || typeof reading.available !== 'boolean' || !Array.isArray(reading.gpus) || reading.gpus.length > 16) throw new Error('Invalid GPU reading')
    const gpus = reading.gpus.map(parseGpuDevice)
    if ((!reading.available && gpus.length) || (reading.available && !gpus.length) || new Set(gpus.map(d => d.index)).size !== gpus.length) throw new Error('Invalid GPU availability')
    return { id: reading.id, observed_at: reading.observed_at, available: reading.available, gpus }
  })
  return { observed_at: value.observed_at, jobs, gpu }
}

export async function fetchPipelineStatus(signal: AbortSignal): Promise<PipelineSnapshot> {
  const response = await fetch(`${config.apiBase}/pipeline/status`, { credentials: 'omit', signal })
  if (!response.ok) throw new Error('Pipeline status unavailable')
  return parseSnapshot(await response.json())
}

export function duration(value: number | null): string {
  if (value === null) return 'Unavailable'
  if (value < 60) return `${value.toFixed(1)}s`
  const total = Math.floor(value)
  return `${Math.floor(total / 60)}m ${total % 60}s`
}

export function snapshotStale(snapshot: PipelineSnapshot, now: number): boolean {
  return now - Date.parse(snapshot.observed_at) > 30_000
}
