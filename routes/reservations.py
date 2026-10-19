from flask import Blueprint, request, jsonify
from database import get_connection
from middleware.auth import protect, admin_required

reservations_bp = Blueprint("reservations", __name__)


@reservations_bp.route("/", methods=["GET"])
@protect
@admin_required
def get_reservations(user):
    status = request.args.get("status")
    date = request.args.get("date")

    conn = get_connection()
    query = """
        SELECT r.*, t.table_number, t.capacity
        FROM reservations r
        JOIN tables t ON r.table_id = t.id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND r.status = ?"
        params.append(status)
    if date:
        query += " AND r.reservation_date = ?"
        params.append(date)
    query += " ORDER BY r.reservation_date, r.reservation_time"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    data = [{
        "id": r["id"],
        "table_id": r["table_id"],
        "table_number": r["table_number"],
        "customer_name": r["customer_name"],
        "customer_phone": r["customer_phone"],
        "reservation_date": r["reservation_date"],
        "reservation_time": r["reservation_time"],
        "guests": r["guests"],
        "status": r["status"],
        "notes": r["notes"]
    } for r in rows]

    return jsonify({"success": True, "count": len(data), "data": data}), 200


@reservations_bp.route("/", methods=["POST"])
def create_reservation():
    """Public endpoint - customers can reserve tables."""
    data = request.get_json(silent=True) or {}
    table_id = data.get("table_id")
    customer_name = (data.get("customer_name") or "").strip()
    customer_phone = (data.get("customer_phone") or "").strip()
    reservation_date = data.get("reservation_date")
    reservation_time = data.get("reservation_time")
    guests = data.get("guests")
    notes = data.get("notes", "")

    if not all([table_id, customer_name, reservation_date, reservation_time, guests]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    try:
        guests = int(guests)
        table_id = int(table_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid guests or table_id"}), 400

    conn = get_connection()

    # Check table exists and capacity
    table = conn.execute("SELECT * FROM tables WHERE id = ?", (table_id,)).fetchone()
    if not table:
        conn.close()
        return jsonify({"success": False, "message": "Table not found"}), 404

    if guests > table["capacity"]:
        conn.close()
        return jsonify({
            "success": False,
            "message": f"Table capacity is {table['capacity']}, cannot seat {guests} guests"
        }), 400

    # Check if table is already reserved/occupied at that time (simple check)
    existing = conn.execute("""
        SELECT id FROM reservations
        WHERE table_id = ? AND reservation_date = ? AND reservation_time = ?
        AND status IN ('pending', 'confirmed')
    """, (table_id, reservation_date, reservation_time)).fetchone()

    if existing:
        conn.close()
        return jsonify({"success": False, "message": "Table already reserved for this time"}), 409

    cursor = conn.execute("""
        INSERT INTO reservations
        (table_id, customer_name, customer_phone, reservation_date, reservation_time, guests, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed')
    """, (table_id, customer_name, customer_phone, reservation_date, reservation_time, guests, notes))

    # Mark table as reserved
    conn.execute("UPDATE tables SET status = 'reserved' WHERE id = ?", (table_id,))
    conn.commit()
    res_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "success": True,
        "message": "Reservation created successfully",
        "data": {"id": res_id, "table_number": table["table_number"], "status": "confirmed"}
    }), 201


@reservations_bp.route("/<int:res_id>/status", methods=["PUT"])
@protect
@admin_required
def update_reservation_status(user, res_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if status not in ("pending", "confirmed", "cancelled", "completed"):
        return jsonify({"success": False, "message": "Invalid status"}), 400

    conn = get_connection()
    res = conn.execute("SELECT * FROM reservations WHERE id = ?", (res_id,)).fetchone()
    if not res:
        conn.close()
        return jsonify({"success": False, "message": "Reservation not found"}), 404

    conn.execute("UPDATE reservations SET status = ? WHERE id = ?", (status, res_id))

    # Free the table if cancelled or completed
    if status in ("cancelled", "completed"):
        conn.execute("UPDATE tables SET status = 'available' WHERE id = ?", (res["table_id"],))

    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": f"Reservation status updated to {status}"}), 200
