from flask import Blueprint, request, jsonify
import requests

chatbot = Blueprint('chatbot', __name__)

API_KEY = "INSERT API KEY HERE"

# Model:openchat
MODEL = "openchat/openchat-7b:free"

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
            {"role": "system", "content": "You are a helpful AI tutor."},
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
