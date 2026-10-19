from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_connection
from middleware.auth import protect, admin_required

orders_bp = Blueprint("orders", __name__)


def calculate_order_total(conn, order_id):
    total = conn.execute(
        "SELECT COALESCE(SUM(subtotal), 0) as total FROM order_items WHERE order_id = ?",
        (order_id,)
    ).fetchone()["total"]
    conn.execute("UPDATE orders SET total_amount = ? WHERE id = ?", (total, order_id))
    return total


def decrease_inventory(conn, menu_item_id, quantity):
    """Auto-update inventory when an order item is added."""
    links = conn.execute(
        "SELECT inventory_id, quantity_used FROM menu_inventory WHERE menu_item_id = ?",
        (menu_item_id,)
    ).fetchall()

    for link in links:
        used = link["quantity_used"] * quantity
        conn.execute(
            """UPDATE inventory
               SET quantity = quantity - ?, last_updated = ?
               WHERE id = ?""",
            (used, datetime.utcnow().isoformat(), link["inventory_id"])
        )


@orders_bp.route("/", methods=["GET"])
@protect
@admin_required
def get_orders(user):
    status = request.args.get("status")
    conn = get_connection()

    query = """
        SELECT o.*, t.table_number
        FROM orders o
        LEFT JOIN tables t ON o.table_id = t.id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND o.status = ?"
        params.append(status)
    query += " ORDER BY o.created_at DESC"

    rows = conn.execute(query, params).fetchall()

    orders = []
    for r in rows:
        items = conn.execute("""
            SELECT oi.*, m.name as item_name
            FROM order_items oi
            JOIN menu_items m ON oi.menu_item_id = m.id
            WHERE oi.order_id = ?
        """, (r["id"],)).fetchall()

        orders.append({
            "id": r["id"],
            "table_id": r["table_id"],
            "table_number": r["table_number"],
            "order_type": r["order_type"],
            "status": r["status"],
            "total_amount": r["total_amount"],
            "customer_name": r["customer_name"],
            "notes": r["notes"],
            "created_at": r["created_at"],
            "items": [{
                "id": i["id"],
                "menu_item_id": i["menu_item_id"],
                "name": i["item_name"],
                "quantity": i["quantity"],
                "unit_price": i["unit_price"],
                "subtotal": i["subtotal"]
            } for i in items]
        })

    conn.close()
    return jsonify({"success": True, "count": len(orders), "data": orders}), 200


@orders_bp.route("/", methods=["POST"])
@protect
def create_order(user):
    """
    Place a new order.
    Body example:
    {
      "table_id": 1,
      "order_type": "dine_in",
      "customer_name": "Ali",
      "notes": "Extra spicy",
      "items": [
        {"menu_item_id": 1, "quantity": 2},
        {"menu_item_id": 3, "quantity": 1}
      ]
    }
    """
    data = request.get_json(silent=True) or {}
    table_id = data.get("table_id")
    order_type = data.get("order_type", "dine_in")
    customer_name = data.get("customer_name", "")
    notes = data.get("notes", "")
    items = data.get("items", [])

    if not items:
        return jsonify({"success": False, "message": "Order must have at least one item"}), 400

    if order_type not in ("dine_in", "takeaway", "delivery"):
        return jsonify({"success": False, "message": "Invalid order_type"}), 400

    conn = get_connection()

    # Validate table if dine_in
    if order_type == "dine_in" and table_id:
        table = conn.execute("SELECT * FROM tables WHERE id = ?", (table_id,)).fetchone()
        if not table:
            conn.close()
            return jsonify({"success": False, "message": "Table not found"}), 404

    # Create order
    cursor = conn.execute("""
        INSERT INTO orders (table_id, order_type, status, customer_name, notes, created_by)
        VALUES (?, ?, 'pending', ?, ?, ?)
    """, (table_id, order_type, customer_name, notes, user["id"]))
    order_id = cursor.lastrowid

    # Add items + update inventory
    for item in items:
        menu_item_id = item.get("menu_item_id")
        quantity = int(item.get("quantity", 1))

        menu_item = conn.execute(
            "SELECT * FROM menu_items WHERE id = ? AND is_available = 1", (menu_item_id,)
        ).fetchone()

        if not menu_item:
            conn.rollback()
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Menu item {menu_item_id} not found or unavailable"
            }), 400

        unit_price = menu_item["price"]
        subtotal = unit_price * quantity

        conn.execute("""
            INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?)
        """, (order_id, menu_item_id, quantity, unit_price, subtotal))

        # Auto decrease inventory
        decrease_inventory(conn, menu_item_id, quantity)

    # Update table status if dine-in
    if order_type == "dine_in" and table_id:
        conn.execute("UPDATE tables SET status = 'occupied' WHERE id = ?", (table_id,))

    total = calculate_order_total(conn, order_id)
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Order placed successfully",
        "data": {"id": order_id, "total_amount": total, "status": "pending"}
    }), 201


@orders_bp.route("/<int:order_id>/status", methods=["PUT"])
@protect
@admin_required
def update_order_status(user, order_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")

    valid = ("pending", "preparing", "ready", "served", "completed", "cancelled")
    if status not in valid:
        return jsonify({"success": False, "message": "Invalid status"}), 400

    conn = get_connection()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"success": False, "message": "Order not found"}), 404

    conn.execute(
        "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.utcnow().isoformat(), order_id)
    )

    # Free table when order is completed or cancelled
    if status in ("completed", "cancelled") and order["table_id"]:
        conn.execute("UPDATE tables SET status = 'available' WHERE id = ?", (order["table_id"],))

    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": f"Order status updated to {status}"}), 200


@orders_bp.route("/<int:order_id>", methods=["GET"])
@protect
def get_order(user, order_id):
    conn = get_connection()
    order = conn.execute("""
        SELECT o.*, t.table_number
        FROM orders o
        LEFT JOIN tables t ON o.table_id = t.id
        WHERE o.id = ?
    """, (order_id,)).fetchone()

    if not order:
        conn.close()
        return jsonify({"success": False, "message": "Order not found"}), 404

    items = conn.execute("""
        SELECT oi.*, m.name as item_name
        FROM order_items oi
        JOIN menu_items m ON oi.menu_item_id = m.id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()
    conn.close()

    return jsonify({
        "success": True,
        "data": {
            "id": order["id"],
            "table_number": order["table_number"],
            "order_type": order["order_type"],
            "status": order["status"],
            "total_amount": order["total_amount"],
            "customer_name": order["customer_name"],
            "notes": order["notes"],
            "created_at": order["created_at"],
            "items": [{
                "name": i["item_name"],
                "quantity": i["quantity"],
                "unit_price": i["unit_price"],
                "subtotal": i["subtotal"]
            } for i in items]
        }
    }), 200
