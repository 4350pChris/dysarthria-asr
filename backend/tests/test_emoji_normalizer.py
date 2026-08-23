from src.emoji_normalizer import emoji_from_spoken_name, replace_spoken_emojis


def test_finds_a_complete_german_emoji_name() -> None:
    assert emoji_from_spoken_name("weißes Herz") == ("🤍", "weißes Herz")


def test_does_not_find_an_emoji_in_a_sentence() -> None:
    assert emoji_from_spoken_name("Ich sende weißes Herz") is None


def test_replaces_german_cldr_emoji_name_with_marker() -> None:
    assert replace_spoken_emojis("weißes Herz emoji") == "🤍"


def test_replaces_only_the_named_part_of_a_sentence() -> None:
    assert replace_spoken_emojis("Ich sende weißes Herz emoji heute.") == "Ich sende 🤍 heute."


def test_keeps_regular_text_without_marker() -> None:
    assert replace_spoken_emojis("Das weiße Herz ist schön.") == "Das weiße Herz ist schön."


def test_accepts_the_german_plural_marker() -> None:
    assert replace_spoken_emojis("Daumen hoch emojis") == "👍"
