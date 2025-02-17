from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from . import mysql

import stripe
from werkzeug.security import generate_password_hash
from datetime import datetime

from FYP25S109.controller import LoginController, CreateUserAccController, DisplayUserDetailController, UpdateUserRoleController
from FYP25S109.entity import UserAccount

boundary = Blueprint('boundary', __name__)  # Blueprints mean it has routes inside a bunch of URLs defined

YOUR_DOMAIN = "http://localhost:5000"

# Homepage
@boundary.route('/', methods=['GET', 'POST'])
def home():
    username = session.get('username')
    return render_template("homepage.html", user_name=username)

# Log In
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


# Log Out
@boundary.route('/logout')
def logout():
    session.pop('username', None)
    session['user_authenticated'] = False
    flash('You have been logged out', category='success')
    return redirect(url_for('boundary.home'))


# Create Account
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


# User Account Details
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


# Admin
# Create Admin
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



# Confirm Teacher
@boundary.route('/confirmTeacher', methods=['GET'])
def confirm_teacher_page():
    """Show all users with role 'User' for Admin approval."""
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
    """Allows an Admin to confirm a 'User' as a 'Teacher'."""
    if session.get('role') != "Admin":
        flash("Access Denied!", category="error")
        return redirect(url_for("boundary.home"))

    success = UpdateUserRoleController.change_role(username, "Teacher")

    if success:
        flash(f"{username} is now a Teacher!", category="success")
    else:
        flash("Failed to update role. Ensure the username exists.", category="error")

    return redirect(url_for("boundary.confirm_teacher_page"))


        