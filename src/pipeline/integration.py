from models import CompanyRaw, ContactInfo, LeadProfile, ScoreBreakdown, SearchConfig
from pipeline.enrichment.activity_scorer import score_activity
from pipeline.enrichment.tech_analyzer import analyze_tech
from pipeline.enrichment.geo_scorer import score_geo, score_geo_async
from pipeline.enrichment.seniority_scorer import score_seniority
from pipeline.enrichment.contact_finder import find_contact, find_contact_from_api
from pipeline.enrichment.stability_scorer import score_stability
from pipeline.enrichment.company_api import fetch_company
from pipeline.quality_gate import assign_tier, compute_score

_STABILITY_SCORE_DEFAULT = 0.0


def _assemble(
    company: CompanyRaw,
    config: SearchConfig,
    contact_info: ContactInfo,
    contact_score: float,
    stability: float = _STABILITY_SCORE_DEFAULT,
    geo_score: float | None = None,
    registration_date: str | None = None,
    employee_range: str | None = None,
    is_active: bool | None = None,
    org_number: str | None = None,
) -> LeadProfile:
    analysis_text = " ".join(filter(None, [company.job_title, company.description]))
    tech_score = analyze_tech(config.tech_stack, analysis_text)
    if geo_score is None:
        geo_score = score_geo(company.city, config.city, config.all_sweden)
    seniority_score = score_seniority(company.job_title or "", company.description or "")
    breakdown = ScoreBreakdown(
        tech_match=tech_score,
        geo=geo_score,
        contact=contact_score,
        activity=score_activity(company.publication_date),
        stability=stability,
        seniority=seniority_score,
    )
    score = compute_score(breakdown)
    tier = assign_tier(score)
    matched = [t for t in config.tech_stack if t.lower() in analysis_text.lower()]
    reason_parts = [f"Matchar {', '.join(matched)}"] if matched else []
    if geo_score == 100.0:
        reason_parts.append(company.city)
    elif config.all_sweden:
        reason_parts.append("Hela Sverige")
    return LeadProfile(
        company_name=company.name,
        org_number=org_number,
        website=company.website,
        city=company.city,
        source=company.source,
        job_title=company.job_title,
        job_url=company.job_url,
        publication_date=company.publication_date,
        tech_tags=[t.lower() for t in config.tech_stack if t.lower() in analysis_text.lower()],
        contact=contact_info,
        score=score,
        score_breakdown=breakdown,
        match_reason=", ".join(reason_parts) or "Generell matchning",
        tier=tier,
        registration_date=registration_date,
        employee_range=employee_range,
        is_active=is_active,
    )


def build_profile(company: CompanyRaw, config: SearchConfig) -> LeadProfile:
    """Sync build — contact defaults to 0.0."""
    return _assemble(company, config, ContactInfo(), 0.0)


async def build_profile_fast(
    company: CompanyRaw,
    config: SearchConfig,
    center_coords: tuple[float, float] | None = None,
) -> LeadProfile:
    """Pass 1: no external API calls. stability=50, contact=empty. Used for initial ranking."""
    geo_score = await score_geo_async(
        company.city, config.city, config.all_sweden, center_coords, config.radius_km
    )
    return _assemble(company, config, ContactInfo(), 0.0, stability=50.0, geo_score=geo_score)


async def build_profile_async(
    company: CompanyRaw,
    config: SearchConfig,
    center_coords: tuple[float, float] | None = None,
) -> LeadProfile:
    """Async build — enriches via company APIs (cached) then falls back to scraping."""
    import asyncio
    api_data, geo_score = await asyncio.gather(
        fetch_company(company.name, company.city),
        score_geo_async(company.city, config.city, config.all_sweden, center_coords, config.radius_km),
    )

    # Stability: use API data (financial health or age)
    stability = await score_stability(company.name, company.city)

    # Contact: prefer API data, fall back to website scraping
    api_contact = await find_contact_from_api(api_data.website, api_data.linkedin)
    if api_contact:
        contact_info, contact_score = api_contact
    else:
        website = api_data.website or company.website
        contact_info, contact_score = await find_contact(website)

    return _assemble(
        company, config, contact_info, contact_score, stability, geo_score,
        registration_date=api_data.registration_date,
        employee_range=_employee_range(api_data.employee_score),
        is_active=api_data.is_active,
        org_number=api_data.org_number,
    )


def _employee_range(score: float | None) -> str | None:
    if score is None:
        return None
    return {20.0: "1–4", 60.0: "5–19", 85.0: "20–49", 95.0: "50–249"}.get(score, "250+")
