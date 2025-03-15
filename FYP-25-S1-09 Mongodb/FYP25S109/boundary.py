from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from . import mongo
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from FYP25S109.controller import *
from FYP25S109.entity import * 

boundary = Blueprint('boundary', __name__)
YOUR_DOMAIN = "http://localhost:5000"
OPENSHOT_API_URL = "https://cloud.openshot.org/api/projects/"

# Homepage
class HomePage:
    @staticmethod
    @boundary.route('/')
    def home():
        admin_users = [user["username"] for user in mongo.db.useraccount.find({"role": "Admin"}, {"username": 1})]
        admin_videos = list(mongo.db.tutorialvideo.find(
            {"username": {"$in": admin_users}},
            {"_id": 0, "title": 1, "video_name": 1, "file_path": 1, "username": 1}
        ))
        avatars = list(mongo.db.avatar.find({}, {"_id": 0, "file_path": 1, "avatarname": 1, 'upload_date': 1}))
        username = session.get("username", None)
        role = session.get("role", None)

        classrooms = []

        if role == "Teacher":
            # Teachers should only see the classrooms they own
            classrooms = list(mongo.db.classroom.find(
                {"teacher": username},
                {"_id": 0, "classroom_name": 1, "teacher": 1, "description": 1, "capacity": 1}
            ))
        elif role == "Student":
            # Students should only see classrooms they are enrolled in
            classrooms = list(mongo.db.classroom.find(
                {"student_list": username},
                {"_id": 0, "classroom_name": 1, "teacher": 1, "description": 1, "capacity": 1}
            ))

        return render_template("homepage.html", videos=admin_videos, avatars=avatars, username=username, classrooms=classrooms)



# Generate Video 
class GenerateVideoBoundary:
    @staticmethod
    @boundary.route('/generate_video', methods=['POST'])
    def generate_video():
        if 'username' not in session:
            return jsonify({"success": False, "error": "User not logged in"}), 401

        data = request.get_json()
        text = data.get("text")
        selected_avatar = data.get("selected_avatar")

        if not text or not selected_avatar:
            return jsonify({"success": False, "error": "Text or avatar not provided"}), 400

        username = session.get("username", "Guest")

        print(f"Generating video for user: {username} with text: {text} and avatar: {selected_avatar}")

        headers = {
            "Authorization": f"Token 9054f7aa9305e012b3c2300408c3dfdf390fcddf",
            "Content-Type": "application/json"
        }

        # Step 1: Create a new project in OpenShot
        payload = {
            "name": f"Generated Video - {username}",
            "description": text,
            "fps_num": 30,
            "fps_den": 1,
            "width": 1920,
            "height": 1080,
            "video_length": 10
        }

        try:
            response = requests.post(OPENSHOT_API_URL, json=payload, headers=headers)
            response_data = response.json()

            if response.status_code != 201:
                return jsonify({"success": False, "error": "Failed to create OpenShot project"}), 500

            project_id = response_data.get("id")  # ✅ Get project ID

            # Step 2: Upload the avatar as a media file
            UPLOAD_URL = "https://cloud.openshot.org/api/files/"
            with open(f"FYP25S109/static/{selected_avatar}", "rb") as avatar_file:
                files = {"file": avatar_file}
                upload_response = requests.post(UPLOAD_URL, files=files, headers=headers)

            if upload_response.status_code != 201:
                return jsonify({"success": False, "error": "Failed to upload avatar file"}), 500

            file_id = upload_response.json().get("id")  # ✅ Get uploaded file ID

            # Step 3: Add the uploaded avatar file as a clip
            ADD_CLIP_URL = "https://cloud.openshot.org/api/clips/"
            clip_payload = {
                "project": project_id,
                "file_id": file_id,
                "start": 0,
                "end": 10,  # Adjust duration as needed
                "layer": 1
            }
            clip_response = requests.post(ADD_CLIP_URL, json=clip_payload, headers=headers)

            if clip_response.status_code != 201:
                return jsonify({"success": False, "error": "Failed to add clip to project"}), 500

            # Step 4: Export the project
            EXPORT_URL = "https://cloud.openshot.org/api/exports/"
            export_payload = {
                "project": project_id,
                "video_format": "mp4"
            }
            export_response = requests.post(EXPORT_URL, json=export_payload, headers=headers)

            if export_response.status_code == 201:
                export_id = export_response.json().get("id")
                return jsonify({"success": True, "export_id": export_id, "message": "Video generation started!"})
            else:
                return jsonify({"success": False, "error": "Failed to start video export"}), 500

        except Exception as e:
            return jsonify({"success": False, "error": f"OpenShot API request failed: {str(e)}"}), 500


    @staticmethod
    @boundary.route('/generate_video', methods=['GET'])
    def generate_video_page():
        avatars = list(mongo.db.avatar.find({}, {"_id": 0, "file_path": 1}))  # Retrieve only file_path

        # Extract avatar paths
        available_avatars = [avatar["file_path"] for avatar in avatars]

        print("Available Avatars:", available_avatars)  # ✅ Debugging

        return render_template("generateVideo.html", available_avatars=available_avatars)
    
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
            search_results = TutorialVideo.search_video(search_query)
        elif filter_type == 'avatar':
            search_results = Avatar.search_avatar(search_query)
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
            user_role = session.get("role", "User")
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
            video = TutorialVideo(
                title=title,
                video_name=file.filename,
                video_file=file,
                username=username,
                user_role=user_role,
                description = description
            )
            result = video.save_video()
            flash(result["message"], category="success" if result["success"] else "error")
            return redirect(url_for('boundary.upload_tutorial'))
        return render_template("uploadTutorial.html")

