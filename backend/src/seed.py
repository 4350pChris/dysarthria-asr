from __future__ import annotations

import csv

from sqlmodel import Session, col, select

from .models import Category, GrammarPattern, GrammarSlot, GrammarSlotValue, Phrase
from .paths import PHRASES_FILE, SEED_PHRASES_FILE

GRAMMAR_SEED = {
    "thing_acc": {"patterns": ["Ich will {thing_acc}.", "Ich möchte {thing_acc}.", "Ich brauche {thing_acc}.", "Gib mir bitte {thing_acc}."], "values": ["Wasser", "Kaffee", "Tee", "Saft", "etwas zu essen", "meine Medikamente", "meine Brille", "mein Handy", "meine Kopfhörer", "meine Tasche", "Papier", "einen Stift", "eine Decke", "ein Kissen", "die Fernbedienung", "mein Ladegerät", "den Rollstuhl"]},
    "thing_nom": {"patterns": ["Wo ist {thing_nom}?"], "values": ["das Wasser", "der Kaffee", "der Tee", "der Saft", "meine Brille", "mein Handy", "meine Tasche", "das Papier", "der Stift", "die Decke", "das Kissen", "die Fernbedienung", "mein Ladegerät", "der Rollstuhl"]},
    "verb_inf": {"patterns": ["Ich möchte {verb_inf}.", "Ich kann nicht {verb_inf}."], "values": ["schlafen", "mich hinlegen", "aufstehen", "sitzen", "liegen", "duschen", "mich waschen", "mich umziehen", "essen", "trinken", "reden", "allein sein", "lesen", "fernsehen", "Musik hören"]},
    "activity_nom": {"patterns": ["Hilf mir bitte beim {activity_nom}.", "Ich brauche Hilfe beim {activity_nom}."], "values": ["Aufstehen", "Hinlegen", "Sitzen", "Liegen", "Duschen", "Waschen", "Umziehen", "Essen", "Trinken", "Lesen"]},
    "destination": {"patterns": ["Ich möchte {destination}.", "Ich muss {destination}.", "Bring mich bitte {destination}."], "values": ["zur Toilette", "raus", "nach draußen", "nach Hause", "ins Bett", "zurück"]},
    "state_mir_ist": {"patterns": ["Mir ist {state_mir_ist}."], "values": ["kalt", "warm", "schlecht", "schwindelig", "übel"]},
    "state_wellbeing": {"patterns": ["Mir geht es {state_wellbeing}."], "values": ["gut", "schlecht", "besser", "schlimmer"]},
    "symptom_acc": {"patterns": ["Ich habe {symptom_acc}."], "values": ["Schmerzen", "Kopfschmerzen", "Bauchschmerzen", "Halsschmerzen", "Rückenschmerzen", "Durst", "Hunger", "Angst", "Übelkeit", "Atemnot", "Schwindel"]},
    "body_part_am": {"patterns": ["Ich habe Schmerzen am {body_part_am}."], "values": ["Kopf", "Bauch", "Rücken", "Hals", "Arm", "Bein", "Fuß"]},
    "body_part_fem_dat": {"patterns": ["Ich habe Schmerzen in der {body_part_fem_dat}."], "values": ["Hand", "Schulter", "Brust"]},
    "body_part_poss_masc": {"patterns": ["Mein {body_part_poss_masc} tut weh."], "values": ["Kopf", "Bauch", "Rücken", "Hals", "Arm", "Fuß"]},
    "body_part_poss_neut": {"patterns": ["Mein {body_part_poss_neut} tut weh."], "values": ["Bein"]},
    "body_part_poss_fem": {"patterns": ["Meine {body_part_poss_fem} tut weh."], "values": ["Hand", "Schulter", "Brust"]},
}


def seed_database(session: Session) -> None:
    for name, data in GRAMMAR_SEED.items():
        slot = session.exec(select(GrammarSlot).where(col(GrammarSlot.name) == name)).first()
        if slot is None:
            slot = GrammarSlot(name=name)
            session.add(slot)
            session.flush()
        for template in data["patterns"]:
            if not session.exec(select(GrammarPattern).where(col(GrammarPattern.slot_id) == slot.id, col(GrammarPattern.template) == template)).first():
                session.add(GrammarPattern(slot_id=slot.id, template=template))
        for value in data["values"]:
            if not session.exec(select(GrammarSlotValue).where(col(GrammarSlotValue.slot_id) == slot.id, col(GrammarSlotValue.value) == value)).first():
                session.add(GrammarSlotValue(slot_id=slot.id, value=value))
    seed_file = PHRASES_FILE if PHRASES_FILE.exists() else SEED_PHRASES_FILE
    if not seed_file.exists():
        return
    for row in csv.DictReader(seed_file.open(newline="", encoding="utf-8")):
        name, text = row["category"].strip(), row["text"].strip()
        category = session.exec(select(Category).where(col(Category.name) == name)).first()
        if category is None:
            category = Category(name=name)
            session.add(category)
            session.flush()
        if not session.exec(select(Phrase).where(col(Phrase.category_id) == category.id, col(Phrase.text) == text)).first():
            session.add(Phrase(category_id=category.id, text=text))
