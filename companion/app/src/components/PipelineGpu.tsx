import type { PipelineSnapshot } from '../lib/pipeline-status'

const memory = (value: number | null) => value === null ? 'Unavailable' : `${(value / 1024).toFixed(1)} GiB`
const utc = (value: string) => new Date(value).toISOString().replace('T', ' ').replace(/\.\d{3}Z$/, ' UTC')

export function PipelineGpu({ snapshot, failed, now }: { snapshot: PipelineSnapshot | null; failed: boolean; now: number }) {
  const readings = snapshot?.gpu ?? []
  return <section className="pipeline-gpu" aria-labelledby="pipeline-gpu-title">
    <header className="pipeline-gpu-heading"><div><p className="eyebrow">VULTR / GPU WORKER</p><h2 id="pipeline-gpu-title">GPU measurements</h2></div><span className="pipeline-caption">Sampled every 10 seconds</span></header>
    <p className="pipeline-caption">Utilization and VRAM across the worker’s GPU, including the vision model and other GPU work. These are sampled readings, not per-job usage or peak measurements.</p>
    {!readings.length && <p role="status" className="pipeline-gpu-empty">{!snapshot && !failed ? 'Loading GPU measurements…' : failed ? 'GPU measurements are unavailable. Retrying automatically…' : 'No GPU measurements reported yet. Readings appear when the worker starts reporting, even with an empty queue.'}</p>}
    {readings.map((reading, workerIndex) => {
      const stale = failed || now - Date.parse(reading.observed_at) > 30_000 || now - Date.parse(snapshot!.observed_at) > 30_000
      return <div key={reading.id} className={`pipeline-gpu-worker${stale ? ' is-stale' : ''}`}>
        <div className="pipeline-gpu-observed"><span className={`pipeline-state ${stale ? '' : reading.available ? 'pipeline-state-ready' : 'pipeline-state-failed'}`}>{stale ? 'Stale · last reported' : reading.available ? 'Reporting' : 'Unavailable'}</span>
          <p className="pipeline-caption">{readings.length > 1 ? `Worker ${workerIndex + 1} · ` : ''}<time dateTime={reading.observed_at}>{utc(reading.observed_at)}</time></p></div>
        {stale && <p className="pipeline-caption" role="status">Updates have stopped. These readings are frozen until the worker reports again.</p>}
        {!reading.available ? <p className="pipeline-gpu-empty">The worker could not read GPU metrics. Retrying automatically; character builds can continue.</p> : <div className="pipeline-gpu-devices">{reading.gpus.map(gpu => {
          const utilization = gpu.utilization_gpu_pct
          const used = gpu.memory_used_mib, total = gpu.memory_total_mib
          return <article className="pipeline-gpu-device" key={gpu.index}>
            <h3>GPU {gpu.index + 1}</h3>
            <div className="pipeline-gpu-metric"><span>GPU utilization</span><strong>{utilization === null ? 'Unavailable' : `${utilization.toFixed(0)}%`}</strong></div>
            {utilization !== null && <meter aria-label={`GPU ${gpu.index + 1} utilization`} min={0} max={100} value={utilization}>{utilization}%</meter>}
            <div className="pipeline-gpu-metric"><span>VRAM used</span><strong>{memory(used)}<small> / {memory(total)}</small></strong></div>
            {used !== null && total !== null && <meter aria-label={`GPU ${gpu.index + 1} VRAM used`} min={0} max={total} value={used}>{memory(used)} of {memory(total)}</meter>}
            {(utilization === null || used === null || total === null) && <p className="pipeline-caption">Some metrics are not available from the GPU driver.</p>}
          </article>
        })}</div>}
      </div>
    })}
  </section>
}