# View Uploaded Videos (Multiple Videos at one time)
class AdminViewUploadedVideosBoundary:
    @staticmethod
    @boundary.route('/uploadedVideos', methods=['GET'])
    def view_uploaded_videos():
        if 'username' not in session:
            flash("You must be logged in to view uploaded videos.", category='error')
            return redirect(url_for('boundary.login'))
        admin_videos = list(mongo.db.tutorialvideo.find(
            {"username": session['username']},
            {"_id": 0, "title": 1, "file_path": 1, "status": 1, "upload_date": 1, "description": 1, "username": 1, "video_name": 1}
        ))
        return render_template("manageVideo.html", videos=admin_videos)
    
    
# View Uploaded Videos (Single Video)
class AdminViewSingleTutorialBoundary:
    @staticmethod
    @boundary.route('/viewTutorial/<video_name>', methods=['GET'])
    def view_tutorial(video_name):
        video = mongo.db.tutorialvideo.find_one({"video_name": video_name})
        if not video:
            flash("Video not found.", category='error')
            return redirect(url_for('boundary.home'))
        return render_template("viewTutorial.html", video=video)

#Delete Video
class AdminDeleteUploadedVideosBoundary:
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
        if video["username"] != session["username"]:
            flash("Unauthorized access! You can only delete your own videos.", category='error')
            return redirect(url_for('boundary.view_uploaded_videos'))
        try:
            os.remove(video["file_path"])
            mongo.db.tutorialvideo.delete_one({"video_name": video_name})
            flash("Video deleted successfully.", category='success')
        except Exception as e:
            flash(f"Failed to delete video: {str(e)}", category='error')
        return redirect(url_for('boundary.view_uploaded_videos'))

# Manage Avatar
class ManageAvatarBoundary:
    @staticmethod
    @boundary.route('/admin_manage_avatars')
    def admin_manage_avatars():
        if 'username' not in session:
            flash("You must be logged in to manage your avatar.", category='error')
            return redirect(url_for('boundary.login'))
        username = session.get('username')
        user_role = session.get('role')
        avatars = AdminManageAvatarController.get_avatars_by_username(username)
        if not avatars:
            flash("No avatars found for your account.", category='info')
        return render_template(
            "admin_manage_avatars.html",
            username=username,
            user_role=user_role,
            avatars=avatars
        )

