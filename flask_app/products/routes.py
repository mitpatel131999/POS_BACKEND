from flask import Blueprint, request, jsonify, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId
from auth.utils import login_required
import threading
import uuid
from datetime import datetime
from config import Config
<<<<<<< HEAD
from database.db import profile_db, transactions_db, products_db, orders_db, settings_db, pending_transactions_db, logs_db, client
from gridfs import GridFS
from PIL import Image
from io import BytesIO
import uuid
import os
=======
from database.db import profile_db, transactions_db, products_db, orders_db, settings_db, pending_transactions_db, logs_db
from gridfs import GridFS
from PIL import Image
from io import BytesIO
>>>>>>> 19868571793498183aaf34bda9e40a1cc87d74e4

# Lock to handle multi-threaded operations
db_lock = threading.Lock()

products_bp = Blueprint('products', __name__)

# Initialize GridFS for image storage
fs = GridFS(products_db.database)

# Maximum image size (width, height)
MAX_IMAGE_SIZE = (800, 800)  # 800x800 pixels

<<<<<<< HEAD
IMAGE_DATA_DIR = 'image_data'
os.makedirs(IMAGE_DATA_DIR, exist_ok=True)

def save_image_data(image_data):
    # Generate a unique token for the image
    token = str(uuid.uuid4())
    image_path = os.path.join(IMAGE_DATA_DIR, f"{token}.txt")

    # Save the image data to a file
    with open(image_path, 'w') as f:
        f.write(image_data)

    return token  # Return the token for storing in MongoDB


=======
>>>>>>> 19868571793498183aaf34bda9e40a1cc87d74e4
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

