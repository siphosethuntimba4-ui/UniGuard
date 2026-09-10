
from flask import Flask, request, jsonify, send_file, session
from werkzeug.security import generate_password_hash, check_password_hash
import os

from backend.ai import ask_uniguide
from database.database import (
    get_all_qualifications,
    get_qualifications_by_aps,
    qualification_meets_requirements,

    create_student,
    get_student_by_username,
    update_student_password,

    create_conversation,
    get_student_conversations,
    get_student_conversation,
    save_message,
    get_conversation_messages,
    update_conversation_title,
    delete_conversation
)


# ============================================================
# UNIGUIDE FLASK APPLICATION
# ============================================================

# Get the main UniGuard project folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Create Flask application
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static")
)

# ============================================================
# LOGIN SESSION
# ============================================================

app.secret_key = os.environ.get(
    "UNIGUIDE_SECRET_KEY",
    "uniguide-development-secret-key"
)

# ============================================================
# # LOGIN PAGE
# ============================================================

@app.route("/login")
def login_page():
    return send_file(
        os.path.join(BASE_DIR, "frontend", "login.html")
    )


# ============================================================
# FRONTEND PAGES
# ============================================================

@app.route("/")
def home():
    """Open the main UniGuide page."""
    return send_file(
        os.path.join(BASE_DIR, "frontend", "body.html")
    )


@app.route("/academic")
def academic():
    """Open the academic information page."""
    return send_file(
        os.path.join(BASE_DIR, "frontend", "academic.html")
    )
# ============================================================
# DATABASE TEST
# ============================================================

@app.route("/qualifications")
def qualifications():

    try:

        data = get_all_qualifications()

        return jsonify({
            "count": len(data),
            "qualifications": data
        })

    except Exception as e:

        print("DATABASE ERROR:", e)

        return jsonify({
            "error": "Could not load qualifications."
        }), 500

# ============================================================
# ACADEMIC RECOMMENDATIONS
# ============================================================

@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No academic information received."
            }), 400

        aps = data.get("aps")
        subjects = data.get("subjects", [])

        # -----------------------------------------
        # LIFE ORIENTATION CHECK
        # -----------------------------------------

        life_orientation = None

        for subject in subjects:
            if subject.get("subject") == "Life Orientation":
                life_orientation = subject
                break

        if life_orientation is None:
            return jsonify({
                "success": False,
                "qualified": False,
                "error": "Life Orientation mark is required."
            }), 400

        try:
            lo_percentage = float(
                life_orientation.get("percentage", 0)
            )
        except (ValueError, TypeError):
            lo_percentage = 0

        # Below 50% LO = student does not qualify
        if lo_percentage < 50:
            return jsonify({
                "success": True,
                "qualified": False,
                "aps": 0,
                "message": (
                    "The student does not qualify because "
                    "Life Orientation is below 50%."
                ),
                "qualifications": []
            })

        # -----------------------------------------
        # APS CHECK
        # -----------------------------------------

        try:
            aps = int(aps)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": "Invalid APS."
            }), 400

        # LO 80%+ gives one additional APS point
        lo_point = 1 if lo_percentage >= 80 else 0

        final_aps = aps + lo_point

        # -----------------------------------------
        # GET APS QUALIFICATIONS
        # -----------------------------------------

        aps_qualifications = get_qualifications_by_aps(
            final_aps
        )

        # -----------------------------------------
        # CHECK SUBJECT REQUIREMENTS
        # -----------------------------------------

        recommended = []

        for qualification in aps_qualifications:

            result = qualification_meets_requirements(
                qualification["admission_description"],
                qualification["minimum_aps"],
                final_aps,
                subjects
            )

            qualification_result = dict(qualification)

            qualification_result["aps_met"] = result["aps_met"]
            qualification_result["subjects_met"] = result["subjects_met"]
            qualification_result["fully_meets_requirements"] = (
                result["fully_meets_requirements"]
            )
            qualification_result["subject_requirements"] = (
                result["subject_requirements"]
            )

            # Only recommend qualifications where
            # BOTH APS and subject requirements are met.
            if result["fully_meets_requirements"]:
                recommended.append(qualification_result)

        # -----------------------------------------
        # RESPONSE
        # -----------------------------------------

        return jsonify({
            "success": True,
            "qualified": True,
            "aps": final_aps,
            "academic_aps": aps,
            "life_orientation_percentage": lo_percentage,
            "life_orientation_point": lo_point,
            "subjects": subjects,

            "count": len(recommended),

            "qualifications": recommended
        })

    except Exception as e:

        print("RECOMMENDATION ERROR:", e)

        return jsonify({
            "success": False,
            "error": "Could not generate recommendations."
        }), 500