# Add Avatar
class AddAvatarBoundary:
    UPLOAD_FOLDER_AVATAR = 'FYP25S109/static/uploads/avatar/'

    @staticmethod
    @boundary.route('/admin_create_avatar', methods=['GET', 'POST'])
    def admin_create_avatar():
        if 'username' not in session:
            flash("You must be logged in to create an avatar.", category='error')
            return redirect(url_for('boundary.login'))

        if request.method == 'POST':
            username = session.get('username')
            avatar_file = request.files.get('avatar')
            avatarname = request.form.get('avatarname')  # ✅ Capture avatar name

            if not username or not avatar_file or not avatarname:
                flash("Username, avatar name, and avatar file are required.", category='error')
                return redirect(url_for('boundary.admin_create_avatar'))
            
            result = AdminAddAvatarController.add_avatar(username, avatarname, avatar_file)

            if result['success']:
                flash("Avatar added successfully.", category='success')
            else:
                flash(f"Failed to add avatar: {result['message']}", category='error')

            return redirect(url_for('boundary.admin_create_avatar'))

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
            return redirect(url_for('boundary.admin_manage_avatars'))
        if Avatar.delete_avatar(avatar_id):
            flash("Avatar deleted successfully.", category='success')
        else:
            flash("Failed to delete avatar.", category='error')
        return redirect(url_for('boundary.admin_manage_avatars'))
    
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
        users = list(mongo.db.useraccount.find(
            {"$or": [
                {"username": {"$regex": query, "$options": "i"}},
                {"email": {"$regex": query, "$options": "i"}},
                {"role": {"$regex": query, "$options": "i"}}
            ]},
            {"_id": 0, "username": 1, "email": 1, "role": 1, "status": 1}
        ))

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
#Teacher manage classrooms
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
            result = controller.create_classroom(classroom_name, teacher, classroom_description, classroom_capacity,)

            if result['success']:
                flash(result['message'], category='success')
                return redirect(url_for('boundary.manage_classrooms'))
            else:
                flash(result['message'], category='error')

        return render_template("addClassroom.html")
    
class ViewClassRoomBoundary:
    @staticmethod
    @boundary.route('/teacher/viewClassroom/<classroom_name>', methods=['GET', 'POST'])
    def view_classroom(classroom_name):
        if 'role' not in session or (session.get('role') != 'Teacher' and session.get('role') != 'Student'):
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        classroom = mongo.db.classroom.find_one({"classroom_name": classroom_name})
        if not classroom:
            flash("Classroom not found.", category='error')
            return redirect(url_for('boundary.manage_classrooms'))

        if session.get('role') == 'Student':
            student_username = session.get('username')
            if student_username.strip() not in [s.strip() for s in classroom['student_list']]:
                flash("You are not enrolled in this classroom.", category='error')
                return redirect(url_for('boundary.home'))
        
        if session.get('role') == 'Teacher':
            teacher_username = session.get('username')
            if teacher_username.strip() != classroom['teacher'].strip():
                flash("You are not the teacher of this classroom.", category='error')
                return redirect(url_for('boundary.home'))
            return render_template("viewClassroom.html", classroom=classroom)

        return render_template("viewClassroom.html", classroom=classroom)



class TeacherDeleteClassroomBoundary:
    @staticmethod
    @boundary.route('/teacher/deleteClassroom/<classroom_name>', methods=['POST'])
    def delete_classroom(classroom_name):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        result = mongo.db.classroom.delete_one({"classroom_name": classroom_name})

        if result.deleted_count:
            flash(f"Classroom {classroom_name} deleted successfully.", category='success')
        else:
            flash("Classroom not found.", category='error')

        return redirect(url_for('boundary.manage_classrooms'))
    #update classroom
class TeacherUpdateClassroomBoundary:
    @staticmethod
    @boundary.route('/teacher/updateClassroom/<classroom_name>', methods=['GET', 'POST'])
    def update_classroom(classroom_name):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        classroom = mongo.db.classroom.find_one({"classroom_name": classroom_name})
        print(f"Classroom: {classroom}")  # Debugging line to check the classroom object

        if not classroom:
            flash("Classroom not found.", category='error')
            return redirect(url_for('boundary.manage_classrooms'))

        if request.method == 'POST':
            new_classroom_name = request.form.get('classroom_name')
            new_description = request.form.get('classroom_description')
            new_capacity = request.form.get('classroom_capacity')

            if not new_classroom_name:
                flash("Classroom name is required.", category='error')
                return redirect(url_for('boundary.update_classroom', classroom_name=classroom_name))

            result = UpdateClassroomController.update_classroom(classroom_name, new_details={
                "classroom_name": new_classroom_name,
                "description": new_description,
                "capacity": new_capacity
            })

            print(f"Update result: {result}")  # Debugging line to check result

            return redirect(url_for('boundary.manage_classrooms'))

        return render_template("updateClassroom.html", classroom=classroom)
