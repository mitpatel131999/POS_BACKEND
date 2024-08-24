from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import uuid
from auth.utils import login_required
import threading
from datetime import datetime
from config import Config
from database.db import profile_db, transactions_db, products_db, orders_db, settings_db, pending_transactions_db, logs_db

# Lock to handle MongoDB operations safely in a multi-threaded environment
db_lock = threading.Lock()

transactions_bp = Blueprint('transactions', __name__)

# Utility function to log actions
def log_action(user_id, action, details):
    log_entry = {
        "user_id": user_id,
        "action": action,
        "details": details,
        "timestamp": datetime.utcnow()
    }
    with db_lock:
        logs_db.insert_one(log_entry)
    print(f"Logged action: {action}, details: {details}")  # Debug statement

# Utility function to check if the user owns the transaction
def check_ownership(user_id, transaction_id):
    transaction = transactions_db.find_one({"invoiceNumber": transaction_id})
    ownership = transaction and transaction.get('user_id') == user_id
    log_action(user_id, "check_ownership", {"transaction_id": transaction_id, "ownership": ownership})
    return ownership

# Utility function to get a product by its ID
def get_product_by_id(product_id):
    product = products_db.find_one({"id": int(product_id)})
    log_action(None, "get_product_by_id", {"product_id": product_id, "product": product})
    return product

# Utility function to update a product
def update_product(product):
    products_db.update_one({"id": int(product['id'])}, {"$set": product})
    log_action(None, "update_product", {"product": product})

# Utility function to adjust product quantity
def adjust_product_quantity(product_id, quantity):
    product = get_product_by_id(product_id)
    if product:
        new_quantity = product['quantity'] + quantity
        products_db.update_one({"id": int(product_id)}, {"$set": {"quantity": new_quantity}})
        log_action(None, "adjust_product_quantity", {"product_id": product_id, "adjustment": quantity, "new_quantity": new_quantity})
    return product

# Utility function to validate product availability
def validate_product_availability(product_id, requested_quantity):
    product = get_product_by_id(product_id)
    if not product:
        log_action(None, "validate_product_availability", {"product_id": product_id, "status": "Product not found"})
        return False, "Product not found"
    
    available_quantity = product['quantity']
    if requested_quantity > available_quantity:
        log_action(None, "validate_product_availability", {"product_id": product_id, "status": "Not enough stock"})
        return False, f"Not enough stock for {product['name']}. Available: {available_quantity}, Requested: {requested_quantity}"
    
    log_action(None, "validate_product_availability", {"product_id": product_id, "status": "Validated"})
    return True, None

# Rollback changes made to product quantities in case of failure
def rollback_quantities(adjusted_items):
    for item in adjusted_items:
        adjust_product_quantity(item['id'], item['quantity'])
    log_action(None, "rollback_quantities", {"adjusted_items": adjusted_items})

