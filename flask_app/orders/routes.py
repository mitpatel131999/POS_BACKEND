from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import uuid
from auth.utils import login_required
import threading
from config import Config
from datetime import datetime
from database.db import profile_db, transactions_db, products_db, orders_db, settings_db, pending_transactions_db, logs_db

# Lock to handle MongoDB operations safely in a multi-threaded environment
db_lock = threading.Lock()

orders_bp = Blueprint('orders', __name__)

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

# Utility function to find order by invoice number
def find_order_by_invoice(invoice_number):
    print(f"Finding order with invoice number: {invoice_number}")  # Debug statement
    with db_lock:
        order = orders_db.find_one({"invoiceNumber": invoice_number})
    print(f"Order found: {order}")  # Debug statement
    return order

# Utility function to check if the user owns the order
def check_ownership(user_id, order_id):
    print(f"Checking ownership for user_id: {user_id} and order_id: {order_id}")  # Debug statement
    with db_lock:
        order = orders_db.find_one({"id": order_id})
    ownership = order and order.get('user_id') == user_id
    print(f"Ownership check result: {ownership}")  # Debug statement
    return ownership

# Utility function to get a product by its ID
def get_product_by_id(product_id):
    print(f"Getting product with ID: {product_id}")  # Debug statement
    with db_lock:
        product = products_db.find_one({"id": int(product_id)})
    print(f"Product found: {product}")  # Debug statement
    return product

# Utility function to update a product
def update_product(product):
    print(f"Updating product with ID: {product['id']}")  # Debug statement
    with db_lock:
        products_db.update_one({"id": int(product['id'])}, {"$set": product})
    print("Product updated successfully")  # Debug statement

# Utility function to validate and reserve product availability
def validate_and_reserve_product_availability(product_id, requested_quantity):
    print(f"Validating availability for product_id: {product_id}, requested_quantity: {requested_quantity}")  # Debug statement
    product = get_product_by_id(product_id)
    if not product:
        print("Product not found")  # Debug statement
        return False, "Product not found"

    available_quantity = product['quantity'] - product.get('reserved_quantity', 0)
    if requested_quantity > available_quantity:
        print(f"Not enough stock for {product['name']}. Available: {available_quantity}, Requested: {requested_quantity}")  # Debug statement
        return False, f"Not enough stock for {product['name']}. Available: {available_quantity}, Requested: {requested_quantity}"

    print("Product availability validated successfully")  # Debug statement
    return True, None

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
        products_db.update_one({"id": int(product_id)}, {"$set": {"reserved_quantity": new_reserved_quantity}})
    print("Product quantity released successfully")  # Debug statement
    return product

def adjust_product_quantity(product_id, quantity):
    print(f"Adjusting quantity: {quantity} for product_id: {product_id}")  # Debug statement
    product = get_product_by_id(product_id)
    if product:
        new_quantity = product['quantity'] + quantity
        products_db.update_one({"id": int(product_id)}, {"$set": {"quantity": new_quantity}})
    print("Product quantity adjusted successfully")  # Debug statement
    return product

# API to get all orders
@orders_bp.route('/orders', methods=['GET'])
@login_required
def get_orders(user_data):
    try:
        user_id = user_data.get('user_id')
        print(f"Getting orders for user_id: {user_id}")  # Debug statement
        
        orders = list(orders_db.find({"user_id": user_id}))
        
        for order in orders:
            if '_id' in order:
                order['_id'] = str(order['_id'])
        
        print(f"Orders retrieved: {orders}")  # Debug statement
        log_action(user_id, "retrieve_orders", {"order_count": len(orders)})
        return jsonify(orders), 200
    except Exception as e:
        print(f"Error retrieving orders: {str(e)}")  # Debug statement
        log_action(user_id, "retrieve_orders_error", {"error": str(e)})
        return jsonify({"message": "Error retrieving orders", "error": str(e)}), 500

