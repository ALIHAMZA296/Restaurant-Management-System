from flask import Blueprint, request, jsonify
from database import get_connection
from middleware.auth import protect, admin_required

tables_bp = Blueprint("tables", __name__)


@tables_bp.route("/", methods=["GET"])
def get_tables():
    """Get all tables with current status."""
    status = request.args.get("status")  # available, occupied, reserved

    conn = get_connection()
    if status:
        rows = conn.execute(
            "SELECT * FROM tables WHERE status = ? ORDER BY table_number", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tables ORDER BY table_number").fetchall()
    conn.close()

    tables = [{
        "id": r["id"],
        "table_number": r["table_number"],
        "capacity": r["capacity"],
        "status": r["status"],
        "location": r["location"]
    } for r in rows]

    return jsonify({"success": True, "count": len(tables), "data": tables}), 200


@tables_bp.route("/", methods=["POST"])
@protect
@admin_required
def create_table(user):
    data = request.get_json(silent=True) or {}
    table_number = data.get("table_number")
    capacity = data.get("capacity")
    location = data.get("location", "Main Hall")

    if not table_number or not capacity:
        return jsonify({"success": False, "message": "table_number and capacity required"}), 400

    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO tables (table_number, capacity, location) VALUES (?, ?, ?)",
            (int(table_number), int(capacity), location)
        )
        conn.commit()
        tid = cursor.lastrowid
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": str(e)}), 400
    conn.close()

    return jsonify({
        "success": True,
        "data": {"id": tid, "table_number": table_number, "capacity": capacity, "status": "available"}
    }), 201


@tables_bp.route("/<int:table_id>/status", methods=["PUT"])
@protect
@admin_required
def update_table_status(user, table_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if status not in ("available", "occupied", "reserved"):
        return jsonify({"success": False, "message": "Invalid status"}), 400

    conn = get_connection()
    table = conn.execute("SELECT * FROM tables WHERE id = ?", (table_id,)).fetchone()
    if not table:
        conn.close()
        return jsonify({"success": False, "message": "Table not found"}), 404

    conn.execute("UPDATE tables SET status = ? WHERE id = ?", (status, table_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": f"Table status updated to {status}"}), 200
