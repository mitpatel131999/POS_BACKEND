from flask import Blueprint, request, jsonify
from database.db import transactions_db, products_db  # Assuming you have a products database in addition to transactions
import uuid
from tinydb import Query
from auth.utils import login_required
import threading

# Lock to handle TinyDB's single-threaded nature
db_lock = threading.Lock()

transactions_bp = Blueprint('transactions', __name__)

# Utility function to check if the user owns the transaction
def check_ownership(user_id, transaction_id):
    Transaction = Query()
    with db_lock:
        transaction = transactions_db.get(Transaction.invoiceNumber == transaction_id)
    return transaction and transaction.get('user_id') == user_id

# Utility function to get a product by its ID
def get_product_by_id(product_id):
    Product = Query()
    with db_lock:
        product = products_db.get(Product.id == product_id)
    return product

# Utility function to update a product
def update_product(product):
    with db_lock:
        products_db.update(product, Query().id == product['id'])

# Utility function to adjust product quantity
def adjust_product_quantity(product_id, quantity):
    product = get_product_by_id(product_id)
    if product:
        product['quantity'] += quantity
        update_product(product)
    return product

# Utility function to validate product availability
def validate_product_availability(product_id, requested_quantity):
    product = get_product_by_id(product_id)
    if not product:
        return False, "Product not found"
    
    available_quantity = product['quantity']
    if requested_quantity > available_quantity:
        return False, f"Not enough stock for {product['name']}. Available: {available_quantity}, Requested: {requested_quantity}"
    
    return True, None

# Rollback changes made to product quantities in case of failure
def rollback_quantities(adjusted_items):
    for item in adjusted_items:
        adjust_product_quantity(item['id'], item['quantity'])

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

        Transaction = Query()
        filters = [Transaction.user_id == user_id]  # Enforce user ownership
        if start_date:
            filters.append(Transaction.date >= start_date)
        if end_date:
            filters.append(Transaction.date <= end_date)
        if txn_type:
            filters.append(Transaction.type == txn_type)

        with db_lock:
            if filters:
                transactions = transactions_db.search(filters[0])
                for f in filters[1:]:
                    transactions = [txn for txn in transactions if f(transactions_db.get(doc_id=txn.doc_id))]
                print(f'{len(transactions)} transactions found with filters')  # Debug statement
            else:
                transactions = transactions_db.all()
                print(f'{len(transactions)} transactions found without filters')  # Debug statement

        return jsonify(transactions), 200
    except Exception as e:
        print('Error retrieving transactions:', str(e))  # Debug statement
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

        # List to track successfully adjusted products for potential rollback
        adjusted_items = []

        try:
            # Validate and update inventory for sale or refund
            if transaction_data['txn_type'] == 'sale':
                for item in transaction_data['cart']:
                    valid, message = validate_product_availability(item['id'], item['quantity'])
                    if not valid:
                        rollback_quantities(adjusted_items)
                        return jsonify({"message": message}), 400
                    
                    adjust_product_quantity(item['id'], -item['quantity'])
                    adjusted_items.append(item)  # Track successful adjustments

            elif transaction_data['txn_type'] == 'refund':
                for item in transaction_data['cart']:
                    adjust_product_quantity(item['id'], item['quantity'])

            with db_lock:
                transactions_db.insert(transaction_data)

            print('Transaction created with ID:', transaction_data['id'])  # Debug statement
            return jsonify(transaction_data), 201

        except Exception as e:
            print('Error during transaction creation, rolling back changes:', str(e))  # Debug statement
            rollback_quantities(adjusted_items)
            return jsonify({"message": "Error creating transaction, changes rolled back"}), 500

    except Exception as e:
        print('Error creating transaction:', str(e))  # Debug statement
        return jsonify({"message": "Error creating transaction"}), 500

@transactions_bp.route('/transactions/<string:transaction_id>', methods=['PUT'])
@login_required
def update_transaction(user_data, transaction_id):
    print(f'PUT /transactions/{transaction_id} called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not check_ownership(user_id, transaction_id):
            return jsonify({"message": "Unauthorized to update this transaction"}), 403

        transaction_data = request.json
        print('Transaction data to update:', transaction_data)  # Debug statement

        with db_lock:
            Transaction = Query()
            transactions_db.update(transaction_data, Transaction.id == transaction_id)
        print(f'Transaction with ID {transaction_id} updated')  # Debug statement

        return jsonify({"message": "Transaction updated successfully"}), 200
    except Exception as e:
        print(f'Error updating transaction with ID {transaction_id}:', str(e))  # Debug statement
        return jsonify({"message": "Error updating transaction"}), 500

@transactions_bp.route('/transactions/<string:transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(user_data, transaction_id):
    print(f'DELETE /transactions/{transaction_id} called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not check_ownership(user_id, transaction_id):
            return jsonify({"message": "Unauthorized to delete this transaction"}), 403

        with db_lock:
            # Revert inventory changes if the transaction is deleted
            transaction = transactions_db.get(Query().invoiceNumber == transaction_id)
            if transaction:
                if transaction['txn_type'] == 'sale':
                    for item in transaction['cart']:
                        adjust_product_quantity(item['id'], item['quantity'])
                elif transaction['txn_type'] == 'refund':
                    for item in transaction['cart']:
                        adjust_product_quantity(item['id'], -item['quantity'])

                # Remove the transaction from the database
                transactions_db.remove(Query().invoiceNumber == transaction_id)

        print(f'Transaction with ID {transaction_id} deleted')  # Debug statement
        return jsonify({"message": "Transaction deleted successfully"}), 200
    except Exception as e:
        print(f'Error deleting transaction with ID {transaction_id}:', str(e))  # Debug statement
        return jsonify({"message": "Error deleting transaction"}), 500
