import logging
from itertools import combinations

import httpx

from models import CompanyRaw
from pipeline.enrichment.geocoder import geocode

logger = logging.getLogger(__name__)

AF_SEARCH_URL = "https://jobsearch.api.jobtechdev.se/search"
HEADERS = {"Accept": "application/json"}
PAGE_SIZE = 10


def _split_sticky_terms(query_parts: list[str]) -> tuple[list[str], list[str]]:
    """Split query terms into droppable (plain) and sticky ("+required" /
    "-excluded") terms. AF's search natively understands a leading "-" as
    exclusion (confirmed: "systemutvecklare -java" measurably drops
    java-related ads) — a "+" prefix doesn't appear to change anything
    but is accepted the same way for anyone used to Google-style syntax.
    Sticky terms are modifiers, not independent topics: the fallback/merge
    logic below must never drop them or treat them as their own
    standalone single-term search."""
    sticky = [t for t in query_parts if t.startswith(("+", "-"))]
    droppable = [t for t in query_parts if not t.startswith(("+", "-"))]
    return droppable, sticky


def _candidate_query_tiers(droppable: list[str]) -> list[list[list[str]]]:
    """Tiers of candidate subsets over the droppable terms only, largest
    first: the full set, then each subset with one term dropped, ..., down
    to each term alone as the last tier.

    A single rare/narrow term (e.g. a long Swedish compound word AF's search
    doesn't decompose, like "Yrkeshögskolelärare") can silently zero out an
    otherwise good combined query. Subsets are tried dropping one term at a
    time (favoring dropping the last term first) before reaching single
    terms, so scrape_af can fall back instead of just returning nothing.
    """
    n = len(droppable)
    if n == 0:
        return [[[]]]
    tiers = [[list(droppable)]]
    for size in range(n - 1, 0, -1):
        tiers.append([[droppable[i] for i in combo] for combo in combinations(range(n), size)])
    return tiers


_MIN_RESULTS_THRESHOLD = 5


async def scrape_af(
    tech_stack: list[str], city: str, all_sweden: bool = False,
    radius_km: int = 0, limit: int = 100,
) -> tuple[list[CompanyRaw], int]:
    """Search Arbetsförmedlingen JobSearch API. Returns (companies, total_hits).

    Supports Google-style "+required"/"-excluded" prefixes on any term (AF's
    own search understands "-excluded" natively; see _split_sticky_terms).

    Falls back to smaller subsets of the plain (non-prefixed) search terms
    if the full combination returns fewer than _MIN_RESULTS_THRESHOLD hits
    (see _candidate_query_tiers) — +/- terms are always kept in every
    attempt. If it comes down to single terms that never worked combined
    (e.g. "java" and "lärare" essentially never co-occur), merges each
    term's own results instead of arbitrarily picking whichever term the
    caller happened to list first — see _merged_single_term_results.
    Returns the best subset seen if nothing clears the threshold (e.g.
    tech_stack has only one droppable term, or every subset is genuinely
    narrow)."""
    query_parts = tech_stack[:3]
    droppable, sticky = _split_sticky_terms(query_parts)
    tiers = _candidate_query_tiers(droppable)

    best_result: tuple[list[CompanyRaw], int] | None = None
    for tier_index, tier in enumerate(tiers):
        is_single_term_tier = (
            tier_index == len(tiers) - 1
            and len(droppable) > 1
            and all(len(candidate) == 1 for candidate in tier)
        )
        if is_single_term_tier:
            single_term_candidates = [candidate + sticky for candidate in tier]
            return await _merged_single_term_results(single_term_candidates, city, all_sweden, radius_km, limit)

        for candidate in tier:
            companies, total = await _search_af(candidate + sticky, city, all_sweden, radius_km, limit)
            if best_result is None or total > best_result[1]:
                best_result = (companies, total)
            if total >= _MIN_RESULTS_THRESHOLD:
                return companies, total
    return best_result


async def _merged_single_term_results(
    single_term_candidates: list[list[str]], city: str, all_sweden: bool, radius_km: int, limit: int,
) -> tuple[list[CompanyRaw], int]:
    """Query each term independently and merge the results (deduped by
    job_url, falling back to name+title), summing each term's reported hit
    count. Used only when no multi-term combination reached the results
    threshold — picking just one term's results at that point would hide
    equally relevant ads under whichever term wasn't chosen.

    Each term gets an even share of `limit` (rather than fetching `limit`
    per term and truncating the merged list afterward) — otherwise
    whichever term happened to be queried first would still dominate the
    final list even after the total-hits count became order-independent.
    """
    per_term_limit = max(1, limit // len(single_term_candidates))
    merged: list[CompanyRaw] = []
    seen: set[str] = set()
    total = 0
    for candidate in single_term_candidates:
        companies, term_total = await _search_af(candidate, city, all_sweden, radius_km, per_term_limit)
        total += term_total
        for company in companies:
            key = company.job_url or f"{company.name}|{company.job_title}"
            if key not in seen:
                seen.add(key)
                merged.append(company)
    return merged, total


async def _search_af(
    query_parts: list[str], city: str, all_sweden: bool, radius_km: int, limit: int,
) -> tuple[list[CompanyRaw], int]:
    """One AF search attempt for the given query terms."""
    params: dict = {
        "q": " ".join(query_parts),
        "offset": 0,
        "limit": min(limit, 100),
    }

    if radius_km > 0:
        coords = await geocode(city)
        if coords:
            params["position"] = f"{coords[0]},{coords[1]}"
            params["position.radius"] = radius_km
        else:
            if not all_sweden:
                params["q"] += f" {city}"
    elif not all_sweden:
        params["q"] += f" {city}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(AF_SEARCH_URL, params=params, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.warning("AF scrape failed: %s", exc)
        return [], 0

    total = data.get("total", {}).get("value", 0)

    try:
        companies: list[CompanyRaw] = []
        for hit in data.get("hits", []):
            employer = hit.get("employer") or {}
            address = hit.get("workplace_address") or {}
            name = employer.get("name", "").strip()
            if not name:
                continue
            desc = (hit.get("description") or {}).get("text", "") or ""
            companies.append(
                CompanyRaw(
                    name=name,
                    website=employer.get("url") or None,
                    city=address.get("city") or address.get("municipality") or city,
                    source="af",
                    job_title=hit.get("headline"),
                    job_url=hit.get("webpage_url"),
                    publication_date=hit.get("publication_date"),
                    description=desc or None,
                )
            )
        return companies, total
    except Exception as exc:
        logger.warning("AF parse failed: %s", exc)
        return [], 0
