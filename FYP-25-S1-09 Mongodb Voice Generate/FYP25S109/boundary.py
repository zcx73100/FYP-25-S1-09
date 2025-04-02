from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify, send_from_directory
from . import mongo
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from bson import ObjectId
from markupsafe import Markup
import base64
import mimetypes
import threading
import time
from flask import Flask, send_file, Response
from gradio_client import Client
from FYP25S109.controller import *
from FYP25S109.entity import * 


boundary = Blueprint('boundary', __name__)
UPLOAD_FOLDER = 'FYP25S109/static/uploads/materials'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ASSIGNMENT_UPLOAD_FOLDER = 'FYP25S109/static/uploads/assignments'
os.makedirs(ASSIGNMENT_UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt'}

YOUR_DOMAIN = "http://localhost:5000"
# API_URL = "https://vinthony-sadtalker.hf.space/--replicas/55zml"
#client = Client(API_URL)

GENERATE_FOLDER_AUDIOS = 'FYP25S109/static/generated_audios'
GENERATE_FOLDER_VIDEOS = 'FYP25S109/static/generated_videos'
os.makedirs(GENERATE_FOLDER_AUDIOS, exist_ok=True)
os.makedirs(GENERATE_FOLDER_VIDEOS, exist_ok=True)

def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Homepage
class HomePage:
    @staticmethod
    @boundary.route('/')
    def home():
        teacher_users = [user["username"] for user in mongo.db.useraccount.find({"role": "Teacher"}, {"username": 1})]
        teacher_videos = list(mongo.db.tutorialvideo.find(
            {"username": {"$in": teacher_users}},
            {}
        ))

        admin_users = [user["username"] for user in mongo.db.useraccount.find({"role": "Admin"}, {"username": 1})]
        admin_videos = list(mongo.db.tutorialvideo.find(
            {"username": {"$in": admin_users}},
            {}
        ))

        avatars = list(mongo.db.avatar.find({}, {}))
        username = session.get("username", None)
        role = session.get("role", None)

        classrooms = []

        if role == "Teacher":
            classrooms = list(mongo.db.classroom.find(
                {"teacher": username},
                {"_id": 1, "classroom_name": 1, "description": 1}
            ))

        elif role == "Student":
            classrooms = list(mongo.db.classroom.find(
                {"student_list": username},
                {"_id": 1, "classroom_name": 1, "description": 1}
            ))

        elif role == "Admin":
            classrooms = list(mongo.db.classroom.find(
                {},  # ✅ No filter, Admins see all classrooms
                {"_id": 1, "classroom_name": 1, "description": 1}
            ))

        # ✅ Extract classroom _ids
        classroom_ids = [classroom["_id"] for classroom in classrooms]

        # ✅ Fetch Classroom-Specific Announcements, Materials, Assignments, and Quizzes by _id
        announcements = {classroom["_id"]: list(mongo.db.announcements.find(
            {"classroom_id": classroom["_id"]},
            {"_id": 1, "title": 1, "content": 1, "created_at": 1}
        )) for classroom in classrooms}

        materials = {classroom["_id"]: list(mongo.db.materials.find(
            {"classroom_id": classroom["_id"]}, # ✅ Filter by classroom_id
            {"_id": 1, "title": 1}
        )) for classroom in classrooms}

        assignments = {classroom["_id"]: list(mongo.db.assignments.find(
            {"classroom_id": classroom["_id"]}, # ✅ Filter by classroom_id
            {"_id": 1, "title": 1}
        )) for classroom in classrooms}

        quizzes = {str(classroom["_id"]): list(mongo.db.quizzes.find(
            {"classroom_id": ObjectId(classroom["_id"])},  # ✅ Filter by classroom_id
            {"_id": 1, "title": 1}
        )) for classroom in classrooms}

        return render_template(
            "homepage.html",
            videos=admin_videos + teacher_videos,  # ✅ Videos Restored
            avatars=avatars,  # ✅ Avatars Restored
            username=username,
            classrooms=classrooms,
            announcements=announcements,  # ✅ Announcements Moved Inside Classroom Box
            materials=materials,  # ✅ Materials first
            assignments=assignments,  # ✅ Assignments second
            quizzes=quizzes  # ✅ Quizzes last
        )

      
        
# Generate Video
"""
video_progress = {}

@boundary.route("/generate_voice", methods=["POST"])
def generate_voice():
    try:
        data = request.get_json()
        text = data.get("text")

        if not text:
            print("❌ Error: No text received!")
            return jsonify({"success": False, "error": "Text is required"}), 400

        print(f"📝 Received text for voice generation: {text}")

        # ✅ Generate voice
        voice_entity = GenerateVideoEntity(text)
        audio_url = voice_entity.generate_voice()

        # ✅ Debugging: Ensure file exists
        audio_filename = os.path.basename(audio_url)
        audio_path = os.path.join("FYP25S109", "static", "generated_audios", audio_filename)
        print(f"🔍 Checking if audio file exists: {audio_path}")

        if not os.path.exists(audio_path):
            print(f"❌ ERROR: Audio file was NOT saved at {audio_path}")
            return jsonify({"success": False, "error": "Failed to save audio file"}), 500

        print(f"✅ Audio file saved successfully: {audio_path}")
        return jsonify({"success": True, "audio_url": audio_url})

    except Exception as e:
        print(f"❌ Server error: {e}")
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500

@boundary.route("/generate_video", methods=["GET", "POST"])
def generate_video():
    try:
        if request.method == "GET":
            print("📄 GET request received → Loading generate video page...")
            avatars = list(mongo.db.avatar.find({}, {"_id": 0, "file_path": 1, "avatarname": 1}))
            return render_template("generateVideo.html", avatars=avatars)  # Load the page

        elif request.method == "POST":
            print("📥 POST request received → Generating video...")
            data = request.get_json()

            if not data:
                print("❌ Error: No data received!")
                return jsonify({"success": False, "error": "No data received"}), 400

            print(f"🔹 Request Data: {data}")

            text = data.get("text")
            avatar_path = os.path.join("FYP25S109/static", data.get("selected_avatar")).replace("\\", "/")
            audio_path = os.path.join("FYP25S109", data.get("audio_path").lstrip("/")).replace("\\", "/")

            if not text or not avatar_path or not audio_path:
                print("❌ Missing required parameters!")
                return jsonify({"success": False, "error": "Text, avatar, and audio are required!"}), 400

            print(f"🖼️ Avatar URL: {avatar_path}")
            print(f"🔊 Audio URL: {audio_path}")

            # ✅ Call the entity to generate video
            video_entity = GenerateVideoEntity(text, avatar_path)
            video_url = video_entity.generate_video()  # No need to pass audio_path here

            if not video_url:
                print("❌ Video generation failed!")
                return jsonify({"success": False, "error": "Failed to generate video"}), 500

            print(f"✅ Video generated: {video_url}")
            return jsonify({"success": True, "video_url": video_url})

    except Exception as e:
        print(f"❌ Server error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



def process_video(video_id, text, avatar_path, audio_path):
    try:
        for i in range(0, 101, 10):
            video_progress[video_id] = i
            time.sleep(3)  # Simulate processing time

        print(f"🎬 Sending request to SadTalker API with Avatar: {avatar_path} and Audio: {audio_path}")
        result = client.predict(avatar_path, audio_path, "crop", True, True, 0, "256", 0, fn_index=0)

        if not result:
            print("❌ SadTalker API failed to return a video URL!")
            video_progress[video_id] = -1
            return None  # Return None on failure

        # ✅ Extract video path and update progress
        video_filename = os.path.basename(result)
        video_path = f"/static/generated_videos/{video_filename}"
        video_progress[video_id] = 100
        print(f"✅ Video Processing Complete: {video_path}")
        return video_path  

    except Exception as e:
        print(f"❌ Error in video processing: {e}")
        video_progress[video_id] = -1
        return None


@boundary.route("/video_status", methods=["GET"])
def video_status():
    video_id = request.args.get("video_id")

    if video_id not in video_progress:
        return jsonify({"success": False, "error": "Invalid video ID"}), 400

    progress = video_progress[video_id]

    # Handle errors if video processing failed
    if progress == -1:
        return jsonify({"success": False, "error": "Video processing failed!"}), 500

    time_left = (100 - progress) // 10 * 3

    return jsonify({"success": True, "progress": progress, "time_left": time_left})
"""

# Generate Video Local
@boundary.route("/generate_voice", methods=["POST"])
def generate_voice():
    try:
        data = request.get_json()
        text = data.get("text")

        if not text:
            return jsonify({"success": False, "error": "Text is required"}), 400

        voice_entity = GenerateVideoEntity(text)
        audio_url = voice_entity.generate_voice()

        if not audio_url:
            return jsonify({"success": False, "error": "Voice generation failed"}), 500

        return jsonify({"success": True, "audio_url": audio_url})

    except Exception as e:
        return jsonify({"success": False, "error": repr(e)}), 500

# Generate Talking Video
@boundary.route("/status")
def proxy_status():
    return requests.get("http://127.0.0.1:7860/status").json()

@boundary.route("/progress")
def proxy_progress():
    try:
        response = requests.get("http://127.0.0.1:7860/progress")
        response.raise_for_status()  # 🚨 force error for non-200s
        return jsonify(response.json())
    except Exception as e:
        print(f"Progress fetch failed: {e}")  # ✅ useful log
        return jsonify({"progress": 0, "error": str(e)})

@boundary.route("/generate_video", methods=["GET", "POST"])
def generate_video():
    try:
        if request.method == "GET":
            avatars = list(mongo.db.avatar.find({}, {"_id": 0, "file_path": 1, "avatarname": 1}))
            return render_template("generateVideo.html", avatars=avatars)

        # POST — handle video generation request
        text = request.form.get("text")
        avatar_path = request.form.get("avatar_path")
        audio_path = request.form.get("audio_path")

        print("📥 Incoming POST /generate_video:")
        print("Text:", text)
        print("Avatar Path:", avatar_path)
        print("Audio Path:", audio_path)

        if not all([text, avatar_path, audio_path]):
            return jsonify({"success": False, "error": "Missing required parameters"}), 400

        # Rebuild absolute file paths from relative URLs
        avatar_path = os.path.join("FYP25S109", avatar_path.replace("/static/", "static/"))
        audio_path = os.path.join("FYP25S109", audio_path.replace("/static/", "static/"))

        if not os.path.exists(avatar_path):
            return jsonify({"success": False, "error": f"Avatar file not found: {avatar_path}"}), 404
        if not os.path.exists(audio_path):
            return jsonify({"success": False, "error": f"Audio file not found: {audio_path}"}), 404

        # Generate the video
        entity = GenerateVideoEntity(text, avatar_path, audio_path)
        video_url = entity.generate_video()

        if not video_url:
            return jsonify({"success": False, "error": "Video generation failed"}), 500

        return jsonify({"success": True, "video_url": video_url})

    except Exception as e:
        print(f"❌ Error in /generate_video route: {str(e)}")
        return jsonify({"success": False, "error": repr(e)}), 500

# Log In
class LoginBoundary:
    @staticmethod
    @boundary.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            # Fetch user from DB
            user = mongo.db.useraccount.find_one({"username": username})

            if user:
                # Check user status
                if user.get('status') == 'suspended':
                    flash('Your account is suspended. Please contact admin.', category='error')
                    return redirect(url_for('boundary.login'))
                elif user.get('status') == 'deleted':
                    flash('This account has been deleted.', category='error')
                    return redirect(url_for('boundary.login'))

                # Validate password
                stored_hashed_password = user["password"]
                if check_password_hash(stored_hashed_password, password):
                    # Successful login for active users only
                    session['username'] = username
                    session['role'] = user['role']
                    session['user_authenticated'] = True
                    flash(f'Login successful! You are logged in as {user["role"].capitalize()}.', category='success')
                    return redirect(url_for('boundary.home'))
                else:
                    flash('Wrong password.', category='error')
            else:
                flash('Username does not exist.', category='error')

        return render_template("login.html")

# Log Out
class LogoutBoundary:
    @staticmethod
    @boundary.route('/logout')
    def logout():
        session.clear()
        flash("You have been logged out.", category="info")
        return redirect(url_for('boundary.home'))

# Create Account
class CreateAccountBoundary:
    @staticmethod
    @boundary.route('/createAccount', methods=['GET', 'POST'])
    def sign_up():
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            name = request.form.get('name')
            surname = request.form.get('surname')
            date_of_birth = request.form.get('date_of_birth')
            password1 = request.form.get('password1')
            password2 = request.form.get('password2')
            role = "Student" if session.get('role') == "Teacher" else "User"

            # Check if the username already exists
            existing_user = mongo.db.useraccount.find_one({"username": username})
            if existing_user:
                flash('Username already taken. Please choose a different one.', category='error')
                return render_template("createAccount.html")

            if len(email) < 4:
                flash('Email must be greater than 3 characters.', category='error')
            elif len(name) < 2:
                flash('First name must be greater than 1 character.', category='error')
            elif password1 != password2:
                flash('Passwords do not match.', category='error')
            elif len(password1) < 7:
                flash('Password must be at least 7 characters.', category='error')
            else:
                try:
                    date_of_birth_obj = datetime.strptime(date_of_birth, '%Y-%m-%d')
                    formatted_date_of_birth = date_of_birth_obj.strftime('%Y-%m-%d')
                    hashed_password = generate_password_hash(password1, method='pbkdf2:sha256')
                    
                    # Insert the new user if all checks pass
                    mongo.db.useraccount.insert_one({
                        "username": username,
                        "password": hashed_password,
                        "email": email,
                        "role": role,
                        "name": name,
                        "surname": surname,
                        "date_of_birth": formatted_date_of_birth,
                        "status": "active"
                    })
                    flash(f'Account created successfully! Assigned Role: {role}', category='success')
                    return redirect(url_for('boundary.login'))
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', category='error')

        return render_template("createAccount.html")

# User Account Details
class AccountDetailsBoundary:
    @staticmethod
    @boundary.route('/accountDetails', methods=['GET'])
    def accDetails():
        if 'username' not in session:
            flash("You must be logged in to view account details.", category='error')
            return redirect(url_for('boundary.login'))
        username = session.get('username')
        user_info = mongo.db.useraccount.find_one(
            {"username": username},
            {"_id": 0, "username": 1, "name": 1, "surname": 1, "date_of_birth": 1, "email": 1, "role": 1}
        )
        if not user_info:
            flash("User details not found.", category='error')
            return redirect(url_for('boundary.home'))
        return render_template("accountDetails.html", user_info=user_info)

# Edit Account Details
class UpdateAccountDetailsBoundary:
    @staticmethod
    @boundary.route('/updateAccDetail', methods=['GET', 'POST'])
    def update_account_detail():
        if 'username' not in session:
            flash("You must be logged in to update account details.", category='error')
            return redirect(url_for('boundary.login'))
        username = session['username']
        if request.method == 'POST':
            updated_data = {
                "name": request.form.get("name"),
                "surname": request.form.get("surname"),
                "date_of_birth": request.form.get("date_of_birth"),
            }
            updated_data = {key: value for key, value in updated_data.items() if value}
            if UpdateAccountDetailController.update_account_detail(username, updated_data):
                flash("Account details updated successfully!", category='success')
            else:
                flash("Failed to update account details.", category='error')
            return redirect(url_for('boundary.accDetails'))
        user_info = DisplayUserDetailController.get_user_info(username)
        if not user_info:
            flash("User details not found.", category='error')
            return redirect(url_for('boundary.home'))
        return render_template("updateAccDetail.html", user_info=user_info)

# Update Password
class UpdatePasswordBoundary:
    @staticmethod
    @boundary.route('/update_password', methods=['GET', 'POST'])
    def update_password():
        if 'username' not in session:
            flash("You must be logged in to change your password.", category='error')
            return redirect(url_for('boundary.login'))
        username = session['username']
        if request.method == 'POST':
            old_password = request.form.get("old_password")
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")
            user = mongo.db.useraccount.find_one({"username": username})
            if not user:
                flash("User not found.", category='error')
                return redirect(url_for('boundary.accDetails'))
            stored_hashed_password = user.get("password")
            if not check_password_hash(stored_hashed_password, old_password):
                flash("Incorrect current password.", category='error')
                return redirect(url_for('boundary.update_password'))
            if new_password != confirm_password:
                flash("New passwords do not match.", category='error')
                return redirect(url_for('boundary.update_password'))
            if len(new_password) < 7:
                flash("New password must be at least 7 characters long.", category='error')
                return redirect(url_for('boundary.update_password'))
            hashed_new_password = generate_password_hash(new_password)
            update_result = mongo.db.useraccount.update_one(
                {"username": username},
                {"$set": {"password": hashed_new_password}}
            )
            if update_result.modified_count > 0:
                flash("Password updated successfully!", category='success')
                return redirect(url_for('boundary.accDetails'))
            else:
                flash("Failed to update password. Try again.", category='error')
        return render_template("updatePassword.html")

class ResetPasswordBoundary:
    @staticmethod
    @boundary.route('/resetPassword', methods=['GET', 'POST'])
    def reset_password():
        if request.method == 'POST':
            username = request.form.get("username")
            new_password = request.form.get("new_password")
            if len(new_password) < 7:
                flash("Password must be at least 7 characters long.", category="error")
                return redirect(url_for("boundary.reset_password"))
            if ResetPasswordController.reset_password(username, new_password):
                flash(f"Password reset for {username}.", category="success")
            else:
                flash("Failed to reset password. Ensure the username exists.", category="error")
            return redirect(url_for("boundary.reset_password"))
        return render_template("resetPassword.html")


# Search     
class SearchBoundary:
    @staticmethod
    @boundary.route('/search', methods=['GET'])
    def search():
        search_query = request.args.get('query', '').strip()
        filter_type = request.args.get('filter', 'video')

        print(f"Received Search Query: '{search_query}' | Filter: '{filter_type}'")

        if not search_query:
            flash("Please enter a search query.", category="error")
            return redirect(url_for('boundary.home'))

        if filter_type == 'video':
            search_results = SearchTutorialController.search_video(search_query)
        elif filter_type == 'avatar':
            search_results = SearchAvatarController.search_avatar(search_query)
        else:
            flash("Invalid filter type.", category="error")
            return redirect(url_for('boundary.home'))

        if not search_results:
            flash(f"No {filter_type} results found.", category="info")
        else:
            print(f"Found {len(search_results)} results.")

        return render_template("search.html", search_results=search_results, filter_type=filter_type)



# -------------------------------------------------------------ADMIN-----------------------------------------------
# Admin Create Account
class CreateAccountAdminBoundary:
    @staticmethod
    @boundary.route('/createAccountAdmin', methods=['GET', 'POST'])
    def create_account_admin():
        if session.get("role") != "Admin":
            flash("Unauthorized access! Only admins can create users.", category="error")
            return redirect(url_for("boundary.home"))
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            name = request.form.get('name')
            surname = request.form.get('surname')
            date_of_birth = request.form.get('date_of_birth')
            password1 = request.form.get('password1')
            password2 = request.form.get('password2')
            role = request.form.get('role')
            if password1 != password2:
                flash("Passwords do not match.", category="error")
                return redirect(url_for("boundary.create_account_admin"))
            valid_roles = ["Admin", "Teacher", "Student"]
            if role not in valid_roles:
                flash("Invalid role selection.", category="error")
                return redirect(url_for("boundary.create_account_admin"))
            hashed_password = generate_password_hash(password1, method='pbkdf2:sha256')
            try:
                date_of_birth_obj = datetime.strptime(date_of_birth, '%Y-%m-%d')
                formatted_date_of_birth = date_of_birth_obj.strftime('%Y-%m-%d')
                mongo.db.useraccount.insert_one({
                    "username": username,
                    "password": hashed_password,
                    "email": email,
                    "role": role,
                    "name": name,
                    "surname": surname,
                    "date_of_birth": formatted_date_of_birth,
                    "status": "active"
                })
                flash(f"Account created successfully! Assigned Role: {role}", category="success")
                return redirect(url_for("boundary.home"))
            except ValueError:
                flash("Invalid date format. Use YYYY-MM-DD.", category="error")
                return redirect(url_for("boundary.create_account_admin"))
        return render_template("createAccountAdmin.html")


# Admin Confirm Teacher
class ConfirmTeacherBoundary:
    @staticmethod
    @boundary.route('/confirmTeacher/', methods=['GET', 'POST'])
    def confirm_teacher_page():
        if session.get('role') != "Admin":
            flash("Access Denied! Only Admins can confirm teachers.", category="error")
            return redirect(url_for("boundary.home"))
        users = list(mongo.db.useraccount.find({"role": "User"}, {"_id": 0, "username": 1, "email": 1}))
        return render_template("confirmTeacher.html", users=users)

    @staticmethod
    @boundary.route('/confirmTeacher/<username>', methods=['POST'])
    def confirm_teacher(username):
        if session.get('role') != "Admin":
            flash("Access Denied!", category="error")
            return redirect(url_for("boundary.home"))
        update_result = mongo.db.useraccount.update_one(
            {"username": username, "role": "User"},
            {"$set": {"role": "Teacher"}}
        )
        if update_result.modified_count > 0:
            flash(f"{username} is now a Teacher!", category="success")
        else:
            flash("Failed to update role. Ensure the username exists and is not already a Teacher.", category="error")
        return redirect(url_for("boundary.confirm_teacher_page"))

# Admin Upload Tutorial Video
class UploadTutorialBoundary:
    UPLOAD_FOLDER_VIDEO = 'FYP25S109/static/uploads/videos/'
    ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in UploadTutorialBoundary.ALLOWED_EXTENSIONS

    @staticmethod
    @boundary.route('/uploadTutorial', methods=['GET', 'POST'])
    def upload_tutorial():
        if 'username' not in session:
            flash("You must be logged in to upload a tutorial video.", category='error')
            return redirect(url_for('boundary.login'))

        if request.method == 'POST':
            file = request.files.get('file')
            title = request.form.get("title")
            username = session.get("username")
            description = request.form.get("description")

            if not title:
                flash("Please provide a title for the video.", category='error')
                return redirect(url_for('boundary.upload_tutorial'))

            if not file or file.filename == '':
                flash("No file selected. Please upload a video file.", category='error')
                return redirect(url_for('boundary.upload_tutorial'))

            if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() not in UploadTutorialBoundary.ALLOWED_EXTENSIONS:
                flash("Invalid file type. Please upload a valid video file.", category='error')
                return redirect(url_for('boundary.upload_tutorial'))
            
            video = UploadTutorialController.upload_video(file, title, username, description)

            if video['success']:
                flash("Video uploaded successfully!", category='success')
                return redirect(url_for('boundary.view_uploaded_videos'))
            else:
                flash(f"Failed to upload video: {video['message']}", category='error')
                return redirect(url_for('boundary.upload_tutorial'))

        # 👇 Handle GET request (return the upload form)
        return render_template("uploadTutorial.html")

# View Uploaded Videos (Multiple Videos at one time)
class ViewUploadedVideosBoundary:
    @boundary.route('/video/<file_id>')
    def serve_video(file_id):
        try:
            grid_out = fs.get(ObjectId(file_id))
            file_size = grid_out.length
            range_header = request.headers.get('Range')

            if range_header:
                start, end = range_header.replace('bytes=', '').split('-')
                start = int(start)
                end = int(end) if end else file_size - 1
                length = end - start + 1

                grid_out.seek(start)  # Move to the requested byte position
                data = grid_out.read(length)

                response = Response(data, status=206, mimetype=grid_out.content_type)
                response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
                response.headers.add('Accept-Ranges', 'bytes')
                response.headers.add('Content-Length', str(length))
                return response

            # Full video response (if no Range header)
            return Response(grid_out.read(), mimetype=grid_out.content_type)

        except Exception as e:
            logging.error(f"Failed to serve video: {str(e)}")
            return "Video not found", 404
        
        
    @staticmethod
    @boundary.route('/uploadedVideos', methods=['GET'])
    def view_uploaded_videos():
        if 'username' not in session:
            flash("You must be logged in to view uploaded videos.", category='error')
            return redirect(url_for('boundary.login'))
        admin_videos = list(mongo.db.tutorialvideo.find(
            {"username": session['username']},
            {}
        ))
        return render_template("manageVideo.html", videos=admin_videos)
    

# View Uploaded Videos (Single Video)
class ViewSingleTutorialBoundary:
    @staticmethod
    @boundary.route('/viewTutorial/<video_name>', methods=['GET'])
    def view_tutorial(video_name):
        video = mongo.db.tutorialvideo.find_one({"video_name": video_name})
        if not video:
            flash("Video not found.", category='error')
            return redirect(url_for('boundary.home'))
        return render_template("viewTutorial.html", video=video)

#Delete Video
class DeleteUploadedVideosBoundary:
    @staticmethod
    @boundary.route('/deleteVideo/<video_name>', methods=['POST'])
    def delete_video(video_name):
        if 'username' not in session:
            flash("You must be logged in to delete a video.", category='error')
            return redirect(url_for('boundary.login'))
        video = mongo.db.tutorialvideo.find_one({"video_name": video_name})
        if not video:
            flash("Video not found.", category='error')
            return redirect(url_for('boundary.view_uploaded_videos'))
        try:
            mongo.db.tutorialvideo.delete_one({"video_name": video_name})
            flash("Video deleted successfully.", category='success')
        except Exception as e:
            flash(f"Failed to delete video: {str(e)}", category='error')
        return redirect(url_for('boundary.view_uploaded_videos'))

# Manage Avatar
class ManageAvatarBoundary:
    @staticmethod
    @boundary.route('/manage_avatars')
    def manage_avatars():
        if 'username' not in session:
            flash("You must be logged in to manage your avatar.", category='error')
            return redirect(url_for('boundary.login'))
        username = session.get('username')
        user_role = session.get('role')
        avatars = ManageAvatarController.get_avatars_by_username(username)
        if not avatars:
            flash("No avatars found for your account.", category='info')
        return render_template(
            "manage_avatars.html",
            username=username,
            user_role=user_role,
            avatars=avatars
        )

# Add Avatar
class AddAvatarBoundary:
    UPLOAD_FOLDER_AVATAR = 'FYP25S109/static/uploads/avatar/'

    @staticmethod
    @boundary.route('/create_avatar', methods=['GET', 'POST'])
    def create_avatar():
        if 'username' not in session:
            flash("You must be logged in to create an avatar.", category='error')
            return redirect(url_for('boundary.login'))

        if request.method == 'POST':
            username = session.get('username')
            avatar_file = request.files.get('avatar')
            avatarname = request.form.get('avatarname')  # ✅ Capture avatar name

            if not username or not avatar_file or not avatarname:
                flash("Username, avatar name, and avatar file are required.", category='error')
                return redirect(url_for('boundary.create_avatar'))

            result = AddAvatarController.add_avatar(username, avatarname, avatar_file)

            if result['success']:
                flash("Avatar added successfully.", category='success')
            else:
                flash(f"Failed to add avatar: {result['message']}", category='error')

            return redirect(url_for('boundary.create_avatar'))

        return render_template("admin_add_avatar.html")
    
class DeleteAvatarBoundary:
    @staticmethod
    @boundary.route('/admin_delete_avatar/<avatar_id>', methods=['POST'])
    def delete_avatar(avatar_id):
        if 'username' not in session:
            flash("You must be logged in to delete an avatar.", category='error')
            return redirect(url_for('boundary.login'))
        avatar = Avatar.find_by_id(avatar_id)
        if not avatar:
            flash("Avatar not found.", category='error')
            return redirect(url_for('boundary.manage_avatars'))
        if DeleteAvatarController.delete_avatar(avatar_id):
            flash("Avatar deleted successfully.", category='success')
        else:
            flash("Failed to delete avatar.", category='error')
        return redirect(url_for('boundary.manage_avatars'))
    
# Admin Manage User
class ManageUserBoundary:
    @staticmethod
    @boundary.route('/admin/manageUsers', methods=['GET'])
    def manage_users():
        # Ensure only admins can access this page
        if 'role' not in session or session.get('role') != 'Admin':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        # Fetch all users
        users = list(mongo.db.useraccount.find({}, {"_id": 0, "username": 1, "email": 1, "role": 1, "status": 1}))
        return render_template("manageUsers.html", users=users)

    @staticmethod
    @boundary.route('/admin/searchUser', methods=['GET'])
    def search_user():
        if 'role' not in session or session.get('role') != 'Admin':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        query = request.args.get('query', '')
        users = SearchAccountController.search_account(query)
        
        return render_template("manageUsers.html", users=users)

    @staticmethod
    @boundary.route('/admin/suspendUser/<username>', methods=['POST'])
    def suspend_user(username):
        if 'role' not in session or session.get('role') != 'Admin':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        result = mongo.db.useraccount.update_one(
            {"username": username},
            {"$set": {"status": "suspended"}}
        )

        if result.modified_count:
            flash(f"User {username} suspended successfully.", category='success')
        else:
            flash("User not found or already suspended.", category='error')

        return redirect(url_for('boundary.manage_users'))

# Delete User 
    @staticmethod
    @boundary.route('/admin/deleteUser/<username>', methods=['POST'])
    def delete_user(username):
        if 'role' not in session or session.get('role') != 'Admin':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        # Prevent self-deletion
        if username == session.get('username'):
            flash("You cannot delete your own account.", category='error')
            return redirect(url_for('ManageUserBoundary.manage_users'))

        # Permanently delete user from DB
        result = mongo.db.useraccount.delete_one({"username": username})

        if result.deleted_count:
            flash(f"User {username} permanently deleted.", category='success')
        else:
            flash("User not found.", category='error')

        return redirect(url_for('boundary.manage_users'))


# Reactivate User
    @staticmethod
    @boundary.route('/admin/activateUser/<username>', methods=['POST'])
    def activate_user(username):
        if 'role' not in session or session.get('role') != 'Admin':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        result = mongo.db.useraccount.update_one(
            {"username": username},
            {"$set": {"status": "active"}}
        )

        if result.modified_count:
            flash(f"User {username} reactivated successfully.", category='success')
        else:
            flash("Failed to reactivate user.", category='error')

        return redirect(url_for('boundary.manage_users'))
    
# -------------------------------------------------------------TEACHER-----------------------------------------------
# Teacher manage classrooms
class TeacherManageClassroomsBoundary:
    @staticmethod
    @boundary.route('/teacher/manageClassrooms', methods=['GET'])
    def manage_classrooms():
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))
        username = session.get('username')
        classrooms = list(mongo.db.classroom.find({"teacher": username}))
        return render_template("manageClassrooms.html", classrooms=classrooms)

