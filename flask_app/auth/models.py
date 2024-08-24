from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import random
import string
import uuid
import datetime
from config import Config
from database.db import users_db, logs_db

# Buffer for batch logging
log_buffer = []

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
        users_db.insert_one({
            'user_id': self.user_id,
            'username': self.username,
            'password_hash': self.password_hash,
            'role': self.role,
            'business_id': self.business_id,
            'permissions': self.permissions
        })
        log_action(self.user_id, 'create_user', f'User {self.username} created with role {self.role}.')

    @staticmethod
    def find_by_username(username):
        print('Attempting to find user by username...')
        user_data = users_db.find_one({'username': username}, {'username': 1, 'password_hash': 1, 'user_id': 1, 'role': 1, 'permissions': 1})
        print('User data retrieved:', user_data)
        if user_data:
            log_action(user_data['user_id'], 'find_user_by_username', f'User {username} retrieved.')
        return user_data

    @staticmethod
    def find_by_user_id(user_id):
        user_data = users_db.find_one({'user_id': user_id}, {'username': 1, 'role': 1, 'permissions': 1})
        if user_data:
            log_action(user_id, 'find_user_by_user_id', f'User with ID {user_id} retrieved.')
        return user_data

    @staticmethod
    def verify_password(stored_password_hash, password):
        verified = check_password_hash(stored_password_hash, password)
        if not verified:
            log_action(None, 'failed_verify_password', 'Failed password verification attempt.')
        return verified

    @staticmethod
    def generate_temp_password(length=10):
        characters = string.ascii_letters + string.digits + string.punctuation
        temp_password = ''.join(random.choice(characters) for _ in range(length))
        log_action(None, 'generate_temp_password', 'Temporary password generated.')
        return temp_password

def log_action(user_id, action, details):
    log_entry = {
        'user_id': user_id,
        'action': action,
        'details': details,
        'timestamp': datetime.datetime.utcnow()
    }
    log_buffer.append(log_entry)
    if len(log_buffer) >= 100:
        flush_log_buffer()

def flush_log_buffer():
    if log_buffer:
        logs_db.insert_many(log_buffer)
        log_buffer.clear()

import atexit
atexit.register(flush_log_buffer)
