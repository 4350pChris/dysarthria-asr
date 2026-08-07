from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


WORD = re.compile(r"[\w]+", re.UNICODE)
SENTENCE_END = re.compile(r"[.!?]+(?:\s+|$)")


@dataclass(frozen=True)
class TimedWord:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Clip:
    text: str
    first_word: int
    word_count: int


def normalise(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    return "".join(character for character in value if character.isalnum())


def words(text: str) -> list[str]:
    return WORD.findall(text)


def read_timestamps(path: Path) -> list[TimedWord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("Timestamp JSON has no word segments.")
    return [
        TimedWord(str(segment["text"]), float(segment["start"]), float(segment["end"]))
        for segment in segments
        if str(segment.get("text", "")).strip()
    ]


def anchors(source: list[str], timed: list[TimedWord]) -> list[tuple[int, float]]:
    source_keys = [normalise(word) for word in source]
    timed_keys = [normalise(word.text) for word in timed]
    matcher = difflib.SequenceMatcher(a=source_keys, b=timed_keys, autojunk=False)
    matched: list[tuple[int, float]] = []
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            source_index = block.a + offset
            time = (timed[block.b + offset].start + timed[block.b + offset].end) / 2
            matched.append((source_index, time))
    return matched


def time_at(index: int, source_count: int, points: list[tuple[int, float]]) -> float:
    before = max((point for point in points if point[0] <= index), default=points[0])
    after = min((point for point in points if point[0] >= index), default=points[-1])
    if before[0] == after[0]:
        return before[1]
    fraction = (index - before[0]) / (after[0] - before[0])
    return before[1] + fraction * (after[1] - before[1])


def chunks(text: str, maximum_words: int) -> list[Clip]:
    result: list[Clip] = []
    word_matches = list(WORD.finditer(text))
    sentence_start = 0
    source_index = 0
    sentence_ends = [match.end() for match in SENTENCE_END.finditer(text)]
    if not sentence_ends or sentence_ends[-1] != len(text):
        sentence_ends.append(len(text))

    for sentence_end in sentence_ends:
        sentence_words = [
            match for match in word_matches if sentence_start <= match.start() < sentence_end
        ]
        for start in range(0, len(sentence_words), maximum_words):
            group = sentence_words[start : start + maximum_words]
            if not group:
                continue
            end = sentence_end if start + maximum_words >= len(sentence_words) else group[-1].end()
            result.append(
                Clip(
                    text=text[group[0].start() : end].strip(),
                    first_word=source_index + start,
                    word_count=len(group),
                )
            )
        source_index += len(sentence_words)
        sentence_start = sentence_end
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Make reviewable training-clip timings from exact text and MLX ASR timestamps."
    )
    parser.add_argument("text", type=Path, help="Exact UTF-8 text that was read.")
    parser.add_argument("timestamps", type=Path, help="JSON made by mlx-qwen3-asr --timestamps.")
    parser.add_argument("--output", type=Path, required=True, help="CSV output path.")
    parser.add_argument("--maximum-words", type=int, default=20, help="Maximum source words per clip.")
    arguments = parser.parse_args()

    source_text = arguments.text.read_text(encoding="utf-8").strip()
    source_words = words(source_text)
    timed_words = read_timestamps(arguments.timestamps)
    matched = anchors(source_words, timed_words)
    if not matched:
        raise ValueError("No matching words. Check that the text and audio part belong together.")

    points = [(0, timed_words[0].start), *matched, (len(source_words), timed_words[-1].end)]
    clip_words = chunks(source_text, arguments.maximum_words)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=["clip_id", "text", "start_seconds", "end_seconds", "word_count", "anchor_count", "needs_review"],
        )
        writer.writeheader()
        for clip_id, clip in enumerate(clip_words, start=1):
            start = time_at(clip.first_word, len(source_words), points)
            end = time_at(clip.first_word + clip.word_count, len(source_words), points)
            anchor_count = sum(clip.first_word <= point[0] < clip.first_word + clip.word_count for point in matched)
            writer.writerow(
                {
                    "clip_id": clip_id,
                    "text": clip.text,
                    "start_seconds": f"{start:.2f}",
                    "end_seconds": f"{max(start, end):.2f}",
                    "word_count": clip.word_count,
                    "anchor_count": anchor_count,
                    "needs_review": "yes",
                }
            )
    print(f"Wrote {len(clip_words)} review rows with {len(matched)} exact word anchors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
