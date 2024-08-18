from tinydb import TinyDB
from config import Config


profile_db = TinyDB(Config.TINYDB_PROFILE)
transactions_db = TinyDB(Config.TINYDB_TRANSACTIONS)
products_db = TinyDB(Config.TINYDB_PRODUCTS)
users_db = TinyDB(Config.TINYDB_USERS)
orders_db = TinyDB(Config.TINYDB_ORDERS)
settings_db = TinyDB(Config.TINYDB_SETTINGS)  # Add settings_db
pending_transactions_db = TinyDB(Config.TINYDB_PENDING_TRANSACTIONS)  # Add pending_transactions_db

