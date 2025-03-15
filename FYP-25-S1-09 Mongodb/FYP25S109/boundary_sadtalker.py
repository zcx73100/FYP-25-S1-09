import os
import subprocess
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from datetime import datetime

boundary_sadtalker = Blueprint('boundary_sadtalker', __name__)

@boundary_sadtalker.route('/form', methods=['GET'])
def sadtalker_form():
    return render_template("sadtalker_form.html")

@boundary_sadtalker.route('/run', methods=['POST'])
def run_sadtalker():
    """
    Receives uploaded image/audio, calls SadTalker's inference, and displays the result.
    """
    image_file = request.files.get('image_file')
    audio_file = request.files.get('audio_file')
    if not image_file or not audio_file:
        flash("Both image and audio files are required!", "error")
        return redirect(url_for('boundary_sadtalker.sadtalker_form'))
    
    # Use the main app’s static folder (e.g., FYP25S109/static)
    static_folder = current_app.static_folder  # e.g. ...\FYP-25-S1-09 Mongodb\FYP25S109\static
    
    # We want results in: static/sadtalker_results
    results_dir = os.path.join(static_folder, "sadtalker_results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Save inputs in a temporary subfolder
    input_folder = os.path.join(results_dir, "temp_input")
    os.makedirs(input_folder, exist_ok=True)
    image_filename = secure_filename(image_file.filename)
    audio_filename = secure_filename(audio_file.filename)
    image_path = os.path.join(input_folder, image_filename)
    audio_path = os.path.join(input_folder, audio_filename)
    image_file.save(image_path)
    audio_file.save(audio_path)
    
    # --- ADJUSTED PATH BUILDING LOGIC ---
    # Go up three levels from static folder:
    #  1) ...\FYP25S109\static -> ...\FYP25S109
    #  2) ...\FYP25S109       -> ...\FYP-25-S1-09 Mongodb
    #  3) ...\FYP-25-S1-09 Mongodb -> ...\FYP-25-S1-09
    level1 = os.path.dirname(static_folder)    # e.g. ...\FYP25S109
    level2 = os.path.dirname(level1)           # e.g. ...\FYP-25-S1-09 Mongodb
    project_root = os.path.dirname(level2)     # e.g. ...\FYP-25-S1-09
    
    # Now append SadTalker\inference.py
    sad_inference = os.path.join(project_root, "SadTalker", "inference.py")
    sad_inference = os.path.abspath(sad_inference)
    
    # Build the command
    command = [
        "python", sad_inference,
        "--driven_audio", audio_path,
        "--source_image", image_path,
        "--result_dir", results_dir,
        "--still",
        "--preprocess", "crop",
        #"--preprocess", "full",
        "--enhancer", "gfpgan"
    ]
    
    try:
        proc = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        flash("SadTalker generation successful!", "success")
    except subprocess.CalledProcessError as e:
        flash(f"SadTalker failed: {e.stderr}", "error")
        return redirect(url_for('boundary_sadtalker.sadtalker_form'))
    
    # Parse the final output for the final video path
    final_video = None
    for line in proc.stdout.splitlines():
        if line.startswith("FINAL_OUTPUT:"):
            final_video = line.split("FINAL_OUTPUT:")[1].strip()
            break
    
    if not final_video or not os.path.exists(final_video):
        flash("Final video not found. Please try again.", "error")
        return redirect(url_for('boundary_sadtalker.sadtalker_form'))
    
    # Convert final_video absolute path to a URL relative to static_folder
    rel_path = os.path.relpath(final_video, static_folder)
    video_url = "/static/" + rel_path.replace(os.path.sep, "/")
    
    return render_template("sadtalker_result.html", video_url=video_url, video_path=final_video)

@boundary_sadtalker.route('/clear', methods=['POST'])
def clear_results():
    flash("Clearing results. Starting fresh.", "info")
    return redirect(url_for('boundary_sadtalker.sadtalker_form'))
