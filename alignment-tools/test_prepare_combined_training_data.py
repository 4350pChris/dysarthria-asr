import unittest
import csv
import tempfile
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import prepare_combined_training_data as builder
from prepare_combined_training_data import aligned_clips, prepare_items, split_name


class SplitNameTest(unittest.TestCase):
    def test_groups_are_stable_and_text_based(self) -> None:
        self.assertEqual(split_name("Hallo, Welt!"), split_name("hallo welt"))
        self.assertEqual({split_name(str(number)) for number in range(100)}, {"train", "validation", "test"})


class AlignedClipsTest(unittest.TestCase):
    def test_five_minutes_keep_every_word_and_punctuation(self) -> None:
        text = " ".join(f"Wort{index}," for index in range(100))
        timed = [SimpleNamespace(text=f"Wort{index}", start_time=index * 3 + .2, end_time=index * 3 + 2.5) for index in range(100)]
        clips = aligned_clips(text, timed, 300)
        self.assertGreater(len(clips), 1)
        self.assertEqual(" ".join(clip[2] for clip in clips), text)
        self.assertTrue(all(0 <= start < end <= 300 and end - start <= 25 for start, end, _ in clips))
        self.assertTrue(all(left[1] <= right[0] for left, right in zip(clips, clips[1:])))

    def test_rejects_missing_words_and_bad_times(self) -> None:
        for timed in [
            [],
            [SimpleNamespace(text="anderes", start_time=0, end_time=1)],
            [SimpleNamespace(text="Hallo", start_time=2, end_time=1)],
            [SimpleNamespace(text="Hallo", start_time=0, end_time=float("nan"))],
            [SimpleNamespace(text="Hallo", start_time=0, end_time=40)],
        ]:
            with self.subTest(timed=timed), self.assertRaises(ValueError):
                aligned_clips("Hallo!", timed, 40)

    def test_keeps_punctuation_only_tokens(self) -> None:
        timed = [SimpleNamespace(text="Hallo", start_time=.2, end_time=1), SimpleNamespace(text="Welt", start_time=2, end_time=3)]
        self.assertEqual(aligned_clips("„ Hallo — Welt !", timed, 4)[0][2], "„ Hallo — Welt !")

    def test_keeps_hyphens_and_numbers(self) -> None:
        timed = [SimpleNamespace(text="EMail", start_time=.2, end_time=1), SimpleNamespace(text="125", start_time=2, end_time=3)]
        self.assertEqual(aligned_clips("E-Mail 1,25!", timed, 4)[0][2], "E-Mail 1,25!")


def write_audio(path: Path, seconds: int, sample_rate: int = 16_000) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(b"\0\0" * sample_rate * seconds)


