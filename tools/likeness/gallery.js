const $ = (selector, root = document) => root.querySelector(selector)
const panels = [...document.querySelectorAll('.panel')]
const batch = document.body.dataset.batch || 'round-01'
const storageKey = `sgl-likeness-${batch}-notes`
let models = [], group = 'Faces', selected = [], active = 0, view = 'quarter', closeup = true, spinning = false
let notes = {}
try { notes = JSON.parse(localStorage.getItem(storageKey) || '{}') } catch { /* Notes can still be downloaded. */ }
if (!notes || typeof notes !== 'object' || Array.isArray(notes)) notes = {}

function selectSlot(slot) {
  active = slot
  panels.forEach((panel, i) => {
    panel.classList.toggle('active', i === slot)
    $('.slot-button', panel).setAttribute('aria-pressed', String(i === slot))
  })
  $('#shelf-note').textContent = `Click a study to place it in ${slot === 0 ? 'A' : 'B'}.`
}

function camera() {
  const angle = { front: 0, quarter: 32, side: 90, back: 180 }[view]
  const comparisonSet = models.filter(m => m.group === group)
  const radius = Math.max(...comparisonSet.map(m => closeup ? m.headRadius : m.bodyRadius))
  panels.forEach((panel, i) => {
    const m = selected[i], viewer = $('model-viewer', panel)
    if (!m) return
    const stage = $('.stage', panel)
    const fittedRadius = radius * Math.max(1, stage.clientHeight / stage.clientWidth)
    const target = closeup ? m.headTarget : m.bodyTarget
    viewer.setAttribute('camera-target', target.map(n => `${n}m`).join(' '))
    viewer.setAttribute('camera-orbit', `${angle}deg 85deg ${fittedRadius}m`)
    viewer.setAttribute('min-camera-orbit', `auto auto ${radius * .35}m`)
    viewer.setAttribute('max-camera-orbit', `auto auto ${m.bodyRadius * 2.5}m`)
    viewer.toggleAttribute('auto-rotate', spinning)
    viewer.setAttribute('rotation-per-second', '18deg')
    viewer.setAttribute('auto-rotate-delay', '0')
    if (viewer.resetTurntableRotation) viewer.resetTurntableRotation()
  })
  document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('selected', b.dataset.view === view))
  $('#focus').textContent = closeup ? 'Full body' : 'Face detail'
  $('#spin').setAttribute('aria-pressed', String(spinning))
  $('#spin').classList.toggle('selected', spinning)
}

function updatePanel(i) {
  const panel = panels[i], m = selected[i], viewer = $('model-viewer', panel)
  $('.spec-id', panel).textContent = `${m.id.toUpperCase()} / ${m.group.toUpperCase()}`
  $('h2', panel).textContent = m.label
  $('.download', panel).href = m.model
  $('.download', panel).setAttribute('aria-label', `Download ${m.id} ${m.label} model`)
  $('.model-note', panel).textContent = m.note
  $('textarea', panel).value = notes[m.id] || ''
  $('textarea', panel).setAttribute('aria-label', `Notes for ${m.id} ${m.label}`)
  if (viewer.getAttribute('src') !== m.model) {
    $('.viewer-state', panel).hidden = false
    $('.viewer-state', panel).classList.remove('failed')
    $('.viewer-state', panel).textContent = 'Loading model…'
    viewer.setAttribute('poster', m.poster)
    viewer.setAttribute('src', m.model)
    viewer.setAttribute('alt', `${m.id}: ${m.label}. Interactive character model.`)
  }
  camera()
}

