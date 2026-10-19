from functools import wraps
from flask import request, jsonify
import jwt
from datetime import datetime, timedelta, timezone
from config import Config
from database import get_connection


def create_token(user_id: int) -> str:
    expires = Config.JWT_EXPIRES_IN
    if expires.endswith("d"):
        delta = timedelta(days=int(expires[:-1]))
    elif expires.endswith("h"):
        delta = timedelta(hours=int(expires[:-1]))
    else:
        delta = timedelta(days=7)

    payload = {
        "id": user_id,
        "exp": datetime.now(timezone.utc) + delta,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def get_current_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        conn = get_connection()
        user = conn.execute(
            "SELECT id, name, email, role FROM users WHERE id = ?",
            (payload["id"],)
        ).fetchone()
        conn.close()
        if user:
            return dict(user)
    except Exception:
        return None
    return None


def protect(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "message": "Not authorized. Please login."}), 401
        return f(user, *args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(user, *args, **kwargs):
        if user.get("role") not in ("admin", "staff"):
            return jsonify({"success": False, "message": "Admin/Staff access required"}), 403
        return f(user, *args, **kwargs)
    return decorated
