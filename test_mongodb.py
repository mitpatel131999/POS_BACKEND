import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus

# Retrieve credentials from environment variables
username = 'mitpatelr1999'
password = 'Mit@94285'

# Encode credentials
encoded_username = quote_plus(username)
encoded_password = quote_plus(password)

# Construct the URI
print(encoded_password)
uri = f"mongodb+srv://{encoded_username}:{encoded_password}@cluster0.fdivylq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
uri = f"mongodb+srv://mitpatelr1999:{encoded_password}@cluster0.fdivylq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
print(client)

client = MongoClient(uri)

try:
    # Just to test the connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB")
except Exception as e:
    print(f"Error: {e}")

from pymongo import MongoClient
#from config import Config

# Initialize MongoDB client and database
client = MongoClient(uri)

print(client.list_database_names())
db = client['posdatabase']
users_db = db['users']


try:
    print("Testing collection access...",db.list_collection_names())
except Exception as e:
    print(f"Error accessing the collection: {e}")

# Test the connection and access to the collection
try:
    print("Testing collection access...")
    # Perform a simple find_one query
    user_data = users_db.find_one()
    print("Collection access successful. First document:", user_data)
except Exception as e:
    print(f"Error accessing the collection: {e}")


print(client)
# Send a ping to confirm a successful connection
try:
    #client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
