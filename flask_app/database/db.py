

from pymongo import MongoClient, ASCENDING
from config import Config
from threading import Thread
from bson import ObjectId


#from flask_app.app import app


# Initialize MongoDB client with optimized settings

# MongoDB Client Initialization
try:
    client = MongoClient(
        Config.MONGO_URI,
        connectTimeoutMS=30000,
        maxPoolSize=10,
        readPreference='secondaryPreferred'  # Prefer primary for simplicity during debugging
    )
    db = client.get_database(Config.MONGO_DBNAME)
    print("Connected to MongoDB successfully.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    raise


# Access the database
db = client.get_database(Config.MONGO_DBNAME)

# Access MongoDB collections
users_db = db.get_collection('users')
profile_db = db.get_collection('profiles')
transactions_db = db.get_collection('transactions')
products_db = db.get_collection('products')
offers_db = db.get_collection('offers')
suppliers_db = db.get_collection('suppliers')
purchase_orders_db = db.get_collection('purchase_orders')
orders_db = db.get_collection('orders')
settings_db = db.get_collection('settings')
pending_transactions_db = db.get_collection('pending_transactions')
logs_db = db.get_collection('logs')
payment_db = db.get_collection('payment')
sessions_db = db.get_collection('sessions')
purchase_orders_db = db.get_collection('purchase_orders')  # Added purchase orders
customers_db = db.get_collection('customers')  # Added customers

# Define TTL in seconds (e.g., 30 days)
LOG_RETENTION_SECONDS = 30 * 24 * 60 * 60  # 30 days in seconds

# Create a TTL index on the timestamp field of the logs collection
#logs_db.create_index([('timestamp', ASCENDING)], expireAfterSeconds=LOG_RETENTION_SECONDS)



# Create additional indexes to improve query performance (optional)
profile_db.create_index([('user_id', ASCENDING)])
transactions_db.create_index([('user_id', ASCENDING)])
products_db.create_index([('id', ASCENDING)])
offers_db.create_index([('id', ASCENDING)])
orders_db.create_index([('user_id', ASCENDING), ('invoiceNumber', ASCENDING)])
purchase_orders_db.create_index([('purchaseOrderId', ASCENDING)])  # Index for purchase orders
customers_db.create_index([('customer_id', ASCENDING)])  # Index for customers


def initialize_db():
    """Initialize MongoDB collections."""
    collections = {
        "profiles": db.get_collection('profiles'),
        "transactions": db.get_collection('transactions'),
        "products": db.get_collection('products'),
        "offers": db.get_collection('offers'),
        "suppliers": db.get_collection('suppliers'),
        "orders": db.get_collection('orders'),
        "settings": db.get_collection('settings'),
        "pending_transactions": db.get_collection('pending_transactions'),
        "logs": db.get_collection('logs'),
        "payment": db.get_collection('payment'),
        "sessions": db.get_collection('sessions'),
        "purchase_orders": db.get_collection('purchase_orders'),  # Purchase orders
        "customers": db.get_collection('customers')  # Customers
    }
    return collections


# Define a mapping of collection names to their unique keys
COLLECTION_KEYS = {
    "users": "user_id",
    "profiles": "user_id",
    "transactions": "id",
    "products": "id",  # No specific user_id for products
    "offers": "id",
    "suppliers": "supplier_id",
    "orders": "id",
    "settings": "user_id",
    "pending_transactions": "id",
    "logs": "_id",
    "payment": "_id",
    "sessions": "_id",
    "purchase_orders": "id",
    "customers": "customer_id",
}

def start_change_stream(collection, collection_name, socketio):
    """
    Listens to changes in MongoDB collection and emits object-level updates.
    Emits user-specific events using `user_id` and collection-specific fields.
    """
    unique_key_field = COLLECTION_KEYS.get(collection_name, "_id")  # Default to `_id` if no key specified

    print(f"Starting change stream for {collection_name}")  # Debugging log

    try:
        # Use `fullDocument='updateLookup'` to fetch the full document for updates
        with collection.watch(full_document='updateLookup') as stream:
            for change in stream:
                #print(f"Change detected: {change}")  # Debugging log

                full_document = change.get('fullDocument', {})
                if not full_document:
                    print("No full document available, skipping change")  # Debugging log
                    continue

                user_id = full_document.get("user_id")
                if not user_id:
                    print("No user_id found, skipping change")  # Debugging log
                    continue

                # Ensure '_id' is stringified
                if "_id" in full_document:
                    full_document["_id"] = str(full_document["_id"])
                    print("Key '_id'  found in full_document. \n")
                else:
                    print("Key '_id' not found in full_document.")
                # Convert ObjectId fields to strings
                updated_object = full_document
                
                #full_document['_id'] = str(full_document.get("_id"))

                # Access dictionary key using square bracket notation
                #business_name = full_document.get("businessName", "N/A")  # Default to "N/A" if key not found

                event_name = f'data_updated_{collection_name}_{user_id}'
                print(f"Emitting event {event_name} for user_id: {user_id}  {type(updated_object)}")  # Debugging log

                socketio.emit(event_name, {
                    'collection': collection_name,
                    'user_id': user_id,
                    'updated_object': updated_object,
                })
    except Exception as e:
        print(f"Error in change stream for {collection_name}: {e}")



def start_change_streams(socketio, collections):
    """Start change streams for all collections."""
    for name, collection in collections.items():
        thread = Thread(target=start_change_stream, args=(collection, name, socketio))
        thread.daemon = True
        thread.start()



database = initialize_db()
#start_change_streams(socketio, database)
