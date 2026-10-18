// Local built-page smoke test. Every external request is intercepted; no production access.
// python3 -m http.server 5188 --bind 127.0.0.1 --directory companion/app/dist/client
// node tools/likeness/check_pipeline.mjs
import assert from 'node:assert/strict'
import { chromium } from '../../companion/app/node_modules/playwright-core/index.mjs'
const base = 'http://127.0.0.1:5188'
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM || '/usr/bin/chromium', args: ['--no-sandbox'] })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  const errors = [], unexpected = [], sockets = []
  let mode = 'active', polls = 0
  page.on('pageerror', error => errors.push(error.message))
  page.on('websocket', socket => sockets.push(socket.url()))
  await page.clock.install()
  await page.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url())
    if (url.origin === base) {
      if (url.pathname === '/pipeline') return route.fulfill({ response: await route.fetch({ url: `${base}/pipeline.html` }) })
      return route.continue()
    }
    if (url.origin === 'https://api.gatorcamp.us' && url.pathname === '/pipeline/status') {
      polls++
      assert.equal(request.method(), 'GET')
      assert.equal(request.headers().authorization, undefined)
      assert.equal(request.headers().cookie, undefined)
      if (mode === 'failed') return route.fulfill({ status: 503, body: 'private-error-must-not-render' })
      const observed = await page.evaluate(() => new Date().toISOString())
      return route.fulfill({ json: { observed_at: observed, jobs: mode === 'empty' ? [] : [{
        id: '0123456789ab', state: 'build', step: 'build', elapsed_seconds: 65,
        steps: [{ step: 'spec', seconds: 3, running: false }, { step: 'build', seconds: 62, running: true }],
      }] } })
    }
    unexpected.push(request.url())
    return route.abort()
  })
  await page.goto(`${base}/pipeline`, { waitUntil: 'networkidle' })
  await page.getByRole('heading', { name: 'Processing · build' }).waitFor()
  for (const width of [1440, 1280, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 })
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `overflow at ${width}px`)
  }
  await page.screenshot({ path: '/tmp/sgl-pipeline-mobile.png', fullPage: true })
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.screenshot({ path: '/tmp/sgl-pipeline-desktop.png', fullPage: true })
  mode = 'failed'
  await page.clock.runFor(11_000)
  await page.getByRole('status').filter({ hasText: 'timings are frozen' }).waitFor()
  assert.equal(await page.getByRole('heading', { name: 'Processing · build' }).count(), 1)
  assert.equal((await page.locator('body').innerText()).includes('private-error-must-not-render'), false)
  mode = 'empty'
  await page.clock.runFor(11_000)
  await page.getByRole('heading', { name: 'No jobs yet' }).waitFor()
  await page.getByRole('link', { name: 'Explore the character showcase' }).click()
  await page.getByRole('heading', { name: /Your look/ }).waitFor()
  const previous = polls
  await page.clock.runFor(21_000)
  assert.equal(polls, previous, 'polling must stop after navigation')
  assert.deepEqual(errors, [])
  assert.deepEqual(sockets, [])
  assert.deepEqual(unexpected, [], 'no auth, storage, or other external requests')
  console.log('PASS: public hydration, responsive layout, polling, frozen outage state, recovery, cleanup; no credentials or production requests')
} finally { await browser.close() }
