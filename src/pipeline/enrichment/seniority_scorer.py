import re
from typing import Literal

JUNIOR_SIGNALS = {
    "junior", "trainee", "praktikant", "lärling", "nybörjare",
    "nyexaminerad", "nyutexaminerad", "entry level", "lia", "praktik",
    "internship", "internutbildning", "lärande i arbete",
    "praktik under utbildning", "pågående utbildning",
    "examensarbete", "exjobb", "exjobbet",
}
SENIOR_SIGNALS = {
    "senior", "lead", "principal", "architect", "arkitekt",
    "erfaren", "expert", "staff",
}

# An explicit "N+ years experience" requirement is a stronger, more precise
# senior signal than a bare keyword — e.g. an ad requiring "5 års
# arbetslivserfarenhet (utöver praktik och internships)" should not score as
# LIA-friendly just because it mentions "praktik" in passing.
_EXPERIENCE_YEARS_PATTERN = re.compile(
    r"\d+\+?\s*(?:års?|years?)\s*(?:av\s+|of\s+)?(?:arbetslivs)?(?:erfarenhet|experience)",
    re.IGNORECASE,
)
_SENIOR_EXPERIENCE_THRESHOLD_YEARS = 3


def _compile(signals: set[str]) -> re.Pattern:
    return re.compile(
        r"(?<!\w)(?:" + "|".join(re.escape(s) for s in signals) + r")(?!\w)",
        re.IGNORECASE,
    )


_JUNIOR_PATTERN = _compile(JUNIOR_SIGNALS)
_SENIOR_PATTERN = _compile(SENIOR_SIGNALS)


def _has_senior_experience_requirement(text: str) -> bool:
    for match in re.finditer(r"\d+", text):
        years_match = _EXPERIENCE_YEARS_PATTERN.match(text, match.start())
        if years_match and int(match.group()) >= _SENIOR_EXPERIENCE_THRESHOLD_YEARS:
            return True
    return False


SearchMode = Literal["lia", "junior", "senior"]


def score_seniority(title: str, description: str = "", mode: SearchMode = "lia") -> float:
    """Return 0–100 relevance for the given search mode.

    mode="lia"/"junior": 100=junior/LIA signal, 10=senior signal, 50=neutral. Junior wins on tie.
    mode="senior": mirrored — 100=senior signal, 10=junior/LIA signal, 50=neutral. Senior wins on tie.

    The job title is trusted first (it's the ad's own explicit level claim,
    e.g. "Senior Fullstack-utvecklare"). Only when the title itself doesn't
    unambiguously say junior-or-senior do we fall back to scanning the full
    text — where an explicit years-of-experience requirement then overrides
    a bare junior/LIA keyword (common false positive: a senior ad that
    mentions "utöver praktik och internships" or "mentor junior engineers").
    """
    title = title or ""
    description = description or ""

    title_junior = bool(_JUNIOR_PATTERN.search(title))
    title_senior = bool(_SENIOR_PATTERN.search(title))

    if title_junior and not title_senior:
        junior_hit, senior_hit = True, False
    elif title_senior and not title_junior:
        junior_hit, senior_hit = False, True
    else:
        full_text = f"{title} {description}"
        junior_hit = bool(_JUNIOR_PATTERN.search(full_text))
        senior_hit = bool(_SENIOR_PATTERN.search(full_text))
        if junior_hit and not senior_hit and _has_senior_experience_requirement(full_text):
            junior_hit, senior_hit = False, True

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
