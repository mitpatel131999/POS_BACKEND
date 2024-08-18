from flask import Flask, request, jsonify
from auth.routes import auth_bp
from profile.routes import profile_bp
from transactions.routes import transactions_bp
from products.routes import products_bp
from orders.routes import orders_bp
from flask_cors import CORS
from tinydb import TinyDB
from config import Config

app = Flask(__name__)
CORS(app)
app.config.from_object('config.Config')



# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(profile_bp, url_prefix='/api')
app.register_blueprint(transactions_bp, url_prefix='/api')
app.register_blueprint(products_bp, url_prefix='/api')
app.register_blueprint(orders_bp, url_prefix='/api')




if __name__ == '__main__':
    app.run(debug=True)
