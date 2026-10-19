from flask import Blueprint, request, jsonify
from database import get_connection
from middleware.auth import protect, admin_required

menu_bp = Blueprint("menu", __name__)


@menu_bp.route("/", methods=["GET"])
def get_menu():
    """Public: Get all menu items (optionally filter by category / available)."""
    category = request.args.get("category")
    available_only = request.args.get("available", "true").lower() == "true"

    conn = get_connection()
    query = """
        SELECT m.*, c.name as category_name
        FROM menu_items m
        LEFT JOIN categories c ON m.category_id = c.id
        WHERE 1=1
    """
    params = []

    if available_only:
        query += " AND m.is_available = 1"
    if category:
        query += " AND c.name = ?"
        params.append(category)

    query += " ORDER BY c.name, m.name"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    items = [{
        "id": r["id"],
        "name": r["name"],
        "description": r["description"],
        "price": r["price"],
        "category": r["category_name"],
        "is_available": bool(r["is_available"]),
        "image_url": r["image_url"]
    } for r in rows]

    return jsonify({"success": True, "count": len(items), "data": items}), 200


@menu_bp.route("/categories", methods=["GET"])
def get_categories():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return jsonify({
        "success": True,
        "data": [{"id": r["id"], "name": r["name"]} for r in rows]
    }), 200


@menu_bp.route("/", methods=["POST"])
@protect
@admin_required
def create_menu_item(user):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    price = data.get("price")
    category_id = data.get("category_id")
    is_available = 1 if data.get("is_available", True) else 0

    if not name or price is None:
        return jsonify({"success": False, "message": "Name and price are required"}), 400

    try:
        price = float(price)
        if price < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid price"}), 400

    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO menu_items (name, description, price, category_id, is_available)
           VALUES (?, ?, ?, ?, ?)""",
        (name, description, price, category_id, is_available)
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "success": True,
        "data": {"id": item_id, "name": name, "price": price, "is_available": bool(is_available)}
    }), 201


@menu_bp.route("/<int:item_id>", methods=["PUT"])
@protect
@admin_required
def update_menu_item(user, item_id):
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    item = conn.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        conn.close()
        return jsonify({"success": False, "message": "Menu item not found"}), 404

    name = data.get("name", item["name"])
    description = data.get("description", item["description"])
    price = data.get("price", item["price"])
    category_id = data.get("category_id", item["category_id"])
    is_available = data.get("is_available", item["is_available"])

    conn.execute(
        """UPDATE menu_items SET name=?, description=?, price=?, category_id=?, is_available=?
           WHERE id=?""",
        (name, description, float(price), category_id, 1 if is_available else 0, item_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Menu item updated"}), 200


@menu_bp.route("/<int:item_id>", methods=["DELETE"])
@protect
@admin_required
def delete_menu_item(user, item_id):
    conn = get_connection()
    conn.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Menu item deleted"}), 200
