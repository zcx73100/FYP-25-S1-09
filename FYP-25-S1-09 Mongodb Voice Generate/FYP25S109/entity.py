from flask import session
from . import mongo
import os
import logging
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from rembg import remove
from PIL import Image
import io, requests
from pymongo.errors import DuplicateKeyError
from io import BytesIO
from bson import ObjectId
import pyttsx3

# Separate Upload Folders
UPLOAD_FOLDER_VIDEO = 'FYP25S109/static/uploads/videos/'
UPLOAD_FOLDER_AVATAR = 'FYP25S109/static/uploads/avatar/'
GENERATE_FOLDER_AUDIOS = 'FYP25S109/static/generated_audios'
GENERATE_FOLDER_VIDEOS = 'FYP25S109/static/generated_videos'

# Allowed Extensions
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

# Ensure Directories Exist
os.makedirs(UPLOAD_FOLDER_VIDEO, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_AVATAR, exist_ok=True)
os.makedirs(GENERATE_FOLDER_AUDIOS, exist_ok=True)
os.makedirs(GENERATE_FOLDER_VIDEOS, exist_ok=True)


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
    def __init__(self, title=None, video_name=None, video_file=None, username=None, description=None):
        self.title = title
        self.video_name = video_name
        self.video_file = video_file
        self.username = username
        self.description = description

    def save_video(self):
        try:
            if not self.video_file:
                raise ValueError("No file selected for upload.")

            # Generate a unique filename by adding a timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = secure_filename(f"{timestamp}_{self.video_file.filename}")
            file_path = os.path.join(UPLOAD_FOLDER_VIDEO, filename)

            # Validate file extension
            if filename.split('.')[-1].lower() not in ALLOWED_VIDEO_EXTENSIONS:
                raise ValueError("Invalid video format.")

            # Save the video file
            self.video_file.save(file_path)
            # Insert video information into MongoDB
            mongo.db.tutorialvideo.insert_one({
                'title': self.title,
                'video_name': filename,
                'file_path': file_path,
                'username': self.username,
                'upload_date': datetime.now(),
                'description': self.description
            })
            return {"success": True, "message": "Video uploaded successfully."}

        except Exception as e:
            logging.error(f"Error saving video: {str(e)}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def delete_video(video_id):
        try:
            video = mongo.db.tutorialvideo.find_one({"_id": video_id})
            if video:
                os.remove(video['file_path'])
                mongo.db.tutorialvideo.delete_one({"_id": video_id})
                return {"success": True, "message": "Video deleted successfully."}
            return {"success": False, "message": "Video not found."}

        except Exception as e:
            logging.error(f"Error deleting video: {str(e)}")
            return {"success": False, "message": str(e)}

    @staticmethod
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
    def __init__(self, image_file, avatarname=None, username=None, upload_date=None):
        self.image_file = image_file
        self.avatarname = avatarname
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
            add_result = self.add_avatar(self.avatarname, self.username, processed_file_path)
            if not add_result:
                return {"success": False, "message": "Failed to add avatar to database."}

            return {"success": True, "message": "Avatar uploaded successfully.", "file_path": processed_file_path}

        except Exception as e:
            logging.error(f"Error processing avatar: {str(e)}")
            return {"success": False, "message": f"Error processing avatar: {str(e)}"}

    def add_avatar(self, avatarname, username, file_path):
        try:
            relative_path = file_path.split('static/')[-1]  # Ensure proper relative path handling

            mongo.db.avatar.insert_one({
                'avatarname': avatarname,
                'username': username,
                'file_path': relative_path,
                'upload_date': datetime.now()
            })
            return True
        except Exception as e:
            logging.error(f"Error adding avatar to database: {str(e)}")
            return False
        
    @staticmethod
    def search_avatar(search_query):
        try:
            # Search by both username and avatarname
            avatars = mongo.db.avatar.find({
                "$or": [
                    {"avatarname": {"$regex": search_query, "$options": "i"}}
                ]
            })
            return list(avatars)  # Convert cursor to list
        except Exception as e:
            logging.error(f"Failed to search avatars: {str(e)}")
            return []

    @staticmethod
    def resize_avatar(image_path, size=(150, 150)):
        try:
            img = Image.open(image_path)
            img = img.convert("RGB")
            img.thumbnail(size)

            img_io = BytesIO()
            img.save(img_io, format="JPEG")
            img_io.seek(0)

            return img_io
        except Exception as e:
            logging.error(f"Failed to resize avatar: {str(e)}")
            return None

    @staticmethod
    def find_by_id(avatar_id):
        try:
            avatar = mongo.db.avatar.find_one({"_id": ObjectId(avatar_id)})
            return avatar
        except Exception as e:
            logging.error(f"Failed to find avatar by ID: {str(e)}")
            return None

    @staticmethod
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

class GenerateVideoEntity:
    def __init__(self, text, avatar_path):
        self.text = text
        self.avatar_path = avatar_path
        self.audio_filename = f"{hash(self.text)}.wav"
        self.audio_path = os.path.join(GENERATE_FOLDER_AUDIOS, self.audio_filename)
        self.video_filename = f"generated_{hash(self.text)}.mp4"
        self.video_path = os.path.join(GENERATE_FOLDER_VIDEOS, self.video_filename)

    def generate_voice(self):
        """Converts text to speech and saves it as an audio file."""
        try:
            os.makedirs(GENERATE_FOLDER_AUDIOS, exist_ok=True)

            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            engine.setProperty("volume", 1.0)

            engine.save_to_file(self.text, self.audio_path)
            engine.runAndWait()

            if os.path.exists(self.audio_path):
                return os.path.join("static", "generated_audios", self.audio_filename)           
            else:
                raise Exception("❌ Failed to generate audio file.")

        except Exception as e:
            print(f"❌ Error generating voice: {str(e)}")
            raise e

    def generate_video(self):
        """Generates a video using SadTalker and the selected avatar with generated voice."""
        try:
            os.makedirs(GENERATE_FOLDER_VIDEOS, exist_ok=True)

            # Ensure voice has been generated
            if not os.path.exists(self.audio_path):
                raise Exception("❌ Audio file not found. Generate voice first.")

            # SadTalker API call
            response = requests.post(
                "https://kevinwang676-sadtalker.hf.space/run/predict",
                files={
                    "image": open(self.avatar_path, "rb"),
                    "audio": open(self.audio_path, "rb"),
                }
            )

            if response.status_code == 200:
                with open(self.video_path, "wb") as f:
                    f.write(response.content)
                return os.path.join("static", "generated_videos", self.video_filename)
            else:
                raise Exception(f"❌ SadTalker failed with status {response.status_code}.")

        except Exception as e:
            print(f"❌ Error generating video: {str(e)}")
            raise e
        
class Classroom:
    def __init__(self, classroom_name=None, teacher=None, student_list=None, capacity=None, description=None):
        self.classroom_name = classroom_name
        self.teacher = teacher
        self.description = description
        self.student_list = student_list or []
        self.capacity = capacity
    
    @staticmethod
    def create_classroom(classroom_name, teacher, classroom_description, classroom_capacity,student_list=[]):
        """ Inserts classroom into the database """
        try:
            result = mongo.db.classroom.insert_one({
                'classroom_name': classroom_name,
                'teacher': teacher,
                'student_list': student_list,
                'capacity': classroom_capacity,
                'description': classroom_description,
                'upload_date': datetime.now()
            })
            if result.inserted_id:
                return {"success": True, "message": f"Classroom '{classroom_name}' added successfully."}
        except Exception as e:
            logging.error(f"Error creating classroom: {str(e)}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def search_classroom(search_query):
        """ Searches for classrooms matching the query """
        try:
            classrooms = mongo.db.classroom.find({
                "classroom_name": {"$regex": search_query, "$options": "i"}
            })
            return list(classrooms)
        except Exception as e:
            logging.error(f"Failed to search classrooms: {str(e)}")
            return []

    @staticmethod
    def delete_classroom(classroom_id):
        """ Deletes a classroom by ID """
        try:
            classroom = mongo.db.classroom.find_one({"_id": ObjectId(classroom_id)})
            if classroom:
                mongo.db.classroom.delete_one({"_id": ObjectId(classroom_id)})
                return True
        except Exception as e:
            logging.error(f"Error deleting classroom: {str(e)}")
            return False
    @staticmethod
    def update_classroom(classroom_name, updated_data):
        """ Updates a classroom by ID """
        try:
            result = mongo.db.classroom.update_one(
                {"classroom_name": classroom_name},
                {"$set": updated_data}
            )
            if result.modified_count > 0:
                return True
        except Exception as e:
            logging.error(f"Error updating classroom: {str(e)}")
            return
    
    @staticmethod
    def find_by_teacher(teacher):
        """ Finds classrooms by teacher """
        try:
            classrooms = mongo.db.classroom.find({"teacher": teacher})
            return list(classrooms)
        except Exception as e:
            logging.error(f"Failed to find classrooms by teacher: {str(e)}")
            return []
    
    @staticmethod
    def find_by_student(student):
        """ Finds classrooms by student """
        try:
            student = mongo.db.useraccount.find({"username": student, "role": "Student"})
            return student
        except Exception as e:
            logging.error(f"Failed to find classrooms by student: {str(e)}")
            return []
    
    @staticmethod
    def enroll_student(classroom_name, student_username):
        """Enrolls a student into a classroom, avoiding duplicates."""
        try:
            # Check if the student exists and has the "Student" role
            student_info = mongo.db.useraccount.find_one({"username": student_username, "role": "Student"})
            if not student_info:
                return {"success": False, "message": f"Student '{student_username}' not found or not a student."}

            # Check if the classroom exists
            classroom = mongo.db.classroom.find_one({"classroom_name": classroom_name})
            if not classroom:
                return {"success": False, "message": "Classroom not found."}

            # Check for duplicate enrollment
            if student_username in classroom.get("student_list", []):
                return {"success": False, "message": "Student is already enrolled in this classroom."}

            # Enroll the student using $addToSet to avoid duplicates
            result = mongo.db.classroom.update_one(
                {"classroom_name": classroom_name},
                {"$addToSet": {"student_list": student_username}}
            )
            if result.modified_count > 0:
                return {"success": True, "message": f"Successfully enrolled {student_username}."}
            else:
                return {"success": False, "message": "Failed to enroll the student."}
        except Exception as e:
            logging.error(f"Error enrolling student: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def remove_student(classroom_name, student_username):
        """Removes a student from a classroom."""
        try:
            result = mongo.db.classroom.update_one(
                {"classroom_name": classroom_name},
                {"$pull": {"student_list": student_username}}
            )
            if result.modified_count > 0:
                return {"success": True, "message": f"Successfully removed {student_username}."}
            else:
                return {"success": False, "message": "Failed to remove the student."}
        except Exception as e:
            logging.error(f"Error removing student: {str(e)}")
            return {"success": False, "message": str(e)}

    
    @staticmethod
    def find_by_name(classroom_name):
        """Finds a classroom by name and returns its details."""
        try:
            return mongo.db.classroom.find_one({"classroom_name": classroom_name})
        except Exception as e:
            logging.error(f"Error finding classroom by name: {str(e)}")
            return None
    @staticmethod
    def suspend_student(username):
        """Suspend a student by updating their status to 'suspended'."""
        try:
            result = mongo.db.useraccount.update_one(
                {"username": username},
                {"$set": {"status": "suspended"}}
            )
            if result.modified_count > 0:
                logging.info(f"User {username} suspended successfully.")
                return True
            logging.warning(f"User {username} not found or already suspended.")
            return False
        except Exception as e:
            logging.error(f"Error suspending user: {e}")
            return False
    def unsuspend_student(username):
        """Unsuspend a student by updating their status to 'active'."""
        try:
            result = mongo.db.useraccount.update_one(
                {"username": username},
                {"$set": {"status": "active"}}
            )
            if result.modified_count > 0:
                logging.info(f"User {username} unsuspended successfully.")
                return True
            logging.warning(f"User {username} not found or already active.")
            return False
        except Exception as e:
            logging.error(f"Error unsuspending user: {e}")
            return False
    def search_student(search_query):
        """Search for students by username or email."""
        try:
            students = mongo.db.useraccount.find({
                "$or": [
                    {"username": {"$regex": search_query, "$options": "i"}},
                    {"email": {"$regex": search_query, "$options": "i"}}
                ]
            })
            return list(students)
        except Exception as e:
            logging.error(f"Error searching students: {e}")
            return []
    
class Material:
    UPLOAD_FOLDER_MATERIAL = 'FYP25S109/static/uploads/materials/'
    ALLOWED_MATERIAL_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'zip'}

    def __init__(self, title, file, username, user_role, description):
        self.title = title
        self.file = file
        self.username = username
        self.user_role = user_role
        self.description = description

    def save_material(self): 
        try:
            if not self.file or '.' not in self.file.filename:
                raise ValueError("Invalid file or missing filename.")

            # Validate file extension
            file_extension = self.file.filename.rsplit('.', 1)[1].lower()
            if file_extension not in self.ALLOWED_MATERIAL_EXTENSIONS:
                raise ValueError("Invalid material format.")

            filename = secure_filename(self.file.filename)
            file_path = os.path.join(self.UPLOAD_FOLDER_MATERIAL, filename)

            # Save file to disk
            self.file.save(file_path)

            # Save to database
            mongo.db.material.insert_one({
                'title': self.title,
                'file_name': filename,
                'file_path': file_path,
                'username': self.username,
                'upload_date': datetime.now(),
                'description': self.description
            })
            return {"success": True, "message": "Material uploaded successfully."}

        except Exception as e:
            logging.error(f"Error saving material: {str(e)}")
            return {"success": False, "message": str(e)}

class Assignment:
    def __init__(self, title=None, file=None, username=None, user_role=None, description=None, due_date=None):
        self.title = title
        self.file = file
        self.username = username
        self.user_role = user_role
        self.description = description
        self.due_date = due_date

    def save_assignment(self):
        UPLOAD_FOLDER_ASSIGNMENT = 'FYP25S109/static/uploads/materials/'
        ALLOWED_ASSIGNMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt','zip'}
        try:
            if not self.file:
                raise ValueError("No file selected for upload.")

            filename = secure_filename(self.file.filename)
            file_path = os.path.join(UPLOAD_FOLDER_ASSIGNMENT, filename)

            # Validate file extension
            if filename.split('.')[-1].lower() not in ALLOWED_ASSIGNMENT_EXTENSIONS:
                raise ValueError("Invalid assignment format.")

            self.file.save(file_path)

            mongo.db.assignments.insert_one({
                'title': self.title,
                'file_name': filename,
                'file_path': file_path,
                'username': self.username,
                'upload_date': datetime.now(),
                'description': self.description,
                'due_date': self.due_date
            })
            return {"success": True, "message": "Assignment uploaded successfully."}

        except Exception as e:
            logging.error(f"Error saving assignment: {str(e)}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def search_assignment(search_query):
        try:
            # Use case-insensitive and partial matching
            assignments = mongo.db.assignments.find({
                "title": {"$regex": search_query, "$options": "i"}
            })
            return list(assignments)
        except Exception as e:
            logging.error(f"Failed to search assignments: {str(e)}")
            return []

    @staticmethod
    def delete_assignment(assignment_id):
        try:
            assignment = mongo.db.assignments.find_one({"_id": assignment_id})
            if assignment:
                os.remove(assignment['file_path'])
        except Exception as e:
            logging.error(f"Error deleting assignment: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def get_assignment(assignment_id):
        try:
            print(assignment_id)
            assignment = mongo.db.assignments.find_one({"_id": ObjectId(assignment_id)})
            return assignment
        except Exception as e:
            logging.error(f"Failed to find assignment by ID: {str(e)}")
            return None

        
class Quiz:
    def __init__(self, title=None, questions=None, username=None, user_role=None, description=None):
        self.title = title
        self.questions = questions
        self.username = username
        self.user_role = user_role
        self.description = description

    def save_quiz(self):
        try:

            mongo.db.quiz.insert_one({
                'title': self.title,
                'questions': self.questions,
                'username': self.username,
                'upload_date': datetime.now(),
                'description': self.description
            })
            return {"success": True, "message": "Quiz uploaded successfully."}

        except Exception as e:
            logging.error(f"Error saving quiz: {str(e)}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def search_quiz(search_query):
        try:
            # Use case-insensitive and partial matching
            quizzes = mongo.db.quiz.find({
                "title": {"$regex": search_query, "$options": "i"}
            })
            return list(quizzes)
        except Exception as e:
            logging.error(f"Failed to search quizzes: {str(e)}")
            return []

    @staticmethod
    def delete_quiz(quiz_id):
        try:
            quiz = mongo.db.quiz.find_one({"_id": quiz_id})
            if quiz:
                os.remove(quiz['file_path'])
        except Exception as e:
            logging.error(f"Error deleting quiz: {str(e)}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def find_by_id(quiz_id):
        try:
            quiz = mongo.db.quiz.find_one({"_id": quiz_id})
            return quiz
        except Exception as e:
            logging.error(f"Failed to find quiz by ID: {str(e)}")
            return None

    @staticmethod
    def delete_quiz(quiz_id):
        try:
            quiz = mongo.db.quiz.find_one({"_id": quiz_id})
            if quiz:
                os.remove(quiz['file_path'])
        except Exception as e:
            logging.error(f"Error deleting quiz: {str(e)}")
            return {"success": False, "message": str(e)}
        
        
        