# API to create a new order
@orders_bp.route('/orders/<string:user_id>', methods=['POST'])
def create_order(user_id):
    try:
        order_data = request.json
        print(f"Creating order for user_id: {user_id}, order_data: {order_data}")  # Debug statement

        if not user_id:
            print("User ID is required in the header")  # Debug statement
            return jsonify({"message": "User ID is required in the header"}), 400

        order_data['id'] = str(uuid.uuid4())
        order_data['user_id'] = user_id
        order_data['status'] = 'Pending'

        with db_lock:
            orders_db.insert_one(order_data)
        print("Order created successfully")  # Debug statement
        log_action(user_id, "create_order", order_data)
        if '_id' in order_data:
            order_data['_id'] = str(order_data['_id'])
        return jsonify(order_data), 200
    except Exception as e:
        print(f"Error creating order: {str(e)}")  # Debug statement
        log_action(user_id, "create_order_error", {"error": str(e)})
        return jsonify({"message": "Error creating order", "error": str(e)}), 500

# API to delete an order by ID
@orders_bp.route('/orders/<string:order_id>', methods=['DELETE'])
@login_required
def delete_order(user_data, order_id):
    try:
        user_id = user_data.get('user_id')
        print(f"Deleting order with order_id: {order_id}, user_id: {user_id}")  # Debug statement
        if not check_ownership(user_id, order_id):
            print("Unauthorized to delete this order")  # Debug statement
            log_action(user_id, "delete_order_unauthorized", {"order_id": order_id})
            return jsonify({"message": "Unauthorized to delete this order"}), 403

        with db_lock:
            orders_db.delete_one({"id": order_id})
        print("Order deleted successfully")  # Debug statement
        log_action(user_id, "delete_order", {"order_id": order_id})
        return jsonify({"message": "Order deleted successfully"}), 200
    except Exception as e:
        print(f"Error deleting order: {str(e)}")  # Debug statement
        log_action(user_id, "delete_order_error", {"error": str(e)})
        return jsonify({"message": "Error deleting order", "error": str(e)}), 500

# API to update the status of an order
@orders_bp.route('/orders/<string:invoice_number>/status', methods=['PATCH'])
@login_required
def update_order_status(user_data, invoice_number):
    try:
        user_id = user_data.get('user_id')
        print(f"Updating order status for invoice_number: {invoice_number}, user_id: {user_id}")  # Debug statement
        order = find_order_by_invoice(invoice_number)
        if not order or order['user_id'] != user_id:
            print("Unauthorized to update this order")  # Debug statement
            log_action(user_id, "update_order_status_unauthorized", {"invoice_number": invoice_number})
            return jsonify({"message": "Unauthorized to update this order"}), 403

        new_status = request.json.get('status')
        if not new_status:
            print("Status is required")  # Debug statement
            return jsonify({"message": "Status is required"}), 400

        if order['status'] == 'Pending' and new_status == 'In Progress':
            for item in order['cart']:
                valid, message = validate_and_reserve_product_availability(item['id'], item['quantity'])
                if not valid:
                    print(f"Validation failed: {message}")  # Debug statement
                    log_action(user_id, "update_order_status_failed", {"invoice_number": invoice_number, "message": message})
                    return jsonify({"message": message}), 400

            for item in order['cart']:
                reserve_product_quantity(item['id'], item['quantity'])

        elif order['status'] == 'In Progress' and new_status == 'Pending':
            for item in order['cart']:
                release_product_quantity(item['id'], item['quantity'])

        elif new_status == 'Cancelled':
            if order['status'] == 'In Progress':
                for item in order['cart']:
                    release_product_quantity(item['id'], item['quantity'])

        order['status'] = new_status
        with db_lock:
            orders_db.update_one({"invoiceNumber": invoice_number}, {"$set": {"status": new_status}})
        
        if '_id' in order:
            order['_id'] = str(order['_id'])
        
        print(f"Order status updated to {new_status}")  # Debug statement
        log_action(user_id, "update_order_status", {"invoice_number": invoice_number, "new_status": new_status})

        return jsonify(order), 200
    except Exception as e:
        print(f"Error updating order status: {str(e)}")  # Debug statement
        log_action(user_id, "update_order_status_error", {"error": str(e)})
        return jsonify({"message": "Error updating order status", "error": str(e)}), 500

