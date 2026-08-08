const messages: Record<string, string> = {
  missing: 'Dieses Feld darf nicht leer sein.',
  string_too_short: 'Dieses Feld darf nicht leer sein.',
  audio_required: 'Nimm eine Audio-Datei auf.',
  category_exists: 'Diese Kategorie gibt es bereits.',
  category_name_required: 'Gib einen Namen für die Kategorie ein.',
  category_not_found: 'Diese Kategorie gibt es nicht mehr.',
  phrase_exists: 'Dieser Satz ist bereits in dieser Kategorie.',
  phrase_not_found: 'Dieser Satz gibt es nicht mehr.',
  phrase_text_required: 'Gib einen Satz ein.',
  grammar_pattern_exists: 'Diese Vorlage gibt es bereits.',
  grammar_pattern_not_found: 'Diese Vorlage gibt es nicht mehr.',
  grammar_placeholder_invalid: 'Die Vorlage muss den Platzhalter genau einmal enthalten.',
  grammar_template_required: 'Gib eine Vorlage ein.',
  grammar_value_exists: 'Dieser Wert gibt es bereits.',
  grammar_value_not_found: 'Dieser Wert gibt es nicht mehr.',
  grammar_value_required: 'Gib einen Wert ein.',
  training_prompt_not_found: 'Dieser Lesetext gibt es nicht mehr.',
  training_prompts_unavailable: 'Die Lesetexte konnten nicht geladen werden.'
}

export function apiErrorCode(error: unknown) {
  if (!error || typeof error !== 'object' || !('data' in error)) return undefined
  const data = error.data
  if (!data || typeof data !== 'object' || !('detail' in data)) return undefined
  const detail = data.detail
  if (Array.isArray(detail)) {
    const first = detail[0]
    return first && typeof first === 'object' && typeof first.type === 'string' ? first.type : undefined
  }
  if (!detail || typeof detail !== 'object' || !('code' in detail)) return undefined
  return typeof detail.code === 'string' ? detail.code : undefined
}

export function apiFormErrors(error: unknown, fallback: string) {
  if (!error || typeof error !== 'object' || !('data' in error)) return { _form: fallback }
  const data = error.data
  if (!data || typeof data !== 'object' || !('detail' in data) || !Array.isArray(data.detail)) {
    return { _form: fallback }
  }

  const errors: Record<string, string> = {}
  for (const detail of data.detail) {
    if (!detail || typeof detail !== 'object' || !Array.isArray(detail.loc)) continue
    if (detail.loc[0] !== 'body') continue
    const field = detail.loc.at(-1)
    const code = typeof detail.type === 'string' ? detail.type : ''
    if (typeof field === 'string') errors[field] = messages[code] || fallback
  }
  return Object.keys(errors).length ? errors : { _form: fallback }
}

export function apiErrorMessage(error: unknown, fallback: string) {
  return messages[apiErrorCode(error) || ''] || fallback
}
