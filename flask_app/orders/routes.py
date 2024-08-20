from flask import Blueprint, request, jsonify
from database.db import orders_db, transactions_db, products_db  # Assuming you have orders, transactions, and products databases
import uuid
from tinydb import Query
from auth.utils import login_required
import threading

# Lock to handle TinyDB's single-threaded nature
db_lock = threading.Lock()

orders_bp = Blueprint('orders', __name__)

# Utility function to find order by invoice number
def find_order_by_invoice(invoice_number):
    print(f"Finding order with invoice number: {invoice_number}")  # Debug statement
    Orders = Query()
    with db_lock:
        order = orders_db.get(Orders.invoiceNumber == invoice_number)
    print(f"Order found: {order}")  # Debug statement
    return order

# Utility function to check if the user owns the order
def check_ownership(user_id, order_id):
    print(f"Checking ownership for user_id: {user_id} and order_id: {order_id}")  # Debug statement
    Orders = Query()
    with db_lock:
        order = orders_db.get(Orders.id == order_id)
    ownership = order and order.get('user_id') == user_id
    print(f"Ownership check result: {ownership}")  # Debug statement
    return ownership

# Utility function to get a product by its ID
def get_product_by_id(product_id):
    print(f"Getting product with ID: {product_id}")  # Debug statement
    Product = Query()
    with db_lock:
        product = products_db.get(Product.id == product_id)
    print(f"Product found: {product}")  # Debug statement
    return product

# Utility function to update a product
def update_product(product):
    print(f"Updating product with ID: {product['id']}")  # Debug statement
    Product = Query()
    with db_lock:
        products_db.update(product, Product.id == product['id'])
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
        product['reserved_quantity'] += quantity
        update_product(product)
    print("Product quantity reserved successfully")  # Debug statement
    return product

def release_product_quantity(product_id, quantity):
    print(f"Releasing reserved quantity: {quantity} for product_id: {product_id}")  # Debug statement
    product = get_product_by_id(product_id)
    if product:
        product['reserved_quantity'] -= quantity
        update_product(product)
    print("Product quantity released successfully")  # Debug statement
    return product

def adjust_product_quantity(product_id, quantity):
    print(f"Adjusting quantity: {quantity} for product_id: {product_id}")  # Debug statement
    product = get_product_by_id(product_id)
    if product:
        product['quantity'] += quantity
        update_product(product)
    print("Product quantity adjusted successfully")  # Debug statement
    return product

# API to get all orders (Assuming it's for admin usage or with ownership enforcement)
@orders_bp.route('/orders', methods=['GET'])
@login_required
def get_orders(user_data):
    try:
        user_id = user_data.get('user_id')
        print(f"Getting orders for user_id: {user_id}")  # Debug statement
        Orders = Query()
        with db_lock:
            orders = orders_db.search(Orders.user_id == user_id)  # Retrieve only orders belonging to the user
        print(f"Orders retrieved: {orders}")  # Debug statement
        return jsonify(orders), 200
    except Exception as e:
        print(f"Error retrieving orders: {str(e)}")  # Debug statement
        return jsonify({"message": "Error retrieving orders", "error": str(e)}), 500

# API to create a new order (No login required, but user_id must be in the request)
@orders_bp.route('/orders/<string:user_id>', methods=['POST'])
def create_order(user_id):
    try:
        order_data = request.json
        print(f"Creating order for user_id: {user_id}, order_data: {order_data}")  # Debug statement

        if not user_id:
            print("User ID is required in the header")  # Debug statement
            return jsonify({"message": "User ID is required in the header"}), 400

        order_data['id'] = str(uuid.uuid4())  # Generate a unique ID for the order
        order_data['user_id'] = user_id  # Associate order with the user
        order_data['status'] = 'Pending'  # Default status is Pending

        with db_lock:
            orders_db.insert(order_data)
        print("Order created successfully")  # Debug statement
        return jsonify(order_data), 201
    except Exception as e:
        print(f"Error creating order: {str(e)}")  # Debug statement
        return jsonify({"message": "Error creating order", "error": str(e)}), 500

# API to delete an order by ID (Ownership enforced)
@orders_bp.route('/orders/<string:order_id>', methods=['DELETE'])
@login_required
def delete_order(user_data, order_id):
    try:
        user_id = user_data.get('user_id')
        print(f"Deleting order with order_id: {order_id}, user_id: {user_id}")  # Debug statement
        if not check_ownership(user_id, order_id):
            print("Unauthorized to delete this order")  # Debug statement
            return jsonify({"message": "Unauthorized to delete this order"}), 403

        Orders = Query()
        with db_lock:
            orders_db.remove(Orders.id == order_id)
        print("Order deleted successfully")  # Debug statement
        return jsonify({"message": "Order deleted successfully"}), 200
    except Exception as e:
        print(f"Error deleting order: {str(e)}")  # Debug statement
        return jsonify({"message": "Error deleting order", "error": str(e)}), 500

