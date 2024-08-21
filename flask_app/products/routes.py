from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from auth.utils import login_required
import threading
import uuid
from config import Config

# Initialize MongoDB client and database
client = MongoClient(Config.MONGO_URI)
db = client[Config.MONGO_DBNAME]
products_db = db['products']

# Lock to handle multi-threaded operations
db_lock = threading.Lock()

products_bp = Blueprint('products', __name__)

# Utility function to check if the user owns the product
def check_ownership(user_id, product_id):
    print(f"Checking ownership for product_id: {product_id}, {type(product_id)} and user_id: {user_id}")  # Debug statement
    product = products_db.find_one({"id": int(product_id)})
    if not product:
        print("Product not found")  # Debug statement
        return False
    
    ownership = product.get('user_id') == user_id
    print(f"Ownership check result: {ownership}")  # Debug statement
    return ownership

@products_bp.route('/online-products/<string:user_id>', methods=['GET'])
def get_online_products(user_id):
    print('GET /online-products called')  # Debug statement
    try:
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400
        
        products = list(products_db.find({"user_id": user_id}))
        
        # Convert ObjectId to string for all products
        for product in products:
            product['_id'] = str(product['_id'])
        
        print('Products retrieved:', products)  # Debug statement
        return jsonify(products), 200
    except Exception as e:
        print('Error retrieving products:', str(e))  # Debug statement
        return jsonify({"message": "Error retrieving products"}), 500

@products_bp.route('/products', methods=['GET'])
@login_required
def get_products(user_data):
    print('GET /products called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400
        
        products = list(products_db.find({"user_id": user_id}))
        
        # Convert ObjectId to string for all products
        for product in products:
            product['_id'] = str(product['_id'])
        
        print('Products retrieved:', products)  # Debug statement
        return jsonify(products), 200
    except Exception as e:
        print('Error retrieving products:', str(e))  # Debug statement
        return jsonify({"message": "Error retrieving products"}), 500

@products_bp.route('/products', methods=['POST'])
@login_required
def create_product(user_data):
    print('POST /products called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not user_id:
            return jsonify({"message": "User ID is required to create a product"}), 400
        
        product_data = request.json
        print('Product data received:', product_data)  # Debug statement
        product_data['product_id'] = str(uuid.uuid4())  # Generate a unique product_id
        product_data['user_id'] = user_id  # Associate product with the user
        product_data['reserved_quantity'] = 0
        
        # Insert the product into the database
        insert_result = products_db.insert_one(product_data)
        
        # Convert ObjectId to string before returning
        #product_data['_id'] = str(insert_result.inserted_id)
        
        print('Product created with ID:', product_data['product_id'], "user ID", user_id)  # Debug statement
        return jsonify(product_data), 200
    except Exception as e:
        print('Error creating product:', str(e))  # Debug statement
        return jsonify({"message": "Error creating product"}), 500

@products_bp.route('/products/<string:product_id>', methods=['PUT'])
@login_required
def update_product(user_data, product_id):
    print(f'PUT /products/{product_id} called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400
        
        if not check_ownership(user_id, product_id):
            return jsonify({"message": "Unauthorized to update this product"}), 403

        product_data = request.json
        print('Product data to update:', product_data)  # Debug statement
        
        if '_id' in product_data:
            del product_data['_id']
        # Update only specified fields, preserving the original document's structure
        products_db.update_one({"id": int(product_id)}, {"$set": product_data})
        print(f'Product with ID {product_id} updated')  # Debug statement
        return jsonify({"message": "Product updated successfully"}), 200
    except Exception as e:
        print(f'Error updating product with ID {product_id}:', str(e))  # Debug statement
        return jsonify({"message": "Error updating product"}), 500

@products_bp.route('/products/<string:product_id>', methods=['DELETE'])
@login_required
def delete_product(user_data, product_id):
    print(f'DELETE /products/{product_id} called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400
        
        if not check_ownership(user_id, product_id):
            return jsonify({"message": "Unauthorized to delete this product"}), 403

        

        products_db.delete_one({"id": int(product_id)})
        print(f'Product with ID {product_id} deleted')  # Debug statement
        return jsonify({"message": "Product deleted successfully"}), 200
    except Exception as e:
        print(f'Error deleting product with ID {product_id}:', str(e))  # Debug statement
        return jsonify({"message": "Error deleting product"}), 500

@products_bp.route('/products/<string:product_id>/increase', methods=['PATCH'])
@login_required
def increase_product_quantity(user_data, product_id):
    print(f'PATCH /products/{product_id}/increase called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400
        
        if not check_ownership(user_id, product_id):
            return jsonify({"message": "Unauthorized to modify this product"}), 403

        data = request.json
        amount = data.get('amount', 0)
        print(f'Increase amount: {amount} for product ID {product_id}')  # Debug statement
        if '_id' in product_data:
            del product_data['_id']

        product = products_db.find_one({"id": int(product_id)})
        
        if product:
            new_quantity = product.get('quantity', 0) + amount
            products_db.update_one({"product_id": product_id}, {"$set": {"quantity": new_quantity}})
            print(f'Product quantity increased to {new_quantity} for product ID {product_id}')  # Debug statement
            return jsonify({"message": "Product quantity increased", "new_quantity": new_quantity}), 200
        else:
            print(f'Product with ID {product_id} not found')  # Debug statement
            return jsonify({"message": "Product not found"}), 404
    except Exception as e:
        print(f'Error increasing quantity for product ID {product_id}:', str(e))  # Debug statement
        return jsonify({"message": "Error increasing product quantity"}), 500

@products_bp.route('/products/<string:product_id>/decrease', methods=['PATCH'])
@login_required
def decrease_product_quantity(user_data, product_id):
    print(f'PATCH /products/{product_id}/decrease called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400
        
        if not check_ownership(user_id, product_id):
            return jsonify({"message": "Unauthorized to modify this product"}), 403

        if '_id' in product_data:
            del product_data['_id']

        data = request.json
        amount = data.get('amount', 0)
        print(f'Decrease amount: {amount} for product ID {product_id}')  # Debug statement
        
        product = products_db.find_one({"product_id": product_id})
        
        if product:
            current_quantity = product.get('quantity', 0)
            if current_quantity < amount:
                print(f'Insufficient stock for product ID {product_id}')  # Debug statement
                return jsonify({"message": "Insufficient stock"}), 400
            
            new_quantity = current_quantity - amount
            products_db.update_one({"id": int(product_id)}, {"$set": {"quantity": new_quantity}})
            print(f'Product quantity decreased to {new_quantity} for product ID {product_id}')  # Debug statement
            return jsonify({"message": "Product quantity decreased", "new_quantity": new_quantity}), 200
        else:
            print(f'Product with ID {product_id} not found')  # Debug statement
            return jsonify({"message": "Product not found"}), 404
    except Exception as e:
        print(f'Error decreasing quantity for product ID {product_id}:', str(e))  # Debug statement
        return jsonify({"message": "Error decreasing product quantity"}), 500
