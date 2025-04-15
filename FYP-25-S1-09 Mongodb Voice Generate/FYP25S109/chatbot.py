from flask import Blueprint, request, jsonify
import requests

chatbot = Blueprint('chatbot', __name__)

API_KEY = "your_api_key_here"

# Model:deepseek
MODEL = "deepseek/deepseek-chat-v3-0324:free"

@chatbot.route("/api/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
    "model": MODEL,
    "messages": [
        {
            "role": "system",
            "content": """
You are EduMate, the built-in virtual assistant for an AI-powered Learning Management System (LMS).
This LMS is designed to enhance education through interactive face animation technology.
Your job is to guide users—students and teachers—through the platform and help them make the most of its features.

The LMS offers:
- Animated AI avatars to make learning more engaging.
- Teachers can create and deliver lessons through animated characters.
- Students can access tutorials, take quizzes, and track their learning progress.
- Built-in discussion boards for collaborative learning.
- Face animation tech that mimics human expressions for more immersive online learning.

When responding:
- Speak like a friendly, clear, and helpful digital assistant.
- Offer real guidance or suggestions like you would in a live LMS dashboard.
- If you don’t know the answer, recommend the user contacts support or checks the help section.

Stay professional, informative, and approachable — like a feature users would love to interact with every day.
"""
        },
        {"role": "user", "content": user_message}
    ]
}

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