# API to update the status of an order (Ownership enforced)
@orders_bp.route('/orders/<string:invoice_number>/status', methods=['PATCH'])
@login_required
def update_order_status(user_data, invoice_number):
    try:
        user_id = user_data.get('user_id')
        print(f"Updating order status for invoice_number: {invoice_number}, user_id: {user_id}")  # Debug statement
        order = find_order_by_invoice(invoice_number)
        if not order or order['user_id'] != user_id:
            print("Unauthorized to update this order")  # Debug statement
            return jsonify({"message": "Unauthorized to update this order"}), 403

        new_status = request.json.get('status')
        if not new_status:
            print("Status is required")  # Debug statement
            return jsonify({"message": "Status is required"}), 400

        # Validate and reserve quantities in one operation
        if order['status'] == 'Pending' and new_status == 'In Progress':
            for item in order['cart']:
                valid, message = validate_and_reserve_product_availability(item['id'], item['quantity'])
                if not valid:
                    print(f"Validation failed: {message}")  # Debug statement
                    return jsonify({"message": message}), 400

            # If all products are validated, reserve them
            for item in order['cart']:
                reserve_product_quantity(item['id'], item['quantity'])

        elif order['status'] == 'In Progress' and new_status == 'Pending':
            # Release reserved quantities
            for item in order['cart']:
                release_product_quantity(item['id'], item['quantity'])

        elif new_status == 'Cancelled':
            if order['status'] == 'In Progress':
                # Release reserved quantities
                for item in order['cart']:
                    release_product_quantity(item['id'], item['quantity'])

        order['status'] = new_status
        with db_lock:
            orders_db.update(order, Query().invoiceNumber == invoice_number)
        print(f"Order status updated to {new_status}")  # Debug statement

        return jsonify(order), 200
    except Exception as e:
        print(f"Error updating order status: {str(e)}")  # Debug statement
        return jsonify({"message": "Error updating order status", "error": str(e)}), 500

# API to add a note to an order (Ownership enforced)
@orders_bp.route('/orders/<string:invoice_number>/notes', methods=['PATCH'])
@login_required
def add_order_note(user_data, invoice_number):
    try:
        user_id = user_data.get('user_id')
        print(f"Adding note to order with invoice_number: {invoice_number}, user_id: {user_id}")  # Debug statement
        order = find_order_by_invoice(invoice_number)
        if not order or order['user_id'] != user_id:
            print("Unauthorized to add note to this order")  # Debug statement
            return jsonify({"message": "Unauthorized to add note to this order"}), 403

        note = request.json.get('note')
        if not note:
            print("Note is required")  # Debug statement
            return jsonify({"message": "Note is required"}), 400

        with db_lock:
            if 'notes' not in order:
                order['notes'] = []
            order['notes'].append(note)
            orders_db.update(order, Query().invoiceNumber == invoice_number)
        print("Note added to order successfully")  # Debug statement

        return jsonify(order), 200
    except Exception as e:
        print(f"Error adding note to order: {str(e)}")  # Debug statement
        return jsonify({"message": "Error adding note to order", "error": str(e)}), 500

# API to finalize an order, move it to transactions, and remove it from orders (Ownership enforced)
@orders_bp.route('/orders/<string:invoice_number>/finalize', methods=['POST'])
@login_required
def finalize_order(user_data, invoice_number):
    try:
        user_id = user_data.get('user_id')
        print(f"Finalizing order with invoice_number: {invoice_number}, user_id: {user_id}")  # Debug statement
        order = find_order_by_invoice(invoice_number)

        if not order or order['user_id'] != user_id:
            print("Unauthorized to finalize this order")  # Debug statement
            return jsonify({"message": "Unauthorized to finalize this order"}), 403

        # Generate a new unique ID for the transaction to avoid conflicts
        order['id'] = str(uuid.uuid4())
        order['txn_type'] = 'online sale'

        # Check if all products in the order have sufficient stock
        for item in order['cart']:
            product = get_product_by_id(item['id'])
            if product['quantity'] < item['quantity']:
                print(f"Insufficient stock for {product['name']}")  # Debug statement
                return jsonify({"message": f"Insufficient stock for {product['name']}"}), 400

        # If all products have sufficient stock, update quantities
        for item in order['cart']:
            adjust_product_quantity(item['id'], -item['quantity'])
            release_product_quantity(item['id'], item['quantity'])  # Release reserved quantities
        order['status'] = 'Complited'

        with db_lock:
            # Insert the order into the transactions database (finalizing the order)
            transactions_db.insert(order)
            # Remove the order from the orders database
            orders_db.remove(Query().invoiceNumber == invoice_number)
        print("Order finalized successfully")  # Debug statement

        return jsonify({"message": "Order finalized successfully"}), 200
    except Exception as e:
        print(f"Error finalizing order: {str(e)}")  # Debug statement
        return jsonify({"message": "Error finalizing order", "error": str(e)}), 500

# API to get orders by phone number (Ownership enforced)
@orders_bp.route('/orders/byPhone/<string:user_id>/<string:phone>', methods=['GET'])
def get_orders_by_phone(user_id, phone):
    try:
        print(f"Getting orders for phone number: {phone}, user_id: {user_id}")  # Debug statement
        if not phone:
            print("Phone number is required")  # Debug statement
            return jsonify({"message": "Phone number is required"}), 400

        Orders = Query()
        with db_lock:
            orders = orders_db.search((Orders.customerPhone == phone) & (Orders.user_id == user_id))

        # Reverse the order as per the original function
        orders.reverse()
        print(f"Orders retrieved by phone: {orders}")  # Debug statement
        return jsonify(orders), 200
    except Exception as e:
        print(f"Error retrieving orders by phone number: {str(e)}")  # Debug statement
        return jsonify({"message": "Error retrieving orders by phone number", "error": str(e)}), 500
