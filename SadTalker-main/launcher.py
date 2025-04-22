import gradio as gr
import uvicorn
import shutil
import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware  # ✅ ADD THIS

from app_sadtalker import generate_talking_video, fastapi_error_handler, sadtalker_interface

# ✅ Create FastAPI app
app = FastAPI()

# ✅ Allow cross-origin requests from frontend (Flask on port 5000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5000"],  # or ["*"] if you want everything open
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "SadTalker API is running 🚀"}

# ✅ Mount Gradio app
app = gr.mount_gradio_app(app, sadtalker_interface, path="/gradio")

# ✅ Add custom POST route
@app.post("/generate_video_fastapi")
async def generate_video_fastapi(
    image_file: UploadFile = File(...),
    audio_file: UploadFile = File(...),
    preprocess_type: str = Form("crop"),
    is_still_mode: bool = Form(False),
    enhancer: bool = Form(False),
    batch_size: int = Form(2),
    size_of_image: int = Form(256),
    pose_style: int = Form(0)
):
    import tempfile
    import uuid

    image_ext = os.path.splitext(image_file.filename)[-1]
    audio_ext = os.path.splitext(audio_file.filename)[-1]

    image_path = os.path.join(tempfile.gettempdir(), f"avatar_{uuid.uuid4().hex}{image_ext}")
    audio_path = os.path.join(tempfile.gettempdir(), f"audio_{uuid.uuid4().hex}{audio_ext}")

    with open(image_path, "wb") as f:
        shutil.copyfileobj(image_file.file, f)
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)


    video_url = generate_talking_video(
        image_path, audio_path,
        preprocess_type, is_still_mode, enhancer,
        batch_size, size_of_image, pose_style
    )

    if video_url and video_url.startswith("/static/"):
        video_filename = os.path.basename(video_url)
        correct_path = os.path.abspath(
            os.path.join("C:/Users/atomi/Documents/GitHub/FYP-25-S1-09/FYP-25-S1-09 Mongodb Voice Generate/FYP25S109/static/generated_videos", video_filename)
        )
        return {
            "video_path": correct_path,
            "video_url": video_url
        }
    else:
        return {"error": "Video generation failed."}

# ✅ Progress API
@app.get("/status")
def get_status():
    try:
        with open("status.txt", "r") as f:
            return {"message": f.read().strip()}
    except:
        return {"message": ""}


@app.get("/progress")
def get_progress():
    try:
        with open("progress.txt", "r") as f:
            value = f.read().strip()
            if value == "done":
                return {"progress": 100}
            current, total = map(int, value.split("/"))
            return {"progress": round((current / total) * 100, 2)}
    except:
        return {"progress": 0}

# ✅ Register error handler
app.add_exception_handler(RequestValidationError, fastapi_error_handler)

# ✅ Start server
if __name__ == "__main__":
    print("🚀 Running FastAPI + Gradio at http://127.0.0.1:7860/")
    uvicorn.run(app, host="127.0.0.1", port=7860)
