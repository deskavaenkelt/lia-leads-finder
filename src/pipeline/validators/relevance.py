import re

from models import LeadProfile

TECH_SCORE_MINIMUM = 10.0

# Job titles that are exclusively academic (PhD/postdoc/teaching) positions at
# a university — they routinely mention "examensarbete", "internutbildning",
# "handledning" etc. as generic department boilerplate (supervising *other*
# students' theses, in-house training the candidate has *given*), which
# false-positives them as junior/LIA-friendly. They require academic
# qualifications a YH-praktikant search has no business surfacing.
ACADEMIC_ONLY_TITLES = {
    "doktorand", "postdoktor", "postdoc", "docent", "professor",
    "universitetslektor", "adjunkt", "universitetsadjunkt", "amanuens",
}
_ACADEMIC_TITLE_PATTERN = re.compile(
    r"(?<!\w)(?:" + "|".join(re.escape(s) for s in ACADEMIC_ONLY_TITLES) + r")(?!\w)",
    re.IGNORECASE,
)


def _is_academic_only_position(job_title: str) -> bool:
    return bool(_ACADEMIC_TITLE_PATTERN.search(job_title))


def is_relevant(profile: LeadProfile) -> bool:
    """True if tech match is above minimum threshold and it isn't an
    academic-only (PhD/postdoc/teaching) position."""
    if profile.job_title and _is_academic_only_position(profile.job_title):
        return False
    return profile.score_breakdown.tech_match >= TECH_SCORE_MINIMUM
