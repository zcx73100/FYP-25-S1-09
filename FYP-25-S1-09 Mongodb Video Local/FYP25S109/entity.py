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
from gradio_client import Client
from flask import flash, session, redirect, url_for
import wave
import subprocess

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
    def search_account(query):
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

"""
class GenerateVideoEntity:
    def __init__(self, text, avatar_path=None):
        self.text = text
        self.avatar_path = avatar_path
        self.audio_filename = f"{hash(self.text)}.wav"
        self.audio_path = os.path.join("FYP25S109/static/generated_audios", self.audio_filename).replace("\\", "/")
        self.video_filename = f"{hash(self.text)}.mp4"
        self.video_path = os.path.join("FYP25S109/static/generated_videos", self.video_filename).replace("\\", "/")

    def generate_voice(self):
      
        try:
            os.makedirs(os.path.dirname(self.audio_path), exist_ok=True)
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            engine.setProperty("volume", 1.0)
            engine.save_to_file(self.text, self.audio_path)
            engine.runAndWait()

            if os.path.exists(self.audio_path):
                return f"/static/generated_audios/{self.audio_filename}"
            else:
                raise Exception("❌ Failed to generate audio file.")
        except Exception as e:
            print(f"❌ Error generating voice: {str(e)}")
            return None

    def generate_video(self):
            try:
                # Ensure required files exist
                if not os.path.exists(self.audio_path):
                    raise Exception(f"❌ Audio file not found: {self.audio_path}")
                if not os.path.exists(self.avatar_path):
                    raise Exception(f"❌ Avatar file not found: {self.avatar_path}")

                print(f"🎬 Sending files to SadTalker API:")
                print(f"🖼️ Avatar: {self.avatar_path}")
                print(f"🔊 Audio: {self.audio_path}")

                # Initialize client with the SadTalker API URL
                client = Client("https://vinthony-sadtalker.hf.space/--replicas/li6va/")

                # Prepare parameters for the prediction (SadTalker API call)
                result = client.predict(
                    self.avatar_path,         # Avatar file path
                    self.audio_path,          # Audio file path
                    "crop",                   # Preprocess option
                    True,                     # Still mode option
                    True,                     # Face enhancement option
                    0,                        # Batch size
                    "256",                    # Resolution
                    0,                        # Pose style
                    "facevid2vid",            # Face render option
                    0,                        # Expression scale
                    True,                     # Use reference video
                    None,                     # Reference video (optional)
                    "pose",                   # Pose reference option
                    True,                     # Use idle animation
                    5,                        # Length of generated video (seconds)
                    True,                     # Use eye blink
                    fn_index=2               # Specify function index (this may vary based on your API setup)
                )

                # Check the result and save the generated video
                if result:
                    with open(self.video_path, "wb") as f:
                        f.write(result)  # Write the video to a file
                    print(f"✅ Video generated successfully: {self.video_path}")
                    return f"/static/generated_videos/{self.video_filename}"
                else:
                    raise Exception("❌ No result returned from SadTalker API.")

            except Exception as e:
                print(f"❌ Error generating video: {str(e)}")
                return None
"""

