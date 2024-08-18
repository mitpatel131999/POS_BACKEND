import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')
    TINYDB_STORAGE_TABLE= 'storage_table.json'
    TINYDB_PROFILE = 'profile.json'
    TINYDB_TRANSACTIONS = 'transactions.json'
    TINYDB_PRODUCTS = 'products.json'
    TINYDB_USERS = 'users.json'
    TINYDB_ORDERS = 'orders.json'
    TINYDB_SETTINGS = 'db_settings.json'
    TINYDB_PENDING_TRANSACTIONS = 'db_pending_transactions.json'
