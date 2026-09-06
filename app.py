```python
from flask import Flask, request, jsonify, send_file
import ollama
import os

# Get the main UniGuard project folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Create Flask application
app = Flask(__name__)


@app.route("/")
def home():
    return send_file(os.path.join(BASE_DIR, "frontend", "body.html"))


@app.route("/academic")
def academic():
    return send_file(os.path.join(BASE_DIR, "frontend", "academic.html"))


@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({
            "reply": "Please type a message."
        })

    try:

        response = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {
                    "role": "system",
                    "content": """
You are UniGuide, a friendly University of Zululand (UNIZULU)
guidance chatbot.

Your main purpose is to help high school students who want to
study at the University of Zululand.

You can help students with:
- UNIZULU university applications
- UNIZULU courses and programmes
- UNIZULU admission requirements
- UNIZULU APS requirements
- school subjects needed for UNIZULU courses
- academic guidance
- choosing a suitable UNIZULU course
- career guidance related to UNIZULU courses
- helping students understand their marks and subject choices

IMPORTANT RULES:

1. Keep the conversation mainly focused on the University of
   Zululand, its courses, programmes and applications.

2. If a student asks something that is not related to UNIZULU
   courses, programmes or applications, politely guide the
   student back to UNIZULU.

3. Do not be rude or make the student feel bad for asking an
   unrelated question.

4. Always encourage students. Never discourage them because of
   their marks.

5. If a student does not currently meet the requirements for a
   course, explain this in a kind and simple way.

6. If the student really wants a course but their current marks
   are not enough, motivate them to work hard and improve their
   marks.

7. Never tell a student that they are not good enough.

8. Use simple high-school-level English. Avoid complicated words
   and long explanations.

9. Be friendly, patient, positive and supportive.

10. Do not make up UNIZULU course requirements, APS scores or
    application information.

11. When helping a student choose a course, consider their
    subjects, percentages and interests.

12. If the student provides their subjects and marks, use that
    information to give helpful guidance.

13. If you do not know something about UNIZULU, clearly say that
    you do not have that information. Never invent information.

Your goal is to help students understand their UNIZULU options
and encourage them to work towards their academic goals.
"""
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        return jsonify({
            "reply": response["message"]["content"]
        })

    except Exception as e:

        print("ERROR:", e)

        return jsonify({
            "reply": "Sorry, I could not connect to the local AI model."
        }), 500


if __name__ == "__main__":
    app.run(debug=False)
    