class GenerateVideoEntity:
    def __init__(self, text, avatar_path=None, audio_path=None):
        self.text = text
        self.avatar_path = avatar_path
        self.audio_path = audio_path

        if not self.audio_path:
            self.audio_filename = f"{hash(self.text)}.wav"
            self.audio_path = os.path.join(
                "FYP25S109/static/generated_audios",
                self.audio_filename
            ).replace("\\", "/")

        self.video_filename = f"{hash(self.text)}.mp4"
        self.video_path = os.path.join(
            "FYP25S109/static/generated_videos",
            self.video_filename
        ).replace("\\", "/")


    def generate_voice(self):
        """Convert text to speech and save as audio file."""
        try:
            os.makedirs(os.path.dirname(self.audio_path), exist_ok=True)
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            engine.setProperty("volume", 1.0)
            engine.save_to_file(self.text, self.audio_path)
            engine.runAndWait()

            # ✅ Verify that the generated audio file exists
            if os.path.exists(self.audio_path):
                print(f"✅ Audio file saved successfully: {self.audio_path}")

                # ✅ Validate WAV file
                try:
                    with wave.open(self.audio_path, 'rb') as audio_file:
                        duration = audio_file.getnframes() / audio_file.getframerate()
                        print(f"🎵 Valid WAV file: {self.audio_path}, Duration: {duration:.2f}s")
                except wave.Error:
                    raise Exception(f"❌ Invalid WAV file: {self.audio_path}")

                return f"/static/generated_audios/{self.audio_filename}"
            else:
                raise Exception("❌ Failed to generate audio file.")

        except Exception as e:
            print(f"❌ Error generating voice: {str(e)}")
            return None

    def generate_video(self):
        try:
            if not os.path.exists(self.audio_path):
                raise FileNotFoundError(f"❌ Audio file not found: {self.audio_path}")
            if not os.path.exists(self.avatar_path):
                raise FileNotFoundError(f"❌ Avatar file not found: {self.avatar_path}")

            print("🎬 Generating video using SadTalker API...")
            SADTALKER_API_URL = "http://127.0.0.1:7860/gradio_api/run/generate_talking_video"

            abs_avatar_path = os.path.abspath(self.avatar_path)
            abs_audio_path = os.path.abspath(self.audio_path)

            with open(abs_avatar_path, 'rb') as image_file, \
                 open(abs_audio_path, 'rb') as audio_file:

                files = {
                    "image_file": (os.path.basename(abs_avatar_path), image_file, "image/jpeg"),
                    "audio_file": (os.path.basename(abs_audio_path), audio_file, "audio/wav"),
                }

                response = requests.post(SADTALKER_API_URL, files=files)

                if response.status_code != 200:
                    print(f"❌ SadTalker API Error {response.status_code}")
                    return None

                content_type = response.headers.get('Content-Type', '')

                # Handle multipart response from Gradio
                if 'multipart' in content_type:
                    boundary = re.findall('boundary=(.*)', content_type)
                    if boundary:
                        boundary = boundary[0].encode()
                        parts = response.content.split(b'--' + boundary)

                        for part in parts:
                            if b'Content-Type: video/mp4' in part:
                                video_data = part.split(b'\r\n\r\n', 1)[1].rsplit(b'\r\n', 1)[0]

                                os.makedirs(os.path.dirname(self.video_path), exist_ok=True)
                                with open(self.video_path, 'wb') as vf:
                                    vf.write(video_data)
                                print(f"✅ Video saved successfully: {self.video_path}")
                                return f"/static/generated_videos/{self.video_filename}"

                    print("❌ No video/mp4 part found in multipart response.")
                    return None

                # Direct binary video (ideal scenario)
                elif 'video/mp4' in content_type or response.content.startswith(b'\x00\x00\x00'):
                    os.makedirs(os.path.dirname(self.video_path), exist_ok=True)
                    with open(self.video_path, "wb") as video_file:
                        video_file.write(response.content)
                    print(f"✅ Video saved successfully: {self.video_path}")
                    return f"/static/generated_videos/{self.video_filename}"

                # If JSON is somehow returned
                elif 'application/json' in content_type:
                    result = response.json()
                    video_path = result.get("video_path")
                    if video_path:
                        print(f"✅ Video successfully generated: {video_path}")
                        return video_path
                    else:
                        print("❌ No video_path found in JSON.")
                        return None

                else:
                    print(f"❌ Unsupported response format: {content_type}")
                    return None

        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {str(e)}")
        except Exception as e:
            print(f"❌ Error generating video: {str(e)}")
        return None
            
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
        
class Submission:
    def __init__(self, assignment_id, student, file, submission_date=None):
        self.assignment_id = assignment_id
        self.student = student
        self.file = file
        self.submission_date = submission_date or datetime.now()

    def save_submission(self):
        """
        Saves the submission to the database.
        """
        try:
            if not self.file:
                raise ValueError("No file selected for upload.")

            # Secure the filename and define the file path
            filename = secure_filename(self.file.filename)
            file_path = os.path.join("FYP25S109/static/uploads/submissions/", filename)
            student = self.student
            print(student)

            # Ensure the upload directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Save the file to the server
            self.file.save(file_path)
            submission= {
                'assignment_id': ObjectId(self.assignment_id),
                'student': student,
                'file_name': filename,
                'file_path': file_path,
                'submission_date': self.submission_date
            }
            # Insert submission into MongoDB
            mongo.db.submissions.insert_one(submission)

            mongo.db.assignments.update_one(
                {"_id": ObjectId(self.assignment_id)},
                {"$push": {"submissions": submission}}
            )

            return {"success": True, "message": "Submission uploaded successfully."}

        except Exception as e:
            logging.error(f"Error saving submission: {str(e)}")
            return {"success": False, "message": str(e)}
        