# ============================================================
# UNIGUIDE CHAT
# ============================================================


@app.route("/chat", methods=["POST"])
def chat():

    student_id = session.get("student_id")

    if not student_id:
        return jsonify({
            "reply": "Please log in before using UniGuide."
        }), 401

    data = request.get_json() or {}

    user_message = data.get(
        "message",
        ""
    ).strip()

    conversation_history = data.get(
        "history",
        []
    )

    conversation_id = data.get(
        "conversation_id"
    )

    if not user_message:
        return jsonify({
            "reply": "Please type a message."
        })

    try:

        # -----------------------------------------
        # CREATE CONVERSATION IF NEEDED
        # -----------------------------------------

        if not conversation_id:

            conversation_id = create_conversation(
                student_id
            )

        else:

            conversation = get_student_conversation(
                conversation_id,
                student_id
            )

            if not conversation:

                return jsonify({
                    "reply": "Conversation not found."
                }), 404

        # -----------------------------------------
        # SAVE USER MESSAGE
        # -----------------------------------------

        save_message(
            conversation_id,
            "user",
            user_message
        )

        # -----------------------------------------
        # CREATE A USEFUL CONVERSATION TITLE
        # -----------------------------------------

        conversation = get_student_conversation(
            conversation_id,
            student_id
        )

        if (
            conversation
            and conversation["title"] == "New conversation"
        ):

            title_prompt = f"""
Create a short, useful title for this UniGuide conversation.

Student's first message:
{user_message}

Rules:
- Use 3 to 7 words.
- Describe the main topic of the conversation.
- Do not use quotation marks.
- Do not write a sentence.
- Return only the title.
"""

            title = ask_uniguide(
                title_prompt,
                []
            )

            if title:

                title = (
                    title
                    .strip()
                    .replace('"', "")
                    .replace("'", "")
                )

                update_conversation_title(
                    conversation_id,
                    title
                )

        # -----------------------------------------
        # GET UNIGUIDE AI RESPONSE
        # -----------------------------------------

        reply = ask_uniguide(
            user_message,
            conversation_history
        )

        # -----------------------------------------
        # SAVE AI RESPONSE
        # -----------------------------------------

        save_message(
            conversation_id,
            "assistant",
            reply
        )

        # -----------------------------------------
        # SEND RESPONSE TO FRONTEND
        # -----------------------------------------

        return jsonify({
            "reply": reply,
            "conversation_id": conversation_id
        })

    except Exception as e:

        print("CHAT ERROR:", e)

        return jsonify({
            "reply": (
                "Sorry, UniGuide could not process "
                "your message right now."
            )
        }), 500




# ============================================================
# STUDENT ACCOUNT SYSTEM
# ============================================================

@app.route("/register")
def register_page():
    return send_file(
        os.path.join(
            BASE_DIR,
            "frontend",
            "register.html"
        )
    )

