"""Local language screening; short ambiguous Latin text is treated as English."""

import unicodedata

from langdetect import DetectorFactory, LangDetectException, detect_langs

DetectorFactory.seed = 0


def requires_translation(text: str) -> bool:
    # Mathematical symbols and common Greek units are not a language switch.
    if any(
        char.isalpha()
        and "LATIN" not in unicodedata.name(char, "")
        and char not in "μΔΣθλ"
        for char in text
    ):
        return True
    # Tiny identifiers, names, units and greetings cannot be reliably language-classified.
    if sum(char.isalpha() for char in text) < 20 or len(text.split()) < 4:
        return False
    try:
        languages = detect_langs(text)
    except LangDetectException:
        return False
    return bool(languages and languages[0].lang != "en" and languages[0].prob >= 0.9)