# API to add a note to an order
@orders_bp.route('/orders/<string:invoice_number>/notes', methods=['PATCH'])
@login_required
def add_order_note(user_data, invoice_number):
    try:
        user_id = user_data.get('user_id')
        print(f"Adding note to order with invoice_number: {invoice_number}, user_id: {user_id}")  # Debug statement
        order = find_order_by_invoice(invoice_number)
        
        if not order or order['user_id'] != user_id:
            print("Unauthorized to add note to this order")  # Debug statement
            log_action(user_id, "add_order_note_unauthorized", {"invoice_number": invoice_number})
            return jsonify({"message": "Unauthorized to add note to this order"}), 403

        note = request.json.get('note')
        if not note:
            print("Note is required")  # Debug statement
            return jsonify({"message": "Note is required"}), 400

        with db_lock:
            # Ensure the notes field is a list
            if isinstance(order.get('notes'), str):
                order['notes'] = [order['notes']]
            elif not order.get('notes'):
                order['notes'] = []

            # Append the new note
            order['notes'].append(note)
            
            # Update the order in the database
            orders_db.update_one({"invoiceNumber": invoice_number}, {"$set": {"notes": order['notes']}})
        
        print("Note added to order successfully")  # Debug statement
        log_action(user_id, "add_order_note", {"invoice_number": invoice_number, "note": note})

        if '_id' in order:
            order['_id'] = str(order['_id'])

        return jsonify(order), 200
    except Exception as e:
        print(f"Error adding note to order: {str(e)}")  # Debug statement
        log_action(user_id, "add_order_note_error", {"error": str(e)})
        return jsonify({"message": "Error adding note to order", "error": str(e)}), 500


# API to finalize an order, move it to transactions, and remove it from orders
@orders_bp.route('/orders/<string:invoice_number>/finalize', methods=['POST'])
@login_required
def finalize_order(user_data, invoice_number):
    try:
        user_id = user_data.get('user_id')
        print(f"Finalizing order with invoice_number: {invoice_number}, user_id: {user_id}")  # Debug statement
        order = find_order_by_invoice(invoice_number)

        if not order or order['user_id'] != user_id:
            print("Unauthorized to finalize this order")  # Debug statement
            log_action(user_id, "finalize_order_unauthorized", {"invoice_number": invoice_number})
            return jsonify({"message": "Unauthorized to finalize this order"}), 403

        order['id'] = str(uuid.uuid4())
        order['txn_type'] = 'online sale'
        order['status'] = 'Completed'

        for item in order['cart']:
            product = get_product_by_id(item['id'])
            if product['quantity'] < item['quantity']:
                print(f"Insufficient stock for {product['name']}")  # Debug statement
                log_action(user_id, "finalize_order_insufficient_stock", {"invoice_number": invoice_number, "product_id": item['id']})
                return jsonify({"message": f"Insufficient stock for {product['name']}"}), 400

        for item in order['cart']:
            adjust_product_quantity(item['id'], -item['quantity'])
            release_product_quantity(item['id'], item['quantity'])

        with db_lock:
            transactions_db.insert_one(order)
            orders_db.delete_one({"invoiceNumber": invoice_number})

        print("Order finalized successfully")  # Debug statement
        log_action(user_id, "finalize_order", {"invoice_number": invoice_number})
        return jsonify({"message": "Order finalized successfully"}), 200
    except Exception as e:
        print(f"Error finalizing order: {str(e)}")  # Debug statement
        log_action(user_id, "finalize_order_error", {"error": str(e)})
        return jsonify({"message": "Error finalizing order", "error": str(e)}), 500

# API to get orders by phone number
@orders_bp.route('/orders/byPhone/<string:user_id>/<string:phone>', methods=['GET'])
def get_orders_by_phone(user_id, phone):
    try:
        print(f"Getting orders for phone number: {phone}, user_id: {user_id}")  # Debug statement
        if not phone:
            print("Phone number is required")  # Debug statement
            return jsonify({"message": "Phone number is required"}), 400

        orders = list(orders_db.find({"customerPhone": phone, "user_id": user_id}))

        for order in orders:
            if '_id' in order:
                order['_id'] = str(order['_id'])

        orders.reverse()
        print(f"Orders retrieved by phone: {orders}")  # Debug statement
        log_action(user_id, "get_orders_by_phone", {"phone": phone, "order_count": len(orders)})
        return jsonify(orders), 200
    except Exception as e:
        print(f"Error retrieving orders by phone number: {str(e)}")  # Debug statement
        log_action(user_id, "get_orders_by_phone_error", {"error": str(e)})
        return jsonify({"message": "Error retrieving orders by phone number", "error": str(e)}), 500
