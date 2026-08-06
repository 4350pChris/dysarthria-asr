import { describe, expect, it } from 'vitest'
import { apiErrorCode, apiErrorMessage } from '~/utils/apiError'

describe('apiErrorMessage', () => {
  it('returns a German message for an API error code', () => {
    const error = { data: { detail: { code: 'phrase_exists' } } }

    expect(apiErrorMessage(error, 'Fallback')).toBe('Dieser Satz ist bereits in dieser Kategorie.')
    expect(apiErrorCode(error)).toBe('phrase_exists')
  })

  it('returns the fallback for an unknown error', () => {
    expect(apiErrorMessage(new Error('Network error'), 'Fallback')).toBe('Fallback')
  })
})