class TeacherAddClassroomBoundary:
    @staticmethod
    @boundary.route('/teacher/addClassroom', methods=['GET', 'POST'])
    def add_classroom():
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        if request.method == 'POST':
            teacher = session.get('username')
            classroom_name = request.form.get('classroom_name')
            classroom_description = request.form.get('classroom_description')
            classroom_capacity = request.form.get('classroom_capacity')

            if not classroom_name:
                flash("Classroom name is required.", category='error')
                return redirect(url_for('boundary.add_classroom'))

            controller = AddClassroomController()
            result = controller.create_classroom(classroom_name, teacher, classroom_description, classroom_capacity)

            if result['success']:
                flash(result['message'], category='success')
                return redirect(url_for('boundary.manage_classrooms'))
            else:
                flash(result['message'], category='error')

        return render_template("addClassroom.html")

from datetime import datetime

class ViewClassRoomBoundary:
    @staticmethod
    @boundary.route('/viewClassroom/<classroom_id>', methods=['GET', 'POST'])
    def view_classroom(classroom_id):
        if 'role' not in session or session.get('role') not in ['Teacher', 'Student']:
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        # Fetch the classroom details
        classroom = mongo.db.classroom.find_one({"_id": ObjectId(classroom_id)})
        if not classroom:
            flash("Classroom not found.", category='error')
            return redirect(url_for('boundary.manage_classrooms'))

        # Role-based access control
        username = session.get('username')
        if session.get('role') == 'Student':
            student_list = classroom.get('student_list', [])
            if username.strip() not in [s.strip() for s in student_list]:
                flash("You are not enrolled in this classroom.", category='error')
                return redirect(url_for('boundary.home'))

        elif session.get('role') == 'Teacher':
            if username.strip() != classroom.get('teacher', '').strip():
                flash("You are not the teacher of this classroom.", category='error')
                return redirect(url_for('boundary.home'))
        # Fetch classroom data
        materials = list(mongo.db.materials.find({"classroom_id": ObjectId(classroom_id)}))
        assignments = list(mongo.db.assignments.find({"classroom_id": ObjectId(classroom_id)}))
        quizzes = list(mongo.db.quizzes.find({"classroom_id": ObjectId(classroom_id)}))

        # ✅ Fetch announcements for this classroom
        announcements = list(mongo.db.announcements.find(
            {"classroom_id": ObjectId(classroom_id)},
            {"_id": 0, "title": 1, "content": 1, "created_at": 1}
        ))

        # Convert due_date to readable format
        for assignment in assignments:
            if "due_date" in assignment and assignment["due_date"]:
                try:
                    assignment["due_date"] = datetime.strptime(assignment["due_date"], "%Y-%m-%dT%H:%M").strftime("%d %b %Y, %I:%M %p")
                except ValueError:
                    pass  # Keep as-is if conversion fails

        return render_template(
            "viewClassroom.html",
            classroom=classroom,
            materials=materials,
            assignments=assignments,
            quizzes=quizzes,
            announcements=announcements
        )

