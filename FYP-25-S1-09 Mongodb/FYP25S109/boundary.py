from flask import Blueprint, render_template, request, flash, redirect, url_for, session
# from . import mysql
from . import mongo  

import os
from werkzeug.utils import secure_filename

import stripe
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from datetime import datetime

from FYP25S109.controller import LoginController, CreateUserAccController, DisplayUserDetailController, UpdateUserRoleController, UpdateAccountDetailController
from FYP25S109.entity import UserAccount, TutorialVideo

boundary = Blueprint('boundary', __name__)  # Blueprints mean it has routes inside a bunch of URLs defined

YOUR_DOMAIN = "http://localhost:5000"

# Homepage
@boundary.route('/')
def homepage():
    """Fetch approved videos and display them on the homepage."""
    approved_videos = list(mongo.db.tutorialvideo.find(
        {"status": "Approved"},  # ✅ Show only approved videos
        {"_id": 0, "title": 1, "video_name": 1, "file_path": 1, "username":1}
    ))
    username = session.get("username", None)

    return render_template("homepage.html", videos=approved_videos, username=username)

# Log In
"""
@boundary.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = LoginController.userLogin(username, password)

        if user:
            user_role = user[1]  # Get the role from database

            session['username'] = username
            session['role'] = user_role  # Auto-detected role
            session['user_authenticated'] = True

            flash(f'Login successful! You are logged in as {user_role.capitalize()}.', category='success')
            return redirect(url_for('boundary.home'))
        else:
            flash('Wrong username or password.', category='error')

    return render_template("login.html")
"""

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
    return redirect(url_for('boundary.homepage'))


# Create Account
"""
@boundary.route('/createAccount', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form.get('username')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        email = request.form.get('email')
        name = request.form.get('name')
        surname = request.form.get('surname')
        date_of_birth = request.form.get('date_of_birth')
        role = request.form.get('role')  # Get role from hidden input

        # Validation checks
        if len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords do not match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        elif role not in ["Admin", "Teacher", "Student", "User"]:
            flash('Invalid role selection.', category='error')
        else:
            try:
                # Convert date format
                date_of_birth_obj = datetime.strptime(date_of_birth, '%Y-%m-%d')
                formatted_date_of_birth = date_of_birth_obj.strftime('%Y-%m-%d')

                # Hash the password
                hashed_password = generate_password_hash(password1, method='pbkdf2:sha256')

                # Create UserAccount entity
                userAcc = UserAccount(username, hashed_password, name, surname, email, formatted_date_of_birth, role)

                # Insert into database
                result = CreateUserAccController.createUserAcc(userAcc)

                if result:
                    flash('Account created successfully!', category='success')
                    return redirect(url_for('boundary.login'))  # Redirect to login page
                else:
                    flash('Account creation failed. Try again.', category='error')
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD.', category='error')

    return render_template("createAccount.html")
"""
    
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
"""
@boundary.route('/accountDetails', methods=['GET'])
def accDetails():
    if 'username' not in session:
        flash("You must be logged in to view account details.", category='error')
        return redirect(url_for('boundary.login'))  # Redirect to login if not authenticated

    username = session.get('username')
    user_info = DisplayUserDetailController.get_user_info(username)  # Fetch user info

    if not user_info:
        flash("User details not found.", category='error')
        return redirect(url_for('boundary.home'))

    return render_template("accountDetails.html", user_info=user_info)
"""

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
"""
@boundary.route('/createAccountAdmin', methods=['GET', 'POST'])
def create_account_admin():
    if 'role' not in session or session['role'] != 'Admin':
        flash("Access Denied! Only Admins can create accounts.", category='error')
        return redirect(url_for('boundary.home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        email = request.form.get('email')
        name = request.form.get('name')
        surname = request.form.get('surname')
        date_of_birth = request.form.get('date_of_birth')
        role = request.form.get('role')  # Admin selects the role

        # Validation checks
        if len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords do not match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        elif role not in ["Admin", "Teacher", "Student"]:
            flash('Invalid role selection.', category='error')
        else:
            try:
                # Convert date format
                date_of_birth_obj = datetime.strptime(date_of_birth, '%Y-%m-%d')
                formatted_date_of_birth = date_of_birth_obj.strftime('%Y-%m-%d')

                # Hash the password
                hashed_password = generate_password_hash(password1, method='pbkdf2:sha256')

                # Create UserAccount entity
                userAcc = UserAccount(username, hashed_password, name, surname, email, formatted_date_of_birth, role)

                # Insert into database
                result = CreateUserAccController.createUserAcc(userAcc)

                if result:
                    flash(f'Account created successfully! ({role})', category='success')
                    return redirect(url_for('boundary.home'))  # Redirect to homepage
                else:
                    flash('Account creation failed. Try again.', category='error')
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD.', category='error')

    return render_template("createAccountAdmin.html")
"""
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from datetime import datetime
from FYP25S109 import mongo  # Assuming you're using MongoDB

