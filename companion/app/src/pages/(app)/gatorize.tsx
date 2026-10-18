import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, finishLogin, login, logout } from '../../lib/gator-api'
import GatorAccount from '../../components/GatorAccount'
import CharacterViewer from '../../components/CharacterViewer'
import { PHOTO_ACCEPT, photoSelectionError } from '../../lib/gatorize-photos'
import { pollJob } from '../../lib/job-polling'

type Job = {
  id: string; character_id: string; name: string; state: string; step: string
  pipeline: string[]; step_index: number | null; error?: string; log?: string
  slot?: number; deployed?: boolean; deploy_state?: string
  previews: { name: string; url: string }[]; portrait?: string | null; browser_model?: string | null
}
type Character = { id: string; name: string; state: string; job_id: string }
const savedJob = 'sgl-last-job'
const labels: Record<string, string> = { queued: 'Queued', spec: 'Finding your look', face: 'Drawing your face', build: 'Building your model', export: 'Exporting', validate: 'Checking your model', preview: 'Rendering previews', ready: 'Ready' }
const button = 'rounded-lg bg-primary px-5 py-3 font-semibold text-primary-foreground disabled:opacity-50'

function HowItWorks() {
  return <aside className="gator-how" aria-label="How character generation works"><p className="gator-how-kicker">HOW IT WORKS · BUILT ON VULTR</p><h3>From your photos to a playable gator.</h3><p>Your photos stay inside our private network. A local Qwen vision model on a Vultr Cloud GPU reads visible hair, colors, clothing and distinctive details. Blender then builds the low-poly character, previews and game assets.</p><div className="gator-how-pipeline"><span>PHOTO</span><i>→</i><span>QWEN ON A16</span><i>→</i><span>BLENDER</span><i>→</i><span>GAME</span></div></aside>
}

function PipelineProgress({ pipeline, stepIndex, state }: { pipeline: string[]; stepIndex: number | null; state: string }) {
  const doneThrough = state === 'ready' ? pipeline.length : stepIndex ?? -1
  return <ol className="gatorize-pipeline" aria-label="Build stages">{pipeline.map((phase, i) => {
    const cls = state === 'failed' && i === stepIndex ? 'fail' : i < doneThrough ? 'done' : i === stepIndex ? 'now' : ''
    return <li key={phase} className={cls} aria-current={phase === state ? 'step' : undefined}><span className="dot" aria-hidden="true" />{labels[phase] ?? phase}</li>
  })}</ol>
}

function ReferenceRenders({ previews, name, defaultOpen }: { previews: { name: string; url: string }[]; name: string; defaultOpen: boolean }) {
  return <details className="gatorize-renders" open={defaultOpen}>
    <summary>Reference renders <span className="text-muted-foreground">({previews.length})</span></summary>
    <div className="gatorize-renders-grid">{previews.map(p => <img key={p.name} src={p.url} alt={`${name}: ${p.name}`} loading="lazy" />)}</div>
  </details>
}

