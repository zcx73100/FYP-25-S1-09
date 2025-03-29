from .entity import *
from .boundary import *
import requests
import json
from bson import ObjectId
from datetime import datetime, timezone


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
    
class DeleteVideoController:
    @staticmethod
    def delete_video(video_id):
        return TutorialVideo.delete_video(video_id)  # Call entity method
    
class SearchTutorialController:
    @staticmethod
    def search_video(search_query):
        return TutorialVideo.search_video(search_query)  # Call entity method
    
class SearchAvatarController:
    @staticmethod
    def search_avatar(search_query):
        return Avatar.search_avatar(search_query)  # Call entity method

class ManageAvatarController:
    @staticmethod
    def get_avatars_by_username(username):
        return list(mongo.db.avatar.find({"username": username}))

class AddAvatarController:
    @staticmethod
    def add_avatar(username, avatarname, avatar_file):
        avatar = Avatar(avatar_file, avatarname, username)
        return avatar.save_image()  

class DeleteAvatarController:
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
    def enroll_student(classroom_id, student_username):
        return Classroom.enroll_student(classroom_id, student_username)

class RemoveStudentController:
    @staticmethod
    def remove_student(classroom_id, student_username):
        return Classroom.remove_student(classroom_id, student_username)
    
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
    def upload_quiz(quiz_title, quiz_description, questions, classroom_id):
        quiz = Quiz(
            title=quiz_title,
            description=quiz_description,
            questions=questions,
            classroom_id=classroom_id
        )
        return quiz.save_quiz()

class AttemptQuizController:
    from datetime import datetime, timezone

class AttemptQuizController:
    @staticmethod
    def attempt_quiz(quiz_id, student_username, answers):
        # Retrieve the quiz and its questions from MongoDB
        quiz = mongo.db.quizzes.find_one({"_id": ObjectId(quiz_id)})

        if not quiz:
            return {"error": "Quiz not found."}

        correct_count = 0
        total = len(quiz.get("questions", []))
        results = []
        answer_log = {}

        # Iterate through the quiz questions and compare answers
        for i, question in enumerate(quiz["questions"]):
            qid = str(question.get("_id", i))  # Fallback to index if _id missing
            correct = question.get("correct_answer")
            selected = answers.get(qid)

            # Ensure selected value is handled correctly
            if selected is None:
                selected = "None"  # No selection, mark as None

            # Compare selected answer with the correct one
            if selected == correct:
                correct_count += 1

            results.append({
                "text": question.get("text", ""),
                "image": question.get("image"),
                "correct": correct,
                "selected": selected
            })

            answer_log[qid] = selected

        # Store the attempt in the database with UTC timestamp
        mongo.db.quiz_attempts.insert_one({
            "student_username": student_username,
            "quiz_id": ObjectId(quiz_id),
            "answers": answer_log,
            "score": correct_count,
            "total": total,
            "timestamp": datetime.now(timezone.utc)  # Using the updated method to get the UTC time
        })

        return {
            "score": correct_count,
            "total": total,
            "results": results,
            "classroom_id": str(quiz.get("classroom_id"))
        }





class UploadAssignmentController:
    @staticmethod
    def upload_assignment(file, title, classroom_id, description, deadline, filename, file_path):
        # Create Assignment object and save it
        assignment = Assignment(title=title, file=file, classroom_id=classroom_id, description=description, 
                                due_date=deadline, filename=filename, file_path=file_path)
        return assignment.save_assignment()
    
class ViewUserDetailsController:
    @staticmethod
    def view_user_details(username):
        return UserAccount.find_by_username(username)   

class SuspendStudentController:
    @staticmethod
    def suspend_student(classroom_id, student_username):
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

class SearchAccountController:
    @staticmethod
    def search_account(search_query):
        return UserAccount.search_account(search_query)
class SearchStudentController:
    @staticmethod
    def search_student(search_query):
        return Classroom.search_student(search_query)

class UpdateClassroomController:
    @staticmethod
    def update_classroom(classroom_id, new_details):
        return Classroom.update_classroom(classroom_id, new_details)
    
