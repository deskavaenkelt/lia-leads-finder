import re
from typing import Literal

JUNIOR_SIGNALS = {
    "junior", "trainee", "praktikant", "lärling", "nybörjare",
    "nyexaminerad", "nyutexaminerad", "entry level", "lia", "praktik",
    "internship", "internutbildning", "lärande i arbete",
    "praktik under utbildning", "pågående utbildning",
}
SENIOR_SIGNALS = {
    "senior", "lead", "principal", "architect", "arkitekt",
    "erfaren", "expert", "staff",
}


def _compile(signals: set[str]) -> re.Pattern:
    return re.compile(
        r"(?<!\w)(?:" + "|".join(re.escape(s) for s in signals) + r")(?!\w)",
        re.IGNORECASE,
    )


_JUNIOR_PATTERN = _compile(JUNIOR_SIGNALS)
_SENIOR_PATTERN = _compile(SENIOR_SIGNALS)


SearchMode = Literal["lia", "junior", "senior"]


def score_seniority(text: str, mode: SearchMode = "lia") -> float:
    """Return 0–100 relevance for the given search mode.

    mode="lia"/"junior": 100=junior/LIA signal, 10=senior signal, 50=neutral. Junior wins on tie.
    mode="senior": mirrored — 100=senior signal, 10=junior/LIA signal, 50=neutral. Senior wins on tie.
    """
    junior_hit = bool(_JUNIOR_PATTERN.search(text))
    senior_hit = bool(_SENIOR_PATTERN.search(text))

    if mode == "senior":
        if senior_hit:
            return 100.0
        if junior_hit:
            return 10.0
        return 50.0

    if junior_hit:
        return 100.0
    if senior_hit:
        return 10.0
    return 50.0
