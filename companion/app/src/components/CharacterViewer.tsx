import { createElement, useEffect, useRef, useState } from 'react'

type Props = { src: string; name: string; poster?: string }

export default function CharacterViewer(props: Props) {
  // A refreshed presigned URL starts a fresh attempt even after a load error.
  return <CharacterPreview key={props.src} {...props} />
}

function CharacterPreview({ src, name, poster }: Props) {
  const [attempt, setAttempt] = useState(0)
  return <section className="gator-viewer gator-hero" aria-label={`${name} interactive preview`}>
    <div className="gator-viewer-caption"><span>YOUR GATOR / IN 3D</span><span>Drag to rotate · scroll or pinch to zoom</span></div>
    <PreviewAttempt key={attempt} src={src} name={name} poster={poster} retry={() => setAttempt(value => value + 1)} />
  </section>
}

function PreviewAttempt({ src, name, poster, retry }: Props & { retry: () => void }) {
  const node = useRef<HTMLElement | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let active = true
    let settled = false
    const element = node.current
    const onError = () => {
      if (!active || settled) return
      settled = true; clearTimeout(timeout); setFailed(true)
    }
    const timeout = setTimeout(onError, 20_000)
    const onLoad = () => {
      if (!active || settled) return
      settled = true; clearTimeout(timeout); setLoaded(true)
    }
    element?.addEventListener('load', onLoad)
    element?.addEventListener('error', onError)
    void import('@google/model-viewer').catch(() => { if (active) onError() })
    return () => {
      active = false
      clearTimeout(timeout)
      element?.removeEventListener('load', onLoad)
      element?.removeEventListener('error', onError)
    }
  }, [])
  return <div className="gator-viewer-stage">
    {poster && (!loaded || failed) && <img className="gator-viewer-poster" src={poster} alt={`${name}, rendered character preview`} />}
    {!failed && createElement('model-viewer', {
      ref: node, src, alt: `${name}, a playable character. Drag or use arrow keys to rotate.`,
      'camera-controls': true, 'auto-rotate': true, 'rotation-per-second': '15deg',
      'shadow-intensity': '0.7', exposure: '1.1', 'touch-action': 'pan-y',
      style: { opacity: loaded ? 1 : 0 },
    })}
    {!loaded && !failed && <p role="status" className="gator-viewer-note">Loading your 3D preview…</p>}
    {failed && <div className="gator-viewer-recovery"><p role="status">The 3D preview couldn’t load. {poster ? 'The rendered preview is shown above.' : 'Any reference renders remain available below.'}</p><button type="button" onClick={retry}>Retry 3D preview</button></div>}
  </div>
}