@app.route("/register", methods=["POST"])
def register():

    try:

        data = request.get_json() or {}

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        recovery_question = data.get(
            "recovery_question",
            ""
        ).strip()
        recovery_answer = data.get(
            "recovery_answer",
            ""
        ).strip()

        # -----------------------------------------
        # CHECK REQUIRED INFORMATION
        # -----------------------------------------

        if not username:
            return jsonify({
                "success": False,
                "error": "Please enter a username."
            }), 400

        if not password:
            return jsonify({
                "success": False,
                "error": "Please enter a password."
            }), 400

        if len(password) < 6:
            return jsonify({
                "success": False,
                "error": (
                    "Password must be at least 6 characters."
                )
            }), 400

        if not recovery_question:
            return jsonify({
                "success": False,
                "error": "Please choose a recovery question."
            }), 400

        if not recovery_answer:
            return jsonify({
                "success": False,
                "error": "Please enter a recovery answer."
            }), 400

        # -----------------------------------------
        # CHECK IF USER ALREADY EXISTS
        # -----------------------------------------

        existing_student = get_student_by_username(
            username
        )

        if existing_student:

            return jsonify({
                "success": False,
                "error": "That username already exists."
            }), 409

        # -----------------------------------------
        # HASH PASSWORD
        # -----------------------------------------

        password_hash = generate_password_hash(
            password
        )

        recovery_answer_hash = generate_password_hash(
            recovery_answer.lower()
        )

        # -----------------------------------------
        # CREATE STUDENT
        # -----------------------------------------

        student_id = create_student(
            username,
            password_hash,
            recovery_question,
            recovery_answer_hash
        )

        if student_id is None:

            return jsonify({
                "success": False,
                "error": "That username already exists."
            }), 409

        # -----------------------------------------
        # LOG STUDENT IN
        # -----------------------------------------

        session["student_id"] = student_id
        session["username"] = username

        return jsonify({
            "success": True,
            "message": "Account created successfully.",
            "username": username
        })

    except Exception as e:

        print("REGISTER ERROR:", e)

        return jsonify({
            "success": False,
            "error": "Could not create the account."
        }), 500


# ============================================================
# LOGIN
# ============================================================



@app.route("/dashboard")
def dashboard():
    if "student_id" not in session:
        return send_file(
            os.path.join(BASE_DIR, "frontend", "login.html")
        )

    return send_file(
        os.path.join(BASE_DIR, "frontend", "dashboard.html")
    )



@app.route("/login", methods=["POST"])
def login():

    try:

        data = request.get_json() or {}

        username = data.get(
            "username",
            ""
        ).strip()

        password = data.get(
            "password",
            ""
        )

        if not username or not password:

            return jsonify({
                "success": False,
                "error": "Please enter your username and password."
            }), 400

        student = get_student_by_username(
            username
        )

        if not student:

            return jsonify({
                "success": False,
                "error": "Incorrect username or password."
            }), 401

        password_correct = check_password_hash(
            student["password_hash"],
            password
        )

        if not password_correct:

            return jsonify({
                "success": False,
                "error": "Incorrect username or password."
            }), 401

        # -----------------------------------------
        # SAVE LOGIN SESSION
        # -----------------------------------------

        session["student_id"] = student["id"]
        session["username"] = student["username"]

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "username": student["username"]
        })

    except Exception as e:

        print("LOGIN ERROR:", e)

        return jsonify({
            "success": False,
            "error": "Could not log in."
        }), 500


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    })


# ============================================================
# CHECK CURRENT LOGIN
# ============================================================

@app.route("/me")
def current_student():

    student_id = session.get("student_id")

    if not student_id:

        return jsonify({
            "logged_in": False
        })

    return jsonify({
        "logged_in": True,
        "student_id": student_id,
        "username": session.get("username")
    })


# ============================================================
# FORGOT PASSWORD - GET RECOVERY QUESTION
# ============================================================

@app.route("/forgot-password/question", methods=["POST"])
def forgot_password_question():

    try:

        data = request.get_json() or {}

        username = data.get(
            "username",
            ""
        ).strip()

        if not username:

            return jsonify({
                "success": False,
                "error": "Please enter your username."
            }), 400

        student = get_student_by_username(
            username
        )

        if not student:

            return jsonify({
                "success": False,
                "error": "Username not found."
            }), 404

        return jsonify({
            "success": True,
            "recovery_question": student[
                "recovery_question"
            ]
        })

    except Exception as e:

        print("FORGOT PASSWORD ERROR:", e)

        return jsonify({
            "success": False,
            "error": "Could not find the account."
        }), 500


# ============================================================
# FORGOT PASSWORD - RESET PASSWORD
# ============================================================

