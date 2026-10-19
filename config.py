import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = int(os.getenv("PORT", 5000))
    JWT_SECRET = os.getenv("JWT_SECRET", "restaurant-secret-key-change-me")
    JWT_EXPIRES_IN = os.getenv("JWT_EXPIRES_IN", "7d")
    DATABASE = "restaurant.db"
