from flask import Blueprint, request, jsonify
from database.db import orders_db, transactions_db  # Assuming you have an orders and transactions database
import uuid
from tinydb import Query
from auth.utils import login_required
import threading

# Lock to handle TinyDB's single-threaded nature
db_lock = threading.Lock()

orders_bp = Blueprint('orders', __name__)

# Utility function to find order by invoice number
def find_order_by_invoice(invoice_number):
    with db_lock:
        Orders = Query()
        order = orders_db.get(Orders.invoiceNumber == invoice_number)
    return order

# Utility function to check if the user owns the order
def check_ownership(user_id, order_id):
    with db_lock:
        Orders = Query()
        order = orders_db.get(Orders.id == order_id)
    return order and order.get('user_id') == user_id

# API to get all orders (Assuming it's for admin usage or with ownership enforcement)
@orders_bp.route('/orders', methods=['GET'])
@login_required
def get_orders(user_data):
    try:
        user_id = user_data.get('user_id')
        with db_lock:
            Orders = Query()
            orders = orders_db.search(Orders.user_id == user_id)  # Retrieve only orders belonging to the user
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({"message": "Error retrieving orders", "error": str(e)}), 500

# API to create a new order (No login required, but user_id must be in the request)
@orders_bp.route('/orders/<string:user_id>', methods=['POST'])
def create_order(user_id):
    try:
        order_data = request.json
        
        if not user_id:
            return jsonify({"message": "User ID is required in the header"}), 400

        order_data['id'] = str(uuid.uuid4())  # Generate a unique ID for the order
        order_data['user_id'] = user_id  # Associate order with the user
        with db_lock:
            orders_db.insert(order_data)
        return jsonify(order_data), 201
    except Exception as e:
        return jsonify({"message": "Error creating order", "error": str(e)}), 500

# API to delete an order by ID (Ownership enforced)
@orders_bp.route('/orders/<string:order_id>', methods=['DELETE'])
@login_required
def delete_order(user_data, order_id):
    try:
        user_id = user_data.get('user_id')
        if not check_ownership(user_id, order_id):
            return jsonify({"message": "Unauthorized to delete this order"}), 403

        with db_lock:
            Orders = Query()
            orders_db.remove(Orders.id == order_id)
        return jsonify({"message": "Order deleted successfully"}), 200
    except Exception as e:
        return jsonify({"message": "Error deleting order", "error": str(e)}), 500

# API to update the status of an order (Ownership enforced)
@orders_bp.route('/orders/<string:invoice_number>/status', methods=['PATCH'])
@login_required
def update_order_status(user_data, invoice_number):
    try:
        user_id = user_data.get('user_id')
        order = find_order_by_invoice(invoice_number)
        if not order or order['user_id'] != user_id:
            return jsonify({"message": "Unauthorized to update this order"}), 403

        new_status = request.json.get('status')
        if not new_status:
            return jsonify({"message": "Status is required"}), 400

        with db_lock:
            order['status'] = new_status
            orders_db.update(order, Query().invoiceNumber == invoice_number)

        return jsonify(order), 200
    except Exception as e:
        return jsonify({"message": "Error updating order status", "error": str(e)}), 500

# API to add a note to an order (Ownership enforced)
@orders_bp.route('/orders/<string:invoice_number>/notes', methods=['PATCH'])
@login_required
def add_order_note(user_data, invoice_number):
    try:
        user_id = user_data.get('user_id')
        order = find_order_by_invoice(invoice_number)
        if not order or order['user_id'] != user_id:
            return jsonify({"message": "Unauthorized to add note to this order"}), 403

        note = request.json.get('note')
        if not note:
            return jsonify({"message": "Note is required"}), 400

        with db_lock:
            if 'notes' not in order:
                order['notes'] = []
            order['notes'].append(note)
            orders_db.update(order, Query().invoiceNumber == invoice_number)

        return jsonify(order), 200
    except Exception as e:
        return jsonify({"message": "Error adding note to order", "error": str(e)}), 500

# API to finalize an order, move it to transactions, and remove it from orders (Ownership enforced)
@orders_bp.route('/orders/<string:invoice_number>/finalize', methods=['POST'])
@login_required
def finalize_order(user_data, invoice_number):
    try:
        user_id = user_data.get('user_id')
        order = find_order_by_invoice(invoice_number)
        
        if not order or order['user_id'] != user_id:
            return jsonify({"message": "Unauthorized to finalize this order"}), 403

        # Assign the user ID to the transaction
        order['user_id'] = user_id
        
        # Generate a new unique ID for the transaction to avoid conflicts
        order['id'] = str(uuid.uuid4())
        
        # Debug statement to check the order data before inserting
        print("Finalizing order with new ID:", order)
        
        with db_lock:
            # Insert the order into the transactions database (finalizing the order)
            insert_result = transactions_db.insert(order)
        
            # Check if the insert was successful
            if not insert_result:
                print("Failed to insert order into transactions_db")
                return jsonify({"message": "Failed to finalize order"}), 500
            
            # Remove the order from the orders database
            orders_db.remove(Query().invoiceNumber == invoice_number)

        return jsonify({"message": "Order finalized successfully"}), 200
    except Exception as e:
        print("Error finalizing order:", str(e))
        return jsonify({"message": "Error finalizing order", "error": str(e)}), 500

# API to get orders by phone number (Ownership enforced)
@orders_bp.route('/orders/byPhone/<string:user_id>/<string:phone>', methods=['GET'])
def get_orders_by_phone(user_id, phone):
    try:
        if not phone:
            return jsonify({"message": "Phone number is required"}), 400
        
        with db_lock:
            Orders = Query()
            orders = orders_db.search((Orders.customerPhone == phone) & (Orders.user_id == user_id))
        
        # Reverse the order as per the original function
        orders.reverse()
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({"message": "Error retrieving orders by phone number", "error": str(e)}), 500
