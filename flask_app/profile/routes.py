from flask import Blueprint, request, jsonify
from database.db import profile_db, settings_db, pending_transactions_db
from tinydb import Query
from auth.utils import login_required
import threading

# Lock to handle TinyDB's single-threaded nature
db_lock = threading.Lock()

profile_bp = Blueprint('profile', __name__)

# Utility function to check if the user owns the profile/settings/pending transactions
def check_ownership(user_id, data):
    return data.get('user_id') == user_id

# Profile routes
@profile_bp.route('/profile', methods=['GET'], endpoint='get_profile')
@login_required
def get_profile(user_data):
    print('GET /profile called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        with db_lock:
            profile = profile_db.get(Query().user_id == user_id)
        if profile:
            print('Profile data retrieved:', profile)  # Debug statement
            return jsonify(profile)
        else:
            print('No profile found')  # Debug statement
            return jsonify({"message": "No profile found"}), 404
    except Exception as e:
        print('Error retrieving profile:', str(e))  # Debug statement
        return jsonify({"message": "Error retrieving profile"}), 500

@profile_bp.route('/profile', methods=['POST'], endpoint='update_profile')
@login_required
def update_profile(user_data):
    print('POST /profile called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        profile_data = request.json
        profile_data['user_id'] = user_id  # Associate profile with the user
        print('Profile data received:', profile_data)  # Debug statement
        with db_lock:
            profile_db.upsert(profile_data, Query().user_id == user_id)
        print('Profile updated successfully')  # Debug statement
        return jsonify({"message": "Profile updated successfully"}), 200
    except Exception as e:
        print('Error updating profile:', str(e))  # Debug statement
        return jsonify({"message": "Error updating profile"}), 500

# Settings routes
@profile_bp.route('/settings', methods=['GET'], endpoint='get_settings')
@login_required
def get_settings(user_data):
    print('GET /settings called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        with db_lock:
            settings = settings_db.get(Query().user_id == user_id)
        if settings:
            print('Settings data retrieved:', settings)  # Debug statement
            return jsonify(settings)
        else:
            # Define the default settings
            default_settings = {
                "user_id": user_id,
                "cameraEnabled": False,
                "selectedCamera": '',
                "barcodeScannerEnabled": False,
                "paymentEftposEnabled": False,
            }
            print('No settings found, returning default settings:', default_settings)  # Debug statement
            return jsonify(default_settings)
    except Exception as e:
        print('Error retrieving settings:', str(e))  # Debug statement
        return jsonify({"message": "Error retrieving settings"}), 500

@profile_bp.route('/settings', methods=['POST'], endpoint='update_settings')
@login_required
def update_settings(user_data):
    print('POST /settings called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        settings_data = request.json
        settings_data['user_id'] = user_id  # Associate settings with the user
        print('Settings data received:', settings_data)  # Debug statement
        with db_lock:
            settings_db.upsert(settings_data, Query().user_id == user_id)
        print('Settings updated successfully')  # Debug statement
        return jsonify({"message": "Settings updated successfully"}), 200
    except Exception as e:
        print('Error updating settings:', str(e))  # Debug statement
        return jsonify({"message": "Error updating settings"}), 500

# Pending Transactions routes
@profile_bp.route('/pendingTransactions', methods=['GET'], endpoint='get_pending_transactions')
@login_required
def get_pending_transactions(user_data):
    print('GET /pendingTransactions called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        with db_lock:
            pending_transactions = pending_transactions_db.search(Query().user_id == user_id)
        print('Pending transactions retrieved:', pending_transactions)  # Debug statement
        return jsonify(pending_transactions), 200
    except Exception as e:
        print('Error retrieving pending transactions:', str(e))  # Debug statement
        return jsonify({"message": "Error retrieving pending transactions"}), 500

@profile_bp.route('/pendingTransactions', methods=['POST'], endpoint='add_pending_transaction')
@login_required
def add_pending_transaction(user_data):
    print('POST /pendingTransactions called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        transaction_data = request.json
        transaction_data['user_id'] = user_id  # Associate transaction with the user
        print('Pending transaction data received:', transaction_data)  # Debug statement
        with db_lock:
            pending_transactions_db.insert(transaction_data)
        print('Pending transaction added successfully')  # Debug statement
        return jsonify({"message": "Pending transaction added successfully"}), 201
    except Exception as e:
        print('Error adding pending transaction:', str(e))  # Debug statement
        return jsonify({"message": "Error adding pending transaction"}), 500

@profile_bp.route('/pendingTransactions/<string:transaction_id>', methods=['DELETE'], endpoint='delete_pending_transaction')
@login_required
def delete_pending_transaction(user_data, transaction_id):
    print(f'DELETE /pendingTransactions/{transaction_id} called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        with db_lock:
            transaction = pending_transactions_db.get(Query().id == transaction_id)
        
        if transaction and transaction.get('user_id') == user_id:
            with db_lock:
                pending_transactions_db.remove(Query().id == transaction_id)
            print(f'Pending transaction with ID {transaction_id} deleted')  # Debug statement
            return jsonify({"message": "Pending transaction deleted successfully"}), 200
        else:
            return jsonify({"message": "Unauthorized to delete this transaction"}), 403
    except Exception as e:
        print(f'Error deleting pending transaction with ID {transaction_id}:', str(e))  # Debug statement
        return jsonify({"message": "Error deleting pending transaction"}), 500

# Save or update a pending transaction
@profile_bp.route('/pendingTransactions/save', methods=['POST'], endpoint='save_pending_transaction')
@login_required
def save_pending_transaction(user_data):
    print('POST /pendingTransactions/save called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        transaction_data = request.json
        transaction_data['user_id'] = user_id  # Associate transaction with the user
        print('Pending transaction data received:', transaction_data)  # Debug statement
        
        # Check if the transaction already exists
        with db_lock:
            Transaction = Query()
            existing_transaction = pending_transactions_db.get(Transaction.id == transaction_data.get('id') and Transaction.user_id == user_id)
        
        if existing_transaction:
            # Update the existing transaction
            with db_lock:
                pending_transactions_db.update(transaction_data, Transaction.id == transaction_data.get('id'))
            print('Pending transaction updated successfully')  # Debug statement
            return jsonify({"message": "Pending transaction updated successfully"}), 200
        else:
            # Insert a new transaction
            with db_lock:
                pending_transactions_db.insert(transaction_data)
            print('Pending transaction added successfully')  # Debug statement
            return jsonify({"message": "Pending transaction added successfully"}), 201
        
    except Exception as e:
        print('Error saving pending transaction:', str(e))  # Debug statement
        return jsonify({"message": "Error saving pending transaction"}), 500
