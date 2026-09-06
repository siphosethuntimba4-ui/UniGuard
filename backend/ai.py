import ollama

from database import get_all_qualifications


# ============================================================
# UNIGUIDE AI
# ============================================================

def ask_uniguide(user_message):
    """
    Send the student's message to Ollama together with
    UNIZULU qualification information from SQLite.
    """

    # Get the real UNIZULU qualifications from SQLite
    qualifications = get_all_qualifications()

    # Build a compact database context for the AI
    database_context = ""

    for q in qualifications:

        database_context += f"""
Qualification: {q['name']}
Faculty: {q['faculty']}
Department: {q['department']}
Duration: {q['duration']} years
Minimum APS: {q['minimum_aps']}
Admission requirement: {q['admission_description']}
Description: {q['description']}
---
"""

    # Send the student question and database information to Ollama
    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "system",
                "content": f"""
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

1. Keep the conversation mainly focused on UNIZULU.

2. Use the UNIZULU database information provided below when
   discussing qualifications and admission requirements.

3. Do NOT invent course names, APS requirements or admission
   requirements.

4. If the database does not contain the requested information,
   clearly tell the student that the information is not available
   in the current UniGuide database.

5. If a student provides subjects and marks, use that information
   to give helpful guidance.

6. If a student does not meet a requirement, explain this kindly.

7. Never tell a student that they are not good enough.

8. Encourage students to improve their marks where appropriate.

9. Use simple high-school-level English.

10. Be friendly, patient, positive and supportive.

11. If the question is unrelated to UNIZULU, politely guide the
    student back to UNIZULU.

12. When recommending qualifications, show the qualification name,
    minimum APS and relevant admission requirement.

13. Do not claim that a student is officially admitted. UniGuide
    only provides guidance based on the information in its
    database.

============================================================
UNIZULU DATABASE
============================================================

{database_context}

============================================================
END DATABASE
============================================================
"""
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    return response["message"]["content"]