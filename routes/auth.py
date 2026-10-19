from flask import Blueprint, request, jsonify
import bcrypt
import sqlite3
from database import get_connection
from middleware.auth import create_token, protect

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role", "staff")

    if not name or not email or not password:
        return jsonify({"success": False, "message": "Name, email and password required"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters"}), 400

    # Only allow admin role if explicitly set (for seed), otherwise staff/customer
    safe_role = role if role in ("admin", "staff", "customer") else "staff"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed, safe_role)
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"success": False, "message": "Email already exists"}), 409
    finally:
        conn.close()

    token = create_token(user_id)
    return jsonify({
        "success": True,
        "token": token,
        "user": {"id": user_id, "name": name, "email": email, "role": safe_role}
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400

    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    token = create_token(user["id"])
    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }), 200


@auth_bp.route("/me", methods=["GET"])
@protect
def get_me(user):
    return jsonify({"success": True, "user": user}), 200