@boundary.route('/createAccountAdmin', methods=['GET', 'POST'])
def create_account_admin():
    # ✅ Ensure only Admins can access this route
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

        # ✅ Ensure passwords match
        if password1 != password2:
            flash("Passwords do not match.", category="error")
            return redirect(url_for("boundary.create_account_admin"))

        # ✅ Validate role assignment (only valid roles allowed)
        valid_roles = ["Admin", "Teacher", "Student"]
        if role not in valid_roles:
            flash("Invalid role selection.", category="error")
            return redirect(url_for("boundary.create_account_admin"))

        # ✅ Hash password
        hashed_password = generate_password_hash(password1, method='pbkdf2:sha256')

        # ✅ Save user to database
        try:
            date_of_birth_obj = datetime.strptime(date_of_birth, '%Y-%m-%d')
            formatted_date_of_birth = date_of_birth_obj.strftime('%Y-%m-%d')

            # ✅ Insert user into MongoDB
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
            return redirect(url_for("boundary.home"))  # ✅ Redirect after success
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", category="error")
            return redirect(url_for("boundary.create_account_admin"))

    # ✅ Ensure GET requests return a valid response
    return render_template("createAccountAdmin.html")



# Confirm Teacher
"""
@boundary.route('/confirmTeacher', methods=['GET'])
def confirm_teacher_page():
    if session.get('role') != "Admin":
        flash("Access Denied! Only Admins can confirm teachers.", category="error")
        return redirect(url_for("boundary.home"))

    cur = mysql.connection.cursor()
    cur.execute("SELECT username, email FROM useraccount WHERE role = 'User'")
    users = cur.fetchall()
    cur.close()

    return render_template("confirmTeacher.html", users=users)


@boundary.route('/confirmTeacher/<username>', methods=['POST'])
def confirm_teacher(username):
    if session.get('role') != "Admin":
        flash("Access Denied!", category="error")
        return redirect(url_for("boundary.home"))

    success = UpdateUserRoleController.change_role(username, "Teacher")

    if success:
        flash(f"{username} is now a Teacher!", category="success")
    else:
        flash("Failed to update role. Ensure the username exists.", category="error")

    return redirect(url_for("boundary.confirm_teacher_page"))
"""
@boundary.route('/confirmTeacher/', methods=['GET','POST'])
def confirm_teacher_page():
    """Show all users with role 'User' for Admin approval."""
    if session.get('role') != "Admin":
        flash("Access Denied! Only Admins can confirm teachers.", category="error")
        return redirect(url_for("boundary.home"))

    # ✅ Fetch users with role "User" from MongoDB
    users = list(mongo.db.useraccount.find({"role": "User"}, {"_id": 0, "username": 1, "email": 1}))

    print(f"[DEBUG] Users fetched: {users}")  # ✅ Debugging output

    return render_template("confirmTeacher.html", users=users)

@boundary.route('/confirmTeacher/<username>', methods=['POST'])
def confirm_teacher(username):
    """Allows an Admin to confirm a 'User' as a 'Teacher'."""
    if session.get('role') != "Admin":
        flash("Access Denied!", category="error")
        return redirect(url_for("boundary.home"))

    # ✅ Update role in MongoDB
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
UPLOAD_FOLDER = 'FYP25S109/static/uploads/videos/'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

# Ensure the directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@boundary.route('/uploadTutorial', methods=['GET', 'POST'])
def upload_tutorial():
    """Allows users to upload tutorial videos."""
    if 'username' not in session:
        flash("You must be logged in to upload a tutorial video.", category='error')
        return redirect(url_for('boundary.login'))

    if request.method == 'POST':
        file = request.files.get('file')
        title = request.form.get("title")
        username = session["username"]
        user_role = session.get("role", "User")  # ✅ Retrieve user role, default to "User"

        # ✅ Create a `TutorialVideo` instance and pass `user_role`
        video = TutorialVideo(title=title, video_name=file.filename, video_file=file, username=username, user_role=user_role)

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

    # ✅ Fetch videos uploaded by the user
    user_videos = list(mongo.db.videos.find(
        {"uploader": session['username']},
        {"_id": 0, "title": 1, "description": 1, "file_path": 1, "status": 1}
    ))

    return render_template("viewUploadedVideos.html", videos=user_videos)