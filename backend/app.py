
from flask import Flask, request, jsonify, send_file
import os

from ai import ask_uniguide
from database import (
    get_all_qualifications,
    get_qualifications_by_aps,
    qualification_meets_requirements
)


# ============================================================
# UNIGUIDE FLASK APPLICATION
# ============================================================

# Get the main UniGuard project folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Create Flask application
app = Flask(__name__)


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

    data = request.get_json()

    user_message = data.get("message", "").strip()

    # Check if the user sent an empty message
    if not user_message:
        return jsonify({
            "reply": "Please type a message."
        })

    try:

        # Send the student's message to ai.py
        reply = ask_uniguide(user_message)

        # Return the AI response to the website
        return jsonify({
            "reply": reply
        })

    except Exception as e:

        # Print the error in the terminal
        print("ERROR:", e)

        return jsonify({
            "reply": "Sorry, I could not connect to the local AI model."
        }), 500


# ============================================================
# START FLASK SERVER
# ============================================================

if __name__ == "__main__":
    app.run(debug=False)

