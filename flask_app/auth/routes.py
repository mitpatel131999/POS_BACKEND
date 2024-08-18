from flask import Blueprint, request, jsonify
from auth.models import User
from auth.utils import authenticate, create_jwt, verify_jwt
from auth.utils import authenticate, create_jwt, verify_jwt, login_required


auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')  # Default role is 'user'
    business_id = data.get('business_id')  # Optional, only needed for Business Owner or Moderator
    
    if User.find_by_username(username):
        return jsonify({"message": "User already exists"}), 400
    
    user = User(username, password, role, business_id)
    user.save()
    return jsonify({"message": "User registered successfully", "user_id": user.user_id}), 201  # Return user_id

@auth_bp.route('/login', methods=['POST'])
def login():
    # Get the JSON data from the request
    auth = request.json
    
    # Extract username and password from the JSON data
    username = auth.get('username')
    password = auth.get('password')
    
    # Check if the username and password are provided
    if not username or not password:
        return jsonify({"message": "Missing credentials"}), 400
    
    # Authenticate the user
    if not authenticate(username, password):
        return jsonify({"message": "Invalid credentials"}), 401
    
    # If authentication is successful, retrieve user data
    user_data = User.find_by_username(username)
    
    # Generate a JWT token for the authenticated user
    token = create_jwt(user_data)
    
    # Return the response with the token and user_id
    return jsonify({"message": "Login successful", "token": token, "user_id": user_data['user_id']}), 200

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password(user_data):  # Note that user_data is now passed as an argument
    # Get the new password from the JSON payload
    data = request.json
    new_password = data.get('new_password')
    
    # Ensure the new password is provided
    if not new_password:
        return jsonify({"message": "New password is required"}), 400
    
    # Hash the new password
    new_password_hash = generate_password_hash(new_password)
    
    # Update the user's password in the database
    users_db.update({'password_hash': new_password_hash}, Query().username == user_data['username'])
    
    return jsonify({"message": "Password changed successfully"}), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    username = data.get('username')
    user_data = User.find_by_username(username)
    
    if not user_data:
        return jsonify({"message": "User not found"}), 404
    
    # Generate a random temporary password
    temp_password = User.generate_temp_password()

    # TODO: impliment method to send the password
    # Send the temporary password via email (you need to implement email functionality)
    
    user = User(user_data['username'], temp_password, user_data['role'], user_data['business_id'])
    user.save()
    
    return jsonify({"message": "Temporary password sent to your email"}), 200

@auth_bp.route('/user/<user_id>', methods=['GET'])
def get_user(user_id):
    user_data = User.find_by_user_id(user_id)
    if user_data:
        return jsonify({"user": user_data}), 200
    return jsonify({"message": "User not found"}), 404
