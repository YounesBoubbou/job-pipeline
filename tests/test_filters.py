from filters import (
    names_nl_place, passes_all, passes_dutch_requirement, passes_include, passes_language,
    passes_location, passes_exclude, strip_html,
)


# ── passes_location ───────────────────────────

def test_location_accepts_nl_places():
    assert passes_location("Amsterdam, Netherlands")
    assert passes_location("Utrecht, NL")
    assert passes_location("Den Haag")


def test_location_rejects_countries_containing_nl():
    assert not passes_location("Helsinki, Finland")
    assert not passes_location("Nuuk, Greenland")


def test_location_accepts_other_nl_cities():
    assert passes_location("Veldhoven, Noord-Brabant")
    assert passes_location("The Hague")
    assert passes_location("'s-Hertogenbosch")
    assert passes_location("Eindhoven, nl")


def test_nl_place_ignores_work_modes():
    assert names_nl_place("Remote - Amsterdam")
    assert not names_nl_place("Remote")
    assert not names_nl_place("Hybrid")


def test_location_rejects_empty():
    assert not passes_location("")


def test_location_rejects_bare_hybrid():
    assert not passes_location("Hybrid")
    assert not passes_location("Hybrid; Singapore")
    assert passes_location("Hybrid; Amsterdam, Netherlands")


# ── passes_include ────────────────────────────

def test_include_needs_a_tech_word_in_the_title():
    assert passes_include("Junior Data Analyst")
    assert passes_include("AI/ML Engineer")
    assert passes_include("Medior back-end developer")


def test_include_accepts_graduate_and_internship_titles():
    assert passes_include("Elsevier Netherlands Graduate Program 2027")
    assert passes_include("Thesis Internship - 2027")


def test_include_rejects_seniority_alone_and_partial_words():
    assert not passes_include("Junior Consultant")
    assert not passes_include("Traineeship Kinderverpleegkundige")
    assert not passes_include("Maintenance Planner")   # "ai" inside "Maintenance"


# ── passes_exclude ────────────────────────────

def test_exclude_rejects_non_software_engineers_and_sales():
    assert not passes_exclude("Mechanical Engineer")
    assert not passes_exclude("Presales Customer Engineer")
    assert not passes_exclude("Junior Business Developer")
    assert passes_exclude("Marketing Data Analyst")



def test_exclude_rejects_seniority():
    assert not passes_exclude("Senior Data Engineer")
    assert not passes_exclude("Data Engineering Team Lead")


def test_exclude_keeps_words_containing_lead():
    assert passes_exclude("Junior Data Engineer", "Join a leading fintech")
    assert passes_exclude("Junior Data Engineer", "No misleading dashboards here")


def test_exclude_rejects_short_seniority_in_title():
    assert not passes_exclude("Sr. Software Engineer")


def test_exclude_ignores_seniority_words_in_description():
    assert passes_exclude("Data Engineer", "You report to the engineering manager and work with senior staff")
    assert passes_exclude("Graduate Program", "You will lead a project")


def test_exclude_rejects_bare_year_requirements_in_description():
    assert not passes_exclude("Data Engineer", "Requirements: 5+ years in Python")


def test_exclude_rejects_year_requirements():
    assert not passes_exclude("Data Engineer", "You have 5+ years of experience")
    assert not passes_exclude("Data Engineer", "5-7 years of experience with Python")
    assert not passes_exclude("Data Engineer", "At least 6 years experience")


