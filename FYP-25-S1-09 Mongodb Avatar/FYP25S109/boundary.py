from flask import Blueprint, render_template, request, flash, redirect, url_for, session
# from . import mysql
from . import mongo  

import os
from werkzeug.utils import secure_filename

import stripe
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from datetime import datetime

from FYP25S109.controller import LoginController, CreateUserAccController, DisplayUserDetailController
from FYP25S109.controller import UpdateUserRoleController, UpdateAccountDetailController, ResetPasswordController, AdminAddAvatarController
from FYP25S109.controller import AdminManageAvatarController,AdminAddAvatarController
from FYP25S109.entity import UserAccount, TutorialVideo,Avatar

boundary = Blueprint('boundary', __name__)  # Blueprints mean it has routes inside a bunch of URLs defined

YOUR_DOMAIN = "http://localhost:5000"

# Homepage
@boundary.route('/')
def home():
    admin_users = [user["username"] for user in mongo.db.useraccount.find({"role": "Admin"}, {"username": 1})]

    admin_videos = list(mongo.db.tutorialvideo.find(
        {"username": {"$in": admin_users}},
        {"_id": 0, "title": 1, "video_name": 1, "file_path": 1, "username": 1}
    ))
    
    avatars = list(mongo.db.avatar.find({}, {"_id": 0, "file_path": 1, "username": 1}))

    username = session.get("username", None)

    return render_template("homepage.html", videos=admin_videos, avatars=avatars, username=username)


# Log In
@boundary.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Find user by username 
        user = mongo.db.useraccount.find_one({"username": username})

        if user:
            stored_hashed_password = user["password"]  # 

            print(f"[DEBUG] Entered Password: {password}")
            print(f"[DEBUG] Stored Hashed Password: {stored_hashed_password}")

            if check_password_hash(stored_hashed_password, password): 
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
@boundary.route('/logout')
def logout():
    """Logs out the user and redirects to homepage."""
    session.clear()
    flash("You have been logged out.", category="info")
    return redirect(url_for('boundary.home'))


# Create Account
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

        # ✅ Set role based on the session
        if session.get('role') == "Teacher":
            role = "Student"  # Teacher-created accounts default to Student
        else:
            role = "User"  # All others default to User

        # Validation checks
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

                # Debugging: Print assigned role before insertion
                print(f"[DEBUG] Assigned Role: {role}")

                # Insert new user with assigned role
                mongo.db.useraccount.insert_one({
                    "username": username,
                    "password": hashed_password,
                    "email": email,
                    "role": role,
                    "name": name,
                    "surname": surname,
                    "date_of_birth": formatted_date_of_birth
                })

                flash(f'Account created successfully! Assigned Role: {role}', category='success')
                return redirect(url_for('boundary.login'))
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD.', category='error')

    return render_template("createAccount.html")


# User Account Details
@boundary.route('/accountDetails', methods=['GET'])
def accDetails():
    if 'username' not in session:
        flash("You must be logged in to view account details.", category='error')
        return redirect(url_for('boundary.login'))  

    username = session.get('username')

    # Fetch user info 
    user_info = mongo.db.useraccount.find_one(
        {"username": username},
        {"_id": 0, "username": 1, "name": 1, "surname": 1, "date_of_birth": 1, "email": 1, "role": 1}
    )

    print(f"[DEBUG] Fetched User Info: {user_info}") 

    if not user_info:
        flash("User details not found.", category='error')
        return redirect(url_for('boundary.home'))

    return render_template("accountDetails.html", user_info=user_info)

# Edit Account Details
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

        # Remove empty fields
        updated_data = {key: value for key, value in updated_data.items() if value}

        if UpdateAccountDetailController.update_account_detail(username, updated_data):
            flash("Account details updated successfully!", category='success')
        else:
            flash("Failed to update account details.", category='error')

        return redirect(url_for('boundary.accDetails'))

    # Fetch user details
    user_info = DisplayUserDetailController.get_user_info(username)

    if not user_info:
        flash("User details not found.", category='error')
        return redirect(url_for('boundary.home'))

    return render_template("updateAccDetail.html", user_info=user_info)


# Update Password
@boundary.route('/update_password', methods=['GET', 'POST'])
def update_password():
    """Allows authenticated users to update their password securely."""
    if 'username' not in session:
        flash("You must be logged in to change your password.", category='error')
        return redirect(url_for('boundary.login'))

    username = session['username']

    if request.method == 'POST':
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # ✅ Fetch user from database
        user = mongo.db.useraccount.find_one({"username": username})
        if not user:
            flash("User not found.", category='error')
            return redirect(url_for('boundary.accDetails'))

        stored_hashed_password = user.get("password")

        # ✅ Validate Old Password
        if not check_password_hash(stored_hashed_password, old_password):
            flash("Incorrect current password.", category='error')
            return redirect(url_for('boundary.update_password'))

        # ✅ Validate New Password
        if new_password != confirm_password:
            flash("New passwords do not match.", category='error')
            return redirect(url_for('boundary.update_password'))
        if len(new_password) < 7:
            flash("New password must be at least 7 characters long.", category='error')
            return redirect(url_for('boundary.update_password'))

        # ✅ Hash New Password
        hashed_new_password = generate_password_hash(new_password)

        # ✅ Update Password in Database
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


