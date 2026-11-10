import re
from typing import Literal

JUNIOR_SIGNALS = {
    "junior", "trainee", "praktikant", "praktikplats", "lärling", "nybörjare",
    "nyexaminerad", "nyutexaminerad", "entry level", "lia", "praktik",
    "internship", "lärande i arbete",
    "praktik under utbildning", "pågående utbildning",
    "examensarbete", "exjobb", "exjobbet",
    "i början av din karriär", "i början av karriären",
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

# "praktik" is Swedish for both "internship" AND "practice" (as opposed to
# theory) — "mellan strategi och praktik" / "från teori till praktik" is a
# common business idiom with nothing to do with internships, and kept
# false-positiving LIA-unrelated ads (e.g. a public-sector "erfaren
# systemutvecklare" posting) just for using it.
_PRAKTIK_IDIOM_PATTERN = re.compile(
    r"(?:strategi|teori)\s+(?:och|till)\s+praktik",
    re.IGNORECASE,
)

# How much of the description to trust alongside the title before falling
# back to a full-text scan — long enough to catch an opening framing
# sentence like "We are looking for a Senior X to ...", short enough to
# usually stay clear of an unrelated "mentor junior colleagues" bullet
# further down in the requirements.
_LEAD_TEXT_CHARS = 250


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


def _signals_in(text: str) -> tuple[bool, bool]:
    text = _PRAKTIK_IDIOM_PATTERN.sub(" ", text)
    return bool(_JUNIOR_PATTERN.search(text)), bool(_SENIOR_PATTERN.search(text))


SearchMode = Literal["lia", "junior", "senior"]


def score_seniority(title: str, description: str = "", mode: SearchMode = "lia") -> float:
    """Return 0–100 relevance for the given search mode.

    mode="lia"/"junior": 100=junior/LIA signal, 10=senior signal, 50=neutral. Junior wins on tie.
    mode="senior": mirrored — 100=senior signal, 10=junior/LIA signal, 50=neutral. Senior wins on tie.

    Resolved in three tiers, each trusted only if it unambiguously says
    junior-or-senior (not both, not neither):
    1. The job title alone — the ad's own explicit level claim, e.g.
       "Senior Fullstack-utvecklare".
    2. Title + the first stretch of the description — catches ads whose
       structured title is generic (e.g. "AI Engineer") but which open
       with "We are looking for a Senior Machine Learning Engineer...".
    3. The full text, where an explicit years-of-experience requirement
       then overrides a bare junior/LIA keyword — the common false
       positive of a senior ad that mentions "utöver praktik och
       internships" or "mentor junior engineers" deep in the body.
    """
    title = title or ""
    description = description or ""

    junior_hit, senior_hit = _signals_in(title)
    if junior_hit == senior_hit:  # ambiguous (both) or no signal (neither) — title alone doesn't decide
        junior_hit, senior_hit = _signals_in(f"{title} {description[:_LEAD_TEXT_CHARS]}")
        if junior_hit == senior_hit:
            junior_hit, senior_hit = _signals_in(f"{title} {description}")

        # An explicit years-of-experience requirement anywhere in the ad
        # outranks a bare junior/LIA keyword found via tier 2 or 3 — it
        # never overrides tier 1 (an explicit title claim is authoritative).
        full_text = f"{title} {description}"
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
