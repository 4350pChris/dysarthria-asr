import { all, create } from 'mathjs'

const math = create(all!)

math.import({
  import: () => { throw new Error('Nicht erlaubt.') },
  createUnit: () => { throw new Error('Nicht erlaubt.') },
  reviver: () => { throw new Error('Nicht erlaubt.') }
}, { override: true })

export function normalizeMathExpression(value: string) {
  return value
    .replace(/√\s*([\w.]+)/gu, 'sqrt($1)')
    .replaceAll('²', '^2')
    .replaceAll('π', 'pi')
    .replace(/(\d),(\d)/gu, '$1.$2')
    .trim()
}

export function calculateMathExpression(value: string) {
  const expression = normalizeMathExpression(value)
  if (!expression || expression.includes('=') || /\bx\b/iu.test(expression)) {
    return undefined
  }

  const result = math.evaluate(expression)
  if (typeof result !== 'number' || !Number.isFinite(result)) return undefined
  return math.format(result, { precision: 14 })
}

export function isGraphExpression(value: string) {
  return /(?:^|[^\p{L}])x(?:$|[^\p{L}])/iu.test(
    normalizeMathExpression(value)
  )
}

export function createGraphFunction(value: string) {
  const expression = normalizeMathExpression(value)
    .replace(/^\s*(?:y|f\s*\(\s*x\s*\))\s*=\s*/iu, '')
  if (!expression || expression.includes('=')) return undefined

  const compiled = math.compile(expression)
  return (x: number) => {
    const result = compiled.evaluate({ x })
    return typeof result === 'number' && Number.isFinite(result) ? result : NaN
  }
}
