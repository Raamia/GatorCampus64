import type { ModelViewerElement } from '@google/model-viewer'

export const defaultPalette = { skin: '#f1ae88', hair: '#352e2e', shirt: '#f9694a', pants: '#3e5b6c', shoes: '#fffffc' }
export type Palette = Partial<typeof defaultPalette>
export type PalettePart = keyof Palette
export const paletteParts: { key: PalettePart; label: string; swatches: string[] }[] = [
  { key: 'skin', label: 'Skin tone', swatches: ['#f6d5ba', '#f1ae88', '#c88b62', '#99603d', '#6b402b', '#40271e'] },
  { key: 'hair', label: 'Hair color', swatches: ['#211c1a', '#513224', '#a66b39', '#d7b46c', '#a3482e', '#d2d0cc'] },
  { key: 'shirt', label: 'Top color', swatches: ['#f9694a', '#fa4616', '#0021a5', '#458b60', '#fff6e5', '#282c37'] },
  { key: 'pants', label: 'Bottoms color', swatches: ['#3e5b6c', '#253b60', '#b59975', '#537052', '#ece5d9', '#292a31'] },
  { key: 'shoes', label: 'Shoes color', swatches: ['#fffffc', '#292a31', '#83533c', '#0021a5', '#fa4616', '#9a415e'] },
]

export function materialPart(name: string): PalettePart | undefined {
  if (/^Browser (Skin|Gloves) \(/.test(name)) return 'skin'
  if (/^Browser Hair \(/.test(name)) return 'hair'
  if (/^Browser Shirt \(/.test(name)) return 'shirt'
  if (/^Browser Pants \(/.test(name)) return 'pants'
  if (/^Browser (Shoes|Shoe Soles) \(/.test(name)) return 'shoes'
}

// Face images contain baked skin behind the eyes/lips. Recolor only that
// background; multiplying the entire image would tint eye whites and lips.
export function recolorFace(source: Uint8ClampedArray, hex: string): Uint8ClampedArray<ArrayBuffer> {
  const out = new Uint8ClampedArray(source)
  const rgb = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16))
  for (let i = 0; i < out.length; i += 4) {
    if ([0, 1, 2].every(c => Math.abs(source[i + c] - source[c]) <= 2)) {
      for (let c = 0; c < 3; c++) out[i + c] = rgb[c]
    }
  }
  return out
}

export async function preparePalette(viewer: ModelViewerElement) {
  const materials = viewer.model?.materials ?? []
  const originals = new Map(materials.map(m => [m, [...m.pbrMetallicRoughness.baseColorFactor] as [number, number, number, number]]))
  const faces = await Promise.all(materials.filter(m => /^Browser (Open Eyes|Mouth) \(SKIN\)$/.test(m.name)).map(async material => {
    const original = material.pbrMetallicRoughness.baseColorTexture.texture
    if (!original) throw new Error('Face texture unavailable')
    const width = material.name.includes('Eyes') ? 64 : 32, height = width / 2
    const uri = await original.source.createThumbnail(width, height)
    const image = new Image()
    try {
      image.src = uri
      await image.decode()
      const texture = viewer.createCanvasTexture()
      // Preserve clamped UVs: repeating the face atlas repeats eyes and lips.
      const sampler = texture.sampler, sourceSampler = original.sampler
      sampler.setWrapS(sourceSampler.wrapS); sampler.setWrapT(sourceSampler.wrapT)
      sampler.setMinFilter(sourceSampler.minFilter); sampler.setMagFilter(sourceSampler.magFilter)
      const canvas = texture.source.element as HTMLCanvasElement
      canvas.width = width; canvas.height = height
      const context = canvas.getContext('2d')
      if (!context) throw new Error('Color preview unavailable')
      // GPU thumbnails are read bottom-up; canvas textures expect top-down pixels.
      context.translate(0, height); context.scale(1, -1)
      context.drawImage(image, 0, 0, width, height)
      context.resetTransform()
      const pixels = context.getImageData(0, 0, width, height)
      return { material, original, texture, context, pixels }
    } finally { URL.revokeObjectURL(uri) }
  }))
  return (palette: Palette | null) => {
    for (const material of materials) {
      const part = materialPart(material.name)
      if (part) material.pbrMetallicRoughness.setBaseColorFactor(palette?.[part] ?? originals.get(material)!)
    }
    for (const face of faces) {
      if (palette?.skin) {
        face.context.putImageData(new ImageData(recolorFace(face.pixels.data, palette.skin), face.pixels.width, face.pixels.height), 0, 0)
        face.texture.source.update()
      }
      face.material.pbrMetallicRoughness.baseColorTexture.setTexture(palette?.skin ? face.texture : face.original)
    }
  }
}