@app.route("/forgot-password/reset", methods=["POST"])
def forgot_password_reset():

    try:

        data = request.get_json() or {}

        username = data.get(
            "username",
            ""
        ).strip()

        recovery_answer = data.get(
            "recovery_answer",
            ""
        ).strip()

        new_password = data.get(
            "new_password",
            ""
        ).strip()

        if not username:
            return jsonify({
                "success": False,
                "error": "Please enter your username."
            }), 400

        if not recovery_answer:
            return jsonify({
                "success": False,
                "error": "Please enter your recovery answer."
            }), 400

        if not new_password:
            return jsonify({
                "success": False,
                "error": "Please enter a new password."
            }), 400

        if len(new_password) < 6:
            return jsonify({
                "success": False,
                "error": (
                    "New password must be at least 6 characters."
                )
            }), 400

        # -----------------------------------------
        # FIND STUDENT
        # -----------------------------------------

        student = get_student_by_username(
            username
        )

        if not student:

            return jsonify({
                "success": False,
                "error": "Username not found."
            }), 404

        # -----------------------------------------
        # CHECK RECOVERY ANSWER
        # -----------------------------------------

        answer_correct = check_password_hash(
            student["recovery_answer_hash"],
            recovery_answer.lower()
        )

        if not answer_correct:

            return jsonify({
                "success": False,
                "error": "Incorrect recovery answer."
            }), 401

        # -----------------------------------------
        # SAVE NEW PASSWORD
        # -----------------------------------------

        new_password_hash = generate_password_hash(
            new_password
        )

        updated = update_student_password(
            student["id"],
            new_password_hash
        )

        if not updated:

            return jsonify({
                "success": False,
                "error": "Could not update the password."
            }), 500

        return jsonify({
            "success": True,
            "message": "Password changed successfully."
        })

    except Exception as e:

        print("PASSWORD RESET ERROR:", e)

        return jsonify({
            "success": False,
            "error": "Could not reset the password."
        }), 500


# ============================================================
# STUDENT CONVERSATIONS
# ============================================================

@app.route("/conversations")
def conversations():
    student_id = session.get("student_id")

    if not student_id:
        return jsonify({
            "success": False,
            "error": "Not logged in"
        }), 401

    try:
        rows = get_student_conversations(student_id)

        conversations = [dict(row) for row in rows]

        return jsonify({
            "success": True,
            "conversations": conversations
        })

    except Exception as e:
        print("CONVERSATIONS ERROR:", e)
        return jsonify({
            "success": False,
            "error": "Could not load conversations."
        }), 500




# ============================================================
# CREATE CONVERSATION
# ============================================================

@app.route("/conversations", methods=["POST"])
def new_conversation():

    student_id = session.get("student_id")

    if not student_id:

        return jsonify({
            "success": False,
            "error": "Please log in first."
        }), 401

    try:

        conversation_id = create_conversation(
            student_id
        )

        return jsonify({
            "success": True,
            "conversation_id": conversation_id
        })

    except Exception as e:

        print("NEW CONVERSATION ERROR:", e)

        return jsonify({
            "success": False,
            "error": "Could not create conversation."
        }), 500


# ============================================================
# OPEN SAVED CONVERSATION
# ============================================================

@app.route(
    "/conversations/<int:conversation_id>"
)
def open_conversation(conversation_id):

    student_id = session.get("student_id")

    if not student_id:

        return jsonify({
            "success": False,
            "error": "Please log in first."
        }), 401

    try:

        conversation = get_student_conversation(
            conversation_id,
            student_id
        )

        if not conversation:

            return jsonify({
                "success": False,
                "error": "Conversation not found."
            }), 404

        messages = get_conversation_messages(
            conversation_id,
            student_id
        )

        return jsonify({
            "success": True,
            "conversation": conversation,
            "messages": messages
        })

    except Exception as e:

        print("OPEN CONVERSATION ERROR:", e)

        return jsonify({
            "success": False,
            "error": "Could not open conversation."
        }), 500

# ============================================================
# START FLASK SERVER
# ============================================================

if __name__ == "__main__":
    app.run(debug=False)