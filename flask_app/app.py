from flask import Flask,  send_from_directory, request, jsonify
from auth.routes import auth_bp
from profile.routes import profile_bp
from transactions.routes import transactions_bp
from products.routes import products_bp
from products.routes import purchase_orders_bp
from orders.routes import orders_bp
from database.db import start_change_streams, database
from flask_cors import CORS
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from config import Config
from flask_socketio import SocketIO


app = Flask(__name__, static_folder='build', static_url_path='')
#socketio = SocketIO(app)
#app = Flask(__name__)
CORS(app)
app.config.from_object('config.Config')
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
start_change_streams(socketio, database)



"""
# Initialize MongoDB client
client = MongoClient(app.config['MONGO_URI'], server_api=ServerApi('1'),
                        connectTimeoutMS=30000,
                        socketTimeoutMS=None,
                        connect=False,
                        maxPoolSize=1)
print(client)
db = client[app.config['MONGO_DBNAME']]

'''
# Example: Accessing collections
profile_db = db['profiles']
transactions_db = db['transactions']
products_db = db['products']
users_db = db['users']
orders_db = db['orders']
settings_db = db['settings']
pending_transactions_db = db['pending_transactions']
'''
# Pass collections to blueprints or use within your route logic
app.config['db'] = db  # Optionally store the db in the Flask app config
"""

# Serve React's index.html
@app.route('/')
def serve_react():
    return send_from_directory(app.static_folder, 'index.html')

# Serve static files from React build
@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory(app.static_folder, path)
    except FileNotFoundError:
        return send_from_directory(app.static_folder, 'index.html')



# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(profile_bp, url_prefix='/api')
app.register_blueprint(transactions_bp, url_prefix='/api')
app.register_blueprint(products_bp, url_prefix='/api')
app.register_blueprint(orders_bp, url_prefix='/api')
app.register_blueprint(purchase_orders_bp, url_prefix='/api')

if __name__ == '__main__':
    app.run(debug=True)
