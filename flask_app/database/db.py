from pymongo import MongoClient, ASCENDING
from config import Config

# Initialize MongoDB client with optimized settings
client = MongoClient(Config.MONGO_URI,
                        connectTimeoutMS=30000,
                        socketTimeoutMS=None,
                        connect=False,
                        maxPoolSize=10,  # Increased pool size for better concurrency
                        readPreference='secondaryPreferred'  # Use secondary nodes for read operations in a replica set
                    )

# Access the database
db = client.get_database(Config.MONGO_DBNAME)

# Access MongoDB collections
profile_db = db.get_collection('profiles')
transactions_db = db.get_collection('transactions')
products_db = db.get_collection('products')
users_db = db.get_collection('users')
orders_db = db.get_collection('orders')
settings_db = db.get_collection('settings')
pending_transactions_db = db.get_collection('pending_transactions')
logs_db = db.get_collection('logs')
payment_db = db.get_collection('payment')
sessions_db = db.get_collection('sesaions')

# Define TTL in seconds (e.g., 30 days)
LOG_RETENTION_SECONDS = 30 * 24 * 60 * 60  # 30 days in seconds

# Create a TTL index on the timestamp field of the logs collection
logs_db.create_index([('timestamp', ASCENDING)], expireAfterSeconds=LOG_RETENTION_SECONDS)

# Create additional indexes to improve query performance (optional)
profile_db.create_index([('user_id', ASCENDING)])
transactions_db.create_index([('user_id', ASCENDING)])
products_db.create_index([('id', ASCENDING)])
orders_db.create_index([('user_id', ASCENDING), ('invoiceNumber', ASCENDING)])
