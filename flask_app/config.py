from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus
import os

class Config:
    # Secret key for your Flask app
    SECRET_KEY = os.urandom(24)  # Generates a random 24-byte secret key

    # MongoDB connection details
    MONGO_USERNAME = 'mitpatelr1999'
    MONGO_PASSWORD = 'Mit@94285'

    # Encode credentials
    ENCODED_USERNAME = quote_plus(MONGO_USERNAME)
    ENCODED_PASSWORD = quote_plus(MONGO_PASSWORD)

    # MongoDB URI
<<<<<<< HEAD
    MONGO_URI = f"mongodb+srv://{ENCODED_USERNAME}:{ENCODED_PASSWORD}@cluster0.fdivylq.mongodb.net/?retryWrites=false&w=majority&appName=Cluster0"
=======
    MONGO_URI = f"mongodb+srv://{ENCODED_USERNAME}:{ENCODED_PASSWORD}@cluster0.fdivylq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
>>>>>>> 19868571793498183aaf34bda9e40a1cc87d74e4
    MONGO_DBNAME = 'posdatabase'
