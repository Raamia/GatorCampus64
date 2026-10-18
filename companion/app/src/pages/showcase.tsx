import { createElement, useEffect, useRef, useState } from 'react'
import type { ModelViewerElement } from '@google/model-viewer'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Box, RotateCcw } from 'lucide-react'
import { SiteHeader } from '../components/SiteHeader'
import { Seo } from '../components/Seo'
import { seo } from '../seo'
import models from '../data/character-showcase.json'
import '../showcase.css'
import { defaultPalette, paletteParts, preparePalette, type Palette } from '../lib/showcase-palette'

type Study = (typeof models)[number]
const categories = ['Faces', 'Hair', 'Bodies', 'Clothes'] as const
const descriptions: Record<string, string> = {
  Faces: 'Jaw, cheek, forehead and nose shapes. The haircut stays the same so you can see the difference.',
  Hair: 'From a close crop to curls and longer hair. Turn a model around to see its silhouette.',
  Bodies: 'Different shoulders, waists and proportions, all at the same height.',
  Clothes: 'A tee, a collar, a hood or an overshirt. Small details give each outfit its shape.',
}

function InteractiveModel({ model, palette }: { model: Study; palette: Palette | null }) {
  const node = useRef<ModelViewerElement | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)
  const [angle, setAngle] = useState(32)
  const [spinning, setSpinning] = useState(false)
  const [colorError, setColorError] = useState(false)
  const applyPalette = useRef<((palette: Palette | null) => void) | null>(null)
  const latestPalette = useRef(palette)
  useEffect(() => { latestPalette.current = palette; applyPalette.current?.(palette) }, [palette])
  const detail = model.group === 'Faces' || model.group === 'Hair'
  const target = detail ? model.headTarget : model.bodyTarget
  const radius = detail ? model.headRadius : model.bodyRadius

  function selectAngle(value: number) {
    setSpinning(false)
    setAngle(value)
    if (node.current) {
      node.current.resetTurntableRotation?.()
      // Assign even when the preset is already selected: dragging changes the
      // camera internally without changing React state.
      node.current.cameraOrbit = `${value}deg 85deg ${radius}m`
    }
  }

  useEffect(() => {
    let active = true
    const element = node.current
    const onLoad = () => {
      setLoaded(true)
      if (element) void preparePalette(element).then(apply => {
        if (active) { applyPalette.current = apply; apply(latestPalette.current) }
      }).catch(() => { if (active) setColorError(true) })
    }
    const onError = () => setFailed(true)
    element?.addEventListener('load', onLoad)
    element?.addEventListener('error', onError)
    void import('@google/model-viewer').catch(() => { if (active) setFailed(true) })
    return () => {
      active = false
      element?.removeEventListener('load', onLoad)
      element?.removeEventListener('error', onError)
    }
  }, [])

  return <>
    <div className="showcase-model-stage">
      <img src={`/showcase/${model.id}.webp`} alt={`${model.label} rendered preview`} className="showcase-poster" />
      {!failed && createElement('model-viewer', {
        ref: node, src: `/showcase/${model.id}.glb`,
        alt: `${model.label}. Drag or use arrow keys to rotate the character.`,
        'camera-controls': true, 'interaction-prompt': 'none',
        'camera-target': target.map(n => `${n}m`).join(' '),
        'camera-orbit': `${angle}deg 85deg ${radius}m`, 'field-of-view': '30deg',
        'min-field-of-view': '15deg', 'max-field-of-view': '55deg',
        'shadow-intensity': '0.5', 'environment-image': 'neutral',
        'touch-action': 'pan-y', 'auto-rotate': spinning || undefined,
        'rotation-per-second': '18deg', 'auto-rotate-delay': '0',
        style: { opacity: loaded ? 1 : 0 },
      })}
      {!loaded && !failed && <p className="showcase-viewer-status" role="status">Loading 3D…</p>}
      {failed && <p className="showcase-viewer-status" role="status">3D isn’t available here. You can still explore the rendered previews.</p>}
    </div>
    {colorError && <p className="showcase-viewer-hint" role="status">Color preview could not load. Try reopening the 3D viewer.</p>}
    {!failed && <div className="showcase-camera" aria-label="Model camera">
      {([['Front', 0], ['Three-quarter', 32], ['Side', 90], ['Back', 180]] as const).map(([label, value]) =>
        <button key={value} aria-pressed={angle === value && !spinning} onClick={() => selectAngle(value)}>{label}</button>)}
      <button aria-pressed={spinning} onClick={() => setSpinning(!spinning)}><RotateCcw size={14} aria-hidden /> Rotate</button>
    </div>}
  </>
}

