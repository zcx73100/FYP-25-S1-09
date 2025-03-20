import os
import requests

# ✅ API Endpoint
SADTALKER_API_URL = "http://127.0.0.1:7860/gradio_api/run/generate_talking_video"

# ✅ File Paths
image_path = "FYP25S109/static/uploads/avatar/processed_image_11.jpg"
audio_path = "FYP25S109/static/generated_audios/6441281422125717407.wav"

# ✅ Check if files exist before sending request
if not os.path.exists(image_path):
    print(f"❌ Avatar file not found: {image_path}")
if not os.path.exists(audio_path):
    print(f"❌ Audio file not found: {audio_path}")

try:
    # ✅ Prepare file upload
    with open(image_path, 'rb') as image_file, open(audio_path, 'rb') as audio_file:
        files = {
            "image_file": (os.path.basename(image_path), image_file, "image/jpeg"),
            "audio_file": (os.path.basename(audio_path), audio_file, "audio/wav"),
        }

        # ✅ API Parameters
        payload = {
            "preprocess_type": "crop",
            "is_still_mode": "true",
            "enhancer": "true",
            "batch_size": "2",
            "size_of_image": "256",
            "pose_style": "0",
        }

        # ✅ Send API Request
        response = requests.post(SADTALKER_API_URL, files=files, data=payload)

        # ✅ Check API Response
        if response.status_code == 200:
            try:
                result = response.json()  # Ensure JSON response
                video_path = result.get("video_path")
                if video_path:
                    print(f"✅ Video Generated Successfully: {video_path}")
                else:
                    print("❌ No video path received from API.")
            except requests.exceptions.JSONDecodeError:
                print("❌ API returned binary data instead of JSON!")
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")

except requests.exceptions.RequestException as e:
    print(f"❌ API Request Failed: {e}")