class TeacherSearchClassroomBoundary:
    @staticmethod
    @boundary.route('/teacher/searchClassroom', methods=['GET','POST'])
    def search_classroom():

        query = request.args.get('query', '').strip() if request.method == 'GET' else request.form.get('query', '').strip()
        classrooms = list(mongo.db.classroom.find(
            {"$or": [
                {"classroom_name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"teacher": {"$regex": query, "$options": "i"}}
            ]},
            {"_id": 0, "classroom_name": 1, "description": 1, "teacher": 1, "capacity": 1}
        ))

        return render_template("ClassroomSearchResult.html", classrooms=classrooms, query=query)

class TeacherManageStudentsBoundary:
    @staticmethod
    @boundary.route('/teacher/manageStudents/<classroom_name>', methods=['GET', 'POST'])
    def manage_students(classroom_name):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        # Retrieve classroom document
        classroom = mongo.db.classroom.find_one({"classroom_name": classroom_name})

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

    @boundary.route('/teacher/enrollStudent/<classroom_name>', methods=['POST'])
    def enroll_student(classroom_name):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        if request.method == 'POST':
            student_username = request.form.get('username')

            if not student_username:
                flash("Username cannot be empty.", category='error')
                return redirect(url_for('boundary.manage_students', classroom_name=classroom_name))

            # Call the controller to handle enrollment
            result = EnrollStudentController.enroll_student(classroom_name, student_username)
            if result["success"]:
                flash(result["message"], category='success')
            else:
                flash(result["message"], category='error')

        return redirect(url_for('boundary.manage_students', classroom_name=classroom_name))
    @boundary.route('/teacher/removeStudent/<classroom_name>', methods=['POST'])
    def remove_student(classroom_name):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        if request.method == 'POST':
            student_username = request.form.get('username')

            if not student_username:
                flash("Username cannot be empty.", category='error')
                return redirect(url_for('boundary.manage_students', classroom_name=classroom_name))

            # Call the controller to handle removal
            result = RemoveStudentController.remove_student(classroom_name, student_username)
            if result["success"]:
                flash(result["message"], category='success')
            else:
                flash(result["message"], category='error')

        return redirect(url_for('boundary.manage_students', classroom_name=classroom_name))
    @staticmethod
    @boundary.route('/teacher/suspendStudent/<classroom_name>', methods=['POST'])
    def suspend_student(classroom_name):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        student_username = request.form.get('username')
        if not student_username:
            flash("Username cannot be empty.", category='error')
            return redirect(url_for('boundary.manage_students', classroom_name=classroom_name))

        # Call the Controller to handle suspension
        result = SuspendStudentController.suspend_student(classroom_name, student_username)

        flash(result['message'], category='success' if result['success'] else 'error')
        return redirect(url_for('boundary.manage_students', classroom_name=classroom_name))
    @staticmethod
    @boundary.route('/teacher/unsuspendStudent/<classroom_name>', methods=['POST'])
    def unsuspend_student(classroom_name):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        student_username = request.form.get('username')
        if not student_username:
            flash("Username cannot be empty.", category='error')
            return redirect(url_for('boundary.manage_students', classroom_name=classroom_name))

        # Call the Controller to handle unsuspension
        result = UnsuspendStudentController.unsuspend_student(classroom_name, student_username)

        flash(result['message'], category='success' if result['success'] else 'error')
        return redirect(url_for('boundary.manage_students', classroom_name=classroom_name))
    @staticmethod
    @boundary.route('/teacher/searchStudent/<classroom_name>', methods=['GET'])
    def search_student(classroom_name):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        query = request.args.get('query', '').strip()  # Get query from request parameters

        # Retrieve classroom document
        classroom = mongo.db.classroom.find_one({"classroom_name": classroom_name})
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



    

    
class TeacherUploadMaterialBoundary:
    UPLOAD_FOLDER_MATERIAL = 'FYP25S109/static/uploads/materials/'

    @staticmethod
    @boundary.route('/teacher/uploadMaterial', methods=['GET', 'POST'])
    def upload_material():
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            classroom_name = request.form.get('classroom_name')  
            material_file = request.files.get('file')

            # Pass all inputs to the controller
            controller = UploadMaterialController()
            result = controller.upload_material(title, material_file, session.get('username'), classroom_name, description)

            # Show success or error messages
            flash(result['message'], category='success' if result['success'] else 'error')
            return redirect(url_for('boundary.upload_material'))

        return render_template("uploadMaterial.html")


class TeacherUploadQuizBoundary:
    UPLOAD_FOLDER_QUIZ = 'FYP25S109/static/uploads/quiz/'

    @staticmethod
    @boundary.route('/teacher/uploadQuiz', methods=['GET', 'POST'])
    def upload_quiz():
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        if request.method == 'POST':
            classroom_name = request.form.get('classroom_name')
            quiz_file = request.files.get('quiz_file')
            if not classroom_name:
                flash("Classroom name is required.", category='error')
                return redirect(url_for('boundary.upload_quiz'))
            if not quiz_file:
                flash("Quiz file is required.", category='error')
                return redirect(url_for('boundary.upload_quiz'))
            if '.' in quiz_file.filename and quiz_file.filename.rsplit('.', 1)[1].lower() not in UploadTutorialBoundary.ALLOWED_EXTENSIONS:
                flash("Invalid file type. Please upload a valid quiz file.", category='error')
                return redirect(url_for('boundary.upload_quiz'))
            controller = UploadQuizController()
            result = controller.upload_quiz(classroom_name, quiz_file)
            if result['success']:
                flash(result['message'], category='success')
            else:
                flash(result['message'], category='error')
            return redirect(url_for('boundary.upload_quiz'))
        return render_template("uploadQuiz.html")

class TeacherViewQuizBoundary:
    @staticmethod
    @boundary.route('/teacher/viewQuiz/<quiz_name>', methods=['GET'])
    def view_quiz(quiz_name):
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        quiz = mongo.db.quiz.find_one({"quiz_name": quiz_name})
        if not quiz:
            flash("Quiz not found.", category='error')
            return redirect(url_for('boundary.home'))

        return render_template("viewQuiz.html", quiz=quiz)
        
class TeacherUploadAssignment:
    UPLOAD_FOLDER_ASSIGNMENT = 'FYP' \
    '25S109/static/uploads/assignment/'

    @staticmethod
    @boundary.route('/teacher/uploadAssignment/<classroom_name>', methods=['GET', 'POST'])

    def upload_assignment():
        if 'role' not in session or session.get('role') != 'Teacher':
            flash("Unauthorized access.", category='error')
            return redirect(url_for('boundary.home'))

        if request.method == 'POST':
            classroom_name = request.form.get('classroom_name')
            assignment_file = request.files.get('assignment_file')
            if not classroom_name:
                flash("Classroom name is required.", category='error')
                return redirect(url_for('boundary.upload_assignment'))
            if not assignment_file:
                flash("Assignment file is required.", category='error')
                return redirect(url_for('boundary.upload_assignment'))
            if '.' in assignment_file.filename and assignment_file.filename.rsplit('.', 1)[1].lower() not in UploadTutorialBoundary.ALLOWED_EXTENSIONS:
                flash("Invalid file type. Please upload a valid assignment file.", category='error')
                return redirect(url_for('boundary.upload_assignment'))
            controller = UploadAssignmentController()
            result = controller.upload_assignment(classroom_name, assignment_file)
            if result['success']:
                flash(result['message'], category='success')
            else:
                flash(result['message'], category='error')
            return redirect(url_for('boundary.upload_assignment'))
        return render_template("uploadAssignment.html")
    
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