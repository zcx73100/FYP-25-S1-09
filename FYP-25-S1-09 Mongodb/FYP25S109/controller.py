from flask import session  # Import session to check the logged-in user's role
from FYP25S109 import entity
import os
import logging
from . import mongo  
from .entity import UserAccount, TutorialVideo
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename 


UPLOAD_FOLDER = 'static/uploads/videos'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# User Account
class LoginController:
    @staticmethod
    def userLogin(username, password):
        user = entity.UserAccount.login(username, password)
        print(f"[DEBUG] Login Attempt: {username} → {user}")  # ✅ Debugging log
        return user

class CreateUserAccController:
    @staticmethod
    def createUserAcc(userAcc):        
        if not userAcc.role:  # If role is missing
            if session.get("role") == "Teacher":  
                userAcc.role = "Student"  # Teacher-created accounts default to Student
            else:
                userAcc.role = "User"  # Everyone else defaults to User

        # Create user account in the database
        result = entity.UserAccount.createUserAcc(userAcc)
        print(f"[DEBUG] User Created: {userAcc.username} | Role: {userAcc.role}")  # ✅ Debugging log
        return result
    
class DisplayUserDetailController:
    @staticmethod
    def get_user_info(username):
        user_info = entity.UserAccount.get_user_info(username)
        print(f"[DEBUG] Retrieved user info: {user_info}")  # ✅ Debugging
        return user_info

class UpdateUserRoleController:
    @staticmethod
    def change_role(username, new_role):
        """Changes a user's role using the entity class"""
        result = entity.UserAccount.update_role(username, new_role)
        print(f"[DEBUG] Role Update: {username} → {new_role} | Success: {result}")  # ✅ Debugging log
        return result


class UpdateAccountDetailController:
    @staticmethod
    def update_role(username, new_role):
        """✅ Updates the role of a user in MongoDB."""
        try:
            update_result = mongo.db.useraccount.update_one(
                {"username": username},
                {"$set": {"role": new_role}}
            )

            if update_result.modified_count > 0:
                print(f"[DEBUG] Role updated successfully: {username} → {new_role}")
                return True
            else:
                print(f"[ERROR] Role update failed for {username}.")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to update role: {e}")
            return False

    @staticmethod
    def update_account_detail(username, new_details):
        try:
            update_result = mongo.db.useraccount.update_one(
                {"username": username},
                {"$set": new_details}
            )

            if update_result.modified_count > 0:
                print(f"[DEBUG] Account details updated for: {username}")
                return {"success": True, "message": "Account details updated successfully."}
            else:
                print(f"[ERROR] No account details updated for {username}.")
                return {"success": False, "message": "No changes were made."}

        except Exception as e:
            print(f"[ERROR] Failed to update account details: {e}")
            return {"success": False, "message": f"Error updating account: {str(e)}"}

class UpdatePasswordController:
    @staticmethod
    def update_password(username, old_password, new_password):
        try:
            # Fetch user data from database
            user = entity.UserAccount.get_user_info(username)

            if not user:
                print(f"[ERROR] User {username} not found.")
                return False

            stored_hashed_password = user.get("password")

            # Check if the old password matches the stored password
            if not check_password_hash(stored_hashed_password, old_password):
                print(f"[ERROR] Incorrect current password for {username}.")
                return False

            # Ensure new password is strong
            if len(new_password) < 7:
                print("[ERROR] New password must be at least 7 characters long.")
                return False

            # Hash the new password
            hashed_new_password = generate_password_hash(new_password)

            # Update the password in database
            result = entity.UserAccount.update_password(username, hashed_new_password)

            if result:
                print(f"[DEBUG] Password updated successfully for {username}.")
            else:
                print(f"[ERROR] Password update failed for {username}.")

            return result

        except Exception as e:
            print(f"[ERROR] Failed to update password: {str(e)}")  
            return False



class UploadTutorialController:
    @staticmethod
    def allowed_file(filename):
        """Check if the uploaded file has a valid video extension."""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @staticmethod
    def upload_video(file, title, uploader):
        """Processes video uploads, validates them, and stores metadata in the database."""
        try:
            if not file or file.filename == '':
                return {"success": False, "message": "No file selected."}

            if not UploadTutorialController.allowed_file(file.filename):
                return {"success": False, "message": "Invalid file format. Allowed: mp4, mov, avi, mkv."}

            # Secure filename to prevent security issues
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            #  Save file to the server
            file.save(file_path)

            # Create a `TutorialVideo` entity
            tutorial = TutorialVideo(
                title=title,
                video_name=filename,
                video_file=file_path,  # Save path, not file content
                username=uploader
            )

            mongo.db.videos.insert_one(tutorial.to_dict())

            return {"success": True, "message": "Video uploaded successfully. Awaiting approval."}

        except Exception as e:
            logging.error(f"Error uploading video: {str(e)}")
            return {"success": False, "message": f"Upload failed: {str(e)}"}