class TeacherDeleteClassroomBoundary:
    @staticmethod
    @boundary.route('/teacher/deleteClassroom/<classroom_id>', methods=['POST'])
    def delete_classroom(classroom_id):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        result = mongo.db.classroom.delete_one({"_id": ObjectId(classroom_id)})

        if result.deleted_count:
            flash(f"Classroom deleted successfully.", category='success')
        else:
            flash("Classroom not found.", category='error')

        return redirect(url_for('boundary.manage_classrooms'))

# Update classroom
class TeacherUpdateClassroomBoundary:
    @staticmethod
    @boundary.route('/teacher/updateClassroom/<classroom_id>', methods=['GET', 'POST'])
    def update_classroom(classroom_id):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        classroom = mongo.db.classroom.find_one({"_id": ObjectId(classroom_id)})

        if not classroom:
            flash("Classroom not found.", category='error')
            return redirect(url_for('boundary.manage_classrooms'))

        if request.method == 'POST':
            new_classroom_name = request.form.get('classroom_name')
            new_description = request.form.get('classroom_description')
            new_capacity = request.form.get('classroom_capacity')

            if not new_classroom_name:
                flash("Classroom name is required.", category='error')
                return redirect(url_for('boundary.update_classroom', classroom_id=classroom_id))

            result = UpdateClassroomController.update_classroom(ObjectId(classroom_id), new_details={
                "classroom_name": new_classroom_name,
                "description": new_description,
                "capacity": new_capacity
            })

            return redirect(url_for('boundary.manage_classrooms'))

        return render_template("updateClassroom.html", classroom=classroom)

