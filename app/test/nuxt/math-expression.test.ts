import { describe, expect, it } from 'vitest'
import {
  calculateMathExpression,
  createGraphFunction,
  studyFunction,
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

  it('studies a quadratic function in the graph range', () => {
    const study = studyFunction('y = x^2 - 4x + 3')

    expect(study?.yIntercept).toBe(3)
    expect(study?.roots).toHaveLength(2)
    expect(study?.roots[0]).toBeCloseTo(1)
    expect(study?.roots[1]).toBeCloseTo(3)
    expect(study?.extrema).toHaveLength(1)
    expect(study?.extrema[0]).toMatchObject({ kind: 'Tiefpunkt', y: -1 })
    expect(study?.extrema[0]?.x).toBeCloseTo(2)
  })
})
