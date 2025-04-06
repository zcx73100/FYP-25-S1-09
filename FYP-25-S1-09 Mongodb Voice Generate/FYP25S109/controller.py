from .entity import *
from .boundary import *
import requests
import json
from bson import ObjectId
from datetime import datetime, timezone
class GenerateVideoController:
    @staticmethod
    def generate_voice(text):
        entity = GenerateVideoEntity(text=text, avatar_path=None)
        return entity.generate_voice(text)
    def generate_video(text, avatar_path):
        entity = GenerateVideoEntity(text, avatar_path)
        entity.generate_voice()  # Make sure audio is generated first

class LoginController:
    @staticmethod
    def userLogin(username, password):
        return UserAccount.login(username, password)  # Call entity method

class CreateUserAccController:
    @staticmethod
    def register_user(data):
        """Receives user registration data and passes it to the Entity for insertion."""
        try:
            # Create UserAccount entity
            user_acc = UserAccount(
                username=data["username"],
                password=data["password"],  # Password hashing handled in the Entity
                name=data["name"],
                surname=data["surname"],
                email=data["email"],
                date_of_birth=data["date_of_birth"],
                role=data["role"],
                profile_pic=data.get("profile_pic")  # Optional file upload
            )

            # Call the Entity to insert into DB
            return user_acc.create_user_acc()

        except Exception as e:
            logging.error(f"Registration failed: {e}")
            return False

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
    
    @staticmethod
    def get_user_by_username(username):
        return UserAccount.find_by_username(username)  # Fetch user from entity

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
    def upload_video(file, title, uploader, description):
        video = TutorialVideo(video_file=file, title=title, username=uploader, description=description)
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
class ViewUploadedVideosController:
    @staticmethod
    def view_uploaded_videos():
        return list(mongo.db.tutorialvideo.find({}))

class ViewSingleTutorialController:
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
    def upload_material(title, file, uploader, classroom_id, description):
        # Create the Material entity and delegate the actual work to the entity's method
        material = Material(title, file, uploader, description,classroom_id=classroom_id)
        return material.save_material()
    
class ViewMaterialController:
    @staticmethod
    def get_material(material_id):
        material_data = Material.get_material_by_id(material_id)

        if not material_data:
            return None, None

        material, file_data = material_data
        return material, file_data


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
    def upload_assignment(title, classroom_id, description, deadline, file, filename):
        assignment = Assignment(
            title=title, classroom_id=classroom_id, description=description, 
            due_date=deadline, file=file, filename=filename  # Pass file directly
        )
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

class AddFeedbackController:
    @staticmethod
    def add_feedback(submission_id, student_username, feedback):
        # Optional: verify if student matches (for security)
        submission = Submission.get_submission_by_student_and_id(student_username, submission_id)
        if not submission:
            return {"success": False, "message": "Submission not found or unauthorized."}
        
        # Call the update_feedback method
        return Submission.update_feedback(submission_id,student_username, feedback)

         

class StudentSendSubmissionController:
    @staticmethod
    def submit_assignment_logic(assignment_id, student_username, file):
        """Handles assignment submission and saves it in MongoDB."""
        try:
            submission = Submission(assignment_id, student_username, file)
            result = submission.save_submission()
            return result
        except Exception as e:
            logging.error(f"Error in submit_assignment_logic: {str(e)}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def get_submission(assignment_id, student_username):
        """Retrieves the student's submission from MongoDB."""
        try:
            submission = mongo.db.submissions.find_one(
                {"assignment_id": ObjectId(assignment_id), "student": student_username}
            )
            return submission
        except Exception as e:
            logging.error(f"Error in get_submission: {str(e)}")
            return None

    @staticmethod
    def get_submission_file(file_id):
        """Retrieves the actual file from GridFS."""
        try:
            fs = gridfs.GridFS(mongo.db)
            file = fs.get(ObjectId(file_id))
            return file
        except Exception as e:
            logging.error(f"Error retrieving file: {str(e)}")
            return None
    @staticmethod
    def check_submission_exists(assignment_id, student_username):
        """
        Check if a submission exists for the given student and assignment.
        Returns the submission if found, otherwise None.
        """
        try:
            # Ensure the assignment_id is in ObjectId format if necessary
            assignment_id_obj = ObjectId(assignment_id)

            # Query for the submission using both assignment_id and student_username
            submission = mongo.db.submissions.find_one({
                "assignment_id": assignment_id_obj,
                "student": student_username
            })

            return submission  # Returns None if not found
        except Exception as e:
            logging.error(f"Error in check_submission_exists: {str(e)}")
            return None
        
class StudentViewSubmissionController:
    @staticmethod
    def get_submission_by_student_and_id(student_username, submission_id):
        return Submission.get_submission_by_student_and_id(student_username, submission_id)

class TeacherViewSubmissionController:
    @staticmethod
    def get_submission_by_student_and_id(student_username, submission_id):
        return Submission.get_submission_by_student_and_id(student_username, submission_id)
    
class StudentDeleteSubmissionController:
    @staticmethod
    def delete_submission(submission_id):
        return Submission.delete_submission(submission_id)

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