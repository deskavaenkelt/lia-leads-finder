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
