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
# ============================================================
# CREATE STUDENT AND CHAT TABLES
# ============================================================

def create_user_tables():

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Students
        cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        recovery_question TEXT NOT NULL,
        recovery_answer_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

        # Conversations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'New Conversation',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id)
                    REFERENCES students(id)
                    ON DELETE CASCADE
            )
        """)

        # Messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
            )
        """)

        connection.commit()

    finally:
        connection.close()


# ============================================================
# CREATE STUDENT
# ============================================================

def create_student(username, password_hash):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO students (
                username,
                password_hash
            )
            VALUES (?, ?)
        """, (
            username,
            password_hash
        ))

        connection.commit()

        return cursor.lastrowid

    except sqlite3.IntegrityError:

        return None

    finally:
        connection.close()


# ============================================================
# FIND STUDENT BY USERNAME
# ============================================================

def get_student_by_username(username):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                username,
                password_hash,
                created_at
            FROM students
            WHERE username = ?
        """, (username,))

        row = cursor.fetchone()

        if row:
            return dict(row)

        return None

    finally:
        connection.close()


# ============================================================
# CREATE CONVERSATION
# ============================================================

def create_conversation(student_id, title="New Conversation"):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO conversations (
                student_id,
                title
            )
            VALUES (?, ?)
        """, (
            student_id,
            title
        ))

        connection.commit()

        return cursor.lastrowid

    finally:
        connection.close()


# ============================================================
# GET STUDENT CONVERSATIONS
# ============================================================

def get_student_conversations(student_id):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                title,
                created_at,
                updated_at
            FROM conversations
            WHERE student_id = ?
            ORDER BY updated_at DESC
        """, (student_id,))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()

# ============================================================
# GET ONE STUDENT CONVERSATION
# ============================================================

def get_student_conversation(
    conversation_id,
    student_id
):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                student_id,
                title,
                created_at,
                updated_at

            FROM conversations

            WHERE id = ?

            AND student_id = ?
        """, (
            conversation_id,
            student_id
        ))

        row = cursor.fetchone()

        if row:
            return dict(row)

        return None

    finally:

        connection.close()


# ============================================================
# SAVE CHAT MESSAGE
# ============================================================

def save_message(
    conversation_id,
    role,
    message
):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO messages (
                conversation_id,
                role,
                message
            )
            VALUES (?, ?, ?)
        """, (
            conversation_id,
            role,
            message
        ))

        cursor.execute("""
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            conversation_id,
        ))

        connection.commit()

    finally:
        connection.close()


# ============================================================
# GET CONVERSATION MESSAGES
# ============================================================

def get_conversation_messages(
    conversation_id,
    student_id
):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                m.id,
                m.role,
                m.message,
                m.created_at
            FROM messages m

            JOIN conversations c
                ON m.conversation_id = c.id

            WHERE m.conversation_id = ?
            AND c.student_id = ?

            ORDER BY m.id ASC
        """, (
            conversation_id,
            student_id
        ))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()

# ============================================================
# UPDATE STUDENT PASSWORD
# ============================================================

def update_student_password(
    student_id,
    password_hash
):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            UPDATE students
            SET password_hash = ?
            WHERE id = ?
        """, (
            password_hash,
            student_id
        ))

        connection.commit()

        return cursor.rowcount > 0

    finally:

        connection.close()

# ============================================================
# UPDATE CONVERSATION TITLE
# ============================================================

def update_conversation_title(
    conversation_id,
    student_id,
    title
):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            UPDATE conversations

            SET title = ?

            WHERE id = ?

            AND student_id = ?
        """, (
            title,
            conversation_id,
            student_id
        ))

        connection.commit()

        return cursor.rowcount > 0

    finally:

        connection.close()

# ============================================================
# DELETE CONVERSATION
# ============================================================

def delete_conversation(
    conversation_id,
    student_id
):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            DELETE FROM conversations

            WHERE id = ?

            AND student_id = ?
        """, (
            conversation_id,
            student_id
        ))

        connection.commit()

        return cursor.rowcount > 0

    finally:

        connection.close()