function shelf() {
  const grid = $('#studies')
  grid.replaceChildren()
  const current = models.filter(m => m.group === group)
  $('#shelf-title').textContent = `${group} / ${String(current.length).padStart(2, '0')} studies`
  current.forEach(m => {
    const b = document.createElement('button')
    b.className = 'study'
    b.classList.toggle('selected', selected.some(s => s.id === m.id))
    b.setAttribute('aria-label', `${m.id}: ${m.label}. Place in ${active ? 'B' : 'A'}.`)
    const img = document.createElement('img')
    img.src = m.poster; img.alt = `${m.label} three-quarter view`; img.loading = 'lazy'
    const badges = document.createElement('span'); badges.className = 'badges'
    selected.forEach((s, i) => { if (s.id === m.id) { const badge = document.createElement('span'); badge.textContent = i ? 'B' : 'A'; badges.append(badge) } })
    const caption = document.createElement('span'); caption.className = 'caption'
    const code = document.createElement('span'); code.className = 'code'; code.textContent = m.id.toUpperCase()
    const label = document.createElement('strong'); label.textContent = m.label
    caption.append(code, label); b.append(img, badges, caption)
    b.onclick = () => { selected[active] = m; updatePanel(active); shelf() }
    grid.append(b)
  })
}

function chooseGroup(next) {
  group = next
  const current = models.filter(m => m.group === next)
  selected = [current[0], current[group === 'Faces' ? 2 : 1] || current[0]]
  closeup = group === 'Faces' || group === 'Hair'
  document.querySelectorAll('#categories button').forEach(b => {
    b.classList.toggle('selected', b.dataset.group === group)
    b.setAttribute('aria-pressed', String(b.dataset.group === group))
  })
  panels.forEach((_, i) => updatePanel(i)); selectSlot(0); shelf()
}

panels.forEach((panel, i) => {
  $('.slot-button', panel).onclick = () => { selectSlot(i); shelf() }
  const viewer = $('model-viewer', panel)
  viewer.addEventListener('load', () => { $('.viewer-state', panel).hidden = true; camera() })
  viewer.addEventListener('error', () => {
    const state = $('.viewer-state', panel)
    state.hidden = false; state.classList.add('failed')
    state.textContent = '3D preview unavailable. The study images below are still available.'
  })
  $('textarea', panel).addEventListener('input', event => {
    notes[selected[i].id] = event.target.value
    if (selected[0].id === selected[1].id) $('textarea', panels[1 - i]).value = event.target.value
    try { localStorage.setItem(storageKey, JSON.stringify(notes)); $('#save-status').textContent = 'Notes saved in this browser.' }
    catch { $('#save-status').textContent = 'Download feedback to keep your notes.' }
  })
})
new ResizeObserver(() => { if (models.length && selected.length) camera() }).observe($('.comparison'))
document.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { view = b.dataset.view; camera() })
$('#focus').onclick = () => { closeup = !closeup; camera() }
$('#spin').onclick = () => { spinning = !spinning; camera() }
$('#export-notes').onclick = () => {
  const feedback = { batch, saved: new Date().toISOString(), studies: models.filter(m => notes[m.id]?.trim()).map(m => ({ id: m.id, label: m.label, notes: notes[m.id] })) }
  const url = URL.createObjectURL(new Blob([JSON.stringify(feedback, null, 2)], { type: 'application/json' }))
  const a = document.createElement('a'); a.href = url; a.download = `gatorize-${batch}-feedback.json`; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
try {
  const response = await fetch('catalog.json')
  if (!response.ok) throw new Error('Could not load the model catalog.')
  models = await response.json()
  if (!models.length) throw new Error('The batch has not finished building yet.')
  $('#count').textContent = String(models.length).padStart(2, '0')
  for (const category of ['Faces', 'Hair', 'Bodies', 'Clothes']) {
    const count = models.filter(m => m.group === category).length
    if (!count) continue
    const b = document.createElement('button'); b.dataset.group = category
    b.textContent = category
    const number = document.createElement('small'); number.textContent = count
    b.append(number); b.onclick = () => chooseGroup(category); $('#categories').append(b)
  }
  chooseGroup(models[0].group)
} catch (error) {
  $('#error').hidden = false; $('#error').textContent = error.message
}