@transactions_bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions(user_data):
    print('GET /transactions called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        query_params = request.args
        print('Query parameters:', query_params)  # Debug statement

        start_date = query_params.get('startDate')
        end_date = query_params.get('endDate')
        txn_type = query_params.get('type')

        print(f'Filters - start_date: {start_date}, end_date: {end_date}, txn_type: {txn_type}')  # Debug statement

        filters = {"user_id": user_id}
        if start_date:
            filters["date"] = {"$gte": start_date}
        if end_date:
            if "date" in filters:
                filters["date"]["$lte"] = end_date
            else:
                filters["date"] = {"$lte": end_date}
        if txn_type:
            filters["txn_type"] = txn_type

        transactions = list(transactions_db.find(filters))
        print(f'{len(transactions)} transactions found with filters')  # Debug statement

        for transaction in transactions:
            transaction['_id'] = str(transaction['_id'])  # Convert ObjectId to string for JSON serialization

        log_action(user_id, "get_transactions", {"filters": filters, "transaction_count": len(transactions)})
        return jsonify(transactions), 200
    except Exception as e:
        print('Error retrieving transactions:', str(e))  # Debug statement
        log_action(user_id, "get_transactions_error", {"error": str(e)})
        return jsonify({"message": "Error retrieving transactions"}), 500

@transactions_bp.route('/transactions', methods=['POST'])
@login_required
def create_transaction(user_data):
    print('POST /transactions called')  # Debug statement
    try:
        transaction_data = request.json
        print('Transaction data received:', transaction_data)  # Debug statement
        user_id = user_data.get('user_id')
        transaction_data['id'] = str(uuid.uuid4())
        transaction_data['user_id'] = user_id  # Associate transaction with the user

        adjusted_items = []

        try:
            if transaction_data['txn_type'] == 'sale':
                for item in transaction_data['cart']:
                    valid, message = validate_product_availability(item['id'], item['quantity'])
                    if not valid:
                        rollback_quantities(adjusted_items)
                        log_action(user_id, "create_transaction_validation_failed", {"transaction_data": transaction_data, "message": message})
                        return jsonify({"message": message}), 400
                    
                    adjust_product_quantity(item['id'], -item['quantity'])
                    adjusted_items.append(item)

            elif transaction_data['txn_type'] == 'refund':
                for item in transaction_data['cart']:
                    adjust_product_quantity(item['id'], item['quantity'])

            with db_lock:
                result = transactions_db.insert_one(transaction_data)
                transaction_data['_id'] = str(result.inserted_id)

            print('Transaction created with ID:', transaction_data['id'])  # Debug statement
            log_action(user_id, "create_transaction", transaction_data)
            return jsonify(transaction_data), 200

        except Exception as e:
            print('Error during transaction creation, rolling back changes:', str(e))  # Debug statement
            rollback_quantities(adjusted_items)
            log_action(user_id, "create_transaction_error", {"error": str(e)})
            return jsonify({"message": "Error creating transaction, changes rolled back"}), 500

    except Exception as e:
        print('Error creating transaction:', str(e))  # Debug statement
        log_action(user_id, "create_transaction_error", {"error": str(e)})
        return jsonify({"message": "Error creating transaction"}), 500


@transactions_bp.route('/transactions/<string:transaction_id>', methods=['PUT'])
@login_required
def update_transaction(user_data, transaction_id):
    print(f'PUT /transactions/{transaction_id} called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not check_ownership(user_id, transaction_id):
            log_action(user_id, "update_transaction_unauthorized", {"transaction_id": transaction_id})
            return jsonify({"message": "Unauthorized to update this transaction"}), 403

        transaction_data = request.json
        print('Transaction data to update:', transaction_data)  # Debug statement

        with db_lock:
            transactions_db.update_one({"invoiceNumber": transaction_id}, {"$set": transaction_data})
        print(f'Transaction with ID {transaction_id} updated')  # Debug statement
        log_action(user_id, "update_transaction", {"transaction_id": transaction_id, "transaction_data": transaction_data})
        return jsonify({"message": "Transaction updated successfully"}), 200
    except Exception as e:
        print(f'Error updating transaction with ID {transaction_id}:', str(e))  # Debug statement
        log_action(user_id, "update_transaction_error", {"error": str(e)})
        return jsonify({"message": "Error updating transaction"}), 500

@transactions_bp.route('/transactions/<string:transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(user_data, transaction_id):
    print(f'DELETE /transactions/{transaction_id} called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not check_ownership(user_id, transaction_id):
            log_action(user_id, "delete_transaction_unauthorized", {"transaction_id": transaction_id})
            return jsonify({"message": "Unauthorized to delete this transaction"}), 403

        with db_lock:
            transaction = transactions_db.find_one({"invoiceNumber": transaction_id})
            if transaction:
                if transaction['txn_type'] == 'sale':
                    for item in transaction['cart']:
                        adjust_product_quantity(item['id'], item['quantity'])
                elif transaction['txn_type'] == 'refund':
                    for item in transaction['cart']:
                        adjust_product_quantity(item['id'], -item['quantity'])

                transactions_db.delete_one({"invoiceNumber": transaction_id})

        print(f'Transaction with ID {transaction_id} deleted')  # Debug statement
        log_action(user_id, "delete_transaction", {"transaction_id": transaction_id})
        return jsonify({"message": "Transaction deleted successfully"}), 200
    except Exception as e:
        print(f'Error deleting transaction with ID {transaction_id}:', str(e))  # Debug statement
        log_action(user_id, "delete_transaction_error", {"error": str(e)})
        return jsonify({"message": "Error deleting transaction"}), 500
