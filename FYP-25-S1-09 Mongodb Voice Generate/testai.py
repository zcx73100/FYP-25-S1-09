import requests

API_KEY = "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"
MODEL = "openchat/openchat-7b:free"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "You are a helpful AI tutor."},
        {"role": "user", "content": "Can you explain how AI works in simple terms?"}
    ]
}

response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)

if response.status_code == 200:
    data = response.json()
    print("✅ AI Reply:", data["choices"][0]["message"]["content"])
else:
    print("❌ Error:", response.status_code)
    print("Response:", response.text)
