from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .schemas import LeaderboardSubmitRequest
from .auth import get_current_user
from .nosql_db import leaderboard
from .ws import ws_manager

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

MAX_POINTS_PER_SECOND = 50.0

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@router.get("/top")
def get_top(limit: int = 100):
    limit = max(1, min(limit, 100))
    docs = list(
        leaderboard.find({}, {"_id": 0})
        .sort([("score", -1), ("timestamp", 1)])
        .limit(limit)
    )
    return docs

@router.post("/submit")
async def submit_score(
    payload: LeaderboardSubmitRequest,
    user=Depends(get_current_user),
):
    if payload.durationSeconds <= 0:
        raise HTTPException(status_code=400, detail="Duration must be > 0")

    max_allowed = int(payload.durationSeconds * MAX_POINTS_PER_SECOND) + 100
    if payload.score > max_allowed:
        raise HTTPException(status_code=400, detail="Score rejected (implausible)")

    doc = {
        "user_id": user.user_id,
        "username": user.username,
        "score": int(payload.score),
        "durationSeconds": float(payload.durationSeconds),
        "timestamp": now_iso(),
    }

    leaderboard.insert_one(doc)

    top = list(
        leaderboard.find({}, {"_id": 0})
        .sort([("score", -1), ("timestamp", 1)])
        .limit(100)
    )
    await ws_manager.broadcast_json({"type": "leaderboard_update", "top": top})

    return {"accepted": True}
