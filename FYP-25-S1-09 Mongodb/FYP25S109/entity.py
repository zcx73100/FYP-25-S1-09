from flask import session
# from . import mysql
from . import mongo
import os
import logging
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename 

UPLOAD_FOLDER = 'static/uploads/videos'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

# Ensure the directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class UserAccount:
    def __init__(self, username=None, password=None, name=None, surname=None, email=None, date_of_birth=None, role=None):
        self.username = username
        self.password = password
        self.name = name
        self.surname = surname
        self.email = email
        self.date_of_birth = date_of_birth
        self.role = role


    @staticmethod
    def createUserAcc(userAcc):
        try:
            print(f"[DEBUG] Attempting to insert user: {userAcc.username}, {userAcc.email}, {userAcc.role}")

            # Check if username already exists
            existing_user = mongo.db.useraccount.find_one({"username": userAcc.username})
            if existing_user:
                print("[ERROR] Username already exists.")
                return False  # Username already exists

            # Insert user data into MongoDB
            mongo.db.useraccount.insert_one({
                "username": userAcc.username,
                "password": userAcc.password,  # Hashed password
                "name": userAcc.name,
                "surname": userAcc.surname,
                "email": userAcc.email,
                "date_of_birth": userAcc.date_of_birth,
                "role": userAcc.role
            })

            print("[DEBUG] User successfully inserted into MongoDB!")
            return True

        except Exception as e:
            print(f"[ERROR] Database Insertion Error: {str(e)}")  
            return False

    @staticmethod
    def login(username, password):
        try:
            user = mongo.db.useraccount.find_one({"username": username})

            if user and check_password_hash(user["password"], password):
                return (user["username"], user["role"])  # Return (username, role)
            else:
                return None  # Return None if authentication fails

        except Exception as e:
            print(f"[ERROR] Login failed: {e}")
            return None

    @staticmethod
    def get_user_info(username):
        try:
            user_data = mongo.db.useraccount.find_one(
                {"username": username},
                {"_id": 0, "username": 1, "name": 1, "surname": 1, "email": 1, "role": 1}
            )
            return user_data
        except Exception as e:
            print(f"[ERROR] Fetching user info failed: {e}")
            return None

    @staticmethod
    def update_role(username, new_role):
        try:
            # Check if the user exists
            user = mongo.db.useraccount.find_one({"username": username})
            if not user:
                print(f"[ERROR] User '{username}' not found in database.")
                return False

            # Prevent redundant updates
            if user.get("role") == new_role:
                print(f"[WARNING] User '{username}' is already a '{new_role}'. No update needed.")
                return True
            
            # Perform the update
            update_result = mongo.db.useraccount.update_one(
                {"username": username, "role": "User"},  # Only update if role is "User"
                {"$set": {"role": new_role}}
            )

            if update_result.modified_count > 0:
                print(f"[DEBUG] Role updated successfully: {username} → {new_role}")
                return True
            else:
                print(f"[ERROR] Role update failed for {username}. Ensure user exists and is not already a Teacher.")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to update role: {e}")
            return False

    @staticmethod
    def update_account_detail(username, updated_data):
        try:
            if not updated_data:
                print(f"[WARNING] No update data provided for {username}.")
                return False

            update_result = mongo.db.useraccount.update_one(
                {"username": username},
                {"$set": updated_data}
            )

            if update_result.modified_count > 0:
                print(f"[DEBUG] User Update: Username={username} | Updated Fields={updated_data}")
                return True
            else:
                print(f"[WARNING] No changes made for {username}.")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to update user info: {str(e)}")  
            return False

    @staticmethod
    def update_password(username, new_password):
        try:
            hashed_password = generate_password_hash(new_password)

            update_result = mongo.db.useraccount.update_one(
                {"username": username},
                {"$set": {"password": hashed_password}}
            )

            if update_result.modified_count > 0:
                print(f"[DEBUG] Password updated successfully for {username}.")
                return True
            else:
                print(f"[WARNING] Password update failed for {username}.")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to update password: {str(e)}")
            return False
        
        
class TutorialVideo:
    def __init__(self, title=None, video_name=None, video_file=None, username=None):
        self.title = title
        self.video_name = video_name
        self.video_file = video_file
        self.username = username

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def save_video(self):
        try:
            if not self.video_file or self.video_file.filename == '':
                raise ValueError("No file selected for upload.")

            if not self.allowed_file(self.video_file.filename):
                raise ValueError("Invalid file format. Allowed: mp4, mov, avi, mkv.")

            # Secure filename
            filename = secure_filename(self.video_file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            # Save file to server
            self.video_file.save(file_path)

            # Prepare video metadata
            video_data = {
                'title': self.title,
                'video_name': filename,
                'file_path': file_path,  # Store the path instead of file content
                'username': self.username,
                'status': 'Pending',
                'upload_date': datetime.utcnow()
            }

            # Insert into MongoDB
            mongo.db.videos.insert_one(video_data)

            return {"success": True, "message": "Video uploaded successfully. Awaiting approval."}
        except Exception as e:
            logging.error(f"Error saving video to database: {e}")
            return {"success": False, "message": str(e)}
        
"""
    @staticmethod
    def createUserAcc(userAcc):
        cur = None  # Ensure `cur` is initialized before using it

        try:
            cur = mysql.connection.cursor()

            print(f"[DEBUG] Attempting to insert user: {userAcc.username}, {userAcc.email}, {userAcc.role}")

           
            query =
            INSERT INTO userAccount (username, password, name, surname, email, date_of_birth, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            

            data = (userAcc.username, userAcc.password, userAcc.name, userAcc.surname, 
                    userAcc.email, userAcc.date_of_birth, userAcc.role)

            cur.execute(query, data)
            mysql.connection.commit()

            print("[DEBUG] User successfully inserted into the database!")
            return True

        except Exception as e:
            print(f"[ERROR] Database Insertion Error: {str(e)}")  # <-- Copy this error and send it to me!
            return False

        finally:
            if cur is not None:  # Ensure `cur` is closed only if it was initialized
                cur.close()

    @staticmethod
    def login(username, password):
        try:
            cur = mysql.connection.cursor()
            query = "SELECT username, role, password FROM useraccount WHERE username = %s"
            cur.execute(query, (username,))
            account = cur.fetchone()  # Fetch (username, role, hashed_password)

            if account and check_password_hash(account[2], password):
                return account[:2]  # Return (username, role)
            else:
                return None  # Return None if authentication fails

        except Exception as e:
            print(f"Error during login: {e}")
            return None

        finally:
            cur.close()
            
            
    @staticmethod
    def get_user_info(username):
        try:
            cur = mysql.connection.cursor()
            query = "SELECT username, name, surname, email, role FROM useraccount WHERE username = %s"
            cur.execute(query, (username,))
            user_data = cur.fetchone()  # Fetch user info (username, name, surname, email, role)
            return user_data
        except Exception as e:
            print(f"Error fetching user info: {e}")
            return None
        finally:
            cur.close()

    @staticmethod
    def update_role(username, new_role):
        try:
            cur = mysql.connection.cursor()
            query = "UPDATE useraccount SET role = %s WHERE username = %s"
            cur.execute(query, (new_role, username))
            mysql.connection.commit()
            cur.close()
            return True  # Role update successful
        except Exception as e:
            print(f"[ERROR] Failed to update role: {e}")
            return False  # Role update failed
"""

    