class TeacherSearchClassroomBoundary:
    @staticmethod
    @boundary.route('/teacher/searchClassroom', methods=['GET', 'POST'])
    def search_classroom():
        query = request.args.get('query', '').strip() if request.method == 'GET' else request.form.get('query', '').strip()
        classrooms = SearchClassroomController.search_classroom(query)

        return render_template("ClassroomSearchResult.html", classrooms=classrooms, query=query)

class TeacherManageStudentsBoundary:
    @staticmethod
    @boundary.route('/teacher/manageStudents/<classroom_id>', methods=['GET', 'POST'])
    def manage_students(classroom_id):
        # Retrieve classroom document using classroom_id
        classroom = mongo.db.classroom.find_one({"_id": ObjectId(classroom_id)})

        if not classroom:
            flash("Classroom not found.", category='error')
            return redirect(url_for('boundary.manage_classrooms'))

        # Extract student usernames from the classroom's 'student_list' array
        enrolled_usernames = classroom.get('student_list', [])

        # Fetch all students from the useraccount collection
        all_students = list(mongo.db.useraccount.find({"role": "Student"}))

        # Separate enrolled and unenrolled students
        enrolled_students = []
        unenrolled_students = []

        for student in all_students:
            student['_id'] = str(student['_id'])  # Ensure _id is a string
            student['status'] = student.get('status', False)  # Ensure key exists
            
            if student['username'] in enrolled_usernames:
                enrolled_students.append(student)
            else:
                unenrolled_students.append(student)

        # Render the template with enrolled and unenrolled students
        return render_template(
            "manageStudents.html",
            classroom=classroom,
            enrolled_students=enrolled_students,
            unenrolled_students=unenrolled_students
        )

    @boundary.route('/teacher/enrollStudent/<classroom_id>', methods=['POST'])
    def enroll_student(classroom_id):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        if request.method == 'POST':
            student_username = request.form.get('username')

            if not student_username:
                flash("Username cannot be empty.", category='error')
                return redirect(url_for('boundary.manage_students', classroom_id=classroom_id))

            # Call the controller to handle enrollment
            result = EnrollStudentController.enroll_student(classroom_id, student_username)
            if result["success"]:
                flash(result["message"], category='success')
            else:
                flash(result["message"], category='error')

        return redirect(url_for('boundary.manage_students', classroom_id=classroom_id))

    @boundary.route('/teacher/removeStudent/<classroom_id>', methods=['POST'])
    def remove_student(classroom_id):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        if request.method == 'POST':
            student_username = request.form.get('username')

            if not student_username:
                flash("Username cannot be empty.", category='error')
                return redirect(url_for('boundary.manage_students', classroom_id=classroom_id))

            # Call the controller to handle removal
            result = RemoveStudentController.remove_student(classroom_id, student_username)
            if result["success"]:
                flash(result["message"], category='success')
            else:
                flash(result["message"], category='error')

        return redirect(url_for('boundary.manage_students', classroom_id=classroom_id))

    @staticmethod
    @boundary.route('/teacher/suspendStudent/<classroom_id>', methods=['POST'])
    def suspend_student(classroom_id):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        student_username = request.form.get('username')
        if not student_username:
            flash("Username cannot be empty.", category='error')
            return redirect(url_for('boundary.manage_students', classroom_id=classroom_id))

        # Call the Controller to handle suspension
        result = SuspendStudentController.suspend_student(classroom_id, student_username)

        flash(result['message'], category='success' if result['success'] else 'error')
        return redirect(url_for('boundary.manage_students', classroom_id=classroom_id))

    @staticmethod
    @boundary.route('/teacher/unsuspendStudent/<classroom_id>', methods=['POST'])
    def unsuspend_student(classroom_id):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        student_username = request.form.get('username')
        if not student_username:
            flash("Username cannot be empty.", category='error')
            return redirect(url_for('boundary.manage_students', classroom_id=classroom_id))

        # Call the Controller to handle unsuspension
        result = UnsuspendStudentController.unsuspend_student(classroom_id, student_username)

        flash(result['message'], category='success' if result['success'] else 'error')
        return redirect(url_for('boundary.manage_students', classroom_id=classroom_id))

    @staticmethod
    @boundary.route('/teacher/searchStudent/<classroom_id>', methods=['GET'])
    def search_student(classroom_id):
        query = request.args.get('query', '').strip()  # Get query from request parameters
        # Retrieve classroom document using classroom_id
        classroom = mongo.db.classroom.find_one({"_id": ObjectId(classroom_id)})
        if not classroom:
            flash("Classroom not found.", category='error')
            return redirect(url_for('boundary.manage_classrooms'))

        # Get enrolled usernames from the classroom
        enrolled_usernames = set(classroom.get('student_list', []))
        unenrolled_usernames = set(user['username'] for user in mongo.db.useraccount.find({"role": "Student"})) - enrolled_usernames

        # Fetch students that match the search query
        search_results = list(mongo.db.useraccount.find({
            "role": "Student",
            "$or": [
                {"username": {"$regex": query, "$options": "i"}},
                {"email": {"$regex": query, "$options": "i"}}
            ]
        }))

        # Separate enrolled and unenrolled students
        enrolled_students = []
        unenrolled_students = []
        for student in search_results:
            student['_id'] = str(student['_id'])
            student['status'] = student.get('status', False)
            if student['username'] in enrolled_usernames:
                enrolled_students.append(student)
            elif student['username'] in unenrolled_usernames:
                unenrolled_students.append(student)

        # Render the search results page
        return render_template(
            "searchResultsStudents.html",
            classroom=classroom,
            enrolled_students=enrolled_students,
            unenrolled_students=unenrolled_students,
            query=query
        )


