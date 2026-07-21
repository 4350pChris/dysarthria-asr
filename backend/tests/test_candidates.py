from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app import create_app
from src import database
from src.audio_samples import create_audio_sample
from src.candidates import candidate_suggestions, read_generated_candidates
from src.speech_attempts import create_speech_attempt, read_speech_attempts


class CandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        database.DATA_DIR = Path(self.tmp.name)
        database.DB_FILE = Path(self.tmp.name) / "app.sqlite"
        database.init_db()

    def test_generated_candidates_rank_and_attempts_save_training_label(self) -> None:
        generated = read_generated_candidates()
        self.assertTrue(any(item["text"] == "Ich möchte Kaffee." for item in generated))
        self.assertTrue(any(item["text"] == "Wo ist meine Brille?" for item in generated))
        self.assertTrue(any(item["text"] == "Ich muss zur Toilette." for item in generated))
        self.assertTrue(any(item["text"] == "Mir ist kalt." for item in generated))
        self.assertTrue(any(item["text"] == "Ich habe Schmerzen am Kopf." for item in generated))
        self.assertTrue(any(item["text"] == "Ich habe Schmerzen in der Hand." for item in generated))
        self.assertTrue(any(item["text"] == "Mein Bauch tut weh." for item in generated))
        self.assertTrue(any(item["text"] == "Meine Hand tut weh." for item in generated))
        self.assertTrue(any(item["text"] == "Hilf mir bitte beim Aufstehen." for item in generated))
        self.assertFalse(any(item["text"] == "Hilf mir bitte beim raus." for item in generated))
        self.assertFalse(any(item["text"] == "Wo ist meine Medikamente?" for item in generated))
        self.assertFalse(any(item["text"] == "Mir geht es zu laut." for item in generated))
        self.assertFalse(any(item["text"] == "Ich habe Schmerzen in der Kopf." for item in generated))
        self.assertFalse(any(item["text"] == "Ich habe Schmerzen am Hand." for item in generated))
        self.assertFalse(any(item["text"] == "Meine Bauch tut weh." for item in generated))
        self.assertFalse(any(item["text"] == "Mein Hand tut weh." for item in generated))
        self.assertFalse(any(item["text"] == "Ich möchte jetzt." for item in generated))
        self.assertFalse(any(item["text"] == "Ich brauche kurz später." for item in generated))
        self.assertLess(len(generated), 250)

        suggestions = candidate_suggestions("ich möchte kaffee")
        self.assertGreaterEqual(len(suggestions), 5)
        self.assertTrue(suggestions[0]["id"])

        audio_id = uuid4().hex
        create_audio_sample(audio_id, "data/audio/test.webm", "audio/webm")
        create_speech_attempt(
            audio_id=audio_id,
            raw_transcript="ich möchte kaffee",
            target_text="Ich möchte Kaffee.",
            selected_candidate_id=suggestions[0]["id"],
            selected_candidate_source=suggestions[0]["source"],
            suggested_candidate_id=suggestions[0]["id"],
            suggested_text=suggestions[0]["text"],
            suggestion_score=str(suggestions[0]["score"]),
        )

        attempts = read_speech_attempts()
        self.assertEqual(attempts[0]["audio_id"], audio_id)
        self.assertEqual(attempts[0]["target_text"], "Ich möchte Kaffee.")

    def test_generated_candidates_endpoint(self) -> None:
        response = TestClient(create_app()).get("/api/candidates/generated")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item["text"] == "Ich möchte Kaffee." for item in response.json()))


if __name__ == "__main__":
    unittest.main()
