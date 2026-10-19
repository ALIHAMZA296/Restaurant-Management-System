# Restaurant Management System

A complete Restaurant Management backend + frontend built with **Flask + SQLite**.

## Features

- 🍽️ **Menu Management** – Categories, items, prices, availability
- 🪑 **Tables** – Track available / occupied / reserved tables
- 📅 **Reservations** – Customers can reserve tables
- 🧾 **Orders** – Place orders (dine-in, takeaway, delivery), update status
- 📦 **Inventory** – Auto stock decrease when orders are placed + low stock alerts
- 📊 **Reports** – Daily sales report & top selling items
- 🔐 **Auth** – JWT login (Admin / Staff roles)
- 💻 **Modern Frontend** – Dark theme dashboard

## How to Run

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install packages
pip install -r requirements.txt

# 4. Create .env
cp .env.example .env

# 5. Seed demo data
python seed.py

# 6. Run server
python app.py
```

Open: **http://127.0.0.1:5000**

## Demo Login

| Role  | Email                   | Password    |
|-------|-------------------------|-------------|
| Admin | admin@restaurant.com    | password123 |
| Staff | staff@restaurant.com    | password123 |

## API Endpoints

### Auth
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET  /api/auth/me`

### Menu
- `GET  /api/menu`
- `GET  /api/menu/categories`
- `POST /api/menu` (admin)
- `PUT  /api/menu/:id` (admin)

### Tables
- `GET  /api/tables`
- `POST /api/tables` (admin)
- `PUT  /api/tables/:id/status` (admin)

### Reservations
- `GET  /api/reservations` (admin)
- `POST /api/reservations` (public)
- `PUT  /api/reservations/:id/status` (admin)

### Orders
- `GET  /api/orders` (admin)
- `POST /api/orders`
- `GET  /api/orders/:id`
- `PUT  /api/orders/:id/status` (admin)

### Inventory & Reports
- `GET  /api/inventory`
- `GET  /api/inventory/alerts`
- `GET  /api/inventory/reports/daily-sales`
- `POST /api/inventory` (admin)
- `PUT  /api/inventory/:id` (admin)

## Project Structure

```
restaurant_management/
├── app.py
├── config.py
├── database.py
├── seed.py
├── requirements.txt
├── middleware/auth.py
├── routes/
│   ├── auth.py
│   ├── menu.py
│   ├── tables.py
│   ├── reservations.py
│   ├── orders.py
│   └── inventory.py
└── templates/index.html
```