def test_exclude_rejects_three_or_more_years():
    # Younes, 2026-11-10: more than 2 years asked is out of reach, so 3+ is excluded.
    for text in [
        "3+ years of experience",
        "You have 3 years of experience with Python",
        "3-5 years of experience",
        "3 to 5 years of experience",
        "4 years experience",
        "3 years' relevant experience",
        "3 yrs of hands-on experience",
        "Requirements: 3+ years in Python",
        "5 plus years in data engineering",
        "At least 3 years in a similar role",
        "Minimum of three years in software development",
        "min. 4 yrs working with SQL",
        "At least five years of experience",
        "(3+ years) of professional experience",
        "3 years’ experience",
        "3 years’ relevant experience",
        "3 or more years of experience",
        "Three or more years of experience",
        "3 or more years",
        "Three (3) years of experience",
        "At least three (3) years",
        "3-5 years",
        "5–7 yrs",
        "3+ yrs",
        "3 + years",
        "min 3 yrs",
        "Over 3 years of experience",
        "3 years hands-on experience",
        "1-2 years; 3+ years is a plus",
        # near the round-3 keep cases, still 3 or more years asked
        "3-5 years of experience on a contract basis",
        "Between 3 and 5 years of experience",
        "Between three and five years of experience",
        "More than 3 years of experience",
        "Minimum of 3 years of experience",
        # round 4: "contract" here is the kind of experience, not a contract length
        "3-5 years of contract experience",
        "3-5 years contracting experience",
        "3-5 years experience, contract type: permanent",
        "3-5 years experience; contract: permanent",
        "Requirements: 3-5 years experience Contract: full-time",
        "3-5 years experience contract",
    ]:
        assert not passes_exclude("Data Engineer", text), text


def test_exclude_keeps_junior_year_requirements():
    for text in [
        "1-2 years of experience",
        "0-2 years of experience",
        "2 years of experience",
        "2+ years of experience",
        "2-3 years of experience",
        "2 to 3 years of experience",
        "2 or 3 years of experience",
        "At least 2 years in a similar role",
        "We have been building software for 20 years",
        "Over the next 3 years you will grow into the role",
        "A 3 year contract",
        "Founded 30 years ago",
        "2 - 3 years of experience",
        "2 – 3 years of experience",
        "1.5 years of experience",
        "Less than 3 years of experience",
        "2+ years’ experience",
        "0–3 years of experience",
        "Up to 3 years of experience",
        "A 3-year contract",
        "30 years of history",
        "3 days a week, 2 years of experience",
        # round 3: a contract length, a range starting below 3, a ceiling
        "A 3-5 year contract",
        "A 3 to 5 year fixed-term contract",
        "3-5 years' contract, 2 years of experience",
        "Between 1 and 3 years of experience",
        "Between 2 and 3 years of experience",
        "Between one and three years of experience",
        "Max 3 years of experience",
        "Max. 3 years of experience",
        "No more than 3 years of experience",
        "Not more than 3 years of experience",
        "Maximum of 3 years of experience",
        "Maximum 3 years experience",
        "3-5 year (fixed-term) contract",
        # round 4: "N and M" is only a range after "between"
        "MBO 4 and 2 years of experience",
        "MBO level 4 and 2 years of work experience",
        "Python 3 and 1 year of experience",
        "Experience with Python 3 and 2 years in a data role",
        "Team of 5 and 2 years of experience",
    ]:
        assert passes_exclude("Data Engineer", text), text


def test_location_accepts_bare_work_mode():
    assert passes_location("Remote")
    assert passes_location("Remote job")
    assert passes_location("Hybrid - Amsterdam")


def test_location_rejects_remote_elsewhere():
    assert not passes_location("Remote - Indonesia; Remote - Malaysia")
    assert not passes_location("Remote, United States")


# ── strip_html ────────────────────────────────

def test_strip_html_handles_plain_escaped_and_cut_off_html():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert strip_html("&lt;p&gt;Fish &amp;amp; chips&lt;/p&gt;") == "Fish & chips"
    assert strip_html("Hello&nbsp;world <di") == "Hello world"
    assert strip_html("Plain text") == "Plain text"


# ── passes_language ───────────────────────────

def test_language_rejects_dutch_postings():
    assert not passes_language("Data Engineer", "Wij zoeken een collega voor het team van jouw dromen")
    assert not passes_language("Data Engineer", "&lt;p&gt;Als data engineer werk je aan de data van onze klanten&lt;/p&gt;")


