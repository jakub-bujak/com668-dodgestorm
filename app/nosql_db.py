from pymongo import MongoClient, ASCENDING, DESCENDING
from .config import MONGO_URI, MONGO_DB_NAME, MONGO_LEADERBOARD_COLLECTION

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
leaderboard = db[MONGO_LEADERBOARD_COLLECTION]

leaderboard.create_index([("score", DESCENDING), ("timestamp", ASCENDING)])
leaderboard.create_index([("username", ASCENDING)])
