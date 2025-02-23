from .entity import *
from .boundary import *

class LoginController:
    @staticmethod
    def userLogin(username, password):
        return UserAccount.login(username, password)  # Call entity method

class CreateUserAccController:
    @staticmethod
    def createUserAcc(user_acc):
        return UserAccount.create_user_acc(user_acc)  # Call entity method

class DisplayUserDetailController:
    @staticmethod
    def get_user_info(username):
        return UserAccount.find_by_username(username)  # Call entity method

class UpdateUserRoleController:
    @staticmethod
    def change_role(username, new_role):
        return UserAccount.update_account_detail(username, {"role": new_role})  # Call entity method

class UpdateAccountDetailController:
    @staticmethod
    def update_account_detail(username, new_details):
        return UserAccount.update_account_detail(username, new_details)  # Call entity method

class UpdatePasswordController:
    @staticmethod
    def update_password(username, old_password, new_password):
        user = UserAccount.find_by_username(username)
        if user and check_password_hash(user["password"], old_password):
            return UserAccount.update_account_detail(username, {"password": generate_password_hash(new_password)})
        return False

class ResetPasswordController:
    @staticmethod
    def reset_password(username, new_password):
        return UserAccount.update_account_detail(username, {"password": generate_password_hash(new_password)})

class UploadTutorialController:
    @staticmethod
    def upload_video(file, title, uploader, user_role):
        video = TutorialVideo(title=title, video_file=file, username=uploader, user_role=user_role)
        return video.save_video()  # Call entity method
class AdminDeleteVideoController:
    @staticmethod
    def delete_video(video_id):
        return TutorialVideo.delete_video(video_id)  # Call entity method
    
class SearchVideoController:
    @staticmethod
    def search_video(search_query):
        return TutorialVideo.search_video(search_query)  # Call entity method
    
class SearchAvatarController:
    @staticmethod
    def search_avatar(search_query):
        return Avatar.search_avatar(search_query)  # Call entity method

class AdminManageAvatarController:
    @staticmethod
    def get_avatars_by_username(username):
        return list(mongo.db.avatar.find({"username": username}))

class AdminAddAvatarController:
    @staticmethod
    def add_avatar(username, avatar_file):
        avatar = Avatar(avatar_file, username)
        return avatar.save_image()  # Call entity method

#This is for the admin to view multiple videos at once
class AdminViewUploadedVideosController:
    @staticmethod
    def view_uploaded_videos():
        return list(mongo.db.tutorialvideo.find({}))

class AdminViewSingleTutorialController:
    @staticmethod
    def view_tutorial(video_id):
        return TutorialVideo.find_by_id(video_id)
    
class ResetPasswordController:
    @staticmethod
    def reset_password(username, new_password):
        return UserAccount.update_account_detail(username, {"password": generate_password_hash(new_password)})