export default function GatorizePage() {
  const [ready, setReady] = useState(false)
  const [signedIn, setSignedIn] = useState(false)
  const [name, setName] = useState('')
  const [consent, setConsent] = useState(false)
  const [files, setFiles] = useState<File[]>([])
  const [job, setJob] = useState<Job | null>(null)
  const [characters, setCharacters] = useState<Character[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    let active = true
    async function boot() {
      try {
        const signed = await finishLogin()
        if (!active) return
        setSignedIn(signed)
        if (!signed) return
        const me = await api<{ characters: Character[] }>('/me')
        if (!active) return
        setCharacters(me.characters)
        const id = window.localStorage.getItem(savedJob)
        if (id && me.characters.some(c => c.job_id === id)) {
          const restored = await api<Job>(`/jobs/${encodeURIComponent(id)}`)
          if (active) setJob(restored)
        }
      } catch (e) { if (active) setError((e as Error).message) }
      finally { if (active) setReady(true) }
    }
    void boot()
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!job) return
    return pollJob({
      initial: job,
      request: signal => api<Job>(`/jobs/${encodeURIComponent(job.id)}`, { signal }),
      onJob: next => {
        setJob(next); setError('')
        setCharacters(cs => cs.map(c => c.job_id === next.id ? { ...c, state: next.state } : c))
      },
      onError: error => setError(error.message),
    })
    // The loop owns state transitions; only changing the selected job restarts it.
  }, [job?.id])

  async function openJob(id: string) {
    setError(''); setBusy(true)
    try { setJob(await api<Job>(`/jobs/${encodeURIComponent(id)}`)); window.localStorage.setItem(savedJob, id) }
    catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  async function removeJob() {
    if (!job || !window.confirm(`Delete ${job.name}? This also removes the character from the hosted game.`)) return
    setBusy(true); setError('')
    try {
      await api(`/characters/${encodeURIComponent(job.character_id)}`, { method: 'DELETE' })
      setCharacters(cs => cs.filter(c => c.id !== job.character_id))
      setJob(null); window.localStorage.removeItem(savedJob)
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  async function submit(e: FormEvent) {
    e.preventDefault(); setError('')
    const invalid = photoSelectionError(files)
    if (invalid) return setError(invalid)
    if (!consent) return setError('Confirm you have permission to process these photos.')
    const body = new FormData()
    body.set('name', name.trim()); body.set('consent', 'true')
    files.forEach(f => body.append('photos', f))
    setBusy(true)
    try {
      const created = await api<{ job_id: string; character_id: string; name: string }>('/characters', { method: 'POST', body })
      setFiles([]); setConsent(false)
      if (fileInput.current) fileInput.current.value = ''
      window.localStorage.setItem(savedJob, created.job_id)
      setJob({ id: created.job_id, character_id: created.character_id, name: created.name, state: 'queued', step: 'queued', pipeline: [], step_index: 0, previews: [] })
      setCharacters(cs => [{ id: created.character_id, name: created.name, state: 'queued', job_id: created.job_id }, ...cs])
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  if (!ready) return <main className="mx-auto gator-page" aria-busy="true">Loading Gator Pass…</main>
  return <main className="mx-auto gator-page">
    <header className="gator-header"><p className="text-xs font-semibold tracking-[.2em] text-primary">GATORIZE ME · UF CAMPUS</p><h1 className="mt-3 text-4xl font-bold">Your face. Your gator. Your campus.</h1><p className="mt-3 max-w-xl text-muted-foreground">Upload a few clear photos and make a playable N64-style character. Follow the build here, then meet your friends on campus.</p></header>
    {error && <p role="alert" className="mb-5 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm">{error}</p>}
    {!signedIn ? <section className="gator-card"><h2 className="text-xl font-semibold">Start with Gator Pass</h2><p className="mt-2 text-muted-foreground">Use the same Gator Pass account here and in the game. Field Board sign-in is separate.</p><button className={`${button} mt-5`} onClick={() => login().catch((e: Error) => setError(e.message))}>Sign in with Gator Pass</button></section> : <>
      <div className="mb-4 flex justify-between text-sm"><span>Gator Pass connected</span><button className="underline" onClick={() => logout().catch((e: Error) => setError(e.message))}>Sign out of Gator Pass</button></div>
      <GatorAccount onDeleted={() => { setJob(null); setCharacters([]); setFiles([]); setError(''); window.localStorage.removeItem(savedJob); if (fileInput.current) fileInput.current.value = '' }} />
      {job ? <div className="space-y-5" aria-live="polite">
        <section className="gator-card gatorize-status">
          <div className="gatorize-status-top">
            <div><p className="section-index">{job.state === 'failed' ? 'BUILD FAILED' : labels[job.state]?.toUpperCase() ?? job.state.toUpperCase()}</p><h2 className="mt-1 text-2xl font-semibold">{job.name}</h2></div>
            {job.pipeline.length > 0 && <PipelineProgress pipeline={job.pipeline} stepIndex={job.step_index} state={job.state} />}
          </div>
          {job.state === 'failed' ? <div><p>{job.error ?? 'The build could not finish. Try clear photos in good light.'}</p>{job.log && <details className="mt-3 text-sm"><summary>Build details</summary><pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap">{job.log}</pre></details>}</div> : job.state === 'ready' ? <div className="rounded-lg bg-success/10 p-4"><strong>{job.deployed ? `Live in guest slot ${job.slot}` : job.slot ? `Waiting for the server to load guest slot ${job.slot}` : 'Your gator is ready; waiting for a free guest slot.'}</strong><p className="mt-2 text-sm">{job.deployed ? 'Join the game and type /login with this Gator Pass account to select your character.' : 'Your model is built. Deployment can take a few minutes and may require a server restart.'}</p>{job.deploy_state === 'failed' && <p className="mt-2 text-sm">Server deployment failed. Your model is saved; the operator needs to check its deployment.</p>}</div> : <div><p className="text-muted-foreground">{job.state === 'queued' ? 'Waiting for the GPU. Your build continues if you close this page.' : 'Your gator is taking shape. This usually takes a few minutes; you can come back later.'}</p><HowItWorks /></div>}
        </section>
        {job.browser_model && <CharacterViewer src={job.browser_model} name={job.name} poster={(job.previews.find(p => p.name === 'front.png') ?? job.previews[0])?.url} />}
        {job.previews.length > 0 && <ReferenceRenders previews={job.previews} name={job.name} defaultOpen={!job.browser_model} />}
        <section className="gator-card gatorize-actions">
          <div className="flex flex-wrap gap-4"><Link to="/play" className={button}>How to play</Link><button onClick={() => { setJob(null); setError(''); window.localStorage.removeItem(savedJob) }} className="underline">Back to my gators</button></div>
          <button disabled={busy} onClick={() => void removeJob()} className="mt-4 text-sm text-destructive underline disabled:opacity-50">{busy ? 'Deleting…' : 'Delete this gator'}</button>
        </section>
      </div> : <>
        {characters.length > 0 && <section className="gator-card gatorize-roster mb-6">
          <p className="section-index">YOUR GATORS</p>
          <h2 className="mt-1 mb-4 text-xl font-semibold">Pick up where you left off</h2>
          <div className="gatorize-roster-grid">{characters.map(c => <button key={c.id} disabled={busy} className="gatorize-roster-card" onClick={() => void openJob(c.job_id)}>
            <span className="gatorize-roster-name">{c.name}</span>
            <span className="gatorize-roster-status">{labels[c.state] ?? c.state}</span>
          </button>)}</div>
        </section>}
        <form className="gator-card gatorize-form space-y-5" onSubmit={submit}>
          <div className="gatorize-form-head"><p className="section-index">NEW GATOR</p><h2 className="mt-1 text-xl font-semibold">Make a new gator</h2></div>
          <label className="block"><span className="text-sm font-semibold">Gator name</span><input required maxLength={12} pattern="[ -\u007e]+" value={name} onChange={e => setName(e.target.value)} className="mt-2 w-full rounded-lg border border-input bg-background px-3 py-2" placeholder="Up to 12 characters" /></label>
          <div className="gatorize-dropzone"><span className="text-sm font-semibold">Photos</span><input ref={fileInput} required={files.length === 0} accept={PHOTO_ACCEPT} aria-label="Photos" multiple type="file" onChange={e => { const selected = Array.from(e.target.files ?? []); setFiles(selected); setError(photoSelectionError(selected)) }} className="mt-2 block w-full text-sm" /><span className="mt-2 block text-xs text-muted-foreground">1–4 JPEG or PNG photos, up to 8 MB each. Include a clear face and your outfit. Photos are deleted when processing ends.</span>{files.length > 0 && <ul className="mt-3 space-y-2" aria-label="Selected photos">{files.map((file, index) => <li key={`${file.name}-${file.lastModified}-${index}`} className="flex items-center justify-between gap-3 rounded border border-border bg-background px-3 py-2 text-sm"><span className="min-w-0 truncate">{file.name} <span className="text-xs text-muted-foreground">({(file.size / 1024 / 1024).toFixed(1)} MB)</span></span><button type="button" className="shrink-0 text-xs text-destructive underline" onClick={() => { const remaining = files.filter((_, i) => i !== index); setFiles(remaining); setError(remaining.length ? photoSelectionError(remaining) : ''); if (fileInput.current) fileInput.current.value = '' }}>Remove</button></li>)}</ul>}</div>
          <label className="flex items-start gap-3 text-sm"><input required type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} className="mt-1" />I confirm these photos are of me or I have permission to submit them, and agree they may be processed into a game character.</label>
          <button disabled={busy} className={button} type="submit">{busy ? 'Submitting photos…' : 'Build my gator'}</button>
        </form>
      </>}
    </>}
  </main>
}
