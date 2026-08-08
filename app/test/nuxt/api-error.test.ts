import { describe, expect, it } from 'vitest'
import { apiErrorCode, apiErrorMessage, apiFormErrors } from '~/utils/apiError'

describe('apiErrorMessage', () => {
  it('returns a German message for an API error code', () => {
    const error = { data: { detail: { code: 'phrase_exists' } } }

    expect(apiErrorMessage(error, 'Fallback')).toBe('Dieser Satz ist bereits in dieser Kategorie.')
    expect(apiErrorCode(error)).toBe('phrase_exists')
  })

  it('returns the fallback for an unknown error', () => {
    expect(apiErrorMessage(new Error('Network error'), 'Fallback')).toBe('Fallback')
  })

  it('maps training field errors to German form messages', () => {
    const error = { data: { detail: [{ loc: ['body', 'prompt_id'], type: 'training_prompt_not_found' }] } }

    expect(apiFormErrors(error, 'Fallback')).toEqual({ prompt_id: 'Dieser Lesetext gibt es nicht mehr.' })
  })
})
