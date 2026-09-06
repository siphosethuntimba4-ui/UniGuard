import sqlite3
import os


# ============================================================
# DATABASE LOCATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "database",
    "uniguide.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    connection = sqlite3.connect(DATABASE_FILE)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# GET ALL QUALIFICATIONS
# ============================================================

def get_all_qualifications():

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                q.id,
                q.name,
                q.duration,
                q.description,
                f.name AS faculty,
                d.name AS department,
                ar.minimum_aps,
                ar.description AS admission_description

            FROM qualifications q

            JOIN departments d
                ON q.department_id = d.id

            JOIN faculties f
                ON d.faculty_id = f.id

            JOIN admission_requirements ar
                ON q.id = ar.qualification_id

            ORDER BY q.name
        """)

        return [dict(row) for row in cursor.fetchall()]

    finally:

        connection.close()


# ============================================================
# FIND QUALIFICATIONS BY APS
# ============================================================

def get_qualifications_by_aps(aps):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                q.id,
                q.name,
                q.duration,
                q.description,
                f.name AS faculty,
                d.name AS department,
                ar.minimum_aps,
                ar.description AS admission_description

            FROM qualifications q

            JOIN departments d
                ON q.department_id = d.id

            JOIN faculties f
                ON d.faculty_id = f.id

            JOIN admission_requirements ar
                ON q.id = ar.qualification_id

            WHERE ar.minimum_aps <= ?

            ORDER BY ar.minimum_aps ASC
        """, (aps,))

        return [dict(row) for row in cursor.fetchall()]

    finally:

        connection.close()
import re


# ============================================================
# SUBJECT NAME MATCHING
# ============================================================

SUBJECT_ALIASES = {
    "engl": [
        "english",
        "english hl",
        "english fal"
    ],

    "isizulu": [
        "isizulu",
        "isizulu hl",
        "isizulu fal"
    ],

    "maths": [
        "mathematics",
        "maths"
    ],

    "maths_lit": [
        "mathematical literacy",
        "maths lit"
    ],

    "phys_sci": [
        "physical sciences",
        "physical science",
        "phys sci"
    ],

    "life_sci": [
        "life sciences",
        "life science",
        "life sci"
    ],

    "agric_sci": [
        "agricultural sciences",
        "agricultural science",
        "agric sci"
    ],

    "geog": [
        "geography",
        "geog"
    ],

    "hist": [
        "history",
        "hist"
    ],

    "economics": [
        "economics"
    ],

    "tourism": [
        "tourism"
    ],

    "hospitality": [
        "hospitality studies",
        "hospitality"
    ],

    "business": [
        "business studies",
        "business stud"
    ],

    "accounting": [
        "accounting",
        "acc"
    ],

    "dramatic": [
        "dramatic arts",
        "dramatic art"
    ],

    "visual": [
        "visual arts",
        "visual art"
    ],

    "life_orientation": [
        "life orientation"
    ]
}


# ============================================================
# FIND STUDENT SUBJECT LEVEL
# ============================================================

def get_student_level(student_levels, subject_key):

    aliases = SUBJECT_ALIASES.get(subject_key, [])

    for student_subject, level in student_levels.items():

        student_subject = student_subject.lower().strip()

        for alias in aliases:

            if student_subject == alias.lower():
                return level

    return None


# ============================================================
# CHECK ONE SUBJECT
# ============================================================

def check_one_subject(
    student_levels,
    subject_key,
    required_level=None
):

    student_level = get_student_level(
        student_levels,
        subject_key
    )

    subject_name = subject_key.replace("_", " ").title()

    # Student does not have the subject
    if student_level is None:

        return {
            "requirement": (
                f"{subject_name}"
                + (
                    f" Level {required_level}"
                    if required_level is not None
                    else ""
                )
            ),
            "met": False,
            "student_level": None
        }

    # Requirement has a level
    if required_level is not None:

        return {
            "requirement":
                f"{subject_name} Level {required_level}",

            "met":
                student_level >= required_level,

            "student_level":
                student_level
        }

    # Requirement only says the subject
    return {
        "requirement": subject_name,
        "met": True,
        "student_level": student_level
    }


# ============================================================
# CHECK SUBJECT REQUIREMENTS
# ============================================================

