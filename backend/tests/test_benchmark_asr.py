from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pytest

from scripts.benchmark_asr import DatasetItem, character_metrics, extract_archive, load_dataset, word_metrics


def test_word_metrics_ignore_case_and_punctuation() -> None:
    errors, words = word_metrics("Kaffee, bitte!", "kaffee bitte")

    assert errors == 0
    assert words == 2


def test_character_metrics_counts_substitutions() -> None:
    errors, characters = character_metrics("Haus", "Maus")

    assert errors == 1
    assert characters == 4


def test_load_dataset_reads_audio_paths_from_training_labels(tmp_path: Path) -> None:
    audio_path = tmp_path / "data" / "audio" / "one.ogg"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"audio")
    labels = io.StringIO()
    writer = csv.DictWriter(labels, fieldnames=["audio_id", "audio_file", "source", "transcript"])
    writer.writeheader()
    writer.writerow(
        {
            "audio_id": "one",
            "audio_file": "data/audio/one.ogg",
            "source": "app_recording",
            "transcript": "Kaffee bitte.",
        }
    )
    (tmp_path / "training-labels.csv").write_text(labels.getvalue())

    assert load_dataset(tmp_path) == [
        DatasetItem(
            audio_id="one",
            audio_file="data/audio/one.ogg",
            source="app_recording",
            transcript="Kaffee bitte.",
        )
    ]


def test_extract_archive_rejects_unsafe_path(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.txt", "unsafe")

    with pytest.raises(ValueError, match="unsafe path"):
        extract_archive(archive_path, tmp_path / "output")