class PreparationTest(unittest.TestCase):
    def test_download_command_writes_all_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "source.wav"
            write_audio(source, 1)
            texts = {}
            for number in range(100):
                text = f"Hallo {number}"
                texts.setdefault(split_name(text), text)
            items = [(split, source, "app_recording", text) for split, text in texts.items()]
            dataset = root / "current"
            with patch.object(builder, "OUTPUT_DIR", dataset), \
                 patch.object(builder, "download_app_zip"), \
                 patch.object(builder, "app_items", return_value=items), \
                 patch.object(builder, "reading_items", return_value=[]), \
                 patch.object(builder, "load_aligner", side_effect=AssertionError("Short clips need no model")), \
                 patch("sys.argv", ["prepare_combined_training_data.py"]):
                self.assertEqual(builder.main(), 0)
            with (dataset / "split.csv").open() as output:
                rows = list(csv.DictReader(output))
            self.assertEqual({row["split"] for row in rows}, {"train", "validation", "test"})
            self.assertEqual((dataset / "excluded-recordings.csv").read_text().strip(), "audio_id,reason")
            self.assertTrue((dataset / "training-labels.csv").is_file())

    def test_cuts_real_wav_and_keeps_source_split(self) -> None:
        import soundfile as sf

        timed = [SimpleNamespace(text="Hallo", start_time=.2, end_time=10), SimpleNamespace(text="Welt", start_time=21, end_time=30)]
        aligner = SimpleNamespace(align=lambda **kwargs: [timed])
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "source.wav"
            write_audio(source, 31, 8_000)
            with patch.object(builder, "load_aligner", return_value=aligner):
                labels, splits, excluded = prepare_items([("app-long", source, "app_recording", "Hallo, Welt!")], root / "dataset")
            self.assertEqual([row["transcript"] for row in labels], ["Hallo,", "Welt!"])
            self.assertEqual({row["split"] for row in splits}, {split_name("Hallo, Welt!")})
            self.assertEqual(excluded, [])
            for row in labels:
                info = sf.info(root / "dataset" / row["audio_file"])
                self.assertEqual((info.samplerate, info.channels), (16_000, 1))
                self.assertLessEqual(info.duration, 25)
            self.assertFalse((root / "dataset/data/audio/app-long.wav").exists())

    def test_excludes_bad_alignment_and_over_five_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "source.wav"
            longer = root / "longer.wav"
            write_audio(source, 31)
            write_audio(longer, 301)
            aligner = SimpleNamespace(align=lambda **kwargs: [[]])
            with patch.object(builder, "load_aligner", return_value=aligner):
                labels, splits, excluded = prepare_items([
                    ("bad", source, "app_recording", "Hallo"),
                    ("longer", longer, "app_recording", "Hallo"),
                ], root / "dataset")
            self.assertEqual((labels, splits), ([], []))
            self.assertEqual([row["audio_id"] for row in excluded], ["bad", "longer"])
            self.assertEqual(list((root / "dataset/data/audio").iterdir()), [])

    def test_failed_build_keeps_previous_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            dataset = root / "current"
            dataset.mkdir()
            marker = dataset / "split.csv"
            marker.write_text("old dataset")
            source = root / "source.wav"
            write_audio(source, 31)
            with patch.object(builder, "OUTPUT_DIR", dataset), \
                 patch.object(builder, "download_app_zip"), \
                 patch.object(builder, "app_items", return_value=[("long", source, "app_recording", "Hallo")]), \
                 patch.object(builder, "reading_items", return_value=[]), \
                 patch.object(builder, "load_aligner", side_effect=RuntimeError("model unavailable")), \
                 patch("sys.argv", ["prepare_combined_training_data.py", "--replace"]):
                with self.assertRaisesRegex(RuntimeError, "model unavailable"):
                    builder.main()
            self.assertEqual(marker.read_text(), "old dataset")


class WhisperInputTest(unittest.TestCase):
    def test_rejects_long_or_wrong_sample_rate_before_training(self) -> None:
        import modal_train_whisper_lora as training

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for seconds, rate in [(31, 16_000), (1, 8_000), (0, 16_000)]:
                with self.subTest(seconds=seconds, rate=rate):
                    write_audio(root / "clip.wav", seconds, rate)
                    rows = [{"split": "train", "audio_file": "clip.wav", "transcript": "Hallo", "audio_id": "clip"}]
                    with patch.object(training, "REMOTE_DATASET_DIR", root), patch.object(training, "read_split_rows", return_value=rows):
                        with self.assertRaisesRegex(ValueError, "at most 30 seconds"):
                            training.read_split()

    def test_accepts_thirty_seconds(self) -> None:
        import modal_train_whisper_lora as training

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            write_audio(root / "clip.wav", 30)
            rows = [{"split": split, "audio_file": "clip.wav", "transcript": "Hallo", "audio_id": split} for split in ("train", "validation")]
            with patch.object(training, "REMOTE_DATASET_DIR", root), patch.object(training, "read_split_rows", return_value=rows):
                train, validation = training.read_split()
            self.assertEqual((len(train), len(validation)), (1, 1))


if __name__ == "__main__":
    unittest.main()
