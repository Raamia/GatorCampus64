import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, finishLogin, login, logout } from '../../lib/gator-api'

type Job = {
  id: string; character_id: string; name: string; state: string; step: string
  pipeline: string[]; step_index: number | null; error?: string; log?: string
  slot?: number; deployed?: boolean; deploy_state?: string
  previews: { name: string; url: string }[]; portrait?: string | null
}
type Character = { id: string; name: string; state: string; job_id: string }
const savedJob = 'sgl-last-job'
const labels: Record<string, string> = { queued: 'Queued', spec: 'Finding your look', face: 'Drawing your face', build: 'Building your model', export: 'Exporting', validate: 'Checking your model', preview: 'Rendering previews', ready: 'Ready' }
const button = 'rounded-lg bg-primary px-5 py-3 font-semibold text-primary-foreground disabled:opacity-50'

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
  const [pollTick, setPollTick] = useState(0)
  const timer = useRef<number | undefined>(undefined)

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
    if (!job || job.state === 'failed') return
    let active = true
    timer.current = window.setTimeout(async () => {
      try {
        const next = await api<Job>(`/jobs/${encodeURIComponent(job.id)}`)
        if (active) {
          setJob(next); setError('')
          setCharacters(cs => cs.map(c => c.job_id === next.id ? { ...c, state: next.state } : c))
        }
      } catch (e) {
        if (active) { setError((e as Error).message); setPollTick(t => t + 1) }
      }
    }, job.state === 'ready' ? 30000 : Math.min(30000, 3000 * (pollTick + 1)))
    return () => { active = false; window.clearTimeout(timer.current) }
  }, [job, pollTick])

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
    if (!consent || files.length < 1 || files.length > 4) return setError('Choose 1–4 photos and confirm you have permission to process them.')
    if (files.some(f => f.size > 8 * 1024 * 1024)) return setError('Each photo must be 8 MB or smaller.')
    const body = new FormData()
    body.set('name', name.trim()); body.set('consent', 'true')
    files.forEach(f => body.append('photos', f))
    setBusy(true)
    try {
      const created = await api<{ job_id: string; character_id: string; name: string }>('/characters', { method: 'POST', body })
      window.localStorage.setItem(savedJob, created.job_id)
      setJob({ id: created.job_id, character_id: created.character_id, name: created.name, state: 'queued', step: 'queued', pipeline: [], step_index: 0, previews: [] })
      setCharacters(cs => [{ id: created.character_id, name: created.name, state: 'queued', job_id: created.job_id }, ...cs])
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  if (!ready) return <main className="mx-auto max-w-3xl px-6 py-16" aria-busy="true">Loading Gator Pass…</main>
  return <main className="mx-auto max-w-3xl px-6 py-12 text-foreground">
    <header className="mb-10"><p className="text-xs font-semibold tracking-[.2em] text-primary">GATORIZE ME · UF CAMPUS</p><h1 className="mt-3 text-4xl font-bold">Your face. Your gator. Your campus.</h1><p className="mt-3 max-w-xl text-muted-foreground">Upload a few clear photos and make a playable N64-style character. Follow the build here, then meet your friends on campus.</p></header>
    {error && <p role="alert" className="mb-5 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm">{error}</p>}
    {!signedIn ? <section className="rounded-xl border border-border bg-card p-6"><h2 className="text-xl font-semibold">Start with Gator Pass</h2><p className="mt-2 text-muted-foreground">Use the same Gator Pass account here and in the game. Field Board sign-in is separate.</p><button className={`${button} mt-5`} onClick={() => login().catch((e: Error) => setError(e.message))}>Sign in with Gator Pass</button></section> : <>
      <div className="mb-4 flex justify-between text-sm"><span>Gator Pass connected</span><button className="underline" onClick={() => logout().catch((e: Error) => setError(e.message))}>Sign out of Gator Pass</button></div>
      {job ? <section className="space-y-6 rounded-xl border border-border bg-card p-6" aria-live="polite">
        <div><p className="text-xs tracking-widest text-muted-foreground">{job.state === 'failed' ? 'BUILD FAILED' : labels[job.state]?.toUpperCase() ?? job.state.toUpperCase()}</p><h2 className="mt-1 text-2xl font-semibold">{job.name}</h2></div>
        {job.pipeline.length > 0 && <ol className="flex flex-wrap gap-2" aria-label="Build stages">{job.pipeline.map((phase, i) => <li key={phase} aria-current={phase === job.state ? 'step' : undefined} className={`rounded-full border px-3 py-1 text-xs ${i === job.step_index ? 'border-primary font-bold' : 'border-border text-muted-foreground'}`}>{labels[phase] ?? phase}</li>)}</ol>}
        {job.state === 'failed' ? <div><p>{job.error ?? 'The build could not finish. Try clear photos in good light.'}</p>{job.log && <details className="mt-3 text-sm"><summary>Build details</summary><pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap">{job.log}</pre></details>}</div> : job.state === 'ready' ? <div className="rounded-lg bg-success/10 p-4"><strong>{job.deployed ? `Live in guest slot ${job.slot}` : job.slot ? `Waiting for the server to load guest slot ${job.slot}` : 'Your gator is ready; waiting for a free guest slot.'}</strong><p className="mt-2 text-sm">{job.deployed ? 'Join the game and type /login with this Gator Pass account to select your character.' : 'Your model is built. Deployment can take a few minutes and may require a server restart.'}</p>{job.deploy_state === 'failed' && <p className="mt-2 text-sm">Server deployment failed. Your model is saved; the operator needs to check its deployment.</p>}</div> : <p className="text-muted-foreground">{job.state === 'queued' ? 'Waiting for the GPU. Your build continues if you close this page.' : 'Your gator is taking shape. This usually takes a few minutes; you can come back later.'}</p>}
        {job.previews.length > 0 && <div><h3 className="mb-3 font-semibold">Your model</h3><div className="grid grid-cols-2 gap-3">{job.previews.map(p => <img key={p.name} src={p.url} alt={`${job.name}: ${p.name}`} loading="lazy" className="rounded-lg border border-border" />)}</div></div>}
        <div className="flex flex-wrap gap-4"><Link to="/play" className={button}>How to play</Link><button onClick={() => { setJob(null); setError(''); window.localStorage.removeItem(savedJob) }} className="underline">Back to my gators</button></div>
        <button disabled={busy} onClick={() => void removeJob()} className="text-sm text-destructive underline disabled:opacity-50">{busy ? 'Deleting…' : 'Delete this gator'}</button>
      </section> : <>
        {characters.length > 0 && <section className="mb-6 rounded-xl border border-border bg-card p-6"><h2 className="mb-3 font-semibold">My gators</h2><ul className="space-y-3">{characters.map(c => <li key={c.id} className="flex justify-between gap-3"><button disabled={busy} className="text-left underline" onClick={() => void openJob(c.job_id)}>{c.name}</button><span className="text-sm text-muted-foreground">{labels[c.state] ?? c.state}</span></li>)}</ul></section>}
        <form className="space-y-6 rounded-xl border border-border bg-card p-6" onSubmit={submit}>
          <h2 className="text-xl font-semibold">Make a new gator</h2>
          <label className="block"><span className="text-sm font-semibold">Gator name</span><input required maxLength={12} pattern="[ -\u007e]+" value={name} onChange={e => setName(e.target.value)} className="mt-2 w-full rounded-lg border border-input bg-background px-3 py-2" placeholder="Up to 12 characters" /></label>
          <label className="block"><span className="text-sm font-semibold">Photos</span><input required accept="image/jpeg,image/png,image/webp" multiple type="file" onChange={e => setFiles(Array.from(e.target.files ?? []))} className="mt-2 block w-full text-sm" /><span className="mt-2 block text-xs text-muted-foreground">1–4 photos, up to 8 MB each. Include a clear face and your outfit. Photos are deleted when processing ends.</span></label>
          <label className="flex items-start gap-3 text-sm"><input required type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} className="mt-1" />I confirm these photos are of me or I have permission to submit them, and agree they may be processed into a game character.</label>
          <button disabled={busy} className={button} type="submit">{busy ? 'Submitting photos…' : 'Build my gator'}</button>
        </form>
      </>}
    </>}
  </main>
}
