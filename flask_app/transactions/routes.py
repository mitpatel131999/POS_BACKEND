from flask import Blueprint, request, jsonify, render_template_string
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
    transaction = transactions_db.find_one({"id": transaction_id})
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



# Utility function to get a product by its ID
def get_product_by_id(product_id):
     print(f"Getting product with ID: {product_id}")  # Debug statement
     with db_lock:
         product = products_db.find_one({"id": int(product_id)})
     print(f"Product found: {product}")  # Debug statement
     return product


def reserve_product_quantity(product_id, quantity):
    print(f"Reserving quantity: {quantity} for product_id: {product_id}")  # Debug statement
    product = get_product_by_id(product_id)
    if product:
        new_reserved_quantity = product.get('reserved_quantity', 0) + quantity
        products_db.update_one({"id": int(product_id)}, {"$set": {"reserved_quantity": new_reserved_quantity}})
    print("Product quantity reserved successfully")  # Debug statement
    return product

def release_product_quantity(product_id, quantity):
    print(f"Releasing reserved quantity: {quantity} for product_id: {product_id}")  # Debug statement
    product = get_product_by_id(product_id)
    if product:
        new_reserved_quantity = product.get('reserved_quantity', 0) - quantity
        products_db.update_one({"id": int(product_id)}, {"$set": {"reserved_quantity": max(0, new_reserved_quantity)}})
    print("Product quantity released successfully")  # Debug statement
    return product

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
        
        # Fetch paginated transactions sorted by latest date first
        transactions = list(
             transactions_db.find(filters)
             .sort("_id", -1)  # Sort by date in descending order
             .limit(500)
         )
        #transactions = list(transactions_db.find(filters))
        print(f'{len(transactions)} transactions found with filters')  # Debug statement

        for transaction in transactions:
            transaction['_id'] = str(transaction['_id'])  # Convert ObjectId to string for JSON serialization

        log_action(user_id, "get_transactions", {"filters": filters, "transaction_count": len(transactions)})
        return jsonify(transactions), 200
    except Exception as e:
        print('Error retrieving transactions:', str(e))  # Debug statement
        log_action(user_id, "get_transactions_error", {"error": str(e)})
        return jsonify({"message": "Error retrieving transactions"}), 500

@transactions_bp.route('/transactionsbyid/<invoiceNumber>', methods=['GET'])
#@login_required
def get_transaction(invoiceNumber):
    print(f'GET /transactions/{invoiceNumber} called')  # Debug statement
    try:
        #user_id = user_data.get('user_id')
        print('hi')
        #if not user_id:
        #    return jsonify({"message": "User ID is required"}), 400
        # Debugging
        #print(f"User ID: {user_id}, Invoice Number: {invoiceNumber}")

        # Query for the transaction
        transaction = transactions_db.find_one({
            "invoiceNumber": invoiceNumber.strip(),  # Ensure no spaces
            #"user_id": user_id.strip()
        })
        if not transaction:
            print(f"Transaction not found for {invoiceNumber}")
            return jsonify({"message": "Transaction not found"}), 404
        print('hi')
        transaction['_id'] = str(transaction['_id'])  # Convert ObjectId to string
        print(f'Transaction retrieved: {transaction}')  # Debug statement

        #log_action(user_id, "get_transaction", {"invoiceNumber": invoiceNumber})
        return jsonify(transaction), 200
    except Exception as e:
        print(f'Error retrieving transaction {invoiceNumber}: {str(e)}')  # Debug statement
        #log_action(user_id, "get_transaction_error", {"error": str(e)})
        return jsonify({"message": "Error retrieving transaction"}), 500


