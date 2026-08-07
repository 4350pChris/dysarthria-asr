from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrainingPrompt:
    id: str
    topic: str
    text: str
    source: str


# These are original, short German practice passages. Keeping the corpus in the
# application avoids scraping, copyright uncertainty, and network dependence.
PROMPTS = (
    TrainingPrompt("alltag-01", "Alltag", "Am Morgen öffne ich das Fenster und höre die Vögel im Garten.", "App-Korpus, Originaltext"),
    TrainingPrompt("alltag-02", "Alltag", "Nach dem Frühstück räume ich die Tasse in die Küche.", "App-Korpus, Originaltext"),
    TrainingPrompt("alltag-03", "Alltag", "Heute möchte ich in Ruhe ein paar Seiten lesen.", "App-Korpus, Originaltext"),
    TrainingPrompt("alltag-04", "Alltag", "Am Nachmittag trinken wir zusammen Kaffee und sprechen über den Tag.", "App-Korpus, Originaltext"),
    TrainingPrompt("natur-01", "Natur", "Nach einem warmen Regen riecht die Luft frisch und klar.", "App-Korpus, Originaltext"),
    TrainingPrompt("natur-02", "Natur", "Auf dem Weg zum Park liegen gelbe Blätter auf dem Boden.", "App-Korpus, Originaltext"),
    TrainingPrompt("natur-03", "Natur", "Ein leichter Wind bewegt die Zweige vor dem Fenster.", "App-Korpus, Originaltext"),
    TrainingPrompt("natur-04", "Natur", "Im Sommer bleiben die Abende lange hell und angenehm.", "App-Korpus, Originaltext"),
    TrainingPrompt("wissen-01", "Wissen", "Ein gutes Buch kann neue Fragen stellen und neugierig machen.", "App-Korpus, Originaltext"),
    TrainingPrompt("wissen-02", "Wissen", "Viele Erfindungen beginnen mit einer einfachen Beobachtung.", "App-Korpus, Originaltext"),
    TrainingPrompt("wissen-03", "Wissen", "Wer genau zuhört, entdeckt oft kleine Unterschiede im Gespräch.", "App-Korpus, Originaltext"),
    TrainingPrompt("wissen-04", "Wissen", "Eine Karte hilft uns, Wege zu finden und Orte zu vergleichen.", "App-Korpus, Originaltext"),
)


def topics() -> list[str]:
    return sorted({prompt.topic for prompt in PROMPTS})


def prompts_for_topic(topic: str) -> list[TrainingPrompt]:
    return [prompt for prompt in PROMPTS if prompt.topic == topic]


def prompt_by_id(prompt_id: str) -> TrainingPrompt | None:
    return next((prompt for prompt in PROMPTS if prompt.id == prompt_id), None)
