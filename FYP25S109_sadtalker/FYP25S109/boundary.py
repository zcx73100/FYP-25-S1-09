import os
import subprocess
from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename

boundary_sadtalker = Blueprint('boundary_sadtalker', __name__)

@boundary_sadtalker.route('/form', methods=['GET'])
def sadtalker_form():
    """
    A simple route to show the SadTalker upload form.
    The template can be named sadtalker_form.html, placed in a templates folder
    within this sub-project or in a shared templates folder.
    """
    return render_template("sadtalker_form.html")

@boundary_sadtalker.route('/run', methods=['POST'])
def run_sadtalker():
    """
    Receives the uploaded image/video & audio, calls local SadTalker code,
    and returns the result page.
    """
    image_file = request.files.get('image_file')
    audio_file = request.files.get('audio_file')
    if not image_file or not audio_file:
        flash("Both an image/video and an audio file are required!", "error")
        return redirect(url_for('boundary_sadtalker.sadtalker_form'))

    # 1. Secure the filenames
    image_filename = secure_filename(image_file.filename)
    audio_filename = secure_filename(audio_file.filename)

    # 2. Build a path to your main app's results folder: FYP25S109\static\uploads\results
    # We'll do this by going up from the current file's directory.
    # "FYP-25-S1-09 Sadtalker" is presumably 1 level below your project root:
    # e.g.  <project_root>/FYP-25-S1-09 Sadtalker
    # We want <project_root>/FYP25S109/static/uploads/results
    sadtalker_dir = os.path.dirname(os.path.abspath(__file__))         # e.g. .../FYP-25-S1-09 Sadtalker
    project_root = os.path.dirname(sadtalker_dir)                      # e.g. .../FYP-25-S1-09
    fyp_dir = os.path.join(project_root, "FYP25S109")                  # e.g. .../FYP-25-S1-09/FYP25S109
    results_dir = os.path.join(fyp_dir, "static", "uploads", "results")
    os.makedirs(results_dir, exist_ok=True)

    # 3. Save the uploaded files into a subfolder for input
    input_folder = os.path.join(results_dir, "temp_input")
    os.makedirs(input_folder, exist_ok=True)

    image_path = os.path.join(input_folder, image_filename)
    audio_path = os.path.join(input_folder, audio_filename)
    image_file.save(image_path)
    audio_file.save(audio_path)

    # 4. Build the path to SadTalker's inference.py
    #    We'll assume SadTalker is also in the project root:
    #    <project_root>/SadTalker/inference.py
    sad_inference = os.path.join(project_root, "SadTalker", "inference.py")
    sad_inference = os.path.abspath(sad_inference)

    # 5. Call SadTalker via subprocess
    command = [
        "python", sad_inference,
        "--driven_audio", audio_path,
        "--source_image", image_path,
        "--result_dir", results_dir,
        "--still",
        "--preprocess", "full",
        "--enhancer", "gfpgan"
    ]

    try:
        proc = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        flash("SadTalker generation successful!", "success")
    except subprocess.CalledProcessError as e:
        flash(f"SadTalker failed: {e.stderr}", "error")
        return redirect(url_for('boundary_sadtalker.sadtalker_form'))

    # 6. Parse the final output from stdout
    final_video = None
    for line in proc.stdout.splitlines():
        if line.startswith("FINAL_OUTPUT:"):
            final_video = line.split("FINAL_OUTPUT:")[1].strip()
            break

    if not final_video or not os.path.exists(final_video):
        flash("Final video not found. Please try again.", "error")
        return redirect(url_for('boundary_sadtalker.sadtalker_form'))

    # 7. Convert the final_video path into a relative path from FYP25S109\static,
    #    so that your main app can serve it from /static/... if you want to display it.
    static_folder = os.path.join(fyp_dir, "static")  # e.g. .../FYP25S109/static
    rel_path = os.path.relpath(final_video, static_folder)
    video_url = "/static/" + rel_path.replace("\\", "/")

    # 8. Render a result template (e.g. sadtalker_result.html)
    #    that displays the video from video_url
    return render_template("sadtalker_result.html", video_url=video_url, video_path=final_video)

@boundary_sadtalker.route('/clear', methods=['POST'])
def clear_results():
    """
    Optionally clear everything in the results folder or just redirect to form.
    """
    flash("Clearing results. Starting fresh.", "info")
    return redirect(url_for('boundary_sadtalker.sadtalker_form'))
