from pymongo import MongoClient
from config import Config

# Initialize MongoDB client
client = MongoClient(Config.MONGO_URI,
                        connectTimeoutMS=30000,
                        socketTimeoutMS=None,
                        connect=False,
                        maxPoolSize=1)
db = client[Config.MONGO_DBNAME]

# Access MongoDB collections
profile_db = db['profiles']
transactions_db = db['transactions']
products_db = db['products']
users_db = db['users']
orders_db = db['orders']
settings_db = db['settings']
pending_transactions_db = db['pending_transactions']


