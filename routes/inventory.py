from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_connection
from middleware.auth import protect, admin_required

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("/", methods=["GET"])
@protect
@admin_required
def get_inventory(user):
    low_stock = request.args.get("low_stock") == "true"

    conn = get_connection()
    if low_stock:
        rows = conn.execute(
            "SELECT * FROM inventory WHERE quantity <= low_stock_threshold ORDER BY quantity"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM inventory ORDER BY item_name").fetchall()
    conn.close()

    data = [{
        "id": r["id"],
        "item_name": r["item_name"],
        "quantity": r["quantity"],
        "unit": r["unit"],
        "low_stock_threshold": r["low_stock_threshold"],
        "is_low": r["quantity"] <= r["low_stock_threshold"],
        "last_updated": r["last_updated"]
    } for r in rows]

    return jsonify({"success": True, "count": len(data), "data": data}), 200


@inventory_bp.route("/", methods=["POST"])
@protect
@admin_required
def add_inventory_item(user):
    data = request.get_json(silent=True) or {}
    item_name = (data.get("item_name") or "").strip()
    quantity = data.get("quantity", 0)
    unit = data.get("unit", "pcs")
    threshold = data.get("low_stock_threshold", 10)

    if not item_name:
        return jsonify({"success": False, "message": "item_name is required"}), 400

    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO inventory (item_name, quantity, unit, low_stock_threshold)
               VALUES (?, ?, ?, ?)""",
            (item_name, float(quantity), unit, float(threshold))
        )
        conn.commit()
        iid = cursor.lastrowid
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": str(e)}), 400
    conn.close()

    return jsonify({"success": True, "data": {"id": iid, "item_name": item_name}}), 201


@inventory_bp.route("/<int:item_id>", methods=["PUT"])
@protect
@admin_required
def update_inventory(user, item_id):
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    item = conn.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    if not item:
        conn.close()
        return jsonify({"success": False, "message": "Item not found"}), 404

    quantity = data.get("quantity", item["quantity"])
    threshold = data.get("low_stock_threshold", item["low_stock_threshold"])
    unit = data.get("unit", item["unit"])

    conn.execute(
        """UPDATE inventory SET quantity=?, unit=?, low_stock_threshold=?, last_updated=?
           WHERE id=?""",
        (float(quantity), unit, float(threshold), datetime.utcnow().isoformat(), item_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Inventory updated"}), 200


@inventory_bp.route("/alerts", methods=["GET"])
@protect
@admin_required
def stock_alerts(user):
    """Get items that are low in stock."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM inventory WHERE quantity <= low_stock_threshold ORDER BY quantity"
    ).fetchall()
    conn.close()

    alerts = [{
        "id": r["id"],
        "item_name": r["item_name"],
        "quantity": r["quantity"],
        "unit": r["unit"],
        "threshold": r["low_stock_threshold"]
    } for r in rows]

    return jsonify({
        "success": True,
        "count": len(alerts),
        "message": f"{len(alerts)} item(s) are low in stock" if alerts else "All stock levels are fine",
        "data": alerts
    }), 200


@inventory_bp.route("/reports/daily-sales", methods=["GET"])
@protect
@admin_required
def daily_sales(user):
    """Simple daily sales report."""
    date = request.args.get("date")  # YYYY-MM-DD, default today
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    conn = get_connection()

    # Total sales for the day
    sales = conn.execute("""
        SELECT COUNT(*) as order_count,
               COALESCE(SUM(total_amount), 0) as total_sales
        FROM orders
        WHERE date(created_at) = ? AND status NOT IN ('cancelled')
    """, (date,)).fetchone()

    # Top selling items
    top_items = conn.execute("""
        SELECT m.name, SUM(oi.quantity) as qty_sold, SUM(oi.subtotal) as revenue
        FROM order_items oi
        JOIN menu_items m ON oi.menu_item_id = m.id
        JOIN orders o ON oi.order_id = o.id
        WHERE date(o.created_at) = ? AND o.status NOT IN ('cancelled')
        GROUP BY m.id
        ORDER BY qty_sold DESC
        LIMIT 10
    """, (date,)).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "date": date,
        "data": {
            "order_count": sales["order_count"],
            "total_sales": sales["total_sales"],
            "top_items": [{
                "name": t["name"],
                "quantity_sold": t["qty_sold"],
                "revenue": t["revenue"]
            } for t in top_items]
        }
    }), 200