#---------------------------------------------------------------------------------------
class TeacherManageMaterialBoundary:
    @boundary.route('/upload_material', methods=['POST'])
    def upload_material():
        classroom_id = request.form.get('classroom_id')
        title = request.form.get('title')
        description = request.form.get('description')
        file = request.files.get('file')

        # Call the Controller to process the material upload
        result = UploadMaterialController.upload_material(title, file, session.get('username'), classroom_id, description)

        if result["success"]:
            flash(result["message"], 'success')
            return redirect(url_for('boundary.manage_materials', classroom_id=classroom_id))
        else:
            flash(result["message"], 'danger')
            return redirect(request.url)

    @boundary.route('/upload_material/<classroom_id>', methods=['GET'])
    def upload_material_page(classroom_id):
        return render_template("uploadMaterial.html", classroom_id=classroom_id)
    
    @boundary.route('/manage_materials/<classroom_id>', methods=['GET'])
    def manage_materials(classroom_id):
        # Fetch the materials from the database for the specified classroom
        materials = mongo.db.materials.find({"classroom_id": ObjectId(classroom_id)})
        return render_template("manageMaterials.html", materials=materials, classroom_id=classroom_id)

    @boundary.route('/delete_material/<classroom_id>/<filename>', methods=['POST'])
    def delete_material(classroom_id, filename):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove entry from MongoDB
        mongo.db.materials.delete_one({"classroom_id": ObjectId(classroom_id), "file_name": filename})
        
        flash('Material deleted successfully!', 'success')
        return redirect(url_for('boundary.manage_materials', classroom_id=classroom_id))

    @boundary.route('/view_material/<material_id>/<classroom_id>', methods=['GET'])
    def view_material(material_id, classroom_id):
            material_controller = ViewMaterialController()
            material, file_data = material_controller.get_material(material_id)

            if not material:
                flash('Material not found!', 'danger')
                return redirect(url_for('boundary.manage_materials', classroom_id=classroom_id))

            file_content = file_data.read()
            file_extension = material['file_name'].split('.')[-1].lower()

            # Encode file content as base64 for embedding
            file_base64 = base64.b64encode(file_content).decode('utf-8')

            return render_template("viewMaterial.html",
                                material_id=material['_id'],
                                filename=material['file_name'],
                                classroom_id=classroom_id,
                                file_base64=file_base64,
                                file_extension=file_extension,
                                text_content=file_content.decode('utf-8') if file_extension in ['txt', 'md'] else None)
    
    @boundary.route('/search_materials/<classroom_id>', methods=['GET'])
    def search_materials(classroom_id):
        search_query = request.args.get('search_query', '').strip()

        # If a search query is provided, filter the materials by title or description
        if search_query:
            materials = mongo.db.materials.find({
                "classroom_id": ObjectId(classroom_id),
                "$or": [
                    {"title": {"$regex": search_query, "$options": "i"}},  # Case-insensitive search for title
                    {"description": {"$regex": search_query, "$options": "i"}}  # Case-insensitive search for description
                ]
            })
        else:
            # If no search query, show all materials
            materials = mongo.db.materials.find({"classroom_id": ObjectId(classroom_id)})

        return render_template('manageMaterials.html', materials=materials, classroom_id=classroom_id)
    @staticmethod
    @boundary.route('/teacher/download_material/<material_id>')
    def download_material(material_id):
        material = mongo.db.materials.find_one({"_id": ObjectId(material_id)})
        if not material:
            flash("Material not found!", "danger")
            return redirect(url_for("boundary.home"))

        try:
            # Initialize GridFS
            fs = gridfs.GridFS(mongo.db)
            
            # Retrieve file from GridFS
            file_data = fs.get(material["file_id"])  
            
            return send_file(
                io.BytesIO(file_data.read()),  # Read the binary data
                mimetype=mimetypes.guess_type(material["file_name"])[0] or "application/octet-stream",
                as_attachment=True,
                download_name=material["file_name"]
            )
        except Exception as e:
            flash(f"Error downloading file: {str(e)}", "danger")
            return redirect(url_for("boundary.home"))

        

