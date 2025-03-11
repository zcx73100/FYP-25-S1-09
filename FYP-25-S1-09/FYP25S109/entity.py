from flask import session
#from . import mysql
from werkzeug.security import check_password_hash

class UserAccount:
    def __init__(self, username=None, password=None, name=None, surname=None, email=None, date_of_birth=None, role=None):
        self.username = username
        self.password = password
        self.name = name
        self.surname = surname
        self.email = email
        self.date_of_birth = date_of_birth
        self.role = role

    @staticmethod
    def createUserAcc(userAcc):
        """Create a new user account in the database."""
        cur = None  # Ensure `cur` is initialized before using it

        try:
            cur = mysql.connection.cursor()

            print(f"[DEBUG] Attempting to insert user: {userAcc.username}, {userAcc.email}, {userAcc.role}")

            query = """
            INSERT INTO userAccount (username, password, name, surname, email, date_of_birth, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            data = (userAcc.username, userAcc.password, userAcc.name, userAcc.surname, 
                    userAcc.email, userAcc.date_of_birth, userAcc.role)

            cur.execute(query, data)
            mysql.connection.commit()

            print("[DEBUG] User successfully inserted into the database!")
            return True

        except Exception as e:
            print(f"[ERROR] Database Insertion Error: {str(e)}")  # <-- Copy this error and send it to me!
            return False

        finally:
            if cur is not None:  # Ensure `cur` is closed only if it was initialized
                cur.close()

    @staticmethod
    def login(username, password):
        """Authenticate user login and return (username, role) if valid."""
        try:
            cur = mysql.connection.cursor()
            query = "SELECT username, role, password FROM useraccount WHERE username = %s"
            cur.execute(query, (username,))
            account = cur.fetchone()  # Fetch (username, role, hashed_password)

            if account and check_password_hash(account[2], password):
                return account[:2]  # Return (username, role)
            else:
                return None  # Return None if authentication fails

        except Exception as e:
            print(f"Error during login: {e}")
            return None

        finally:
            cur.close()
            
            
    @staticmethod
    def get_user_info(username):
        """Retrieve user information, including role."""
        try:
            cur = mysql.connection.cursor()
            query = "SELECT username, name, surname, email, role FROM useraccount WHERE username = %s"
            cur.execute(query, (username,))
            user_data = cur.fetchone()  # Fetch user info (username, name, surname, email, role)
            return user_data
        except Exception as e:
            print(f"Error fetching user info: {e}")
            return None
        finally:
            cur.close()

    @staticmethod
    def update_role(username, new_role):
        """Updates the role of a user in the database."""
        try:
            cur = mysql.connection.cursor()
            query = "UPDATE useraccount SET role = %s WHERE username = %s"
            cur.execute(query, (new_role, username))
            mysql.connection.commit()
            cur.close()
            return True  # Role update successful
        except Exception as e:
            print(f"[ERROR] Failed to update role: {e}")
            return False  # Role update failed
