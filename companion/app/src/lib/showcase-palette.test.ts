import { expect, it } from 'vitest'
import { materialPart, recolorFace } from './showcase-palette'

it('changes baked facial skin without tinting eyes, lips, or modifying the source', () => {
  const original = new Uint8ClampedArray([241, 174, 136, 255, 255, 255, 255, 255, 140, 58, 60, 255, 240, 175, 136, 255])
  const result = recolorFace(original, '#40271e')
  expect([...result]).toEqual([64, 39, 30, 255, 255, 255, 255, 255, 140, 58, 60, 255, 64, 39, 30, 255])
  expect([...original.slice(0, 4)]).toEqual([241, 174, 136, 255])
})

it('treats bare hands as skin and leaves textured facial features out of solid recoloring', () => {
  expect(materialPart('Browser Gloves (GLOVES)')).toBe('skin')
  expect(materialPart('Browser Open Eyes (SKIN)')).toBeUndefined()
  expect(materialPart('Browser Mouth (SKIN)')).toBeUndefined()
  expect(materialPart('Browser Shoe Soles (SHOES)')).toBe('shoes')
})
