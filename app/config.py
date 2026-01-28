import os

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set")

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL", "").strip()
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("SQLALCHEMY_DATABASE_URL is not set (must point to Azure SQL)")

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "").strip()
COSMOS_KEY = os.getenv("COSMOS_KEY", "").strip()
COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME", "LeaderboardDB").strip()
COSMOS_CONTAINER = os.getenv("COSMOS_CONTAINER", "Scores").strip()

if not COSMOS_ENDPOINT or not COSMOS_KEY:
    raise RuntimeError("COSMOS_ENDPOINT and COSMOS_KEY must be set")

CORS_ORIGINS = [
    o.strip() for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if o.strip()
]
