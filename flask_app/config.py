from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus
import os

class Config:
    # Secret key for your Flask app
    SECRET_KEY = os.urandom(24)  # Generates a random 24-byte secret key

    # MongoDB connection details
    MONGO_USERNAME = 'mitpatelr1999'
    MONGO_PASSWORD = '****'

    # Encode credentials
    ENCODED_USERNAME = quote_plus(MONGO_USERNAME)
    ENCODED_PASSWORD = quote_plus(MONGO_PASSWORD)

    # MongoDB URI
    MONGO_URI = f"mongodb+srv://{ENCODED_USERNAME}:{ENCODED_PASSWORD}@cluster0.fdivylq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    MONGO_DBNAME = 'posdatabase'
