import requests
import base64

# Replace with your actual public Gradio link
url = "https://YOUR_GRADIO_SUBDOMAIN.gradio.live/gradio_api/run/generate_talking_video"

# Load image and audio (use small test files)
def encode_file(path, mime):
    with open(path, "rb") as f:
        return {
            "name": path.split("/")[-1],
            "data": f"data:{mime};base64," + base64.b64encode(f.read()).decode(),
            "meta": {"_type": "gradio.FileData"}
        }

image = encode_file("test_avatar.jpg", "image/jpeg")
audio = encode_file("test_audio.wav", "audio/wav")

payload = {
    "data": [
        image,
        audio,
        "crop",    # preprocess_type
        False,     # is_still_mode
        False,     # enhancer
        2,         # batch_size
        "256",     # size_of_image
        0          # pose_style
    ]
}

response = requests.post(url, json=payload)
print("Status:", response.status_code)
print("Response:", response.text[:300])
