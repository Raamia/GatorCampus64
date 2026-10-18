import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { SiteHeader } from '../components/SiteHeader'
import { PipelineGpu } from '../components/PipelineGpu'
import { Seo } from '../components/Seo'
import { seo } from '../seo'
import { duration, fetchPipelineStatus, snapshotStale, type PipelineSnapshot } from '../lib/pipeline-status'
import '../pipeline.css'

export function PipelineResults({ snapshot, failed, stale }: { snapshot: PipelineSnapshot | null; failed: boolean; stale: boolean }) {
  return <>
    <p role="status" className="pipeline-refresh">{failed
      ? snapshot ? 'Updates unavailable. Showing the last snapshot; timings are frozen.' : 'Pipeline status is unavailable. Retrying automatically…'
      : stale ? 'The last snapshot is stale. Waiting for a fresh update…'
      : snapshot ? 'Snapshot received. Updates every 10 seconds.' : 'Loading pipeline status…'}</p>
    {snapshot && <>
      <p className="pipeline-caption">Observed at <time dateTime={snapshot.observed_at}>{new Date(snapshot.observed_at).toISOString().replace('T', ' ').replace('Z', ' UTC')}</time>. Timings are measured at this snapshot.</p>
      {snapshot.jobs.length === 0 ? <div className="pipeline-empty"><h2>No jobs yet</h2><p>New Gatorize Me jobs will appear here when they enter the queue.</p></div>
        : <ol className="pipeline-jobs">{snapshot.jobs.map(job => <li key={job.id} className="pipeline-job">
          <header><div><span className="eyebrow">JOB {job.id}</span><h2>{job.state === 'ready' ? 'Ready' : job.state === 'failed' ? 'Failed' : job.state === 'queued' ? 'Queued' : `Processing · ${job.step ?? job.state}`}</h2></div>
            <span className={`pipeline-state pipeline-state-${job.state}`}>{job.state}</span></header>
          <p className="pipeline-caption">Total including queue: <strong>{duration(job.elapsed_seconds)}</strong>{job.state === 'failed' && job.step ? ` · Stopped at ${job.step}` : ''}</p>
          {job.steps.length ? <ol className="pipeline-steps" aria-label={`Step timings for job ${job.id}`}>
            {job.steps.map((step, index) => <li key={`${step.step}-${index}`}><span>{step.step}</span><strong>{duration(step.seconds)}</strong><small>{step.running ? 'in progress at snapshot' : 'completed interval'}</small></li>)}
          </ol> : <p className="pipeline-caption">Step timings unavailable for this earlier job.</p>}
        </li>)}</ol>}
    </>}
  </>
}

export default function Pipeline() {
  const [snapshot, setSnapshot] = useState<PipelineSnapshot | null>(null)
  const [failed, setFailed] = useState(false)
  const [now, setNow] = useState(0)
  useEffect(() => {
    let active = true
    let next: ReturnType<typeof setTimeout>
    let controller: AbortController | undefined
    const poll = async () => {
      controller = new AbortController()
      const timeout = setTimeout(() => controller?.abort(), 8000)
      try {
        const value = await fetchPipelineStatus(controller.signal)
        if (active) { setSnapshot(value); setFailed(false); setNow(Date.now()) }
      } catch {
        if (active) { setFailed(true); setNow(Date.now()) }
      } finally {
        clearTimeout(timeout)
        if (active) next = setTimeout(() => { void poll() }, 10_000)
      }
    }
    void poll()
    const ticker = setInterval(() => setNow(Date.now()), 5000)
    return () => { active = false; clearTimeout(next); clearInterval(ticker); controller?.abort() }
  }, [])

  return <>
    <Seo {...seo} title="Pipeline status · GatorCampus 64" path="/pipeline"
      description="Follow recent Gatorize Me jobs through the Vultr-hosted character pipeline. Public step timings without photos or account information." />
    <SiteHeader />
    <main className="pipeline-page">
      <header className="pipeline-intro"><p className="eyebrow">GATORIZE / LIVE PIPELINE</p><h1>From photo<br /><em>to player.</em></h1>
        <p>Follow the latest 12 character jobs through our Vultr-hosted pipeline: Qwen appearance analysis, Blender modeling, export, validation and previews.</p></header>
      <aside className="pipeline-note"><strong>Public operations view</strong><p>Only anonymous job labels, timings and worker GPU measurements are shown. No photos, names or account details.</p></aside>
      <PipelineGpu snapshot={snapshot} failed={failed} now={now} />
      <section aria-label="Recent pipeline jobs"><PipelineResults snapshot={snapshot} failed={failed} stale={snapshot !== null && snapshotStale(snapshot, now)} /></section>
      <footer className="pipeline-footer"><Link to="/showcase">Explore the character showcase</Link><span>Built for SwampHacks XII · University of Florida</span></footer>
    </main>
  </>
}
