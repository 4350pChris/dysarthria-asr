from __future__ import annotations

import csv
import sqlite3

from .paths import DATA_DIR, DB_FILE, PHRASES_FILE, SEED_PHRASES_FILE

GRAMMAR_SEED = {
    "thing_acc": {
        "patterns": [
            "Ich will {thing_acc}.",
            "Ich möchte {thing_acc}.",
            "Ich brauche {thing_acc}.",
            "Gib mir bitte {thing_acc}.",
        ],
        "values": [
            "Wasser",
            "Kaffee",
            "Tee",
            "Saft",
            "etwas zu essen",
            "meine Medikamente",
            "meine Brille",
            "mein Handy",
            "meine Kopfhörer",
            "meine Tasche",
            "Papier",
            "einen Stift",
            "eine Decke",
            "ein Kissen",
            "die Fernbedienung",
            "mein Ladegerät",
            "den Rollstuhl",
        ],
    },
    "thing_nom": {
        "patterns": ["Wo ist {thing_nom}?"],
        "values": [
            "das Wasser",
            "der Kaffee",
            "der Tee",
            "der Saft",
            "meine Brille",
            "mein Handy",
            "meine Tasche",
            "das Papier",
            "der Stift",
            "die Decke",
            "das Kissen",
            "die Fernbedienung",
            "mein Ladegerät",
            "der Rollstuhl",
        ],
    },
    "verb_inf": {
        "patterns": ["Ich möchte {verb_inf}.", "Ich kann nicht {verb_inf}."],
        "values": [
            "schlafen",
            "mich hinlegen",
            "aufstehen",
            "sitzen",
            "liegen",
            "duschen",
            "mich waschen",
            "mich umziehen",
            "essen",
            "trinken",
            "reden",
            "allein sein",
            "lesen",
            "fernsehen",
            "Musik hören",
        ],
    },
    "activity_nom": {
        "patterns": ["Hilf mir bitte beim {activity_nom}.", "Ich brauche Hilfe beim {activity_nom}."],
        "values": [
            "Aufstehen",
            "Hinlegen",
            "Sitzen",
            "Liegen",
            "Duschen",
            "Waschen",
            "Umziehen",
            "Essen",
            "Trinken",
            "Lesen",
        ],
    },
    "destination": {
        "patterns": ["Ich möchte {destination}.", "Ich muss {destination}.", "Bring mich bitte {destination}."],
        "values": ["zur Toilette", "raus", "nach draußen", "nach Hause", "ins Bett", "zurück"],
    },
    "state_mir_ist": {
        "patterns": ["Mir ist {state_mir_ist}."],
        "values": ["kalt", "warm", "schlecht", "schwindelig", "übel"],
    },
    "state_wellbeing": {
        "patterns": ["Mir geht es {state_wellbeing}."],
        "values": ["gut", "schlecht", "besser", "schlimmer"],
    },
    "symptom_acc": {
        "patterns": ["Ich habe {symptom_acc}."],
        "values": [
            "Schmerzen",
            "Kopfschmerzen",
            "Bauchschmerzen",
            "Halsschmerzen",
            "Rückenschmerzen",
            "Durst",
            "Hunger",
            "Angst",
            "Übelkeit",
            "Atemnot",
            "Schwindel",
        ],
    },
    "body_part_am": {
        "patterns": ["Ich habe Schmerzen am {body_part_am}."],
        "values": ["Kopf", "Bauch", "Rücken", "Hals", "Arm", "Bein", "Fuß"],
    },
    "body_part_fem_dat": {
        "patterns": ["Ich habe Schmerzen in der {body_part_fem_dat}."],
        "values": ["Hand", "Schulter", "Brust"],
    },
    "body_part_poss_masc": {
        "patterns": ["Mein {body_part_poss_masc} tut weh."],
        "values": ["Kopf", "Bauch", "Rücken", "Hals", "Arm", "Fuß"],
    },
    "body_part_poss_neut": {
        "patterns": ["Mein {body_part_poss_neut} tut weh."],
        "values": ["Bein"],
    },
    "body_part_poss_fem": {
        "patterns": ["Meine {body_part_poss_fem} tut weh."],
        "values": ["Hand", "Schulter", "Brust"],
    },
}




class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        self.close()


def connect_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_FILE, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with connect_db() as db:
        reset_db(db)
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS phrases (
                id INTEGER PRIMARY KEY,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                text TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS audio_samples (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS speech_attempts (
                id INTEGER PRIMARY KEY,
                audio_id TEXT NOT NULL REFERENCES audio_samples(id),
                raw_transcript TEXT NOT NULL DEFAULT '',
                target_text TEXT NOT NULL,
                selected_candidate_id TEXT NOT NULL DEFAULT '',
                selected_candidate_source TEXT NOT NULL DEFAULT '',
                suggested_candidate_id TEXT NOT NULL DEFAULT '',
                suggested_text TEXT NOT NULL DEFAULT '',
                suggestion_score REAL,
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS grammar_slots (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS grammar_patterns (
                id INTEGER PRIMARY KEY,
                slot_id INTEGER NOT NULL REFERENCES grammar_slots(id),
                template TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS grammar_slot_values (
                id INTEGER PRIMARY KEY,
                slot_id INTEGER NOT NULL REFERENCES grammar_slots(id),
                value TEXT NOT NULL
            )
            """
        )
        seed_grammar(db)
        seed_file = PHRASES_FILE if PHRASES_FILE.exists() else SEED_PHRASES_FILE
        if not seed_file.exists():
            return
        with seed_file.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                category = row["category"].strip()
                text = row["text"].strip()
                db.execute(
                    "INSERT OR IGNORE INTO categories (name) VALUES (?)",
                    (category,),
                )
                category_id = db.execute("SELECT id FROM categories WHERE name = ?", (category,)).fetchone()[0]
                db.execute(
                    "INSERT INTO phrases (category_id, text) VALUES (?, ?)",
                    (category_id, text),
                )


def reset_db(db: sqlite3.Connection) -> None:
    for table in [
        "speech_attempts",
        "audio_samples",
        "grammar_slot_values",
        "grammar_patterns",
        "grammar_slots",
        "phrases",
        "categories",
    ]:
        db.execute(f"DROP TABLE IF EXISTS {table}")


def seed_grammar(db: sqlite3.Connection) -> None:
    for slot_name, data in GRAMMAR_SEED.items():
        cursor = db.execute(
            "INSERT INTO grammar_slots (name) VALUES (?)",
            (slot_name,),
        )
        slot_id = cursor.lastrowid
        for template in data["patterns"]:
            db.execute(
                "INSERT INTO grammar_patterns (slot_id, template) VALUES (?, ?)",
                (slot_id, template),
            )
        for value in data["values"]:
            db.execute(
                "INSERT INTO grammar_slot_values (slot_id, value) VALUES (?, ?)",
                (slot_id, value),
            )
