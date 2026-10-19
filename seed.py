"""
Seed demo data for Restaurant Management System.
Run: python seed.py
"""

from datetime import datetime, timedelta
import bcrypt
from database import get_connection, init_db


def seed():
    init_db()
    conn = get_connection()

    # Clear tables
    for table in ["order_items", "orders", "reservations", "menu_inventory",
                  "menu_items", "categories", "inventory", "tables", "users"]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    print("Cleared old data.")

    hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt())

    # Users
    conn.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        ("Admin User", "admin@restaurant.com", hashed, "admin")
    )
    conn.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        ("Staff Member", "staff@restaurant.com", hashed, "staff")
    )
    print("Created users: admin@restaurant.com / staff@restaurant.com  (password: password123)")

    # Categories
    cats = ["Starters", "Main Course", "Drinks", "Desserts"]
    cat_ids = {}
    for name in cats:
        cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        cat_ids[name] = cur.lastrowid

    # Menu Items
    menu = [
        ("Chicken Wings", "Crispy fried wings with sauce", 12.99, "Starters"),
        ("Caesar Salad", "Fresh romaine with caesar dressing", 8.50, "Starters"),
        ("Grilled Chicken", "Served with rice and vegetables", 18.99, "Main Course"),
        ("Beef Steak", "300g premium steak", 28.50, "Main Course"),
        ("Pasta Alfredo", "Creamy white sauce pasta", 15.00, "Main Course"),
        ("Fresh Juice", "Orange / Apple / Mango", 4.50, "Drinks"),
        ("Soft Drink", "Coke / Sprite / Fanta", 2.50, "Drinks"),
        ("Chocolate Cake", "Rich chocolate layer cake", 7.00, "Desserts"),
        ("Ice Cream", "Vanilla / Chocolate", 5.00, "Desserts"),
    ]

    menu_ids = {}
    for name, desc, price, cat in menu:
        cur = conn.execute(
            "INSERT INTO menu_items (name, description, price, category_id, is_available) VALUES (?, ?, ?, ?, 1)",
            (name, desc, price, cat_ids[cat])
        )
        menu_ids[name] = cur.lastrowid

    print(f"Created {len(menu)} menu items.")

    # Tables
    for i, cap in enumerate([2, 2, 4, 4, 4, 6, 6, 8], start=1):
        conn.execute(
            "INSERT INTO tables (table_number, capacity, status, location) VALUES (?, ?, 'available', ?)",
            (i, cap, "Main Hall" if i <= 5 else "Outdoor")
        )
    print("Created 8 tables.")

    # Inventory
    inventory_items = [
        ("Chicken", 50, "kg", 10),
        ("Beef", 30, "kg", 8),
        ("Rice", 100, "kg", 20),
        ("Pasta", 40, "kg", 10),
        ("Cooking Oil", 25, "liters", 5),
        ("Soft Drinks", 120, "cans", 30),
        ("Chocolate", 15, "kg", 5),
        ("Vegetables", 40, "kg", 10),
    ]
    inv_ids = {}
    for name, qty, unit, thresh in inventory_items:
        cur = conn.execute(
            "INSERT INTO inventory (item_name, quantity, unit, low_stock_threshold) VALUES (?, ?, ?, ?)",
            (name, qty, unit, thresh)
        )
        inv_ids[name] = cur.lastrowid

    print(f"Created {len(inventory_items)} inventory items.")

    # Link some menu items to inventory (for auto stock decrease)
    links = [
        ("Chicken Wings", "Chicken", 0.3),
        ("Grilled Chicken", "Chicken", 0.4),
        ("Beef Steak", "Beef", 0.35),
        ("Pasta Alfredo", "Pasta", 0.2),
        ("Soft Drink", "Soft Drinks", 1),
        ("Chocolate Cake", "Chocolate", 0.15),
    ]
    for menu_name, inv_name, used in links:
        conn.execute(
            "INSERT INTO menu_inventory (menu_item_id, inventory_id, quantity_used) VALUES (?, ?, ?)",
            (menu_ids[menu_name], inv_ids[inv_name], used)
        )

    # Sample reservation
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    conn.execute("""
        INSERT INTO reservations
        (table_id, customer_name, customer_phone, reservation_date, reservation_time, guests, status)
        VALUES (3, 'Ahmed Khan', '03001234567', ?, '19:00', 3, 'confirmed')
    """, (tomorrow,))

    conn.commit()
    conn.close()
    print("\n✅ Seeding completed successfully!")
    print("\nLogin credentials:")
    print("  Admin → admin@restaurant.com / password123")
    print("  Staff → staff@restaurant.com / password123")


if __name__ == "__main__":
    seed()
