// Browser acceptance checks against the running, localhost-only review gallery.
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import { chromium } from '../../companion/app/node_modules/playwright-core/index.mjs'

const partial = process.argv.includes('--partial')
const baseURL = process.env.GALLERY_URL || 'http://127.0.0.1:5174/'
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROMIUM || '/usr/bin/chromium',
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
})
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } })
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(baseURL, { waitUntil: 'networkidle' })
  async function ready() {
    await page.waitForFunction(() => [...document.querySelectorAll('model-viewer')].every(v => v.loaded))
    await page.locator('model-viewer').evaluateAll(viewers => viewers.forEach(v => v.jumpCameraToGoal()))
  }
  await ready()
  assert.equal(await page.locator('#error').isVisible(), false)
  if (!partial) {
    assert.equal(await page.locator('#count').textContent(), '23')
    for (const [category, count] of [['Faces', 6], ['Hair', 8], ['Bodies', 5], ['Clothes', 4]]) {
      await page.locator(`#categories [data-group="${category}"]`).click()
      await ready()
      assert.equal(await page.locator('.study').count(), count)
      await page.locator('.slot-button[data-slot="1"]').click()
      await page.locator('.study').last().click()
      await ready()
      assert.equal(await page.locator('.panel[data-slot="1"] h2').textContent(), await page.locator('.study strong').last().textContent())
      await page.locator('[data-view="side"]').click()
      assert.match(await page.locator('model-viewer').first().getAttribute('camera-orbit'), /^90deg/)
      await page.locator('[data-view="front"]').click()
      await page.locator('#focus').click()
      await page.locator('#focus').click()
      await page.locator('#spin').click()
      assert.equal(await page.locator('#spin').getAttribute('aria-pressed'), 'true')
      await page.locator('#spin').click()
      const artifact = await page.request.get(new URL(await page.locator('.download').first().getAttribute('href'), baseURL).href)
      assert.equal(artifact.status(), 200)
      assert.equal((await artifact.body()).subarray(0, 4).toString(), 'glTF')
      console.log(`PASS ${category}: selection, GLB loading, camera, rotation and download`)
    }
    await page.locator('#categories [data-group="Faces"]').click()
    await ready()
    await page.locator('textarea').first().fill('Acceptance check: face silhouette feedback')
    await page.reload({ waitUntil: 'networkidle' }); await ready()
    assert.equal(await page.locator('textarea').first().inputValue(), 'Acceptance check: face silhouette feedback')
    const downloadPromise = page.waitForEvent('download')
    await page.locator('#export-notes').click()
    const download = await downloadPromise
    const feedback = JSON.parse(await fs.readFile(await download.path(), 'utf8'))
    assert.equal(feedback.studies[0].id, 'f01')
    assert.match(feedback.studies[0].notes, /silhouette feedback/)
    await page.locator('textarea').first().fill('')
    console.log('PASS notes: persist across reload and export with correct model ID')
  }
  await page.locator('[data-view="quarter"]').click()
  await ready()
  await page.screenshot({ path: '/tmp/sgl-likeness-gallery.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await ready()
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
  await page.screenshot({ path: '/tmp/sgl-likeness-gallery-mobile.png', fullPage: true })
  assert.deepEqual(errors, [])
  console.log('PASS desktop/mobile layouts, rendered models and no JavaScript errors')
} finally {
  await browser.close()
}
