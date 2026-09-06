import sqlite3
import json
import os


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JSON_FILE = os.path.join(
    BASE_DIR,
    "database",
    "university_data Json file.json"
)

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "database",
    "uniguide.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Connect to the UniGuide SQLite database.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    # Allows us to access columns by name
    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# CREATE TABLES
# ============================================================

def create_tables(connection):

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (faculty_id)
                REFERENCES faculties(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qualifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            duration INTEGER,
            description TEXT,
            FOREIGN KEY (department_id)
                REFERENCES departments(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admission_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qualification_id INTEGER NOT NULL,
            minimum_aps INTEGER,
            description TEXT,
            FOREIGN KEY (qualification_id)
                REFERENCES qualifications(id)
        )
    """)

    connection.commit()


# ============================================================
# LOAD JSON DATA
# ============================================================

def load_json_data():

    if not os.path.exists(JSON_FILE):
        print("ERROR: JSON file not found:")
        print(JSON_FILE)
        return None

    try:

        with open(JSON_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except json.JSONDecodeError as error:

        print("ERROR: Invalid JSON file.")
        print(error)

        return None


# ============================================================
# INSERT JSON DATA INTO SQLITE
# ============================================================

def insert_data(connection, data):

    cursor = connection.cursor()

    # Remove old data before importing again
    cursor.execute("DELETE FROM admission_requirements")
    cursor.execute("DELETE FROM qualifications")
    cursor.execute("DELETE FROM departments")
    cursor.execute("DELETE FROM faculties")

    for faculty in data:

        # ----------------------------------------------------
        # FACULTY
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO faculties (
                name,
                description
            )
            VALUES (?, ?)
        """, (
            faculty.get("name"),
            faculty.get("description")
        ))

        faculty_id = cursor.lastrowid

        # ----------------------------------------------------
        # DEPARTMENTS
        # ----------------------------------------------------

        for department in faculty.get("departments", []):

            cursor.execute("""
                INSERT INTO departments (
                    faculty_id,
                    name,
                    description
                )
                VALUES (?, ?, ?)
            """, (
                faculty_id,
                department.get("name"),
                department.get("description")
            ))

            department_id = cursor.lastrowid

            # ------------------------------------------------
            # QUALIFICATIONS
            # ------------------------------------------------

            for qualification in department.get(
                "qualifications",
                []
            ):

                cursor.execute("""
                    INSERT INTO qualifications (
                        department_id,
                        name,
                        duration,
                        description
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    department_id,
                    qualification.get("name"),
                    qualification.get("duration"),
                    qualification.get("description")
                ))

                qualification_id = cursor.lastrowid

                # --------------------------------------------
                # ADMISSION REQUIREMENTS
                # --------------------------------------------

                requirements = qualification.get(
                    "admission_requirements",
                    {}
                )

                cursor.execute("""
                    INSERT INTO admission_requirements (
                        qualification_id,
                        minimum_aps,
                        description
                    )
                    VALUES (?, ?, ?)
                """, (
                    qualification_id,
                    requirements.get("minimum_aps"),
                    requirements.get("description")
                ))

    connection.commit()


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

            LEFT JOIN admission_requirements ar
                ON q.id = ar.qualification_id

            ORDER BY q.name
        """)

        return [dict(row) for row in cursor.fetchall()]

    finally:

        connection.close()


# ============================================================
# SEARCH QUALIFICATIONS
# ============================================================

def search_qualifications(search_term):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        search = f"%{search_term}%"

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

            LEFT JOIN admission_requirements ar
                ON q.id = ar.qualification_id

            WHERE
                q.name LIKE ?
                OR q.description LIKE ?
                OR f.name LIKE ?
                OR d.name LIKE ?
                OR ar.description LIKE ?

            ORDER BY q.name
        """, (
            search,
            search,
            search,
            search,
            search
        ))

        return [dict(row) for row in cursor.fetchall()]

    finally:

        connection.close()


# ============================================================
# GET QUALIFICATION BY NAME
# ============================================================

def get_qualification(name):

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

            LEFT JOIN admission_requirements ar
                ON q.id = ar.qualification_id

            WHERE q.name LIKE ?

            LIMIT 1
        """, (
            f"%{name}%"
        ))

        row = cursor.fetchone()

        if row:
            return dict(row)

        return None

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
        """, (
            aps,
        ))

        return [dict(row) for row in cursor.fetchall()]

    finally:

        connection.close()


# ============================================================
# DATABASE SETUP
# ============================================================

def setup_database():

    print("======================================")
    print("       UNIGUIDE DATABASE SETUP")
    print("======================================")

    print()
    print("Reading UNIZULU JSON data...")

    data = load_json_data()

    if data is None:
        return

    print("JSON data loaded successfully.")
    print()

    connection = sqlite3.connect(DATABASE_FILE)

    try:

        print("Creating database tables...")

        create_tables(connection)

        print("Tables created successfully.")
        print()

        print("Importing UNIZULU data...")

        insert_data(connection, data)

        print("UNIZULU data imported successfully.")
        print()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM faculties"
        )
        faculties = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM departments"
        )
        departments = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM qualifications"
        )
        qualifications = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM admission_requirements"
        )
        requirements = cursor.fetchone()[0]

        print("======================================")
        print("       DATABASE READY")
        print("======================================")

        print()
        print(f"Faculties:              {faculties}")
        print(f"Departments:            {departments}")
        print(f"Qualifications:         {qualifications}")
        print(f"Admission requirements: {requirements}")

        print()
        print("Database:")
        print(DATABASE_FILE)

    finally:

        connection.close()


# ============================================================
# RUN SETUP
# ============================================================

if __name__ == "__main__":
    setup_database()