def check_subject_requirements(
    admission_description,
    student_subjects
):

    results = []

    description = admission_description.lower()

    # --------------------------------------------------------
    # CREATE STUDENT SUBJECT DICTIONARY
    # --------------------------------------------------------

    student_levels = {}

    for subject in student_subjects:

        name = subject.get("subject", "").strip()

        level = subject.get("level", 0)

        if name:

            student_levels[name.lower()] = level

    # --------------------------------------------------------
    # ENGLISH
    # --------------------------------------------------------

    english_match = re.search(
        r"engl(?:ish)?(?:\s+(?:hl|fal))?\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if english_match:

        required_level = int(
            english_match.group(1)
        )

        result = check_one_subject(
            student_levels,
            "engl",
            required_level
        )

        results.append(result)

    elif re.search(r"\bengl\b", description):

        result = check_one_subject(
            student_levels,
            "engl"
        )

        results.append(result)

    # --------------------------------------------------------
    # ENGLISH HL/FAL SPECIAL REQUIREMENT
    # Example:
    # Engl HL 4/FAL 5
    # --------------------------------------------------------

    english_hlfal = re.search(
        r"engl\s+hl\s+(\d+)\s*/\s*fal\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if english_hlfal:

        hl_required = int(
            english_hlfal.group(1)
        )

        fal_required = int(
            english_hlfal.group(2)
        )

        english_hl = get_student_level(
            student_levels,
            "engl"
        )

        met = (
            english_hl is not None
            and english_hl >= hl_required
        )

        results.append({
            "requirement":
                f"English HL Level {hl_required} / "
                f"FAL Level {fal_required}",

            "met": met,

            "student_level": english_hl
        })

    # --------------------------------------------------------
    # GEOGRAPHY
    # --------------------------------------------------------

    geog_match = re.search(
        r"\bgeog(?:raphy)?\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if geog_match:

        required_level = int(
            geog_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "geog",
                required_level
            )
        )

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    hist_match = re.search(
        r"\bhist(?:ory)?\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if hist_match:

        required_level = int(
            hist_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "hist",
                required_level
            )
        )

    # --------------------------------------------------------
    # GEOGRAPHY OR HISTORY
    # --------------------------------------------------------

    social_match = re.search(
        r"social sci\s+\(geography/history\)\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if social_match:

        required_level = int(
            social_match.group(1)
        )

        geography_level = get_student_level(
            student_levels,
            "geog"
        )

        history_level = get_student_level(
            student_levels,
            "hist"
        )

        met = (
            (geography_level is not None
             and geography_level >= required_level)
            or
            (history_level is not None
             and history_level >= required_level)
        )

        results.append({
            "requirement":
                f"Geography OR History Level {required_level}",

            "met": met,

            "student_level":
                geography_level
                if geography_level is not None
                and geography_level >= required_level
                else history_level
        })

    # --------------------------------------------------------
    # MATHEMATICS
    # --------------------------------------------------------

    maths_match = re.search(
        r"\bmaths(?:ematics)?\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if maths_match:

        required_level = int(
            maths_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "maths",
                required_level
            )
        )

    # --------------------------------------------------------
    # MATHEMATICS / MATHS LIT
    # --------------------------------------------------------

    maths_or_lit = re.search(
        r"maths\s*(?:/|or)\s*maths lit\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if maths_or_lit:

        required_level = int(
            maths_or_lit.group(1)
        )

        maths_level = get_student_level(
            student_levels,
            "maths"
        )

        maths_lit_level = get_student_level(
            student_levels,
            "maths_lit"
        )

        met = (
            (maths_level is not None
             and maths_level >= required_level)
            or
            (maths_lit_level is not None
             and maths_lit_level >= required_level)
        )

        results.append({
            "requirement":
                f"Mathematics OR Mathematical Literacy "
                f"Level {required_level}",

            "met": met,

            "student_level":
                maths_level
                if maths_level is not None
                and maths_level >= required_level
                else maths_lit_level
        })

    # --------------------------------------------------------
    # PHYSICAL SCIENCES
    # --------------------------------------------------------

    phys_match = re.search(
        r"phys sci\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if phys_match:

        required_level = int(
            phys_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "phys_sci",
                required_level
            )
        )

    # --------------------------------------------------------
    # LIFE SCIENCES
    # --------------------------------------------------------

    life_match = re.search(
        r"life sci\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if life_match:

        required_level = int(
            life_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "life_sci",
                required_level
            )
        )

    # --------------------------------------------------------
    # AGRICULTURAL SCIENCE
    # --------------------------------------------------------

    agric_match = re.search(
        r"agric sci\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if agric_match:

        required_level = int(
            agric_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "agric_sci",
                required_level
            )
        )

    # --------------------------------------------------------
    # LIFE SCIENCES OR AGRICULTURAL SCIENCES
    # --------------------------------------------------------

    life_or_agric = re.search(
        r"life sci\s+or\s+agric sci\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if life_or_agric:

        required_level = int(
            life_or_agric.group(1)
        )

        life_level = get_student_level(
            student_levels,
            "life_sci"
        )

        agric_level = get_student_level(
            student_levels,
            "agric_sci"
        )

        met = (
            (life_level is not None
             and life_level >= required_level)
            or
            (agric_level is not None
             and agric_level >= required_level)
        )

        results.append({
            "requirement":
                f"Life Sciences OR Agricultural Sciences "
                f"Level {required_level}",

            "met": met,

            "student_level":
                life_level
                if life_level is not None
                and life_level >= required_level
                else agric_level
        })

    # --------------------------------------------------------
    # ECONOMICS
    # --------------------------------------------------------

    economics_match = re.search(
        r"economics\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if economics_match:

        required_level = int(
            economics_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "economics",
                required_level
            )
        )

    # --------------------------------------------------------
    # TOURISM
    # --------------------------------------------------------

    tourism_match = re.search(
        r"tourism\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if tourism_match:

        required_level = int(
            tourism_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "tourism",
                required_level
            )
        )

    # --------------------------------------------------------
    # HOSPITALITY
    # --------------------------------------------------------

    hospitality_match = re.search(
        r"hosp stud\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if hospitality_match:

        required_level = int(
            hospitality_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "hospitality",
                required_level
            )
        )

    # --------------------------------------------------------
    # BUSINESS STUDIES
    # --------------------------------------------------------

    business_match = re.search(
        r"bus stud\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if business_match:

        required_level = int(
            business_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "business",
                required_level
            )
        )

    # --------------------------------------------------------
    # ACCOUNTING
    # --------------------------------------------------------

    accounting_match = re.search(
        r"\bacc\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if accounting_match:

        required_level = int(
            accounting_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "accounting",
                required_level
            )
        )

    # --------------------------------------------------------
    # DRAMATIC ART OR VISUAL ART
    # --------------------------------------------------------

    art_match = re.search(
        r"dramatic art\s+or\s+visual art\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if art_match:

        required_level = int(
            art_match.group(1)
        )

        dramatic_level = get_student_level(
            student_levels,
            "dramatic"
        )

        visual_level = get_student_level(
            student_levels,
            "visual"
        )

        met = (
            (dramatic_level is not None
             and dramatic_level >= required_level)
            or
            (visual_level is not None
             and visual_level >= required_level)
        )

        results.append({
            "requirement":
                f"Dramatic Arts OR Visual Arts "
                f"Level {required_level}",

            "met": met,

            "student_level":
                dramatic_level
                if dramatic_level is not None
                and dramatic_level >= required_level
                else visual_level
        })

    # --------------------------------------------------------
    # ISIZULU
    # --------------------------------------------------------

    isizulu_match = re.search(
        r"isizulu(?:\s+(?:hl|fal))?\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if isizulu_match:

        required_level = int(
            isizulu_match.group(1)
        )

        results.append(
            check_one_subject(
                student_levels,
                "isizulu",
                required_level
            )
        )

    # --------------------------------------------------------
    # LIFE ORIENTATION REQUIREMENT IN DATABASE
    # --------------------------------------------------------

    lo_match = re.search(
        r"lo\s+(\d+)",
        description,
        re.IGNORECASE
    )

    if lo_match:

        required_level = int(
            lo_match.group(1)
        )

        lo_level = get_student_level(
            student_levels,
            "life_orientation"
        )

        results.append({
            "requirement":
                f"Life Orientation Level {required_level}",

            "met":
                lo_level is not None
                and lo_level >= required_level,

            "student_level":
                lo_level
        })

    return results


# ============================================================
# FINAL QUALIFICATION CHECK
# ============================================================

def qualification_meets_requirements(
    admission_description,
    minimum_aps,
    student_aps,
    student_subjects
):

    # Check APS
    aps_met = student_aps >= minimum_aps

    # Check subjects
    subject_results = check_subject_requirements(
        admission_description,
        student_subjects
    )

    # Every detected requirement must be met
    subjects_met = all(
        result["met"]
        for result in subject_results
    )

    return {
        "aps_met": aps_met,

        "subjects_met": subjects_met,

        "fully_meets_requirements":
            aps_met and subjects_met,

        "subject_requirements":
            subject_results
    }