# New function to handle image upload, resizing, and storage
<<<<<<< HEAD
@products_bp.route('/products/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        print('1')
        return jsonify({'message': 'No file part'}), 400
    print('2')
    file = request.files['file']
    if file.filename == '':
        print('3')
        return jsonify({'message': 'No selected file'}), 400

    print(' got the image')
     
    try:
        # Open and process the image
        image = Image.open(file)
        img_byte_arr = BytesIO()
        image.convert('RGB').save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        # Store image in GridFS
        with db_lock:
            with client.start_session() as session:
                file_id = fs.put(img_byte_arr, content_type='image/jpeg', filename=file.filename)
        print('Image stored successfully.')

        # Generate image URL
        file_url = f"/products/image/{file_id}"
        print('Generated file URL:', file_url)

        return jsonify({'url': file_url, 'file_id': str(file_id)}), 200
    except Exception as e:
        print('Error processing image:', e)
        return jsonify({"error": "Failed to process and store image"}), 500

    '''
    # Open the image and resize it
    image = Image.open(file)
    image.thumbnail(MAX_IMAGE_SIZE)  # Resize image to fit within MAX_IMAGE_SIZE
    
    print('4')
=======
@products_bp.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    # Open the image and resize it
    image = Image.open(file)
    image.thumbnail(MAX_IMAGE_SIZE)  # Resize image to fit within MAX_IMAGE_SIZE

>>>>>>> 19868571793498183aaf34bda9e40a1cc87d74e4
    # Convert image to binary
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()

    # Store image in GridFS
    file_id = fs.put(img_byte_arr, content_type='image/jpeg', filename=file.filename)
<<<<<<< HEAD
    print(' store the image')

    # Generate the image URL
    file_url = f"/products/image/{file_id}" 
    print(file_url)

    return jsonify({'url': file_url, 'file_id': str(file_id)}), 200
    '''

# Endpoint to serve images from GridFS
@products_bp.route('/products/image/<file_id>', methods=['GET'])
def get_image(file_id):
    try:
        file_data = fs.get(ObjectId(file_id))
        print(' load image return')
=======

    # Generate the image URL
    file_url = f"/products/image/{file_id}"

    return jsonify({'url': file_url, 'file_id': str(file_id)}), 200

# Endpoint to serve images from GridFS
@products_bp.route('/image/<file_id>', methods=['GET'])
def get_image(file_id):
    try:
        file_data = fs.get(ObjectId(file_id))
>>>>>>> 19868571793498183aaf34bda9e40a1cc87d74e4
        return send_file(BytesIO(file_data.read()), mimetype=file_data.content_type)
    except Exception as e:
        return jsonify({"message": "Error retrieving image", "error": str(e)}), 500

@products_bp.route('/online-products/<string:user_id>', methods=['GET'])
def get_online_products(user_id):
    print('GET /online-products called')  # Debug statement
    try:
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400
        
        products = list(products_db.find({"user_id": user_id}))
        
        for product in products:
            product['_id'] = str(product['_id'])
        
        print('Products retrieved:', products)  # Debug statement
        log_action(user_id, "get_online_products", {"product_count": len(products)})
        return jsonify(products), 200
    except Exception as e:
        print('Error retrieving products:', str(e))  # Debug statement
        log_action(user_id, "get_online_products_error", {"error": str(e)})
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
        
        for product in products:
            product['_id'] = str(product['_id'])
<<<<<<< HEAD
            '''
            # Replace tokens with actual image data
            for image_key in ['frontImage', 'backImage']:
                token = product.get(image_key)
                if token:
                    image_path = os.path.join(IMAGE_DATA_DIR, f"{token}.txt")
                    if os.path.exists(image_path):
                        with open(image_path, 'r') as f:
                            product[image_key] = f.read()  # Replace token with base64 data
            '''
=======
>>>>>>> 19868571793498183aaf34bda9e40a1cc87d74e4
        
        print('Products retrieved:', products)  # Debug statement
        log_action(user_id, "get_products", {"product_count": len(products)})
        return jsonify(products), 200
    except Exception as e:
        print('Error retrieving products:', str(e))  # Debug statement
        log_action(user_id, "get_products_error", {"error": str(e)})
        return jsonify({"message": "Error retrieving products"}), 500

<<<<<<< HEAD
@products_bp.route('/products/<int:product_id>', methods=['GET'])
@login_required
def get_product_by_id(user_data, product_id):
    print(f'GET /products/{product_id} called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400

        

        # Fetch the product by ID
        product = products_db.find_one({"id": int(product_id), "user_id": user_id})

        if not product:
            return jsonify({"message": "Product not found"}), 404

        # Convert ObjectId to string for JSON serialization
        product['_id'] = str(product['_id'])

        # Replace tokens with actual image data (uncomment if needed)
        '''
        for image_key in ['frontImage', 'backImage']:
            token = product.get(image_key)
            if token:
                image_path = os.path.join(IMAGE_DATA_DIR, f"{token}.txt")
                if os.path.exists(image_path):
                    with open(image_path, 'r') as f:
                        product[image_key] = f.read()  # Replace token with base64 data
        '''

        print('Product retrieved:', product)  # Debug statement
        log_action(user_id, "get_product_by_id", {"id": product_id})
        return jsonify(product), 200
    except Exception as e:
        print(f'Error retrieving product {product_id}:', str(e))  # Debug statement
        log_action(user_id, "get_product_by_id_error", {"error": str(e), "id": product_id})
        return jsonify({"message": "Error retrieving product"}), 500

@products_bp.route('/products/paginated', methods=['GET'])
@login_required
def get_paginated_products(user_data):
    print('GET /products/paginated called')  # Debug statement
    try:
        user_id = user_data.get('user_id')
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400
        
        # Extract pagination parameters
        page = int(request.args.get('page', 1))  # Default to page 1
        page_size = int(request.args.get('pageSize', 400))  # Default page size of 400
        
        # Validate pagination inputs
        if page < 1 or page_size < 1:
            return jsonify({"message": "Page and pageSize must be greater than 0"}), 400

        # Calculate the number of documents to skip
        skip = (page - 1) * page_size

        # Fetch paginated products from the database
        with db_lock:
            products_cursor = products_db.find({"user_id": user_id}).skip(skip).limit(page_size)
            products = list(products_cursor)

        # Convert ObjectId to string and handle additional processing
        for product in products:
            product['_id'] = str(product['_id'])

        # Fetch total count of products for the user
        total_count = products_db.count_documents({"user_id": user_id})
        total_pages = (total_count + page_size - 1) // page_size  # Calculate total pages
        
        print(f'Retrieved {len(products)} products for page {page}')  # Debug statement
        log_action(user_id, "get_paginated_products", {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
        })

        # Return the paginated response
        return jsonify({
            "products": products,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages

        }), 200
    except Exception as e:
        print('Error retrieving paginated products:', str(e))  # Debug statement
        log_action(user_data.get('user_id'), "get_paginated_products_error", {"error": str(e)})
        return jsonify({"message": "Error retrieving products", "error": str(e)}), 500


=======
>>>>>>> 19868571793498183aaf34bda9e40a1cc87d74e4
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
        
<<<<<<< HEAD
        '''
        # Replace image data with tokens and save image data to local storage
        if 'frontImage' in product_data:
            front_image_data = product_data.pop('frontImage')
            product_data['frontImage'] = save_image_data(front_image_data)
        if 'backImage' in product_data:
            back_image_data = product_data.pop('backImage')
            product_data['backImage'] = save_image_data(back_image_data)
        '''
=======
>>>>>>> 19868571793498183aaf34bda9e40a1cc87d74e4
        # Insert the product into the database
        insert_result = products_db.insert_one(product_data)
        
        print('Product created with ID:', product_data['product_id'], "user ID", user_id)  # Debug statement
        log_action(user_id, "create_product", product_data)
        if '_id' in product_data:
            del product_data['_id']
        return jsonify(product_data), 200
    except Exception as e:
        print('Error creating product:', str(e))  # Debug statement
        log_action(user_id, "create_product_error", {"error": str(e)})
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
            log_action(user_id, "update_product_unauthorized", {"product_id": product_id})
            return jsonify({"message": "Unauthorized to update this product"}), 403

        product_data = request.json
        print('Product data to update:', product_data)  # Debug statement
<<<<<<< HEAD
       
        # Retrieve the existing product from the database to check for old image tokens
        with db_lock:
            with client.start_session() as session:
                existing_product = products_db.find_one({"product_id": product_id}, session=session)
       
        '''
        # Replace image data with tokens and save image data to local storage
        if 'frontImage' in product_data:
            # Delete the old frontImage data if it exists
            if existing_product and 'frontImage' in existing_product:
                delete_image_data(existing_product['frontImage'])

            # Save new frontImage and update with new token
            front_image_data = product_data.pop('frontImage')
            product_data['frontImage'] = save_image_data(front_image_data)

        if 'backImage' in product_data:
            # Delete the old backImage data if it exists
            if existing_product and 'backImage' in existing_product:
                delete_image_data(existing_product['backImage'])

            # Save new backImage and update with new token
            back_image_data = product_data.pop('backImage')
            product_data['backImage'] = save_image_data(back_image_data)
        '''
        if '_id' in product_data:
            del product_data['_id']
        with db_lock:
            products_db.update_one({"id": int(product_id)}, {"$set": product_data})
=======
        
        if '_id' in product_data:
            del product_data['_id']
        products_db.update_one({"id": int(product_id)}, {"$set": product_data})
>>>>>>> 19868571793498183aaf34bda9e40a1cc87d74e4
        print(f'Product with ID {product_id} updated')  # Debug statement
        log_action(user_id, "update_product", product_data)
        return jsonify({"message": "Product updated successfully"}), 200
    except Exception as e:
        print(f'Error updating product with ID {product_id}:', str(e))  # Debug statement
        log_action(user_id, "update_product_error", {"error": str(e)})
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
            log_action(user_id, "delete_product_unauthorized", {"product_id": product_id})
            return jsonify({"message": "Unauthorized to delete this product"}), 403

        products_db.delete_one({"id": int(product_id)})
        print(f'Product with ID {product_id} deleted')  # Debug statement
        log_action(user_id, "delete_product", {"product_id": product_id})
        return jsonify({"message": "Product deleted successfully"}), 200
    except Exception as e:
        print(f'Error deleting product with ID {product_id}:', str(e))  # Debug statement
        log_action(user_id, "delete_product_error", {"error": str(e)})
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
            log_action(user_id, "increase_product_quantity_unauthorized", {"product_id": product_id})
            return jsonify({"message": "Unauthorized to modify this product"}), 403

        data = request.json
        amount = data.get('amount', 0)
        print(f'Increase amount: {amount} for product ID {product_id}')  # Debug statement

        product = products_db.find_one({"id": int(product_id)})
        
        if product:
            new_quantity = product.get('quantity', 0) + amount
            products_db.update_one({"product_id": product_id}, {"$set": {"quantity": new_quantity}})
            print(f'Product quantity increased to {new_quantity} for product ID {product_id}')  # Debug statement
            log_action(user_id, "increase_product_quantity", {"product_id": product_id, "new_quantity": new_quantity})
            return jsonify({"message": "Product quantity increased", "new_quantity": new_quantity}), 200
        else:
            print(f'Product with ID {product_id} not found')  # Debug statement
            return jsonify({"message": "Product not found"}), 404
    except Exception as e:
        print(f'Error increasing quantity for product ID {product_id}:', str(e))  # Debug statement
        log_action(user_id, "increase_product_quantity_error", {"error": str(e)})
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
            log_action(user_id, "decrease_product_quantity_unauthorized", {"product_id": product_id})
            return jsonify({"message": "Unauthorized to modify this product"}), 403

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
            log_action(user_id, "decrease_product_quantity", {"product_id": product_id, "new_quantity": new_quantity})
            return jsonify({"message": "Product quantity decreased", "new_quantity": new_quantity}), 200
        else:
            print(f'Product with ID {product_id} not found')  # Debug statement
            return jsonify({"message": "Product not found"}), 404
    except Exception as e:
        print(f'Error decreasing quantity for product ID {product_id}:', str(e))  # Debug statement
        log_action(user_id, "decrease_product_quantity_error", {"error": str(e)})
<<<<<<< HEAD
        return jsonify({"message": "Error decreasing product quantity"}), 500
=======
        return jsonify({"message": "Error decreasing product quantity"}), 500
>>>>>>> 19868571793498183aaf34bda9e40a1cc87d74e4