class DiscussionRoom:
    def __init__(self, classroom_name=None, discussion_room_name=None,discussion_room_description=None, created_by =None):
        self.classroom_name = classroom_name
        self.discussion_room_name = discussion_room_name
        self.discussion_room_description = discussion_room_description
        self.created_by = created_by

    @staticmethod
    def create_discussion_room(classroom_name, discussion_room_name, discussion_room_description,created_by):
        try:
            room_data = {
                "classroom_name": classroom_name,
                "discussion_room_name": discussion_room_name,
                "discussion_room_description": discussion_room_description,
                "created_at": datetime.now(),
                "created_by": created_by

            }
            mongo.db.discussion_rooms.insert_one(room_data)
            return True
        except Exception as e:
            print(f"Error creating discussion room: {e}")
            return False

    @staticmethod
    def delete_discussion_room(discussion_room_id):
        try:
            mongo.db.discussion_rooms.delete_one({"_id": ObjectId(discussion_room_id)})
            return True
        except Exception as e:
            print(f"Error deleting discussion room: {e}")
            return False

    @staticmethod
    def update_discussion_room(discussion_room_id, new_details):
        try:
            mongo.db.discussion_rooms.update_one(
                {"_id": ObjectId(discussion_room_id)},
                {"$set": new_details}
            )
            return True
        except Exception as e:
            print(f"Error updating discussion room: {e}")
            return False

    @staticmethod
    def search_discussion_room(search_query):
        try:
            query = {"discussion_room_name": {"$regex": search_query, "$options": "i"}}
            rooms = list(mongo.db.discussion_rooms.find(query))
            return rooms
        except Exception as e:
            print(f"Error searching discussion rooms: {e}")
            return []

    @staticmethod
    def get_all_discussion_rooms():
        try:
            rooms = list(mongo.db.discussion_rooms.find())
            print(rooms)
            return rooms
        except Exception as e:
            print(f"Error retrieving discussion rooms: {e}")
            return []
    @staticmethod
    def find_by_id(discussion_room_id):
        try:
            room = mongo.db.discussion_rooms.find_one({"_id": ObjectId(discussion_room_id)})
            return room
        except Exception as e:
            print(f"Error finding discussion room by ID: {e}")
            return None
    def get_id(discussion_room_id):
        try:
            result = mongo.db.discussion_rooms.find_one({"_id": ObjectId(discussion_room_id)})
            if result:
                print(result['_id'])
                return str(result["_id"])  # Convert to string to avoid ObjectId type issues
            return None
        except Exception as e:
            print(f"Error finding discussion room by ID: {e}")
            return None
     

class Message:
    def __init__(self, discussion_room_id=None, sender=None, message=None):
        self.discussion_room_id = discussion_room_id
        self.sender = sender
        self.message = message

    def send_message(discussion_room_id, sender, message):
        try:
            message_data = {
                "discussion_room_id": discussion_room_id,
                "sender": sender,
                "message": message,
                "sent_at": datetime.now()
            }
            mongo.db.messages.insert_one(message_data)
            return True
        except Exception as e:
            print(f"Error saving message: {e}")
            return False

    @staticmethod
    def get_all_messages(discussion_room_id):
        try:
            messages = list(mongo.db.messages.find({"discussion_room_id": discussion_room_id}))
            print(messages)
            return messages
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []

    @staticmethod
    def delete_message(message_id):
        try:
            mongo.db.messages.delete_one({"_id": ObjectId(message_id)})
            return True
        except Exception as e:
            print(f"Error deleting message: {e}")
            return False

    @staticmethod
    def delete_messages(discussion_room_id):
        try:
            mongo.db.messages.delete_many({"discussion_room_id": discussion_room_id})
            return True
        except Exception as e:
            print(f"Error deleting messages: {e}")
            return False

    @staticmethod
    def search_messages(search_query):
        try:
            query = {"message": {"$regex": search_query, "$options": "i"}}
            messages = list(mongo.db.messages.find(query))
            return messages
        except Exception as e:
            print(f"Error searching messages: {e}")
            return []
        
    @staticmethod
    def update_message(message_id, new_details):
        try:
            mongo.db.messages.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": new_details}
            )
            return True
        except Exception as e:
            print(f"Error updating message: {e}")
            return False