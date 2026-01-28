from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from azure.cosmos.exceptions import CosmosHttpResponseError

from .schemas import LeaderboardSubmitRequest
from .auth import get_current_user
from .nosql_db import insert_score, get_top
from .ws import ws_manager

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

MAX_POINTS_PER_SECOND = 10.0
BUFFER_POINTS = 50

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@router.get("/top")
def leaderboard_top(limit: int = 100):
    limit = max(1, min(limit, 100))
    try:
        return get_top(limit=limit, game_mode="classic")
    except CosmosHttpResponseError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "where": "cosmos.get_top",
                "cosmos_status": getattr(e, "status_code", None),
                "message": str(e),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"where": "leaderboard_top", "message": repr(e)},
        )

@router.post("/submit")
async def submit_score(
    payload: LeaderboardSubmitRequest,
    user=Depends(get_current_user),
):
    if payload.durationSeconds <= 0:
        raise HTTPException(status_code=400, detail="Duration must be > 0")

    max_allowed = int(payload.durationSeconds * MAX_POINTS_PER_SECOND) + BUFFER_POINTS
    if payload.score > max_allowed:
        raise HTTPException(status_code=400, detail="Score rejected (implausible)")

    doc = {
        "userId": int(user.UserId),
        "username": user.Username,
        "score": int(payload.score),
        "durationSeconds": float(payload.durationSeconds),
        "timestamp": now_iso(),
        "gameMode": "classic",
    }

    try:
        insert_score(doc)
        top = get_top(limit=100, game_mode="classic")
        await ws_manager.broadcast_json({"type": "leaderboard_update", "top": top})
        return {"accepted": True}
    except CosmosHttpResponseError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "where": "cosmos.insert_or_query",
                "cosmos_status": getattr(e, "status_code", None),
                "message": str(e),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"where": "submit_score", "message": repr(e)},
        )
