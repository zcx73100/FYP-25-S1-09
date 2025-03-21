from .entity import *
from .boundary import *
import requests


OPENSHOT_API_URL = "https://cloud.openshot.org/api"
API_KEY = "123"

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
    def add_avatar(username, avatarname, avatar_file):
        avatar = Avatar(avatar_file, avatarname, username)
        return avatar.save_image()  

class AdminDeleteAvatarController:
    @staticmethod
    def delete_avatar(avatar_id):
        return Avatar.delete_avatar(avatar_id)  # Call entity method

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
    
class AddClassroomController:
    @staticmethod
    def create_classroom(classroom_name, teacher, classroom_description, classroom_capacity, student_list=[]):
        return Classroom.create_classroom(classroom_name, teacher, classroom_description, classroom_capacity,student_list=[])
    
class TeacherViewClassroomController:
    @staticmethod
    def view_classroom(username):
        return Classroom.find_by_teacher(username)
    
class StudentViewClassroomController:
    @staticmethod
    def view_classroom(username):
        return Classroom.find_by_student(username)

class EnrollStudentController:
    @staticmethod
    def enroll_student(classroom_name, student_username):
        return Classroom.enroll_student(classroom_name, student_username)

class RemoveStudentController:
    @staticmethod
    def remove_student(classroom_name, student_username):
        return Classroom.remove_student(classroom_name, student_username)
    
class TeacherUploadAssignmentController:
    @staticmethod
    def upload_assignment(file, title, uploader, classroom_name):
        pass
        #assignment = Assignment(title=title, assignment_file=file, username=uploader, classroom_name=classroom_name)
        #return assignment.save_assignment()
class ViewAssignmentController:
    @staticmethod
    def view_assignment(username):
        pass
        #return Assignment.find_by_student(username)

class UploadMaterialController:
    @staticmethod
    def upload_material(title, file, uploader, classroom_name, description):
        material = Material(title, file, uploader, session.get('role'), description)
        return material.save_material()

class UploadQuizController:
    @staticmethod
    def upload_quiz(file, title, uploader, classroom_name):
        quiz = Quiz(title=title, quiz_file=file, username=uploader, classroom_name=classroom_name)
        return quiz.save_quiz()

class UploadAssignmentController:
    @staticmethod
    def upload_assignment(file, title, uploader, classroom_name):
        assignment = Assignment(title=title, assignment_file=file, username=uploader, classroom_name=classroom_name)
        return assignment.save_assignment()

class SearchAssignmentController:
    @staticmethod
    def search_assignments(query, classroom_name=None, student_username=None):
        """Search for assignments by title, course, or student."""
        search_filter = {}

        if query:
            search_filter["title"] = {"$regex": query, "$options": "i"}

        if classroom_name:
            search_filter["classroom_name"] = classroom_name

        if student_username:
            search_filter["submissions.student_username"] = student_username

        try:
            assignments = list(mongo.db.assignments.find(search_filter))
            return assignments
        except Exception as e:
            logging.error(f"Error searching assignments: {str(e)}")
            return []


class ViewUserDetailsController:
    @staticmethod
    def view_user_details(username):
        return UserAccount.find_by_username(username)   

class SuspendStudentController:
    @staticmethod
    def suspend_student(classroom_name, student_username):
        # Call the Entity to perform the suspension
        success = Classroom.suspend_student(student_username)
        if success:
            return {"success": True, "message": f"Student '{student_username}' has been suspended."}
        else:
            return {"success": False, "message": "Failed to suspend the student."}
        
class UnsuspendStudentController:
    @staticmethod
    def unsuspend_student(classroom_name, student_username):
        # Call the Entity to perform the suspension
        success = Classroom.unsuspend_student(student_username)
        if success:
            return {"success": True, "message": f"Student '{student_username}' has been unsuspended."}
        else:
            return {"success": False, "message": "Failed to unsuspend the student."}

class SearchStudentController:
    @staticmethod
    def search_student(search_query):
        return Classroom.search_student(search_query)

class UpdateClassroomController:
    @staticmethod
    def update_classroom(classroom_name, new_details):
        return Classroom.update_classroom(classroom_name, new_details)
    
class SearchClassroomController:
    @staticmethod
    def search_classroom(search_query):
        return Classroom.search_classroom(search_query)