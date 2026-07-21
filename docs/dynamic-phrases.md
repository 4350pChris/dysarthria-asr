# Dynamic Phrase Variants

The current phrase list treats every phrase as one fixed sentence.

Example:

```text
010 Ich brauche Wasser.
```

For real use, several spoken forms may mean the same thing:

```text
Ich brauche Wasser.
Ich möchte Wasser.
Wasser bitte.
Ich will Wasser.
```

The better model is:

```text
intent -> variants -> canonical output
```

Example:

```text
intent_id: need_water
canonical_text: Ich brauche Wasser.
variants:
- Ich brauche Wasser.
- Ich möchte Wasser.
- Wasser bitte.
- Ich will Wasser.
```

Fuzzy matching would compare raw ASR against all variants, but return the
canonical output.

Example:

```text
raw ASR: Ich möchte Wasser
matched variant: Ich möchte Wasser.
canonical output: Ich brauche Wasser.
```

## Why This Helps

- Handles natural ways to say the same thing.
- Keeps the app output consistent and easy to read.
- Avoids fine-tuning for simple wording variation.
- Still works with the existing fuzzy matching approach.

## Possible Data Shape

One simple CSV shape:

```csv
intent_id,phrase_number,category,canonical_text,variant_text
need_water,010,requests,Ich brauche Wasser.,Ich brauche Wasser.
need_water,010,requests,Ich brauche Wasser.,Ich möchte Wasser.
need_water,010,requests,Ich brauche Wasser.,Wasser bitte.
need_water,010,requests,Ich brauche Wasser.,Ich will Wasser.
```

The matcher searches `variant_text`, but suggestions show and save
`canonical_text`.

## Risks

Too many variants can increase ambiguity.

Example:

```text
Ich möchte raus.
Ich möchte nach Hause.
Ich möchte nach draußen.
```

These phrases are already similar. Adding very short variants like `raus bitte`
may make matching less precise.

Mitigation:

- Keep top-3 suggestions.
- Require confirmation before speaking.
- Add variants only for real wording patterns or known ASR outputs.
- Measure top-1 and top-3 accuracy after adding variants.

## When To Add This

Add this after collecting a little more real audio, once we know which wording
variants matter. Technically it is straightforward and does not require a model
change.
