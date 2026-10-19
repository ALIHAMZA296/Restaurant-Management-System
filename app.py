"""
Restaurant Management System - Flask + SQLite

Run:
    python app.py
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from config import Config
from database import init_db
from routes.auth import auth_bp
from routes.menu import menu_bp
from routes.tables import tables_bp
from routes.reservations import reservations_bp
from routes.orders import orders_bp
from routes.inventory import inventory_bp

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(menu_bp, url_prefix="/api/menu")
app.register_blueprint(tables_bp, url_prefix="/api/tables")
app.register_blueprint(reservations_bp, url_prefix="/api/reservations")
app.register_blueprint(orders_bp, url_prefix="/api/orders")
app.register_blueprint(inventory_bp, url_prefix="/api/inventory")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api")
def health():
    return jsonify({
        "success": True,
        "message": "Restaurant Management System API is running (Flask + SQLite)"
    }), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "Route not found"}), 404


if __name__ == "__main__":
    init_db()
    print(f"\n✅ Restaurant Management System starting on http://127.0.0.1:{Config.PORT}")
    print("   Press CTRL+C to stop\n")
    app.run(debug=True, port=Config.PORT, host="0.0.0.0")
