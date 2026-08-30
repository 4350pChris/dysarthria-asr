import { describe, expect, it } from 'vitest'
import {
  calculateMathExpression,
  createGraphFunction,
  isGraphExpression,
  normalizeMathExpression
} from '~/utils/mathExpression'

describe('math expressions', () => {
  it('calculates recognized math text', () => {
    expect(normalizeMathExpression('√16 + 2²')).toBe('sqrt(16) + 2^2')
    expect(calculateMathExpression('√16 + 2²')).toBe('8')
  })

  it('creates a graph function from an equation', () => {
    expect(isGraphExpression('y = 2x')).toBe(true)
    expect(createGraphFunction('y = 2x + 3')?.(1)).toBe(5)
  })
})
