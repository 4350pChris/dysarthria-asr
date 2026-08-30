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
    .replace(/[−–—]/gu, '-')
    .replaceAll('×', '*')
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
  if (isEquationExpression(value)) return false

  return /(?:^|[^\p{L}])x(?:$|[^\p{L}])/iu.test(
    normalizeMathExpression(value)
  )
}

export function isEquationExpression(value: string) {
  const expression = normalizeMathExpression(value)
  const parts = expression.split('=')

  return parts.length === 2
    && parts.every(part => part.trim())
    && !/^\s*(?:y|f\s*\(\s*x\s*\))\s*=/iu.test(expression)
    && /(?:^|[^\p{L}])x(?:$|[^\p{L}])/iu.test(expression)
}

function graphExpression(value: string) {
  return normalizeMathExpression(value)
    .replace(/^\s*(?:y|f\s*\(\s*x\s*\))\s*=\s*/iu, '')
}

export function createGraphFunction(value: string) {
  const expression = graphExpression(value)
  if (!expression || expression.includes('=')) return undefined

  try {
    const compiled = math.compile(expression)
    return (x: number) => {
      const result = compiled.evaluate({ x })
      return typeof result === 'number' && Number.isFinite(result) ? result : NaN
    }
  } catch {
    return undefined
  }
}

export type FunctionStudy = {
  derivative: string
  yIntercept?: number
  roots: number[]
  extrema: Array<{
    kind: 'Hochpunkt' | 'Tiefpunkt'
    x: number
    y: number
  }>
}

function rootsOf(fn: (x: number) => number, minimum = -10, maximum = 10) {
  const roots: number[] = []
  const steps = 400
  const step = (maximum - minimum) / steps

  function addRoot(value: number) {
    if (Math.abs(fn(value)) > 0.0001) return
    if (!roots.some(root => Math.abs(root - value) < 0.01)) roots.push(value)
  }

  for (let index = 0; index < steps; index++) {
    const start = minimum + index * step
    const end = start + step
    const startValue = fn(start)
    const endValue = fn(end)

    if (!Number.isFinite(startValue) || !Number.isFinite(endValue)) continue
    if (Math.abs(startValue) < 0.0001) addRoot(start)
    if (startValue * endValue >= 0) continue

    let left = start
    let right = end
    for (let iteration = 0; iteration < 40; iteration++) {
      const middle = (left + right) / 2
      if (fn(left) * fn(middle) <= 0) right = middle
      else left = middle
    }
    addRoot((left + right) / 2)
  }

  return roots.sort((first, second) => first - second)
}

export function studyFunction(value: string, minimum = -10, maximum = 10): FunctionStudy | undefined {
  const expression = graphExpression(value)
  const fn = createGraphFunction(value)
  if (!expression || expression.includes('=') || !fn) return undefined

  try {
    const derivative = math.derivative(expression, 'x').toString()
    const derivativeFunction = createGraphFunction(derivative)
    const secondDerivativeFunction = createGraphFunction(
      math.derivative(derivative, 'x').toString()
    )
    if (!derivativeFunction || !secondDerivativeFunction) return undefined

    const extrema = rootsOf(derivativeFunction, minimum, maximum).reduce<FunctionStudy['extrema']>((points, x) => {
      const curvature = secondDerivativeFunction(x)
      const y = fn(x)
      if (!Number.isFinite(y)) return points
      if (curvature > 0.0001) points.push({ kind: 'Tiefpunkt', x, y })
      if (curvature < -0.0001) points.push({ kind: 'Hochpunkt', x, y })
      return points
    }, [])

    return {
      derivative,
      yIntercept: Number.isFinite(fn(0)) ? fn(0) : undefined,
      roots: rootsOf(fn, minimum, maximum),
      extrema
    }
  } catch {
    return undefined
  }
}

export function formatMathNumber(value: number) {
  return math.format(value, { precision: 6 })
}

export type EquationSolution = {
  kind: 'solutions' | 'none' | 'identity'
  solutions: number[]
  left: string
  right: string
}

export function solveEquation(value: string): EquationSolution | undefined {
  if (!isEquationExpression(value)) return undefined

  const [left, right] = normalizeMathExpression(value).split('=')
  if (!left || !right || !/^[0-9x+\-*/^().\s]+$/u.test(`${left}${right}`)) return undefined

  try {
    const difference = createGraphFunction(`(${left}) - (${right})`)
    if (!difference) return undefined

    const constant = difference(0)
    const quadratic = (difference(1) + difference(-1) - 2 * constant) / 2
    const linear = (difference(1) - difference(-1)) / 2
    const polynomial = (x: number) => quadratic * x ** 2 + linear * x + constant
    const tolerance = 0.000001

    if ([constant, quadratic, linear].some(value => !Number.isFinite(value))) return undefined
    if ([-3, -2, 2, 3].some(x => Math.abs(difference(x) - polynomial(x)) > tolerance)) {
      return undefined
    }

    let solutions: number[] = []
    if (Math.abs(quadratic) < tolerance) {
      if (Math.abs(linear) < tolerance) {
        return {
          kind: Math.abs(constant) < tolerance ? 'identity' : 'none',
          solutions: [],
          left,
          right
        }
      }
      solutions = [-constant / linear]
    } else {
      const discriminant = linear ** 2 - 4 * quadratic * constant
      if (discriminant < -tolerance) {
        return { kind: 'none', solutions: [], left, right }
      }
      if (Math.abs(discriminant) < tolerance) solutions = [-linear / (2 * quadratic)]
      else {
        const root = Math.sqrt(discriminant)
        solutions = [(-linear - root) / (2 * quadratic), (-linear + root) / (2 * quadratic)]
      }
    }

    return {
      kind: 'solutions',
      solutions: solutions.sort((first, second) => first - second),
      left,
      right
    }
  } catch {
    return undefined
  }
}
