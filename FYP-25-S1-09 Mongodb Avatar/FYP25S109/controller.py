from flask import session
from FYP25S109 import entity
import datetime
import os
import logging
from . import mongo
from .entity import UserAccount, TutorialVideo, Avatar
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# Separate Upload Folders
UPLOAD_FOLDER_VIDEO = 'FYP25S109/static/uploads/videos/'
UPLOAD_FOLDER_AVATAR = 'FYP25S109/static/uploads/avatar/'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

# Ensure Upload Directories Exist
os.makedirs(UPLOAD_FOLDER_VIDEO, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_AVATAR, exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# ===================== User Account =====================
class LoginController:
    @staticmethod
    def userLogin(username, password):
        user = entity.UserAccount.login(username, password)
        logging.debug(f"Login Attempt: {username} → {user}")
        return user

class CreateUserAccController:
    @staticmethod
    def createUserAcc(userAcc):
        if not userAcc.role:
            if session.get("role") == "Teacher":
                userAcc.role = "Student"
            else:
                userAcc.role = "User"

        result = entity.UserAccount.createUserAcc(userAcc)
        logging.debug(f"User Created: {userAcc.username} | Role: {userAcc.role}")
        return result

class DisplayUserDetailController:
    @staticmethod
    def get_user_info(username):
        user_info = entity.UserAccount.get_user_info(username)
        logging.debug(f"Retrieved user info: {user_info}")
        return user_info

class UpdateUserRoleController:
    @staticmethod
    def change_role(username, new_role):
        result = entity.UserAccount.update_role(username, new_role)
        logging.debug(f"Role Update: {username} → {new_role} | Success: {result}")
        return result

class UpdateAccountDetailController:
    @staticmethod
    def update_account_detail(username, new_details):
        try:
            update_result = mongo.db.useraccount.update_one(
                {"username": username},
                {"$set": new_details}
            )

            if update_result.modified_count > 0:
                logging.debug(f"Account details updated for: {username}")
                return {"success": True, "message": "Account details updated successfully."}
            else:
                logging.warning(f"No account details updated for {username}.")
                return {"success": False, "message": "No changes were made."}

        except Exception as e:
            logging.error(f"Failed to update account details: {e}")
            return {"success": False, "message": f"Error updating account: {str(e)}"}

# ===================== Password Management =====================
class UpdatePasswordController:
    @staticmethod
    def update_password(username, old_password, new_password):
        try:
            user = entity.UserAccount.get_user_info(username)

            if not user:
                logging.error(f"User {username} not found.")
                return False

            if not check_password_hash(user.get("password"), old_password):
                logging.error(f"Incorrect current password for {username}.")
                return False

            if len(new_password) < 7:
                logging.error("New password must be at least 7 characters long.")
                return False

            hashed_new_password = generate_password_hash(new_password)
            result = entity.UserAccount.update_password(username, hashed_new_password)

            if result:
                logging.debug(f"Password updated successfully for {username}.")
            else:
                logging.error(f"Password update failed for {username}.")

            return result

        except Exception as e:
            logging.error(f"Failed to update password: {str(e)}")
            return False

class ResetPasswordController:
    @staticmethod
    def reset_password(username, new_password):
        try:
            if len(new_password) < 7:
                logging.error("New password must be at least 7 characters long.")
                return {"success": False, "message": "Password too short."}

            user = entity.UserAccount.find_by_username(username)
            if not user:
                logging.error(f"User {username} does not exist.")
                return {"success": False, "message": "User not found."}

            hashed_new_password = generate_password_hash(new_password)
            result = entity.UserAccount.update_password(username, hashed_new_password)

            if result:
                logging.debug(f"Password reset successfully for {username}.")
                return {"success": True, "message": "Password reset successfully."}
            else:
                logging.error(f"Password reset failed for {username}.")
                return {"success": False, "message": "Password reset failed."}

        except Exception as e:
            logging.error(f"Failed to reset password: {str(e)}")
            return {"success": False, "message": f"Error resetting password: {str(e)}"}

# ===================== Video Upload =====================
class UploadTutorialController:
    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @staticmethod
    def upload_video(file, title, uploader):
        try:
            if not file or file.filename == '':
                return {"success": False, "message": "No file selected."}

            if not UploadTutorialController.allowed_file(file.filename):
                return {"success": False, "message": "Invalid file format. Allowed: mp4, mov, avi, mkv."}

            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER_VIDEO, filename)
            file.save(file_path)

            tutorial = TutorialVideo(
                title=title,
                video_name=filename,
                video_file=file_path,
                username=uploader
            )

            return tutorial.save_video()

        except Exception as e:
            logging.error(f"Error uploading video: {str(e)}")
            return {"success": False, "message": f"Upload failed: {str(e)}"}

# ===================== Avatar Management =====================
class AdminManageAvatarController:
    @staticmethod
    def get_avatars_by_username(username):
        try:
            logging.debug(f"Retrieving avatars for user: {username}")
            avatars = mongo.db.avatar.find({"username": username})
            return list(avatars)
        except Exception as e:
            logging.error(f"Failed to retrieve avatars: {str(e)}")
            return []

class AdminAddAvatarController:
    @staticmethod
    def add_avatar(username, avatar_file):
        try:
            logging.debug(f"Adding avatar for user: {username}")

            user = UserAccount.find_by_username(username)
            if not user:
                logging.error(f"User {username} not found.")
                return {"success": False, "message": "User not found."}

            avatar = Avatar(avatar_file, username)
            result = avatar.save_image()

            if not result['success']:
                logging.error(f"Avatar processing failed: {result['message']}")
                return {"success": False, "message": result['message']}

            return {"success": True, "message": "Avatar added successfully.", "file_path": result['file_path']}

        except Exception as e:
            logging.error(f"Failed to add avatar: {str(e)}")
            return {"success": False, "message": f"Failed to add avatar: {str(e)}"}