def test_language_rejects_dutch_titles_without_description():
    assert not passes_language("Junior Software Ontwikkelaar")
    assert not passes_language("Data Engineer bij Coolblue")


def test_language_keeps_english_postings():
    assert passes_language("Data Engineer", "You will work with our team on the data platform")
    assert passes_language("Data Engineer", "Join Van der Berg and the team to work with your peers")


def test_language_keeps_postings_with_no_signal():
    assert passes_language("Data Engineer")
    assert passes_language("Junior Data Analyst", "Python, SQL, dbt")


# ── passes_dutch_requirement ──────────────────

def test_dutch_requirement_rejects_required_phrases():
    for description in [
        "You are fluent in Dutch.",
        "Dutch is a must.",
        "Native Dutch speaker.",
        "Proficiency in Dutch and English.",
        "Fluent in English and Dutch",
        "Dutch (C1)",
        "Dutch C1 level",
        "You speak Dutch.",
        "Dutch and English are required.",
        "Dutch required",
        "Dutch-speaker",
        "Nederlands vereist",
        "Vloeiend Nederlands",
    ]:
        assert not passes_dutch_requirement("Data Engineer", description), description


def test_dutch_requirement_keeps_optional_or_unrelated_mentions():
    for description in [
        "Dutch is a plus.",
        "Dutch is nice-to-have.",
        "Dutch is not required.",
        "No Dutch needed.",
        "Knowledge of Dutch is an advantage.",
        "Dutch preferred",
        "You will work with Dutch clients.",
        "Grow in the Dutch market.",
        "A Dutch company.",
        "Support our Dutch-speaking customers",
        "Speak with Dutch clients daily",
        "A valid Dutch work permit is required",
    ]:
        assert passes_dutch_requirement("Data Engineer", description), description


def test_dutch_requirement_splits_sentences_and_list_items():
    # The "plus" only softens the sentence it is in
    assert passes_dutch_requirement("Data Engineer", "Fluent English required, Dutch is a plus.")
    assert not passes_dutch_requirement("Data Engineer", "Fluent in Dutch. English is a plus.")
    assert not passes_dutch_requirement(
        "Data Engineer", "<li>Fluent in Dutch</li><li>Python is a plus</li>"
    )


# Plain-text cases; the app's copy of this rule (frontend/src/constants/filters.js) must give
# the same answers on them
DUTCH_REQUIRED_CASES = [
    # under a heading or label that isn't optional
    "Requirements:\n- Fluent in Dutch",
    "What we ask: fluent Dutch",
    "Nice to have\n- Python\nRequirements\n- Fluent in Dutch",
    "Nice to have: Python. Must have: fluent Dutch",
    # "Dutch" as the language
    "Fluent in Dutch",
    "fluent Dutch",
    "Native Dutch speaker",
    "Excellent command of Dutch, written and verbal",
    "Excellent command of the Dutch and English language",
    "Proficiency in Dutch and English",
    "You are fluent in both Dutch and English",
    "Fluent in Dutch (written and spoken)",
    "Fluent Dutch and English speaker",
    # you speak it
    "You speak Dutch",
    "Must speak Dutch",
    "You speak and write Dutch fluently",
    "You speak fluent Dutch and English",
    "You master the Dutch language",
    # skills in Dutch
    "Excellent (written and verbal) communication skills in Dutch and English",
    "Strong communication skills in English and Dutch",
    "Very good Dutch and English skills",
    # language lines
    "Dutch: fluent",
    "Language: Dutch (fluent)",
    "Dutch (fluent) and English",
    "Dutch - fluent",
    "Dutch (native) and English",
    "Dutch native level",
    "Native-level Dutch",
    "Languages: Dutch and English (fluent)",
    "Dutch and English: fluent",
    "Dutch is mandatory",
    "Dutch speaking is required",
    "Dutch at C1 level",
    # the optional word is about something else
    "Fluent in Dutch and English, knowledge of German is a plus",
    "Fluency in Dutch and English, German is an advantage",
    "Fluent Dutch required, plus 2 years of Python",
    "Fluent in Dutch and English; Python skills are a plus",
]

