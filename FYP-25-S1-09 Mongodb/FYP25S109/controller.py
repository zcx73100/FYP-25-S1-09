from FYP25S109 import entity
from .entity import UserAccount


# User Account
from flask import session  # Import session to check the logged-in user's role
from FYP25S109 import entity
from .entity import UserAccount


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
        """Ensure role is correctly assigned before account creation"""
        
        # ✅ Determine the role based on session
        if not userAcc.role:  # If role is missing
            if session.get("role") == "Teacher":  
                userAcc.role = "Student"  # Teacher-created accounts default to Student
            else:
                userAcc.role = "User"  # Everyone else defaults to User

        # ✅ Create user account in the database
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
