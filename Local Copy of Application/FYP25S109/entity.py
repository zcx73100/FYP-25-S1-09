from flask import session
from . import mongo
import os
import logging
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename 
from rembg import remove
from PIL import Image
import io

UPLOAD_FOLDER = 'FYP25S109/static/uploads/'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

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
    def create_user_acc(user_acc):
        try:
            print(f"[DEBUG] Attempting to insert user: {user_acc.username}, {user_acc.email}, {user_acc.role}")

            existing_user = mongo.db.useraccount.find_one({"username": user_acc.username})
            if existing_user:
                print("[ERROR] Username already exists.")
                return False  

            mongo.db.useraccount.insert_one({
                "username": user_acc.username,
                "password": generate_password_hash(user_acc.password),
                "name": user_acc.name,
                "surname": user_acc.surname,
                "email": user_acc.email,
                "date_of_birth": user_acc.date_of_birth,
                "role": user_acc.role
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
                return user["username"], user["role"]
            return None
        except Exception as e:
            print(f"[ERROR] Login failed: {e}")
            return None

    @staticmethod
    def update_account_detail(username, updated_data):
        try:
            if not updated_data:
                print(f"[WARNING] No update data provided for {username}.")
                return False

            update_result = mongo.db.useraccount.update_one({"username": username}, {"$set": updated_data})

            if update_result.modified_count > 0:
                print(f"[DEBUG] User Update: Username={username} | Updated Fields={updated_data}")
                return True
            print(f"[WARNING] No changes made for {username}.")
            return False

        except Exception as e:
            print(f"[ERROR] Failed to update user info: {str(e)}")  
            return False
    @staticmethod
    def find_by_username(username):
        """
        Find a user by their username in the database.
        """
        try:
            print(f"[DEBUG] Finding user by username: {username}")  # Debugging: Print username
            user = mongo.db.useraccount.find_one({"username": username})
            return user
        except Exception as e:
            print(f"[ERROR] Failed to find user by username: {str(e)}")
            return None

class TutorialVideo:
    def __init__(self, title=None, video_file=None, username=None, user_role=None):
        self.title = title
        self.video_file = video_file
        self.username = username
        self.user_role = user_role  

    def save_video(self):
        try:
            if not self.video_file:
                raise ValueError("No file selected for upload.")

            filename = secure_filename(self.video_file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, 'videos', filename)

            self.video_file.save(file_path)
            status = 'Approved' if self.user_role == 'Admin' else 'Pending'

            mongo.db.tutorialvideo.insert_one({
                'title': self.title,
                'file_path': file_path,
                'username': self.username,
                'status': status,
                'upload_date': datetime.utcnow()
            })
            return {"success": True, "message": "Video uploaded successfully." if self.user_role == "Admin" else "Awaiting approval."}

        except Exception as e:
            logging.error(f"Error saving video: {str(e)}")
            return {"success": False, "message": str(e)}


class Avatar:
    def __init__(self, image_file, username=None):
        self.image_file = image_file
        self.username = username

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

    def save_image(self):
        """
        Save the image file, process it (e.g., remove background), and store it in the database.
        """
        try:
            if not self.image_file:
                raise ValueError("No file selected for upload.")

            filename = secure_filename(self.image_file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, 'avatars', filename)

            # Save the uploaded file
            self.image_file.save(file_path)

            # Process the image (e.g., remove background)
            try:
                with open(file_path, "rb") as f:
                    output_image = remove(f.read())  
            except Exception as e:
                print(f"[ERROR] Error reading or processing image: {str(e)}")
                return {"success": False, "message": f"Error processing image: {str(e)}"}

            # Save the processed image
            processed_filename = f"processed_{filename}"
            processed_file_path = os.path.join(UPLOAD_FOLDER, 'avatars', processed_filename)

            try:
                with open(processed_file_path, "wb") as f:
                    f.write(output_image)
            except Exception as e:
                print(f"[ERROR] Error saving processed image: {str(e)}")
                return {"success": False, "message": f"Error saving processed image: {str(e)}"}

            # Remove the original uploaded file
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[ERROR] Error deleting original file: {str(e)}")
                return {"success": False, "message": f"Error deleting original file: {str(e)}"}

            # Add the avatar to the database
            add_result = self.add_avatar(self.username, processed_file_path)
            if not add_result:
                return {"success": False, "message": "Failed to add avatar to database."}

            return {"success": True, "message": "Avatar uploaded successfully.", "file_path": processed_file_path}

        except Exception as e:
            return {"success": False, "message": f"Error processing avatar: {str(e)}"}

    def add_avatar(self, username, file_path):
        """
        Add the avatar to the database.
        """
        try:
            print(f"[DEBUG] Adding avatar to database for user: {username}")  # Debugging: Print username
            print(f"[DEBUG] File path: {file_path}")  # Debugging: Print file path

            mongo.db.avatar.insert_one({
                'username': username,
                'file_path': file_path,
                'upload_date': datetime.utcnow()
            })
            return True
        except Exception as e:
            print(f"[ERROR] Error adding avatar to database: {str(e)}")  # Debugging: Print error
            return False