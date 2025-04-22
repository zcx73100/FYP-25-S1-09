import os
import gradio as gr
from src.gradio_demo import SadTalker
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request

# ✅ Core function
import shutil

# Define absolute paths
SADTALKER_RESULTS_DIR = os.path.abspath("C:/Users/atomi/Documents/GitHub/FYP-25-S1-09/SadTalker-main/results")  # Update this if needed
FLASK_STATIC_VIDEOS = os.path.abspath("C:/Users/atomi/Documents/GitHub/FYP-25-S1-09/FYP-25-S1-09 Mongodb Voice Generate/FYP25S109/static/generated_videos")

# Ensure Flask's static video folder exists
os.makedirs(FLASK_STATIC_VIDEOS, exist_ok=True)

def update_progress(step, total=6, message=""):
    with open("progress.txt", "w", encoding="utf-8") as f:
        f.write(f"{step}/{total}")
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(message)


def generate_talking_video(image_path, audio_path, preprocess_type, is_still_mode, enhancer, batch_size, size_of_image, pose_style):
    try:
        update_progress(1, 6, "🔧 Initializing SadTalker...")
        sad_talker = SadTalker('checkpoints', 'src/config', lazy_load=True)

        update_progress(2, 6, "🎨 Preparing inputs...")

        update_progress(3, 6, "🧠 Generating Talking Video...")

        print(f"[CALL] sad_talker.test(...) with:\n image={image_path}\n audio={audio_path}")

        video_path = sad_talker.test(
            image_path,
            audio_path,
            preprocess_type,
            is_still_mode,
            enhancer,
            batch_size,
            size_of_image,
            pose_style
        )

        print(f"[RETURN] sad_talker.test() → {video_path}")

        # ⛔ If SadTalker fails and returns None
        if not video_path or not os.path.exists(video_path):
            print(f"❌ SadTalker did not generate a valid video. video_path: {video_path}")
            return None

        update_progress(4, 6, "📦 Moving video to static folder...")

        abs_video_path = os.path.abspath(video_path)
        safe_filename = os.path.basename(video_path).replace("##", "_")
        final_video_path = os.path.join(FLASK_STATIC_VIDEOS, safe_filename)

        shutil.move(abs_video_path, final_video_path)

        update_progress(5, 6, "✅ Finalizing...")

        update_progress(6, 6, "✅ Done.")
        print(f"[✅] Video moved to: {final_video_path}")
        return f"/static/generated_videos/{safe_filename}"

    except Exception as e:
        print("❌ Error during generation:", repr(e))
        return None  # Return None to trigger 500 in Flask or frontend



# ✅ Gradio REST interface using 3.41-safe config
sadtalker_interface = gr.Interface(
    fn=generate_talking_video,
    inputs=[
        gr.File(label="Upload Image", type="filepath", file_types=[".jpg", ".png"]),
        gr.File(label="Upload Audio", type="filepath", file_types=[".wav", ".mp3"]),
        gr.Radio(['crop', 'resize', 'full', 'extcrop', 'extfull'], value='crop', label="Preprocess Type"),
        gr.Checkbox(label="Still Mode (Less head movement)"),
        gr.Checkbox(label="Use GFPGAN Face Enhancer"),
        gr.Slider(1, 10, step=1, value=2, label="Batch Size"),
        gr.Radio([256, 512], value=256, label="Face Model Resolution"),
        gr.Slider(0, 46, step=1, value=0, label="Pose Style")
    ],
    outputs=gr.File(label="Generated Video"),
    title="SadTalker REST API",
    allow_flagging="never",
    live=False,
    api_name="generate_talking_video"  # ✅ This must be set here
).queue()

# ✅ FastAPI error handler
async def safe_validation_exception_handler(request: Request, exc: RequestValidationError):
    print("⚠️ Validation error occurred. Using safe handler.")
    try:
        safe_errors = []
        for err in exc.errors():
            safe_err = {k: repr(v[:100]) if isinstance(v, bytes) else v for k, v in err.items()}
            safe_errors.append(safe_err)
        return JSONResponse(status_code=400, content={"detail": safe_errors})
    except Exception as e:
        print("❌ Failed to encode validation error:", repr(e))
        return JSONResponse(status_code=500, content={"detail": "Internal error during validation failure."})

fastapi_error_handler = safe_validation_exception_handler