#---------------------------------------------------------------------------------------
class TeacherViewQuizBoundary:
    @boundary.route('/teacher/view_quiz/<quiz_id>', methods=['GET'])
    def view_quiz(quiz_id):
        try:
            quiz = mongo.db.quizzes.find_one({"_id": ObjectId(quiz_id)})
        except:
            flash("Invalid quiz ID!", "danger")
            return redirect(url_for('boundary.manage_quizzes'))

        if not quiz:
            flash("Quiz not found!", "danger")
            return redirect(url_for('boundary.manage_quizzes'))

        return render_template("viewQuiz.html", quiz=quiz)
            
class ViewUserDetailsBoundary:
    @staticmethod
    @boundary.route('/userDetails/<username>', methods=['GET'])
    def view_user_details(username):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        user_info = mongo.db.useraccount.find_one(
            {"username": username},
            {"_id": 0, "username": 1, "name": 1, "surname": 1, "date_of_birth": 1, "email": 1, "role": 1}
        )

        if not user_info:
            flash("User not found.", category='error')
            return redirect(url_for('boundary.home'))

        return render_template("userDetails.html", user_info=user_info)
    


# ------------------------------------------------------------------------------------------------------- Upload Assignment
class TeacherAssignmentBoundary:
    @boundary.route('/teacher/upload_assignment/<classroom_id>', methods=['GET'])
    def upload_assignment_page(classroom_id):
        return render_template("uploadAssignment.html", classroom_id=classroom_id)

    @boundary.route('/teacher/upload_assignment/<classroom_id>', methods=['POST'])
    def upload_assignment(classroom_id):
        title = request.form.get('title')
        description = request.form.get('description')
        deadline = request.form.get('deadline')
        file = request.files.get('file')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)  # Secure the filename

            # Call controller to upload directly to MongoDB
            result = UploadAssignmentController.upload_assignment(
                title, ObjectId(classroom_id), description, deadline, file, filename
            )
            
            flash(result['message'], 'success' if result['success'] else 'danger')
            return redirect(request.url)
        else:
            flash('Invalid file type!', 'danger')
            return redirect(request.url)


    @staticmethod
    @boundary.route('/teacher/manage_assignments/<classroom_id>', methods=['GET', 'POST'])
    def manage_assignments(classroom_id):
        """Retrieve all assignments and allow searching."""
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", "error")
            return redirect(url_for('boundary.home'))

        query = request.form.get('search', '').strip()

        # Search logic
        if query:
            assignments = list(mongo.db.assignments.find({
                "classroom_id": ObjectId(classroom_id),
                "title": {"$regex": query, "$options": "i"}  # Case-insensitive search
            }))
        else:
            assignments = list(mongo.db.assignments.find({"classroom_id": ObjectId(classroom_id)}))

        return render_template("manageAssignments.html", assignments=assignments, classroom_id=classroom_id)

    @staticmethod
    @boundary.route('/teacher/download_assignment/<assignment_id>')
    def download_assignment(assignment_id):
        assignment = Assignment.get_assignment(assignment_id)

        if not assignment:
            flash("Assignment not found!", "danger")
            return redirect(url_for("boundary.home"))

        file_data = Assignment.get_assignment_file(assignment["file_id"])
        
        return send_file(
            io.BytesIO(file_data),
            mimetype=mimetypes.guess_type(assignment["file_name"])[0],
            as_attachment=True,
            download_name=assignment["file_name"]
        )

    @staticmethod
    @boundary.route('/teacher/view_submissions/<classroom_id>/<assignment_id>')
    def view_submissions(classroom_id, assignment_id):
        """Show all student submissions for an assignment"""

        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        # Ensure the assignment exists
        assignment = mongo.db.assignments.find_one({"_id": ObjectId(assignment_id)})
        if not assignment:
            flash("Assignment not found!", "danger")
            return redirect(url_for('boundary.manage_assignments', classroom_id=classroom_id))

        # Fetch submissions and ensure it's always a list
        submissions = list(mongo.db.submissions.find({"assignment_id": ObjectId(assignment_id)}))

        # Ensure every submission has necessary fields to prevent errors in Jinja
        for submission in submissions:
            submission.setdefault("student_username", "Unknown")
            submission.setdefault("filename", "Not Available")
            submission.setdefault("submitted_at", None)
            submission.setdefault("grade", "Not graded")
            submission.setdefault("_id", ObjectId())  # Ensure submission has an ID

            # Convert `submitted_at` to datetime if it's a string
            if isinstance(submission["submitted_at"], str):
                try:
                    submission["submitted_at"] = datetime.strptime(submission["submitted_at"], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"⚠️ Invalid date format for submission {submission['_id']}")
                    submission["submitted_at"] = None

        return render_template(
            'viewSubmissions.html',
            assignment=assignment,
            submissions=submissions,  # Make sure `submissions` is passed
            classroom_id=classroom_id
        )



    @boundary.route('/delete_submission/<submission_id>')
    def delete_submission(submission_id):
        """Allows a teacher to delete a student's submission."""
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        # Find the submission
        submission = mongo.db.submissions.find_one({"_id": ObjectId(submission_id)})
        if not submission:
            flash("Submission not found!", "danger")
            return redirect(request.referrer)

        # Delete the file from storage
        file_path = submission.get("file_path")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        # Remove submission from database
        mongo.db.submissions.delete_one({"_id": ObjectId(submission_id)})

        flash("Submission deleted successfully!", "success")
        return redirect(request.referrer)



    @staticmethod
    @boundary.route('/grade_assignment/<classroom_id>/<assignment_id>/<student_username>/<submission_id>', methods=['POST'])
    def grade_assignment(classroom_id, assignment_id, student_username, submission_id):
        """Assigns grades and feedback to student submissions."""
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        grade = request.form.get('grade')

        # Ensure grade is a valid number between 0-100
        try:
            grade = int(grade)
            if grade < 0 or grade > 100:
                raise ValueError
        except ValueError:
            flash("Invalid grade! Must be between 0-100.", "danger")
            return redirect(request.referrer)

        # Update grade in the database
        mongo.db.submissions.update_one(
            {"_id": ObjectId(submission_id)},
            {"$set": {"grade": grade}}
        )

        flash("Grade assigned successfully!", "success")
        return redirect(url_for('boundary.view_submissions', classroom_id=classroom_id, assignment_id=assignment_id))



    @staticmethod
    @boundary.route('/teacher/delete_assignment/<classroom_id>/<assignment_id>')
    def delete_assignment(classroom_id, assignment_id):
        """Deletes an assignment and its associated file."""
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        assignment = mongo.db.assignments.find_one({"_id": ObjectId(assignment_id)})
        if assignment:
            file_path = assignment.get("file_path")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

            mongo.db.assignments.delete_one({"_id": ObjectId(assignment_id)})
            flash('Assignment deleted successfully!', 'success')
        else:
            flash('Assignment not found!', 'danger')

        return redirect(url_for('boundary.manage_assignments', classroom_id=classroom_id))
    
    
    @boundary.route('/view_submitted_assignment/<filename>', methods=['GET'])
    def view_submitted_assignment(filename):
        """Serves student-submitted assignments for viewing."""
        
        # Ensure the correct absolute file path
        file_path = os.path.join(os.getcwd(), "FYP25S109", "static", "uploads", "submissions", filename)
        
        # Debugging logs
        print(f"Trying to open file: {file_path}")

        # Check if the file exists
        if os.path.exists(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)  # Detect file type
            return send_file(file_path, mimetype=mime_type, as_attachment=False)

        # If file is not found, show an error
        flash("File not found!", "danger")
        return redirect(request.referrer)


