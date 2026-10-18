// Run against the built companion's static dist/client directory; no auth plane is needed.
// SHOWCASE_URL=http://127.0.0.1:5175 node tools/likeness/check_showcase.mjs
import assert from 'node:assert/strict'
import { chromium } from '../../companion/app/node_modules/playwright-core/index.mjs'

const base = process.env.SHOWCASE_URL || 'http://127.0.0.1:5175'
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM || '/usr/bin/chromium',
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
try {
  const page = await browser.newPage({ viewport: { width: 1365, height: 1000 } })
  const api = [], sockets = [], models = [], errors = []
  page.on('request', request => {
    if (new URL(request.url()).pathname.startsWith('/api/')) api.push(request.url())
    if (request.url().endsWith('.glb')) models.push(request.url())
  })
  page.on('websocket', socket => sockets.push(socket.url()))
  page.on('pageerror', error => errors.push(error.message))
  // Python's static server lacks Cloudflare's clean-URL HTML resolution.
  // Keep the real route in the browser so hydration and client routing run.
  await page.route(`${base}/showcase`, async route => {
    const response = await route.fetch({ url: `${base}/showcase.html` })
    await route.fulfill({ response })
  })
  await page.goto(`${base}/showcase`, { waitUntil: 'networkidle' })
  assert.equal(await page.locator('.showcase-card').count(), 8)
  assert.equal(models.length, 0, '3D assets must not load before requested')
  await page.getByRole('button', { name: 'Explore in 3D', exact: true }).click()
  const ready = () => page.waitForFunction(() => document.querySelector('model-viewer')?.loaded === true)
  await ready()
  for (const [category, count] of [['Faces', 6], ['Hair', 8], ['Bodies', 5], ['Clothes', 4]]) {
    await page.getByRole('group', { name: 'Character category' }).getByRole('button', { name: new RegExp(`^${category}`) }).click()
    await ready()
    assert.equal(await page.locator('.showcase-card').count(), count)
    await page.locator('.showcase-card').last().click()
    await ready()
    await page.getByRole('button', { name: 'Back', exact: true }).click()
    assert.match(await page.locator('model-viewer').getAttribute('camera-orbit'), /^180deg/)
    console.log(`PASS ${category}: selection, actual GLB load and camera`)
  }
  await page.getByRole('group', { name: 'Character category' }).getByRole('button', { name: /^Hair/ }).click()
  await page.getByRole('button', { name: 'View Curly fade', exact: true }).click()
  await ready()
  await page.getByRole('button', { name: 'Front', exact: true }).click()
  await page.locator('model-viewer').evaluate(model => {
    model.cameraOrbit = '90deg 85deg 1m'
    model.resetTurntableRotation(1)
  })
  await page.getByRole('button', { name: 'Front', exact: true }).click()
  await page.waitForFunction(() => {
    const model = document.querySelector('model-viewer')
    return Math.abs(model.getCameraOrbit().theta) < 0.01 && model.turntableRotation === 0
  })
  await page.getByRole('button', { name: 'Three-quarter', exact: true }).click()
  await page.screenshot({ path: '/tmp/sgl-showcase-desktop.png', fullPage: true })
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 })
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `overflow at ${width}px`)
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: '/tmp/sgl-showcase-mobile.png', fullPage: true })
  assert.deepEqual(api, [], 'public showcase must not call app APIs')
  assert.deepEqual(sockets, [], 'public showcase must not open database sockets')
  assert.deepEqual(errors, [])
  await page.route('**/*.glb', route => route.abort())
  await page.reload({ waitUntil: 'networkidle' })
  await page.getByRole('button', { name: 'Explore in 3D', exact: true }).click()
  await page.getByRole('status').filter({ hasText: '3D isn’t available' }).waitFor()
  assert.equal(await page.locator('.showcase-poster').evaluate(image => image.complete && image.naturalWidth > 0), true)
  await page.getByRole('group', { name: 'Character category' }).getByRole('button', { name: /^Bodies/ }).click()
  assert.equal(await page.locator('.showcase-card').count(), 5)
  console.log('PASS no-login/no-API contract, lazy 3D, mobile layouts and usable image fallback')
} finally { await browser.close() }