# Admin
# Create Admin
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
                "date_of_birth": formatted_date_of_birth
            })

            flash(f"Account created successfully! Assigned Role: {role}", category="success")
            return redirect(url_for("boundary.home"))  
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", category="error")
            return redirect(url_for("boundary.create_account_admin"))

    return render_template("createAccountAdmin.html")



# Confirm Teacher
@boundary.route('/confirmTeacher/', methods=['GET','POST'])
def confirm_teacher_page():
    """Show all users with role 'User' for Admin approval."""
    if session.get('role') != "Admin":
        flash("Access Denied! Only Admins can confirm teachers.", category="error")
        return redirect(url_for("boundary.home"))

    # Fetch users with role "User" from MongoDB
    users = list(mongo.db.useraccount.find({"role": "User"}, {"_id": 0, "username": 1, "email": 1}))

    print(f"[DEBUG] Users fetched: {users}")  # Debugging output

    return render_template("confirmTeacher.html", users=users)

@boundary.route('/confirmTeacher/<username>', methods=['POST'])
def confirm_teacher(username):
    """Allows an Admin to confirm a 'User' as a 'Teacher'."""
    if session.get('role') != "Admin":
        flash("Access Denied!", category="error")
        return redirect(url_for("boundary.home"))

    # Update role in MongoDB
    update_result = mongo.db.useraccount.update_one(
        {"username": username, "role": "User"},
        {"$set": {"role": "Teacher"}}
    )

    if update_result.modified_count > 0:
        flash(f"{username} is now a Teacher!", category="success")
    else:
        flash("Failed to update role. Ensure the username exists and is not already a Teacher.", category="error")

    return redirect(url_for("boundary.confirm_teacher_page"))


# Upload Tutorial Video        
UPLOAD_FOLDER_VIDEO = 'FYP25S109/static/uploads/videos/'
UPLOAD_FOLDER_AVATAR = 'FYP25S109/static/uploads/avatar/'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

os.makedirs(UPLOAD_FOLDER_VIDEO, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_AVATAR, exist_ok=True)

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

        # ✅ Validate title and file
        if not title:
            flash("Please provide a title for the video.", category='error')
            return redirect(url_for('boundary.upload_tutorial'))

        if not file or file.filename == '':
            flash("No file selected. Please upload a video file.", category='error')
            return redirect(url_for('boundary.upload_tutorial'))

        # ✅ Validate file extension
        allowed_extensions = {'mp4', 'mov', 'avi', 'mkv'}
        if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            flash("Invalid file type. Please upload a valid video file.", category='error')
            return redirect(url_for('boundary.upload_tutorial'))

        # ✅ Create a `TutorialVideo` instance
        video = TutorialVideo(
            title=title,
            video_name=file.filename,
            video_file=file,
            username=username,
            user_role=user_role
        )

        # ✅ Save the video
        result = video.save_video()

        flash(result["message"], category="success" if result["success"] else "error")
        return redirect(url_for('boundary.upload_tutorial'))

    return render_template("uploadTutorial.html")

@boundary.route('/uploadedVideos', methods=['GET'])
def view_uploaded_videos():
    if 'username' not in session:
        flash("You must be logged in to view uploaded videos.", category='error')
        return redirect(url_for('boundary.login'))

    # Fetch videos uploaded by the user
    user_videos = list(mongo.db.videos.find(
        {"uploader": session['username']},
        {"_id": 0, "title": 1, "description": 1, "file_path": 1}
    ))

    return render_template("viewUploadedVideos.html", videos=user_videos)

# Delete Tutorial Video
@boundary.route('/manageVideos')
def manage_video():
    
    if 'username' not in session or session.get("role") != "Admin":
        flash("You are not authorized to view this page.", category="error")
        return redirect(url_for('boundary.home'))
    
    all_videos = list(mongo.db.tutorialvideo.find({}, {"_id": 1, "title": 1, "video_name": 1, "file_path": 1, "username": 1}))

    return render_template("manageVideo.html", videos=all_videos, mongo=mongo)