class TeacherManageQuizBoundary:
    UPLOAD_FOLDER_QUIZ = 'FYP25S109/static/uploads/quiz/'

    @boundary.route('/teacher/upload_quiz/<classroom_id>', methods=['GET', 'POST'])
    def upload_quiz(classroom_id):
        if request.method == "POST":
            quiz_title = request.form.get('quiz_title', '').strip()
            quiz_description = request.form.get('quiz_description', '').strip()
            questions = []

            question_count = sum(1 for key in request.form.keys() if key.startswith('question_'))

            for i in range(1, question_count + 1):
                question_text = request.form.get(f'question_{i}', '').strip()
                options = [
                    request.form.get(f'option_{i}_1', '').strip(),
                    request.form.get(f'option_{i}_2', '').strip(),
                    request.form.get(f'option_{i}_3', '').strip(),
                    request.form.get(f'option_{i}_4', '').strip()
                ]
                correct_answer = request.form.get(f'correct_answer_{i}', '').strip()
                image_file = request.files.get(f'image_{i}')

                # Convert image to base64 if uploaded
                image_data = None
                if image_file and image_file.filename:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')

                questions.append({
                    "text": question_text,
                    "options": options,
                    "correct_answer": correct_answer,
                    "image": image_data
                })

            # Call controller function
            result = UploadQuizController.upload_quiz(quiz_title, quiz_description, questions, classroom_id)

            if result.get("success"):
                flash("Quiz created successfully!", "success")
                return redirect(url_for('boundary.manage_quizzes', classroom_id=classroom_id))
            else:
                flash(f"Error: {result.get('message')}", "danger")

        # If GET request, show the quiz creation form
        return render_template("uploadQuiz.html", classroom_id=classroom_id)
    
    
    @boundary.route('/teacher/manage_quizzes/<classroom_id>', methods=['GET'])
    def manage_quizzes(classroom_id):
        quizzes = list(mongo.db.quizzes.find({"classroom_id": ObjectId(classroom_id)}))
        return render_template("manageQuizzes.html", quizzes=quizzes, classroom_id=classroom_id)

    @boundary.route('/teacher/delete_quiz/<quiz_id>', methods=['POST'])
    def delete_quiz(quiz_id):
        mongo.db.quizzes.delete_one({"_id": ObjectId(quiz_id)})
        flash("Quiz deleted successfully!", category='success')
        return redirect(request.referrer)

class StudentQuizBoundary:
    @boundary.route('/attempt_quiz/<quiz_id>', methods=['GET', 'POST'])
    def attempt_quiz(quiz_id):
        from datetime import datetime, timezone
        student_username = session.get('username')

        if request.method == 'POST':
            answers = {}
            results = []
            score = 0
            total = 0

            quiz = mongo.db.quizzes.find_one({'_id': ObjectId(quiz_id)})
            if not quiz:
                flash("Quiz not found.", "danger")
                return redirect(url_for('boundary.home'))

            for index, question in enumerate(quiz.get("questions", [])):
                qid_str = str(question.get("_id", index))
                submitted_index = request.form.get(qid_str)

                selected_index = -1  # Default for unanswered
                selected_value = "None"

                if submitted_index is not None and submitted_index.isdigit():
                    selected_index = int(submitted_index)
                    options = question.get("options", [])
                    if 0 <= selected_index < len(options):
                        selected_value = options[selected_index]

                try:
                    correct_index = int(question.get("correct_answer", -1)) - 1
                except (ValueError, TypeError):
                    correct_index = -1
                correct_value = question.get("options", [])[correct_index] if 0 <= correct_index < len(question.get("options", [])) else "N/A"

                if selected_index == correct_index:
                    score += 1

                results.append({
                    "text": question.get("text", ""),
                    "correct": correct_value,
                    "selected": selected_value,
                    "image": question.get("image", None)
                })

                # ✅ Save index instead of value here:
                answers[qid_str] = selected_index  
                total += 1
                
            # Store the attempt in the database
            mongo.db.quiz_attempts.insert_one({
                "student_username": student_username,
                "quiz_id": ObjectId(quiz_id),
                "answers": answers,
                "score": score,
                "total": total,
                "timestamp": datetime.utcnow().replace(tzinfo=timezone.utc)
            })

            classroom_id = quiz.get("classroom_id", "")
            return render_template('quiz_result.html', score=score, total=total, results=results, classroom_id=classroom_id)

        # GET Request - Show Quiz Form
        quiz = mongo.db.quizzes.find_one({'_id': ObjectId(quiz_id)})
        if not quiz:
            flash("Quiz not found.", "danger")
            return redirect(url_for('boundary.home'))
        return render_template('attempt_quiz.html', quiz=quiz)


