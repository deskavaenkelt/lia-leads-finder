from pipeline.enrichment.seniority_scorer import score_seniority

def test_lia_keyword(): assert score_seniority("LIA-plats för Python-student") == 100.0
def test_junior_keyword(): assert score_seniority("We are looking for a trainee developer") == 100.0
def test_praktikant(): assert score_seniority("Vi söker en praktikant till vårt team") == 100.0
def test_nyexaminerad(): assert score_seniority("Perfekt för nyexaminerad") == 100.0
def test_internutbildning(): assert score_seniority("Vi erbjuder internutbildning") == 100.0
def test_internship(): assert score_seniority("Looking for an internship") == 100.0

def test_intern_not_false_positive():
    assert score_seniority("internal tooling team") == 50.0
def test_senior_keyword(): assert score_seniority("Senior Python Engineer wanted") == 10.0
def test_erfaren(): assert score_seniority("Vi söker en erfaren arkitekt") == 10.0
def test_principal(): assert score_seniority("Principal Engineer role") == 10.0
def test_neutral(): assert score_seniority("Python developer at growing company") == 50.0
def test_empty(): assert score_seniority("") == 50.0

def test_junior_wins_when_both():
    assert score_seniority("junior senior developer") == 100.0

def test_familiar_not_false_positive_for_lia():
    assert score_seniority("Senior Engineer, familiar with distributed systems") == 10.0

def test_reliable_not_false_positive_for_lia():
    assert score_seniority("Senior Architect, must be reliable") == 10.0

def test_larande_i_arbete_phrase():
    assert score_seniority("Vi erbjuder lärande i arbete för studenter") == 100.0

def test_praktik_under_utbildning_phrase():
    assert score_seniority("Praktik under utbildning, deltid") == 100.0

def test_pagaende_utbildning_phrase():
    assert score_seniority("Passar dig med pågående utbildning") == 100.0

# --- mode="senior" (mirrored scoring) ---

def test_senior_mode_senior_keyword_scores_high():
    assert score_seniority("Senior Python Engineer wanted", mode="senior") == 100.0

def test_senior_mode_junior_keyword_scores_low():
    assert score_seniority("Junior developer wanted", mode="senior") == 10.0

def test_senior_mode_lia_keyword_scores_low():
    assert score_seniority("LIA-plats för Python-student", mode="senior") == 10.0

def test_senior_mode_neutral():
    assert score_seniority("Python developer at growing company", mode="senior") == 50.0

def test_senior_mode_senior_wins_when_both():
    assert score_seniority("junior senior developer", mode="senior") == 100.0

def test_senior_mode_still_immune_to_familiar_reliable():
    assert score_seniority("Senior Engineer, familiar with distributed systems", mode="senior") == 100.0

# --- mode="junior" behaves like the default "lia" mode ---

def test_junior_mode_matches_lia_mode_behavior():
    assert score_seniority("Senior Software Architect", mode="junior") == 10.0
    assert score_seniority("Trainee developer wanted", mode="junior") == 100.0

# --- title vs. description: found via a real-ad audit (2026-09-13) ---
# A senior-titled ad that mentions mentoring/working with junior colleagues in
# the body used to score 100 (junior-friendly) just because "junior" appeared
# as a bare word in the description. The title is now trusted first.

def test_senior_title_mentioning_junior_colleagues_in_body_stays_senior():
    title = "Senior Fullstack-utvecklare till Filed"
    description = "Du höjer ribban för kodkvalitet och delar med dig av ditt kunnande till mer juniora kollegor, and mentor more junior engineers."
    assert score_seniority(title, description) == 10.0

def test_junior_title_wins_even_if_body_mentions_senior_colleagues():
    title = "Junior Fullstack-utvecklare"
    description = "Du får jobba tillsammans med erfarna seniora kollegor i ett härligt team."
    assert score_seniority(title, description) == 100.0

# --- explicit years-of-experience overrides a bare junior/LIA keyword when
# the title itself is neutral (real example: a "5 years experience... beyond
# internships" requirement that used to score 100 just for mentioning "praktik")

def test_years_experience_requirement_overrides_bare_praktik_mention():
    title = "Fullstackutvecklare 5 år + arbetslivserfarenhet"
    description = "Minst 5 års arbetslivserfarenhet som Fullstackutvecklare (utöver praktik och internships)."
    assert score_seniority(title, description) == 10.0

def test_years_experience_requirement_english_phrasing():
    title = "Backend Developer"
    description = "5+ years of experience required (in addition to any internship experience)."
    assert score_seniority(title, description) == 10.0

def test_short_experience_requirement_does_not_override_junior():
    # under the 3-year threshold — should not flip a genuine junior/LIA mention
    title = "Junior Developer"
    description = "1 års erfarenhet av Python är meriterande men inget krav, praktikplats finns."
    assert score_seniority(title, description) == 100.0

# --- new LIA-adjacent signal: thesis/exjobb postings (found via audit —
# previously scored neutral despite being a clear junior/LIA-friendly opening)

def test_examensarbete_thesis_posting_scores_junior():
    title = "Master Thesis & Academy – Starta din karriär inom Automotive Software"
    description = "Vill du göra ditt examensarbete hos oss och samtidigt få en tydlig väg från exjobb till en framtida roll som Software Engineer?"
    assert score_seniority(title, description) == 100.0

# --- a genuinely level-inclusive ad (no experience-years override present)
# should still let junior win on tie, same as before the audit fixes

def test_inclusive_ad_with_no_title_signal_still_lets_junior_win():
    title = "Intresseanmälan Fullstack Engineer"
    description = "Är du en junior/medior eller erfaren Fullstack Engineer som älskar modern systemutveckling?"
    assert score_seniority(title, description) == 100.0
