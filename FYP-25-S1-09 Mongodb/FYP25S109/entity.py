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
from pymongo.errors import DuplicateKeyError
from io import BytesIO
from bson import ObjectId
# Separate Upload Folders
UPLOAD_FOLDER_VIDEO = 'FYP25S109/static/uploads/videos/'
UPLOAD_FOLDER_AVATAR = 'FYP25S109/static/uploads/avatar/'

# Allowed Extensions
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

# Ensure Directories Exist
os.makedirs(UPLOAD_FOLDER_VIDEO, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_AVATAR, exist_ok=True)


def setup_indexes():
    #This index will prevent users to create another account with a username taken by other user 
    mongo.db.useraccount.create_index("username", unique=True)
    print("Unique index on 'username' field created.")

class UserAccount:
    def __init__(self, username=None, password=None, name=None, surname=None, email=None, date_of_birth=None, role=None, status='active'):
        self.username = username
        self.password = password
        self.name = name
        self.surname = surname
        self.email = email
        self.date_of_birth = date_of_birth
        self.role = role
        self.status = status

    @staticmethod
    def create_user_acc(user_acc):
        try:
            logging.debug(f"Attempting to insert user: {user_acc.username}, {user_acc.email}, {user_acc.role}")

            existing_user = mongo.db.useraccount.find_one({"username": user_acc.username})
            if existing_user:
                logging.error("Username already exists.")
                return False

            mongo.db.useraccount.insert_one({
                "username": user_acc.username,
                "password": generate_password_hash(user_acc.password),
                "name": user_acc.name,
                "surname": user_acc.surname,
                "email": user_acc.email,
                "date_of_birth": user_acc.date_of_birth,
                "role": user_acc.role,
                "status": user_acc.status
            })
            logging.info("User created successfully.")
            return True
        except DuplicateKeyError:
            logging.error("Username already exists.")
            return False
        except Exception as e:
            logging.error(f"Error creating user: {e}")
            return False

    @staticmethod
    def login(username, password):
        try:
            user = mongo.db.useraccount.find_one({"username": username})

            if user and check_password_hash(user["password"], password):
                return user["username"], user["role"]
            return None
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return None

    @staticmethod
    def update_account_detail(username, updated_data):
        try:
            if not updated_data:
                logging.warning(f"No update data provided for {username}.")
                return False

            update_result = mongo.db.useraccount.update_one({"username": username}, {"$set": updated_data})

            if update_result.modified_count > 0:
                logging.debug(f"User Update: Username={username} | Updated Fields={updated_data}")
                return True
            logging.warning(f"No changes made for {username}.")
            return False

        except Exception as e:
            logging.error(f"Failed to update user info: {str(e)}")
            return False

    @staticmethod
    def find_by_username(username):
        try:
            logging.debug(f"Finding user by username: {username}")
            user = mongo.db.useraccount.find_one({"username": username})
            return user
        except Exception as e:
            logging.error(f"Failed to find user by username: {str(e)}")
            return None

    @staticmethod
    def search_user(query):
        try:
            users = list(mongo.db.useraccount.find({
                "$or": [
                    {"username": {"$regex": query, "$options": "i"}},
                    {"email": {"$regex": query, "$options": "i"}}
                ]
            }, {"_id": 0}))  # Exclude MongoDB's _id from the result

            return users
        except Exception as e:
            logging.error(f"Error searching users: {e}")
            return []

    @staticmethod
    def suspend_user(username):
        try:
            result = mongo.db.useraccount.update_one(
                {"username": username},
                {"$set": {"status": "suspended"}}
            )
            if result.modified_count == 0:
                logging.warning("No user found to suspend.")
                return False
            logging.info(f"User {username} suspended successfully.")
            return True
        except Exception as e:
            logging.error(f"Error suspending user: {e}")
            return False

    @staticmethod
    def delete_user(username):
        try:
            result = mongo.db.useraccount.update_one(
                {"username": username},
                {"$set": {"status": "deleted"}}
            )
            if result.modified_count == 0:
                logging.warning("No user found to delete.")
                return False
            logging.info(f"User {username} marked as deleted.")
            return True
        except Exception as e:
            logging.error(f"Error deleting user: {e}")
            return False