DUTCH_OPTIONAL_CASES = [
    # under an optional heading or label
    "Nice to have: fluent Dutch",
    "Nice to have: Dutch language skills",
    "Nice to haves\n- Fluent in Dutch",
    "Nice to have\n- Fluent in Dutch\n- Python",
    "Preferred qualifications:\n- Proficiency in Dutch",
    "Bonus points: you speak Dutch",
    "Pluses\n- Fluent in Dutch",
    "Requirements\n- Python\nNice to have\n- Fluent in Dutch",
    # not needed
    "You don't need to speak Dutch",
    "You don’t need to speak Dutch",
    "You do not need to speak Dutch",
    "No need to speak Dutch",
    "Our working language is English, so you don't need to speak Dutch",
    "Knowledge of Dutch is not a prerequisite",
    "Dutch language skills are not essential",
    "Dutch is an asset",
    "Preferably you speak Dutch",
    "Fluent English required, Dutch is a plus",
    "Fluent in English; Dutch is a plus",
    "Dutch speaker or not, you are welcome",
    "Fluent in Dutch is welcome but not mandatory",
    "Being fluent in Dutch is a plus",
    # "Dutch" as an adjective
    "knowledge of the Dutch market",
    "command of the Dutch tax system",
    "proficiency in Dutch payroll regulations",
    "Knowledge of Dutch GAAP and IFRS",
    "Experience with Dutch privacy law; knowledge of the Dutch healthcare system",
    "native Dutch and international team",
    "excellent Dutch pension scheme",
    "excellent Dutch work-life balance",
    "Experience with Dutch speakers",
    # the team speaks it, not you
    "We speak Dutch and English in the office",
    "Our team speaks Dutch and English",
]


def test_dutch_requirement_drops_required_cases():
    for description in DUTCH_REQUIRED_CASES:
        assert not passes_dutch_requirement("Data Engineer", description), description


def test_dutch_requirement_keeps_optional_cases():
    for description in DUTCH_OPTIONAL_CASES:
        assert passes_dutch_requirement("Data Engineer", description), description


def test_dutch_requirement_reads_html_headings_and_lists():
    assert passes_dutch_requirement(
        "Data Engineer", "<h3>Nice to have</h3><ul><li>Fluent in Dutch</li></ul>"
    )
    assert passes_dutch_requirement(
        "Data Engineer", "<p><strong>Nice to have:</strong></p><ul><li>Fluent in Dutch</li></ul>"
    )
    assert not passes_dutch_requirement(
        "Data Engineer",
        "<h3>Requirements</h3><ul><li>Fluent in Dutch</li></ul>"
        "<h3>Nice to have</h3><ul><li>Python</li></ul>",
    )
    # Escaped twice, list items without closing tags, table cells
    assert not passes_dutch_requirement(
        "Data Engineer", "&amp;lt;ul&amp;gt;&amp;lt;li&amp;gt;Python&amp;lt;li&amp;gt;Fluent in Dutch"
    )
    assert passes_dutch_requirement(
        "Data Engineer", "&amp;lt;h3&amp;gt;Nice to have&amp;lt;/h3&amp;gt;&amp;lt;li&amp;gt;Fluent in Dutch"
    )
    assert not passes_dutch_requirement(
        "Data Engineer", "<table><tr><td>Python</td></tr><tr><td>Fluent in Dutch</td></tr></table>"
    )
    # Line breaks inside HTML source don't split a sentence
    assert not passes_dutch_requirement("Data Engineer", "<p>You are fluent in\nDutch.</p>")


def test_passes_all_drops_dutch_required():
    assert not passes_all("Junior Data Engineer", "Amsterdam", "You are fluent in Dutch.")
    assert passes_all("Junior Data Engineer", "Amsterdam", "Dutch is a plus.")