export default function Showcase() {
  const [selectedId, setSelectedId] = useState('h05')
  const [interactive, setInteractive] = useState(false)
  const [palette, setPalette] = useState<Palette | null>(null)
  const selected = models.find(m => m.id === selectedId)!
  const studies = models.filter(m => m.group === selected.group)
  return <>
    <Seo {...seo} title="Character showcase · Super Gatorlator 64" path="/showcase"
      description="Explore 23 low-poly character studies: faces, hair, body shapes and outfits. View rendered samples or rotate them in 3D, without signing in." />
    <SiteHeader />
    <main className="showcase-page" data-testid="character-showcase">
      <header className="showcase-intro">
        <div><p className="eyebrow">GATORIZE / CHARACTER SHOWCASE</p><h1>Your look.<br /><em>In low poly.</em></h1>
          <p>Big personality, a few polygons. Explore the shapes that make a campus character your own.</p></div>
        <div className="showcase-intro-note"><strong>23</strong><span>shape studies<br />No login or upload needed.</span></div>
      </header>
      <div className="showcase-categories" role="group" aria-label="Character category">
        {categories.map(group => <button key={group} aria-pressed={selected.group === group}
          onClick={() => setSelectedId(models.find(m => m.group === group)!.id)}>{group}<span>{models.filter(m => m.group === group).length}</span></button>)}
      </div>
      <div className="showcase-workspace">
        <section className="showcase-viewer" aria-label="Selected character">
          <div className="showcase-viewer-heading"><div><span>{selected.group} / {selected.id.toUpperCase()}</span><h2>{selected.label}</h2></div><span className="showcase-sample-badge">SYNTHETIC SAMPLE</span></div>
          {interactive ? <InteractiveModel key={selected.id} model={selected} palette={palette} /> : <div className="showcase-model-stage">
            <img className="showcase-poster" src={`/showcase/${selected.id}.webp`} alt={`${selected.label} rendered preview`} fetchPriority="high" />
            <button className="showcase-load" onClick={() => setInteractive(true)}><Box size={18} aria-hidden /> Explore in 3D</button>
          </div>}
          <p className="showcase-viewer-hint">{interactive ? 'Drag or use arrow keys to turn. Scroll or pinch to zoom.' : 'A rendered preview. Load the 3D model when you’re ready to look around.'}</p>
        </section>
        <section className="showcase-selection" aria-labelledby="showcase-choose">
          <p className="eyebrow">CHANGE THE SILHOUETTE</p><h2 id="showcase-choose">Explore {selected.group.toLowerCase()}</h2>
          <p>{descriptions[selected.group]}</p>
          <div className="showcase-grid">
            {studies.map(model => <button key={model.id} className="showcase-card" aria-pressed={model.id === selected.id}
              aria-label={`View ${model.label}`} onClick={() => setSelectedId(model.id)}>
              <img src={`/showcase/${model.id}.webp`} alt="" loading="lazy" width="768" height="768" />
              <span>{model.label}</span>
            </button>)}
          </div>
        </section>
      </div>
      <section className="showcase-colors" aria-labelledby="showcase-colors-title">
        <div className="showcase-colors-heading"><div><p className="eyebrow">MAKE IT YOURS</p><h2 id="showcase-colors-title">Try a palette</h2><p>Choose skin, hair and outfit colors. Your palette follows you between samples in 3D.</p></div>
          <button onClick={() => setPalette(null)} disabled={!palette}>Reset colors</button></div>
        <div className="showcase-color-grid">{paletteParts.map(({ key, label, swatches }) => <fieldset key={key}>
          <legend>{label}</legend><div className="showcase-swatches">{swatches.map(color => <button key={color} type="button" aria-label={`${label} ${color}`} aria-pressed={palette?.[key] === color} style={{ backgroundColor: color }} onClick={() => { setPalette(p => ({ ...p, [key]: color })); setInteractive(true) }} />)}</div>
          <label className="showcase-custom-color"><span>Custom {label.toLowerCase()}</span><input type="color" value={palette?.[key] ?? defaultPalette[key]} onChange={e => { setPalette(p => ({ ...p, [key]: e.target.value })); setInteractive(true) }} /></label>
        </fieldset>)}</div>
        <p className="showcase-small">Colors change this preview only. Sample thumbnails keep their original palette.</p>
      </section>
      <section className="showcase-about">
        <div><p className="eyebrow">FROM A SHAPE TO YOUR PLAYER</p><h2>Four parts. Plenty of character.</h2><p>Faces, hair, bodies and outfits are selected independently when we build a character. These fixed samples show one change at a time; they were made without reference photos.</p></div>
        <div><p>For your own character, Qwen reads your photos and chooses appearance profiles. Our Blender builder creates the model and previews for the game. The result is a stylized interpretation of your look.</p><Link className="primary-action" to="/gatorize">Make your gator <ArrowUpRight size={16} aria-hidden /></Link><p className="showcase-small">Build and preview without login. Gator Pass sign-in is needed to use your model in the game.</p></div>
      </section>
      <footer className="showcase-footer"><Link to="/">Super Gatorlator 64</Link><span>Built for SwampHacks XII · Gainesville, FL</span></footer>
    </main>
  </>
}
