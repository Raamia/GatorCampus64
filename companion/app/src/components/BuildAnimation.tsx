import '../build-animation.css'

// Animated stage scene for a Gatorize job that is still building: spinning GPU fans while it waits for a GPU,
// a scanline sweeping the photo while the vision model reads it, blinking pixel eyes for the face art, a
// turning wireframe gator while Blender builds and exports it, ticks for validation and a camera flash for the
// preview renders. Pure CSS, no assets; it holds still for prefers-reduced-motion.
const SCENES: Record<string, { title: string; caption: string }> = {
  queued: { title: 'Spinning up the GPU', caption: 'Your build is in line for the Vultr GPU.' },
  spec: { title: 'Reading your photos', caption: 'The vision model looks at hair, colors and outfit.' },
  face: { title: 'Drawing the face', caption: 'Pixel eyes and a grin, 8 expressions.' },
  build: { title: 'Building the model', caption: 'Blender shapes your low-poly gator.' },
  export: { title: 'Exporting to the game', caption: 'Turning the model into N64 display lists.' },
  validate: { title: 'Checking every part', caption: 'Eyes, textures and materials, one by one.' },
  preview: { title: 'Taking photos', caption: 'Rendering your gator from every side.' },
}

function Fans() {
  return <div className="ba-fans" aria-hidden="true">
    {[0, 1].map(i => <div key={i} className="ba-fan"><div className="ba-fan-blades">{[0, 1, 2, 3, 4].map(b => <span key={b} style={{ transform: `rotate(${b * 72}deg)` }} />)}</div><div className="ba-fan-hub" /></div>)}
    <div className="ba-gpu-label">VULTR GPU</div>
  </div>
}

function Scan() {
  return <div className="ba-scan" aria-hidden="true"><div className="ba-photo"><div className="ba-head" /><div className="ba-body" /></div><div className="ba-scanline" /></div>
}

function Eyes() {
  return <div className="ba-eyes" aria-hidden="true">{[0, 1].map(i => <div key={i} className="ba-eye"><div className="ba-pupil" /></div>)}<div className="ba-mouth" /></div>
}

function Cube({ fast }: { fast?: boolean }) {
  return <div className={`ba-cube-wrap${fast ? ' fast' : ''}`} aria-hidden="true"><div className="ba-cube">{['front', 'back', 'left', 'right', 'top', 'bottom'].map(f => <span key={f} className={`ba-face ba-${f}`} />)}</div><div className="ba-gear" /></div>
}

function Ticks() {
  return <ul className="ba-ticks" aria-hidden="true">{['Eyes', 'Textures', 'Materials', 'Rig'].map((t, i) => <li key={t} style={{ animationDelay: `${i * 0.45}s` }}><span>✓</span>{t}</li>)}</ul>
}

function Flash() {
  return <div className="ba-camera" aria-hidden="true"><div className="ba-camera-body"><div className="ba-lens" /></div><div className="ba-flash" /></div>
}

export default function BuildAnimation({ state }: { state: string }) {
  const scene = SCENES[state]
  if (!scene) return null
  const art = state === 'queued' ? <Fans />
    : state === 'spec' ? <Scan />
    : state === 'face' ? <Eyes />
    : state === 'build' ? <Cube />
    : state === 'export' ? <Cube fast />
    : state === 'validate' ? <Ticks />
    : <Flash />
  return <div className="ba-stage" role="img" aria-label={scene.title}>
    <div className="ba-art">{art}</div>
    <div className="ba-text"><strong>{scene.title}<span className="ba-dots"><i>.</i><i>.</i><i>.</i></span></strong><span>{scene.caption}</span></div>
    <div className="ba-bar"><span /></div>
  </div>
}