class TeacherAnnouncementBoundary:
    @boundary.route('/teacher/add_announcement/<classroom_id>/<classroom_name>', methods=['GET', 'POST'])
    def add_announcement(classroom_id, classroom_name):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')

            if not title or not content:
                flash("Title and content cannot be empty.", category='error')
                return redirect(url_for('boundary.add_announcement', classroom_id=classroom_id, classroom_name=classroom_name))

            mongo.db.announcements.insert_one({
                "classroom_id": ObjectId(classroom_id),
                "classroom_name": classroom_name.strip(),
                "title": title.strip(),
                "content": content.strip(),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            flash("Announcement added successfully!", category='success')
            return redirect(url_for('boundary.view_classroom', classroom_id=classroom_id))

        return render_template("addAnnouncement.html", classroom_name=classroom_name)

    @boundary.route('/teacher/delete_announcement/<classroom_id>/<announcement_id>', methods=['POST'])
    def delete_announcement(classroom_id, announcement_id):
        mongo.db.announcements.delete_one({"_id": ObjectId(announcement_id)})

        flash("Announcement deleted successfully!", category='success')
        return redirect(url_for('boundary.view_classroom', classroom_id=classroom_id))

    
class ViewAssignmentBoundary:
    @boundary.route('/view_assignment/<assignment_id>')
    def view_assignment(assignment_id):
        # Retrieve assignment details
        assignment = Assignment.get_assignment(assignment_id)

        if not assignment:
            flash("Assignment not found!", "danger")
            return redirect(url_for("boundary.home"))

        # Get file content
        file_data = Assignment.get_assignment_file(assignment["file_id"])
        file_extension = assignment["file_name"].split(".")[-1]

        # Convert to Base64 (for PDFs and text)
        if file_extension in ["pdf", "txt", "md"]:
            file_base64 = base64.b64encode(file_data).decode("utf-8")
            text_content = file_data.decode("utf-8") if file_extension in ["txt", "md"] else None
        else:
            file_base64 = None
            text_content = None

        # Check if student has already submitted the assignment
        student_username = session.get('username')  # Get the logged-in student's username
        student_submission = Submission.get_submission_by_student_and_assignment(student_username, assignment_id)

        # Pass the necessary data to the template
        return render_template("viewAssignment.html",
                            filename=assignment["file_name"],
                            file_extension=file_extension,
                            file_base64=file_base64,
                            text_content=text_content,
                            assignment=assignment,
                            student_submission=student_submission)  # Pass submission data to template



class StudentAssignmentBoundary:
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

    @staticmethod
    def allowed_file(filename):
        """
        Checks if the file has an allowed extension.
        """
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in StudentAssignmentBoundary.ALLOWED_EXTENSIONS

    
    @boundary.route('/view_assignment/<assignment_id>/<filename>', methods=['GET', 'POST'])
    def submit_assignment(assignment_id, filename):
        """Handles assignment submission and displays the submission form."""
        try:
            student_username = session.get('username')  # Get logged-in student's username
            student_submission = None  # Default to no submission

            if request.method == 'POST':
                file = request.files.get('file')

                if not file:
                    flash('No file uploaded!', 'danger')
                    return redirect(url_for('boundary.view_assignment', filename=filename, assignment_id=assignment_id))

                result = StudentSendSubmissionController.submit_assignment_logic(assignment_id, student_username, file)

                if result['success']:
                    flash('Assignment submitted successfully!', 'success')
                else:
                    flash(f"Submission failed: {result['message']}", 'danger')

                return redirect(url_for('boundary.view_assignment', filename=filename, assignment_id=assignment_id))

            # **Check if student has submitted**
            student_submission = StudentSendSubmissionController.get_submission(assignment_id, student_username)

            return render_template(
                'view_assignment.html',
                assignment_id=assignment_id,
                filename=filename,
                student_submission=student_submission
            )

        except Exception as e:
            logging.error(f"Error in submit_assignment: {str(e)}")
            flash('An error occurred while submitting the assignment.', 'danger')
            return redirect(url_for('boundary.view_assignment', filename=filename, assignment_id=assignment_id))

    @boundary.route('/download_submission/<file_id>')
    def download_submission(file_id):
        """Serves the student's submitted file."""
        try:
            file = StudentSendSubmissionController.get_submission_file(file_id)
            if file:
                return send_file(
                    io.BytesIO(file.read()),
                    attachment_filename=file.filename,
                    as_attachment=True
                )
            else:
                flash("File not found!", "danger")
                return redirect(request.referrer)
        except Exception as e:
            logging.error(f"Error in download_submission: {str(e)}")
            flash("An error occurred while downloading the file.", "danger")
            return redirect(request.referrer)
    @boundary.route('student/view_submission/<submission_id>', methods=['GET'])
    def student_view_submission(submission_id):
        """Allows a student to view their own submission."""
        student_username = session.get('username')
        
        if not student_username:
            flash("You need to be logged in to view your submission.", "danger")
            return redirect(url_for('boundary.login'))  # Redirect to login page if not logged in

        # Fetch the submission from the database by submission_id and student username
        submission = StudentViewSubmissionController.get_submission_by_student_and_id(student_username, submission_id)
        
        if not submission:
            flash("Submission not found.", "danger")
            return redirect(url_for('boundary.home'))  # Redirect if the submission is not found

        # Fetch the file content from the student's submission
        file_data = Submission.get_submission_file(submission["file_id"])  # Correct method to get submission file
        file_extension = submission["file_name"].split(".")[-1]  # Get file extension from student's submission file name
        
        # Handle different file types
        if file_extension in ["pdf", "txt", "md"]:
            file_base64 = base64.b64encode(file_data).decode("utf-8")
            text_content = file_data.decode("utf-8") if file_extension in ["txt", "md"] else None
        else:
            file_base64 = None
            text_content = None

        # Render the submission details page
        return render_template(
            "reviewSubmission.html",
            submission=submission,
            file_base64=file_base64,
            text_content=text_content,
            file_extension=file_extension
        )



    @boundary.route('/edit_submission/<submission_id>', methods=['GET', 'POST'])
    def student_edit_submission(submission_id):
        pass

    @boundary.route('/delete_submission/<submission_id>/<assignment_id>', methods=['GET','POST'])
    def student_delete_submission(submission_id, assignment_id):
        """Allows a student to delete their own submission."""
        
        student_username = session.get('username')
        
        if not student_username:
            flash("Unauthorized action.", "danger")
            return redirect(url_for('boundary.view_assignment', assignment_id=assignment_id))

        result = StudentDeleteSubmissionController.delete_submission(submission_id)

        if result["success"]:
            flash("Submission deleted successfully!", "success")
        else:
            flash("Error Deleting Submission", "danger")

        return redirect(url_for('boundary.view_assignment', assignment_id=assignment_id))

        

        






class AccessForumBoundary:
    @staticmethod
    @boundary.route('/forum/<classroom_id>', methods=['GET','POST'])
    def access_forum(classroom_id):
        return render_template("forum.html", classroom_id=classroom_id, discussion_rooms=RetrieveDiscussionRoomController.get_all_discussion_rooms_by_classroom_id(classroom_id))


class DiscussionRoomBoundary:
    @staticmethod
    @boundary.route('/forum/<classroom_id>/create', methods=['POST'])
    def create_discussion_room(classroom_id):
        discussion_room_name = request.form.get('discussion_room_name')
        discussion_room_description = request.form.get('discussion_room_description')
        created_by = session.get('username')
        
        if AddDiscussionRoomController.add_discussion_room(classroom_id, discussion_room_name, discussion_room_description, created_by):
            flash("Discussion room created successfully!", "success")
        else:
            flash("Failed to create discussion room.", "danger")

        # Redirecting back to the forum page
        return redirect(url_for('boundary.access_forum', classroom_id=classroom_id))

    @staticmethod
    @boundary.route('/forum/<classroom_id>/<discussion_room_id>/delete', methods=['GET', 'POST'])
    def delete_discussion_room(classroom_id, discussion_room_id):
        if DeleteDiscussionRoomController.delete_discussion_room(discussion_room_id):
            flash("Discussion room deleted successfully!", "success")
        else:
            flash("Failed to delete discussion room.", "danger")

        return redirect(url_for('boundary.access_forum', classroom_id=classroom_id))

    @staticmethod
    @boundary.route('/forum/<classroom_id>', methods=['GET'])
    def view_discussion_room_list(classroom_id):
        rooms = RetrieveDiscussionRoomController.get_all_discussion_rooms_by_classroom_id(classroom_id)
        return render_template('forum.html', discussion_rooms=rooms, classroom_id=classroom_id)

    @staticmethod
    @boundary.route('/forum/search', methods=['GET'])
    def search_discussion_room():
        search_query = request.args.get('query')
        rooms = SearchDiscussionRoomController.search_discussion_room(search_query)
        return render_template('forum.html', discussion_rooms=rooms)

    @staticmethod
    @boundary.route('/discussion_room/<discussion_room_id>', methods=['GET', 'POST'])
    def access_room(discussion_room_id):
        # Fetch messages using the controller
        messages = RetrieveMessageController.get_all_messages(discussion_room_id)
        room = RetrieveDiscussionRoomController.get_discussion_room_id(discussion_room_id)

        # Check if the discussion room exists
        if not room:
            flash("Discussion room not found.", "danger")
            return redirect(url_for('boundary.view_discussion_room_list'))

        # Render the template with messages and room data
        return render_template('discussionRoom.html', room=room, messages=messages, discussion_room_id=discussion_room_id)

    @staticmethod
    @boundary.route('/discussion_room/update/<discussion_room_id>', methods=['GET', 'POST'])
    def update_discussion_room(discussion_room_id):

        if request.method == 'GET':
            # Fetch existing details from the database
            discussion_room = UpdateDiscussionRoomController.get_discussion_room_by_id(discussion_room_id)

            if not discussion_room:
                flash("Discussion room not found.", "danger")
                return redirect(url_for('boundary.view_discussion_room_list'))

            # Show the update form
            return render_template('update_discussion_room.html', discussion_room=discussion_room)

        elif request.method == 'POST':
            classroom_id = request.form.get('classroom_id') or discussion_room.get('classroom_id')
            discussion_room_name = request.form.get('discussion_room_name')
            discussion_room_description = request.form.get('discussion_room_description')
            print(f"Discussion Room Name: {discussion_room_name}")
            print(f"Discussion Room Description: {discussion_room_description}")
            
            new_details = {
                "discussion_room_name": discussion_room_name,
                "discussion_room_description": discussion_room_description
            }

            if UpdateDiscussionRoomController.update_discussion_room(discussion_room_id, new_details):
                flash("Discussion room updated successfully!", "success")
            else:
                flash("Failed to update discussion room.", "danger")

            return redirect(url_for('boundary.access_forum', classroom_id=classroom_id))


class MessageBoundary:
    @staticmethod
    @boundary.route('/discussion_room/<discussion_room_id>/message', methods=['POST'])
    def send_message(discussion_room_id):
        message_content = request.form.get('message_content')
        message_author = session.get('username')
        if AddMessageController.send_message(discussion_room_id, message_author, message_content):
            flash("Message sent successfully!", "success")
        else:
            flash("Failed to send message.", "danger")
        return redirect(url_for('boundary.access_room', discussion_room_id=discussion_room_id))

    
    @staticmethod
    @boundary.route('/message/<message_id>/delete', methods=['POST'])
    def unsend_message(message_id):
        if DeleteMessageController.delete_message(message_id):
            flash("Message deleted successfully!", "success")
        else:
            flash("Failed to delete message.", "danger")
        return redirect(request.referrer)
    
    @staticmethod
    @boundary.route('/message/<message_id>/update', methods=['POST'])
    def edit_message(message_id):
        message_content = request.form.get('message_content')
        if UpdateMessageController.update_message(message_id, message_content):
            flash("Message updated successfully!", "success")
        else:
            flash("Failed to update message.", "danger")
        return redirect(request.referrer)
    
       