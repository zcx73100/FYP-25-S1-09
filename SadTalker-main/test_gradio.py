import os
import shutil
import gradio as gr

# Ensure upload directories exist
image_dir = "uploads/images"
audio_dir = "uploads/audio"
os.makedirs(image_dir, exist_ok=True)
os.makedirs(audio_dir, exist_ok=True)

def handle_upload(image_file, audio_file):
    results = []
    
    # Process image upload
    if image_file:
        image_filename = os.path.basename(image_file)
        image_path = os.path.join(image_dir, image_filename)
        shutil.move(image_file, image_path)  # ✅ Fix: Use shutil.move()
        results.append(f"✅ Image uploaded successfully: {image_path}")
    
    # Process audio upload
    if audio_file:
        audio_filename = os.path.basename(audio_file)
        audio_path = os.path.join(audio_dir, audio_filename)
        shutil.move(audio_file, audio_path)  # ✅ Fix: Use shutil.move()
        results.append(f"🎵 Audio uploaded successfully: {audio_path}")
    
    return results if results else ["⚠️ No files uploaded."]

# UI Components
image_input = gr.File(label="Upload Image", type="filepath", file_types=[".jpg", ".png"])
audio_input = gr.File(label="Upload Audio", type="filepath", file_types=[".wav", ".mp3"])
output_text = gr.Textbox(label="Upload Result", lines=2)

# Create Interface
gr.Interface(
    fn=handle_upload,
    inputs=[image_input, audio_input],
    outputs=output_text
).launch()
