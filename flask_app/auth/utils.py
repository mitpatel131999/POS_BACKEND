import jwt
import datetime
from auth.models import User
from werkzeug.security import generate_password_hash, check_password_hash
from tinydb import Query
from functools import wraps
from flask import request, jsonify

SECRET_KEY = "your_secret_key"

def create_jwt(user_data):
    payload = {
        'user_id': user_data['user_id'],
        'username': user_data['username'],
        'role': user_data['role'],
        'permissions': user_data['permissions'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_jwt(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def authenticate(username, password):
    user_data = User.find_by_username(username)
    #password = generate_password_hash(password) # comment this once we implimwnt correctly  and hash at froent end only 
    print(password)
    if user_data and User.verify_password(user_data['password_hash'], password):
        return True
    return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Retrieve the Authorization header from the request
            auth_header = request.headers.get('Authorization')
            
            # Check if the token is present
            if not auth_header:
                return jsonify({"message": "Authorization header is missing!"}), 403
            
            # Extract token from the header (handling the "Bearer" prefix)
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
            
            # Verify the JWT token
            user_data = verify_jwt(token)
            
            # Check if the token is valid
            if not user_data:
                return jsonify({"message": "Invalid or expired token!"}), 401
            
            # If the token is valid, proceed with the request
            return f(user_data, *args, **kwargs)
        
        except IndexError:
            return jsonify({"message": "Bearer token malformed!"}), 400
        except Exception as e:
            return jsonify({"message": "An error occurred", "error": str(e)}), 500
    
    return decorated_function