import { createElement, useEffect, useRef, useState } from 'react'

export default function CharacterViewer({ src, name }: { src: string; name: string }) {
  const node = useRef<HTMLElement | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let active = true
    void import('@google/model-viewer').catch(() => { if (active) setFailed(true) })
    const element = node.current
    const onLoad = () => { setLoaded(true); setFailed(false) }
    const onError = () => { setFailed(true) }
    element?.addEventListener('load', onLoad)
    element?.addEventListener('error', onError)
    return () => {
      active = false
      element?.removeEventListener('load', onLoad)
      element?.removeEventListener('error', onError)
    }
  }, [src])
  return <section className="gator-viewer" aria-label={`${name} interactive preview`}>
    <div className="gator-viewer-caption"><span>YOUR GATOR / IN 3D</span><span>Drag to rotate · scroll or pinch to zoom</span></div>
    {!failed && createElement('model-viewer', {
      ref: node, src, alt: `${name}, a playable character. Drag or use arrow keys to rotate.`,
      'camera-controls': true, 'auto-rotate': true, 'rotation-per-second': '15deg',
      'shadow-intensity': '0.7', exposure: '1.1', 'touch-action': 'pan-y',
      style: { width: '100%', height: 'min(65vh, 520px)' },
    })}
    {!loaded && !failed && <p role="status" className="gator-viewer-note">Loading your 3D preview…</p>}
    {failed && <p role="status" className="gator-viewer-note">The 3D preview couldn’t load. Your reference renders are still available below.</p>}
  </section>
}
