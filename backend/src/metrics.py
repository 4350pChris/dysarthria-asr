from .text import normalize_text


def error_rate(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 0.0 if not actual else 1.0
    row = list(range(len(actual) + 1))
    for index, value in enumerate(expected, start=1):
        next_row = [index]
        for actual_index, actual_value in enumerate(actual, start=1):
            next_row.append(min(row[actual_index] + 1, next_row[-1] + 1, row[actual_index - 1] + (value != actual_value)))
        row = next_row
    return row[-1] / len(expected)


def transcription_metrics(expected: str, actual: str) -> tuple[float, float]:
    expected_text = normalize_text(expected)
    actual_text = normalize_text(actual)
    return error_rate(expected_text.split(), actual_text.split()), error_rate(list(expected_text), list(actual_text))