class TutorialVideo:
    def __init__(self, title=None, video_name=None ,video_file=None, username=None, user_role=None,description=None):
        self.title = title
        self.video_name = video_name
        self.video_file = video_file
        self.username = username
        self.user_role = user_role
        self.description = description

    def save_video(self):
        try:
            if not self.video_file:
                raise ValueError("No file selected for upload.")

            filename = secure_filename(self.video_file.filename)
            file_path = os.path.join(UPLOAD_FOLDER_VIDEO, filename)

            # Validate file extension
            if filename.split('.')[-1].lower() not in ALLOWED_VIDEO_EXTENSIONS:
                raise ValueError("Invalid video format.")

            self.video_file.save(file_path)
            status = 'Approved' if self.user_role == 'Admin' else 'Pending'

            mongo.db.tutorialvideo.insert_one({
                'title': self.title,
                'video_name': filename,
                'file_path': file_path,
                'username': self.username,
                'status': status,
                'upload_date': datetime.now(),
                'description': self.description
            })
            return {"success": True, "message": "Video uploaded successfully." if self.user_role == "Admin" else "Awaiting approval."}

        except Exception as e:
            logging.error(f"Error saving video: {str(e)}")
            return {"success": False, "message": str(e)}
    def delete_video(video_id):
        try:
            video = mongo.db.tutorialvideo.find_one({"_id": video_id})
            if video:
                os.remove(video['file_path'])
        except Exception as e:
            logging.error(f"Error deleting video: {str(e)}")
            return {"success": False, "message": str(e)}
        
    def search_video(search_query):
        try:
            # Use case-insensitive and partial matching
            videos = mongo.db.tutorialvideo.find({
                "title": {"$regex": search_query, "$options": "i"}
            })
            return list(videos)
        except Exception as e:
            logging.error(f"Failed to search videos: {str(e)}")
            return []

class Avatar:
    def __init__(self, image_file, username=None,upload_date=None):
        self.image_file = image_file
        self.username = username
        self.upload_date = upload_date

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

    def save_image(self):
        try:
            if not self.image_file:
                raise ValueError("No file selected for upload.")

            filename = secure_filename(self.image_file.filename)
            if not self.allowed_file(filename):
                raise ValueError("Invalid image format.")

            file_path = os.path.join(UPLOAD_FOLDER_AVATAR, filename)
            self.image_file.save(file_path)

            # Process image (e.g., remove background)
            try:
                with open(file_path, "rb") as f:
                    output_image = remove(f.read())
            except Exception as e:
                logging.error(f"Error processing image: {str(e)}")
                return {"success": False, "message": f"Error processing image: {str(e)}"}

            processed_filename = f"processed_{filename}"
            processed_file_path = os.path.join(UPLOAD_FOLDER_AVATAR, processed_filename)

            try:
                with open(processed_file_path, "wb") as f:
                    f.write(output_image)
            except Exception as e:
                logging.error(f"Error saving processed image: {str(e)}")
                return {"success": False, "message": f"Error saving processed image: {str(e)}"}

            # Remove original uploaded file
            try:
                os.remove(file_path)
            except Exception as e:
                logging.error(f"Error deleting original file: {str(e)}")
                return {"success": False, "message": f"Error deleting original file: {str(e)}"}

            # Add avatar to DB
            add_result = self.add_avatar(self.username, processed_file_path)
            if not add_result:
                return {"success": False, "message": "Failed to add avatar to database."}

            return {"success": True, "message": "Avatar uploaded successfully.", "file_path": processed_file_path}

        except Exception as e:
            logging.error(f"Error processing avatar: {str(e)}")
            return {"success": False, "message": f"Error processing avatar: {str(e)}"}

    def add_avatar(self, username, file_path):
        try:
            relative_path = file_path.split('static/')[1]  # Get relative path for Flask

            mongo.db.avatar.insert_one({
                'username': username,
                'file_path': relative_path,
                'upload_date': datetime.now()
            })
            return True
        except Exception as e:
            logging.error(f"Error adding avatar to database: {str(e)}")
            return False
   
    def search_avatar(search_query):
        try:
            # Use regex for partial and case-insensitive matching
            avatars = mongo.db.avatar.find({
                "username": {"$regex": search_query, "$options": "i"}
            })
            return list(avatars)  # Convert cursor to list
        except Exception as e:
            logging.error(f"Failed to search avatars: {str(e)}")
            return []
    def resize_avatar(image_file, size=(150, 150)):
        img = Image.open(image_file)
        img = img.convert("RGB")
        img.thumbnail(size)

        img_io = BytesIO()
        img.save(img_io, format="JPEG")
        img_io.seek(0)
    
        return img_io

    def find_by_id(avatar_id):
        try:
            avatar = mongo.db.avatar.find_one({"_id": ObjectId(avatar_id)})
            return avatar
        except Exception as e:
            logging.error(f"Failed to find avatar by ID: {str(e)}")
            return None
        
    def delete_avatar(avatar_id):
     try:
        avatar = mongo.db.avatar.find_one({"_id": ObjectId(avatar_id)})
        if avatar:
            # Remove the file from storage
            file_path = os.path.join("static", avatar["file_path"])
            if os.path.exists(file_path):
                os.remove(file_path)

            # Delete the record from the database
            mongo.db.avatar.delete_one({"_id": ObjectId(avatar_id)})
            return True
     except Exception as e:
        logging.error(f"Error deleting avatar: {str(e)}")
        return False

