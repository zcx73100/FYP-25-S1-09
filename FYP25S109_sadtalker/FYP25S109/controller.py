from FYP25S109 import entity
from .entity import UserAccount


# User Account
class LoginController:
    @staticmethod
    def userLogin(username, password):
        return entity.UserAccount.login(username, password)

class CreateUserAccController:
    @staticmethod
    def createUserAcc(userAcc):
        return entity.UserAccount.createUserAcc(userAcc)

class DisplayUserDetailController:
    @staticmethod
    def get_user_info(username):
        return entity.UserAccount.get_user_info(username)

class UpdateUserRoleController:
    @staticmethod
    def change_role(username, new_role):
        """Changes a user's role using the entity class"""
        return UserAccount.update_role(username, new_role)