@transactions_bp.route('/transactionsV1', methods=['GET'])
@login_required
def get_transactionsV1(user_data):
    print('GET /transactionsV1 called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        query_params = request.args
        print('Query parameters:', query_params)  # Debug statement

        # Initialize filters with user_id
        filters = {"user_id": user_id}

        # Dynamic filtering: Loop through query parameters and apply filters
        for key, value in query_params.items():
            if key in ['page', 'pageSize']:  # Skip pagination parameters
                continue
            if key == 'startDate':
                filters.setdefault("date", {})["$gte"] = value
            elif key == 'endDate':
                filters.setdefault("date", {})["$lte"] = value
            elif key in ['type', 'customerName', 'customerPhone', 'productName']:
                filters[key] = {"$regex": value, "$options": "i"}  # Case-insensitive regex match
            else:
                filters[key] = value  # Direct match for other keys

        print(f'Applied Filters: {filters}')  # Debug statement

        # Pagination parameters
        page = int(query_params.get('page', 1))  # Default to page 1
        page_size = int(query_params.get('pageSize', 500))  # Default to 20 transactions per page
        skip = (page - 1) * page_size

        # Fetch total transaction count for filters
        total_count = transactions_db.count_documents(filters)
        print(f'Total transactions matching filters: {total_count}')  # Debug statement

        # Fetch paginated transactions sorted by latest date first
        transactions = list(
            transactions_db.find(filters)
            .sort("_id", -1)  # Sort by date in descending order
            .skip(skip)
            .limit(page_size)
        )
        print(f'{len(transactions)} transactions found for page {page}')  # Debug statement

        # Convert ObjectId to string for JSON serialization
        for transaction in transactions:
            transaction['_id'] = str(transaction['_id'])

        log_action(user_id, "get_transactions", {
            "filters": filters,
            "transaction_count": len(transactions),
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
        })
        # Return transactions along with metadata
        return jsonify({
            "transactions": transactions,
            "totalCount": total_count,
            "page": page,
            "pageSize": page_size,
        }), 200
    except Exception as e:
        print('Error retrieving transactions:', str(e))  # Debug statement
        log_action(user_id, "get_transactions_error", {"error": str(e)})
        return jsonify({"message": "Error retrieving transactions"}), 500

@transactions_bp.route('/transactionsV2', methods=['GET'])
@login_required
def get_transactions_v2(user_data):
    print('GET /transactionsV2 called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        query_params = request.args
        print('Query parameters:', query_params)  # Debug statement

        # Initialize filters with user_id
        filters = {"user_id": user_id}

        # Apply dynamic filtering based on query parameters
        for key, value in query_params.items():
            if key in ['page', 'pageSize']:  # Skip pagination parameters
                continue
            if key == 'startDate':
                filters.setdefault("date", {})["$gte"] = value
            elif key == 'endDate':
                filters.setdefault("date", {})["$lte"] = value
            elif key in ['type', 'customerName', 'customerPhone', 'productName']:
                filters[key] = {"$regex": value, "$options": "i"}  # Case-insensitive regex match
            else:
                filters[key] = value  # Direct match for other keys

        print(f'Applied Filters: {filters}')  # Debug statement

        # Pagination parameters
        page = int(query_params.get('page', 1))  # Default to page 1
        page_size = int(query_params.get('pageSize', 500))  # Default to 500 transactions per page
        skip = (page - 1) * page_size

        # Fetch total transaction count for filters
        total_count = transactions_db.count_documents(filters)
        print(f'Total transactions matching filters: {total_count}')  # Debug statement

        # Fetch paginated transactions sorted by latest date first
        transactions = list(
            transactions_db.find(filters)
            .sort("_id", -1)  # Sort by date in descending order
            .skip(skip)
            .limit(page_size)
        )
        print(f'{len(transactions)} transactions found for page {page}')  # Debug statement

        # Convert ObjectId to string for JSON serialization
        for transaction in transactions:
            transaction['_id'] = str(transaction['_id'])

        log_action(user_id, "get_transactions", {
            "filters": filters,
            "transaction_count": len(transactions),
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
        })
        # Return transactions along with metadata
        return jsonify({
            "transactions": transactions,
            "totalCount": total_count,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total_count + page_size - 1) // page_size,  # Calculate total pages
        }), 200
    except Exception as e:
        print('Error retrieving transactions:', str(e))  # Debug statement
        log_action(user_id, "get_transactions_error", {"error": str(e)})
        return jsonify({"message": "Error retrieving transactions"}), 500

'''
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

        # Remove image data from each item in the cart
        for item in transaction_data.get('cart', []):
            # Remove image fields from the cart item if they exist
            # Set image fields to empty strings if they exist
            item['backImage'] = ""
            item['frontImage'] = ""

        

        adjusted_items = []

        try:
            if transaction_data['txn_type'] == 'sale' or transaction_data['txn_type'] == 'online_sale':
                for item in transaction_data['cart']:
                    valid, message = validate_product_availability(item['id'], float(item['quantity']))
                    if not valid:
                        rollback_quantities(adjusted_items)
                        log_action(user_id, "create_transaction_validation_failed", {"transaction_data": transaction_data, "message": message})
                        return jsonify({"message": message}), 400
                    
                    adjust_product_quantity(item['id'], -float(item['quantity']))
                    adjusted_items.append(item)

            elif transaction_data['txn_type'] == 'refund':
                for item in transaction_data['cart']:
                    adjust_product_quantity(item['id'], float(item['quantity']))

            with db_lock:
                result = transactions_db.insert_one(transaction_data)
                transaction_data['_id'] = str(result.inserted_id)

            print('Transaction created with ID:', transaction_data['id'])  # Debug statement
            log_action(user_id, "create_transaction", transaction_data)

            # Check and remove any pending transaction with the same invoice number
            invoice_number = transaction_data.get('invoiceNumber')
            if not invoice_number:
                print("No invoice number provided, skipping pending transaction check")
            else:
                print(f"Checking for existing pending transaction with invoice number: {invoice_number}")
                try:
                    pending_transaction = pending_transactions_db.find_one({"invoiceNumber": invoice_number})
                    if pending_transaction:
                        print(f"Found pending transaction for invoice number: {invoice_number}")
                        for item in pending_transaction.get('cart', []):
                            release_product_quantity(item['id'], float(item['quantity']))
                        with db_lock:
                            pending_transactions_db.delete_one({"invoiceNumber": invoice_number})
                            print(f"Removed pending transaction for invoice number: {invoice_number}")
                    else:
                        print(f"No pending transaction found for invoice number: {invoice_number}")
                except Exception as e:
                    print(f"Error while handling pending transaction: {str(e)}")


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
'''

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

        # Remove image data from each item in the cart
        for item in transaction_data.get('cart', []):
            item['backImage'] = ""
            item['frontImage'] = ""

        adjusted_items = []

        try:
            if transaction_data['txn_type'] in ['sale', 'online_sale']:
                for item in transaction_data['cart']:
                    product = get_product_by_id(item['id'])
                    
                    if product and product.get('isGroupProduct'):
                        # If group product, adjust quantities for all its components
                        for group_item in product['groupDetails']:
                            group_product = get_product_by_id(group_item['id'])
                            if not group_product:
                                rollback_quantities(adjusted_items)
                                return jsonify({"message": f"Component product {group_item['id']} not found"}), 400
                            
                            valid, message = validate_product_availability(
                                group_item['id'],
                                float(group_item['quantity']) * float(item['quantity'])
                            )
                            if not valid:
                                rollback_quantities(adjusted_items)
                                return jsonify({"message": message}), 400
                            
                            adjust_product_quantity(
                                group_item['id'],
                                -float(group_item['quantity']) * float(item['quantity'])
                            )
                            adjusted_items.append({
                                "id": group_item['id'],
                                "quantity": float(group_item['quantity']) * float(item['quantity'])
                            })
                    else:
                        # Handle individual products
                        valid, message = validate_product_availability(item['id'], float(item['quantity']))
                        if not valid:
                            rollback_quantities(adjusted_items)
                            return jsonify({"message": message}), 400
                        
                        adjust_product_quantity(item['id'], -float(item['quantity']))
                        adjusted_items.append(item)

            elif transaction_data['txn_type'] == 'refund':
                for item in transaction_data['cart']:
                    product = get_product_by_id(item['id'])
                    if product and product.get('isGroupProduct'):
                        # If group product, adjust quantities for all its components
                        for group_item in product['groupDetails']:
                            adjust_product_quantity(
                                group_item['id'],
                                float(group_item['quantity']) * float(item['quantity'])
                            )
                    else:
                        # Handle individual products
                        adjust_product_quantity(item['id'], float(item['quantity']))

            with db_lock:
                result = transactions_db.insert_one(transaction_data)
                transaction_data['_id'] = str(result.inserted_id)

            print('Transaction created with ID:', transaction_data['id'])  # Debug statement
            log_action(user_id, "create_transaction", transaction_data)

            # Check and remove any pending transaction with the same invoice number
            invoice_number = transaction_data.get('invoiceNumber')
            if invoice_number:
                pending_transaction = pending_transactions_db.find_one({"invoiceNumber": invoice_number})
                if pending_transaction:
                    for item in pending_transaction.get('cart', []):
                        release_product_quantity(item['id'], float(item['quantity']))
                    with db_lock:
                        pending_transactions_db.delete_one({"invoiceNumber": invoice_number})

            return jsonify(transaction_data), 200

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
            transaction = transactions_db.find_one({"id": transaction_id})
            print('transaction:',transaction)
            if transaction:
                if transaction['txn_type'] == 'sale' or transaction['txn_type'] == 'online sale':
                    for item in transaction['cart']:
                        adjust_product_quantity(item['id'], item['quantity'])
                elif transaction['txn_type'] == 'refund':
                    for item in transaction['cart']:
                        adjust_product_quantity(item['id'], -item['quantity'])
                print('waiting')
                transactions_db.delete_one({"id": transaction_id})

        print(f'Transaction with ID {transaction_id} deleted')  # Debug statement
        log_action(user_id, "delete_transaction", {"transaction_id": transaction_id})
        return jsonify({"message": "Transaction deleted successfully"}), 200
    except Exception as e:
        print(f'Error deleting transaction with ID {transaction_id}:', str(e))  # Debug statement
        log_action(user_id, "delete_transaction_error", {"error": str(e)})
        return jsonify({"message": "Error deleting transaction"}), 500


@transactions_bp.route('/receipt/<string:user_id>/<string:invoiceNumber>', methods=['GET'])

def render_receipt(user_id, invoiceNumber):
    # Fetch profile
    profile_data = profile_db.find_one({'user_id': user_id})
    if not profile_data:
        return jsonify({"message": "Profile not found "+ user_id}), 404

    transaction = transactions_db.find_one({
            "invoiceNumber": invoiceNumber.strip(),  # Ensure no spaces
            #"user_id": user_id.strip()
        })
    if not transaction:
        return jsonify({"message": "Transaction not found"}), 404


    # Calculate total paid and total due in Python
    payments = transaction.get('payments', [])  # Get the list of payments, defaulting to an empty list if not present
    total_paid = sum(float(payment.get('amount', 0)) for payment in payments)  # Sum up the amounts of all payments
    total_due = float(transaction.get('total', 0)) - total_paid  # Calculate the total due

    final_disclaimer = profile_data.get('invoiceDisclaimer', "No disclaimer")  # Use profile's disclaimer or a fallback

    # Split the disclaimer into multiple lines
    disclaimer_lines = final_disclaimer.split("\n")


    # Generate the HTML receipt
    html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Invoice</title>
            <style>
                body {{
                    font-family: "Arial", sans-serif;
                    width: 794px; /* Approx. A4 width */
                    margin: 0 auto;
                    padding: 10px; /* Reduced padding */
                    line-height: 1.2; /* Reduced line height */
                    color: #333;
                }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px; /* Reduced vertical spacing */
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 5px;
                }}
                .header img {{
                    max-width: 160px; /* Smaller logo size */
                    width: auto;
                }}
                .business-details {{
                    text-align: right;
                    font-size: 10px; /* Smaller font */
                }}
                .content h2 {{
                    text-align: center;
                    margin: 10px 0; /* Reduced spacing */
                    font-size: 20px; /* Smaller title font */
                    color: #0056b3;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px; /* Reduced spacing */
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 4px; /* Reduced padding */
                    text-align: left;
                    font-size: 10px; /* Smaller table font */
                }}
                th {{
                    background-color: #f9f9f9;
                }}
                .totals {{
                    margin-top: 10px;
                    text-align: right;
                    font-weight: bold;
                    font-size: 12px; /* Smaller totals font */
                }}
                .totals .important {{
                    color: #0056b3;
                    font-size: 14px; /* Highlighted totals slightly larger */
                }}
                .details-section {{
                    margin-top: 10px;
                    padding: 5px;
                    border: 1px solid #ddd;
                    background-color: #f9f9f9;
                    font-size: 10px; /* Smaller details section font */
                }}
                .totals-table {{
                    width: 40%;
                    margin-left: 60%;
                    margin-top: 5px; /* Reduced spacing */
                    border-collapse: collapse;
                    font-size: 10px; /* Smaller totals table font */
                }}
                .totals-table td {{
                    padding: 3px; /* Reduced padding */
                    border: none; /* No border for totals */
                }}
                .totals-table .label {{
                    text-align: left;
                }}
                .totals-table .labelTotal {{
                    text-align: left;
                    font-size: 15px;
                }}
                .totals-table .value {{
                    text-align: right;
                }}
                .totals-table .valueTotal {{
                    text-align: right;
                    font-size: 15px;
                }}    
                .footer {{
                    margin-top: 8px; /* Reduced spacing */
                    font-size: 10px; /* Smaller footer font */
                    text-align: left;
                    border-top: 1px solid #ddd;
                    padding-top: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <img src="{profile_data['logoBase64']}" alt="Business Logo">
                <div class="business-details">
                    <h1>{profile_data['businessName']}</h1>
                    <p>{profile_data['address']}</p>
                    <p>Phone: {profile_data['phoneNumber']} | Email: {profile_data['email']}</p>
                    <p>{profile_data['businessIdName']}: {profile_data['businessIdNumber']}</p>
                </div>
            </div>
            <div class="content">
                <h2>Tax Invoice</h2>
                <p><strong>Invoice #:</strong> {transaction['invoiceNumber']}</p>
                <p><strong>Date:</strong> {transaction['date']}</p>
                <p><strong>Customer:</strong> {transaction.get('customerName', 'N/A')}</p>
                <p><strong>Phone:</strong> {transaction.get('customerPhone', 'N/A')}</p>
                <table>
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>Description</th>
                            <th>Quantity</th>
                            <th>Unit Price</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join([
                            f"<tr>"
                            f"<td>{item['name']}</td>"
                            f"<td>{item.get('description', '')}</td>"
                            f"<td>{item['quantity']} {item.get('unit', '')}</td>"
                            f"<td>{item['price']}</td>"
                            f"<td>{item['quantity'] * item['price']}</td>"
                            f"</tr>" for item in transaction['cart']
                        ])}
                    </tbody>
                </table>
                <div class="totals">
                    <table class="totals-table">
                        <tr>
                            <td class="label">Subtotal:</td>
                            <td class="value">{transaction['subtotal']}</td>
                        </tr>
                        <tr>
                            <td class="label">Discount:</td>
                            <td class="value">{transaction['discountAmount']}</td>
                        </tr>
                        <tr>
                            <td class="label">Surcharge:</td>
                            <td class="value">{transaction['surchargeAmount']}</td>
                        </tr>
                        <tr>
                            <td class="label">Tax:</td>
                            <td class="value">{transaction['taxAmount']}</td>
                        </tr>
                        <tr>
                            <td class="labelTotal"><strong>Total:</strong></td>
                            <td class="valueTotal"><strong>{transaction['total']}</strong></td>
                        </tr>
                    </table>
                </div>
                <div class="details-section">
                    <p><strong>Payment Details:</strong></p>
                    <p>Total Paid: {total_paid}</p>
                    <p>{'Payment Complete' if total_due <= 0 else f'Amount Due: {total_due}'}</p>
                </div>
                <div class="details-section">
                            <p><strong>{profile_data['bankingDetails'].get('selectedCountry', '')} Bank Details:</strong></p>
                            {
                                ''.join(
                                    f"<p>{key.replace('_', ' ').capitalize()}: {value or 'N/A'}</p>"
                                    for key, value in profile_data['bankingDetails'].get('details', {}).items()
                                ) if 'details' in profile_data['bankingDetails'] else '<p>No banking details available.</p>'
                            }
                        </div>
            </div>
            <div class="footer">
                <p><strong>Disclaimer:</strong></p>
                {''.join([f'<p>{line}</p>' for line in disclaimer_lines])}
            </div>
            <button onclick="window.print()">Print</button>
        </body>
        </html>
        """

    
    return render_template_string(html_content)