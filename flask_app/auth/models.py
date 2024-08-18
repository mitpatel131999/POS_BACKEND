from werkzeug.security import generate_password_hash, check_password_hash
from tinydb import Query
from database.db import users_db
import random
import string
import uuid  # For generating unique user IDs

class User:
    def __init__(self, username, password, role, business_id=None):
        self.user_id = str(uuid.uuid4())  # Generate a unique user ID
        self.username = username
        self.password_hash = generate_password_hash(password)
        self.role = role
        self.business_id = business_id  # Associate with a business if applicable
        self.permissions = self.assign_permissions(role)

    def assign_permissions(self, role):
        roles_permissions = {
            'superuser': ['manage_system', 'create_superuser', 'view_all_businesses'],
            'business_owner': ['manage_business', 'view_orders', 'edit_orders', 'access_business_apis'],
            'moderator': ['view_orders', 'edit_orders', 'access_moderate_apis'],
            'user': ['place_order', 'view_profile', 'edit_profile', 'access_user_apis'],
            'guest': ['view_public_content']
        }
        return roles_permissions.get(role, [])

    def save(self):
        users_db.insert({
            'user_id': self.user_id,  # Save the user ID
            'username': self.username,
            'password_hash': self.password_hash,
            'role': self.role,
            'business_id': self.business_id,
            'permissions': self.permissions
        })

    @staticmethod
    def find_by_username(username):
        UserQuery = Query()
        user_data = users_db.get(UserQuery.username == username)
        return user_data

    @staticmethod
    def find_by_user_id(user_id):
        UserQuery = Query()
        user_data = users_db.get(UserQuery.user_id == user_id)
        return user_data

    @staticmethod
    def verify_password(stored_password_hash, password):
        return check_password_hash(stored_password_hash, password)

    @staticmethod
    def generate_temp_password(length=10):
        characters = string.ascii_letters + string.digits + string.punctuation
        temp_password = ''.join(random.choice(characters) for i in range(length))
        return temp_password
