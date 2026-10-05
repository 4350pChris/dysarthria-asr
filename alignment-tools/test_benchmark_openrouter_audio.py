import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import benchmark_openrouter_audio as benchmark


class AudioTrialTests(unittest.TestCase):
    def test_audio_request_and_response(self):
        body = {"choices": [{"finish_reason": "stop", "message": {"content": " Hallo Welt. "}}], "usage": {"cost": 0.001}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.wav"
            path.write_bytes(b"audio bytes")
            with patch.object(benchmark, "urlopen", return_value=io.BytesIO(json.dumps(body).encode())) as send:
                self.assertEqual(benchmark.transcribe(path, "test-key", benchmark.MODEL), ("Hallo Welt.", {"cost": 0.001}))
            request = send.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
            self.assertEqual(payload["model"], "google/gemini-2.5-flash")
            self.assertEqual(payload["provider"], {"data_collection": "deny"})
            audio = payload["messages"][0]["content"][1]["input_audio"]
            self.assertEqual(audio["format"], "wav")
            self.assertEqual(base64.b64decode(audio["data"]), b"audio bytes")
            body["choices"][0]["finish_reason"] = "length"
            with patch.object(benchmark, "urlopen", return_value=io.BytesIO(json.dumps(body).encode())):
                with self.assertRaises(ValueError):
                    benchmark.transcribe(path, "test-key", benchmark.MODEL)

    def test_weighted_metrics(self):
        rows = [
            {"expected_transcript": "eins zwei drei", "predicted_transcript": "eins zwei", "transcription_seconds": 1},
            {"expected_transcript": "vier", "predicted_transcript": "vier", "transcription_seconds": 2},
        ]
        result = benchmark.score(rows)
        self.assertEqual(result["word_error_rate"], 0.25)
        self.assertEqual(result["total_transcription_seconds"], 3)


if __name__ == "__main__":
    unittest.main()
