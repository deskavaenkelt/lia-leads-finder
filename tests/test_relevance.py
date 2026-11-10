from models import ContactInfo, LeadProfile, ScoreBreakdown
from pipeline.validators.relevance import is_relevant
from pipeline.quality_gate import compute_score, assign_tier


def _make_profile(tech_score: float, job_title: str | None = None) -> LeadProfile:
    bd = ScoreBreakdown(
        tech_match=tech_score, geo=100, contact=0, activity=80, stability=50, seniority=50
    )
    score = compute_score(bd)
    return LeadProfile(
        company_name="Test AB",
        city="Göteborg",
        job_title=job_title,
        tech_tags=[],
        contact=ContactInfo(),
        score=score,
        score_breakdown=bd,
        match_reason="test",
        tier=assign_tier(score),
    )


def test_high_tech_score_is_relevant():
    assert is_relevant(_make_profile(70)) is True


def test_zero_tech_score_is_not_relevant():
    assert is_relevant(_make_profile(0)) is False


def test_threshold_boundary():
    # Profiles with tech_score >= 10 are relevant
    assert is_relevant(_make_profile(10)) is True
    assert is_relevant(_make_profile(9)) is False


# --- academic-only positions (found via a real-ad audit: PhD/adjunct ads
# routinely mention "examensarbete"/"internutbildning" as department
# boilerplate, which false-positived them into LIA/junior results despite
# requiring academic qualifications, not being industry openings) ---

def test_doktorand_position_is_not_relevant():
    profile = _make_profile(70, job_title="Doktorand inom fotofysik av 2D kvantmaterial")
    assert is_relevant(profile) is False

def test_postdoktor_position_is_not_relevant():
    profile = _make_profile(70, job_title="Postdoktor i sexuell selektion och epidemiologi")
    assert is_relevant(profile) is False

def test_universitetsadjunkt_position_is_not_relevant():
    profile = _make_profile(70, job_title="Tidsbegränsad universitetsadjunkt i gränssnittsprogrammering")
    assert is_relevant(profile) is False

def test_amanuens_position_is_not_relevant():
    profile = _make_profile(70, job_title="Amanuens")
    assert is_relevant(profile) is False

def test_normal_industry_title_is_unaffected():
    profile = _make_profile(70, job_title="Backend-utvecklare till fintech-bolag")
    assert is_relevant(profile) is True

def test_no_job_title_falls_back_to_tech_score():
    assert is_relevant(_make_profile(70, job_title=None)) is True
    assert is_relevant(_make_profile(0, job_title=None)) is False
