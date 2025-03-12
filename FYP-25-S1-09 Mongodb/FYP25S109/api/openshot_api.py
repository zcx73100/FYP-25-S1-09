import requests

API_URL = "https://cloud.openshot.org/api/"
API_KEY = "your-api-key-here"

def create_video_project(name="AI Video", width=1920, height=1080):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = {"name": name, "fps_num": 30, "fps_den": 1, "width": width, "height": height}
    
    response = requests.post(API_URL + "projects/", json=data, headers=headers)
    return response.json()  # Returns the project ID