class SearchClassroomController:
    @staticmethod
    def search_classroom(search_query):
        return Classroom.search_classroom(search_query)

class ViewAssignmentDetailsController:
    @staticmethod
    def view_assignment_details(assignment_id):
        print("assignment id from controller", assignment_id)
        assignment = Assignment.get_assignment(assignment_id)
        return assignment

from datetime import datetime, timezone

class StudentSendSubmissionController:
    @staticmethod
    def submit_assignment_logic(assignment_id, student_username, file):
        """
        Processes the assignment submission.
        """
        try:
            # Validate the file
            if not file or file.filename == '':
                return {"success": False, "message": "No file selected for upload."}

            # Secure filename
            filename_secure = secure_filename(file.filename)

            # Define upload path (Ensure UPLOAD_FOLDER_SUBMISSIONS is correctly set)
            upload_folder = "FYP25S109/static/uploads/submissions"
            os.makedirs(upload_folder, exist_ok=True)  # Ensure directory exists

            file_path = os.path.join(upload_folder, filename_secure)
            file.save(file_path)  # Save the file

            # Debugging log
            print(f"File saved at: {file_path}")

            # Store submission in database (Ensure submitted_at is always a datetime object)
            submission_data = {
                "assignment_id": ObjectId(assignment_id),
                "student_username": student_username,
                "filename": filename_secure,
                "file_path": file_path,
                "submitted_at": datetime.now(timezone.utc),  # ✅ Use timezone-aware UTC
                "grade": None,
                "feedback": ""
            }
            mongo.db.submissions.insert_one(submission_data)

            return {"success": True, "message": "Submission successful!"}

        except Exception as e:
            logging.error(f"Error in submit_assignment_logic: {str(e)}")
            return {"success": False, "message": str(e)}


class GenerateVideoController:
    @staticmethod
    def generate_voice(text):
        entity = GenerateVideoEntity(text=text, avatar_path=None)
        audio_path = entity.generate_voice()
        return audio_path

    @staticmethod
    def generate_video(text, avatar_path):
        entity = GenerateVideoEntity(text, avatar_path)
        entity.generate_voice()  # Make sure audio is generated first
        video_path = entity.generate_video()
        return video_path


class AddDiscussionRoomController:
    @staticmethod
    def add_discussion_room(classroom_name, discussion_room_name, discussion_room_description,created_by):
        return DiscussionRoom.create_discussion_room(classroom_name, discussion_room_name, discussion_room_description,created_by)
    
class SearchDiscussionRoomController:
    @staticmethod
    def search_discussion_room(search_query):
        return DiscussionRoom.search_discussion_room(search_query)
    
class UpdateDiscussionRoomController:
    @staticmethod
    def get_discussion_room_by_id(discussion_room_id):
        return DiscussionRoom.find_by_id(discussion_room_id)
    @staticmethod
    def update_discussion_room(discussion_room_id, new_details):
        return DiscussionRoom.update_discussion_room(discussion_room_id, new_details)
    
class DeleteDiscussionRoomController:
    @staticmethod
    def delete_discussion_room(discussion_room_id):
        return DiscussionRoom.delete_discussion_room(discussion_room_id)
    
class RetrieveDiscussionRoomController:
    @staticmethod
    def get_all_discussion_rooms_by_classroom_id(classroom_id):
        return DiscussionRoom.get_all_discussion_rooms_by_classroom_id(classroom_id)
    @staticmethod
    def get_discussion_room_id(discussion_room_id):
        return DiscussionRoom.get_id(discussion_room_id)

class AddMessageController:
    @staticmethod
    def send_message(discussion_room_id, sender, message):
        return Message.send_message(discussion_room_id, sender, message)

class UpdateMessageController:
    @staticmethod
    def update_message(message_id, new_details):
        return Message.update_message(message_id, new_details) 
    
class DeleteMessageController:
    @staticmethod
    def delete_message(message_id):
        return Message.delete_message(message_id)
    
class RetrieveMessageController:
    @staticmethod
    def get_all_messages(discussion_room_id):
        return Message.get_all_messages(discussion_room_id)