@boundary.route('/deleteVideo', methods=['POST'])
def delete_video():
    """Deletes a video from the database and storage with role-based permissions."""
    
    if 'username' not in session:
        flash("You must be logged in to delete videos.", category="error")
        return redirect(url_for('boundary.home'))

    video_name = request.form.get("video_name")  # Get video name from form
    username = session["username"]  # Get logged-in user
    user_role = session.get("role", "User")  # Get user role

    # Fetch video details from the database
    video = mongo.db.tutorialvideo.find_one({"video_name": video_name})

    if not video:
        flash("Video not found!", category="error")
        return redirect(url_for('boundary.home'))

    uploader_username = video["username"]

    # Fetch uploader role
    uploader = mongo.db.useraccount.find_one({"username": uploader_username}, {"role": 1})
    uploader_role = uploader["role"] if uploader else "User"

    # Admins can delete if the uploader is not another Admin
    if user_role == "Admin":
        if uploader_role == "Admin" and uploader_username != username:
            flash("You cannot delete videos uploaded by another Admin.", category="error")
            return redirect(url_for('boundary.home'))

    # Allow the uploader to delete their own video
    if user_role == "Admin" or username == uploader_username:
        # Get video file path
        file_path = os.path.join("static/uploads/videos", video_name)

        # Delete file from storage
        if os.path.exists(file_path):
            os.remove(file_path)

        # Remove video from MongoDB
        mongo.db.tutorialvideo.delete_one({"video_name": video_name})

        flash("Video deleted successfully.", category="success")
    else:
        flash("You are not authorized to delete this video.", category="error")

    return redirect(url_for('boundary.home'))

#Reset password
@boundary.route('/forgetpass', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        new_password = request.form.get('new_password')

        # Find user
        user = mongo.db.useraccount.find_one({"username": username, "email": email})
        if not user:
            print("[ERROR] User not found in MongoDB.")
            flash("User not found. Check your username and email.", category="error")
            return redirect(url_for('boundary.reset_password'))

        print(f"[DEBUG] Found user: {user}")

        # Hash new password
        old_password_hash = user["password"]
        hashed_password = generate_password_hash(new_password)

        # Check if the new password is different
        if hashed_password == old_password_hash:
            print("[ERROR] New password is the same as the old password!")
            flash("New password cannot be the same as the old password.", category="error")
            return redirect(url_for('boundary.reset_password'))

        # Update password
        result = mongo.db.useraccount.update_one(
            {"username": username}, {"$set": {"password": hashed_password}}
        )
        print(f"[DEBUG] MongoDB update result: {result.modified_count}")

        if result.modified_count == 0:
            print("[ERROR] Password update failed in MongoDB.")
            flash("Password update failed. Try again.", category="error")
            return redirect(url_for('boundary.reset_password'))

        flash("Password reset successful!", category="success")
        return redirect(url_for('boundary.login'))

    return render_template("forgetPassword.html")



# Manage Avatar Menu
@boundary.route('/admin_manage_avatars')
def admin_manage_avatars():
    """
    Route to manage avatars for the logged-in user.
    """
    if 'username' not in session:
        flash("You must be logged in to manage your avatar.", category='error')
        return redirect(url_for('boundary.login'))

    username = session.get('username')
    user_role = session.get('role')

    print(f"[DEBUG] Retrieving avatars for user: {username}")  # Debugging: Print username

    # Retrieve avatars for the logged-in user
    avatars = AdminManageAvatarController.get_avatars_by_username(username)

    if not avatars:
        print(f"[DEBUG] No avatars found for user: {username}")  # Debugging: No avatars found
        flash("No avatars found for your account.", category='info')

    return render_template(
        "admin_manage_avatars.html",
        username=username,
        user_role=user_role,
        avatars=avatars  # Pass avatars to the template
    )


# Add Avatar Boundary
@boundary.route('/admin_create_avatar', methods=['GET', 'POST'])
def admin_create_avatar():
    """
    Route to create/upload an avatar for the logged-in user.
    """
    if 'username' not in session:
        flash("You must be logged in to create an avatar.", category='error')
        return redirect(url_for('boundary.login'))

    print("[DEBUG] Route: admin_create_avatar")  # Debugging: Confirm route is called

    if request.method == 'POST':
        username = session.get('username')  # Retrieve username from session
        avatar_file = request.files.get('avatar')  # Retrieve uploaded file

        print(f"[DEBUG] Username from session: {username}")  # Debugging: Print username
        print(f"[DEBUG] Uploaded file: {avatar_file.filename if avatar_file else 'None'}")  # Debugging: Print uploaded file

        if not username or not avatar_file:
            flash("Username and avatar file are required.", category='error')
            return redirect(url_for('boundary.admin_create_avatar'))

        # Call the AdminAddAvatarController to add the avatar
        result = AdminAddAvatarController.add_avatar(username, avatar_file)

        if result['success']:
            flash("Avatar added successfully.", category='success')
        else:
            flash(f"Failed to add avatar: {result['message']}", category='error')

        return redirect(url_for('boundary.admin_create_avatar'))

    return render_template("admin_add_avatar.html")