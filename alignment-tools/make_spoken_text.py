from __future__ import annotations

import argparse
import re
from pathlib import Path


REPLACEMENTS = (
    (re.compile(r"\bDr\.\s*B\."), "Doktor B."),
    (re.compile(r"\bvgl\.\s*S\."), "vergleiche Seite"),
)


def spoken_text(text: str) -> str:
    for pattern, replacement in REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create editable spoken-text files from the original reading text."
    )
    parser.add_argument("text", type=Path, nargs="+", help="Original part text files.")
    parser.add_argument("--output-dir", type=Path, default=Path("spoken"))
    parser.add_argument("--force", action="store_true", help="Replace existing spoken-text files.")
    arguments = parser.parse_args()

    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    for source in arguments.text:
        destination = arguments.output_dir / source.name
        if destination.exists() and not arguments.force:
            raise FileExistsError(f"{destination} already exists. Review it, or use --force.")
        destination.write_text(spoken_text(source.read_text(encoding="utf-8")), encoding="utf-8")
        print(f"Wrote {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
