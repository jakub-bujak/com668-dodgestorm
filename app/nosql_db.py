import logging
import uuid
from typing import Any, Dict, List

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

from .config import COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DB_NAME, COSMOS_CONTAINER

log = logging.getLogger("cosmos")

if not COSMOS_ENDPOINT or not COSMOS_KEY:
    raise RuntimeError("COSMOS_ENDPOINT / COSMOS_KEY not set")

_client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)

try:
    _db = _client.get_database_client(COSMOS_DB_NAME)
    _container = _db.get_container_client(COSMOS_CONTAINER)
    _container.read()
except CosmosHttpResponseError as e:
    log.exception("Cosmos init failed: %s", str(e))
    raise
except Exception as e:
    log.exception("Cosmos init failed (non-Cosmos error): %r", e)
    raise


def insert_score(doc: Dict[str, Any]) -> None:
    doc = dict(doc)
    doc.setdefault("id", str(uuid.uuid4()))
    doc.setdefault("gameMode", "classic")

    try:
        _container.create_item(body=doc)
    except CosmosHttpResponseError as e:
        log.exception("Cosmos insert_score failed: %s", str(e))
        raise


def get_top(limit: int = 100, game_mode: str = "classic") -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 100))
    fetch_limit = max(100, min(limit * 25, 1000))

    query = """
    SELECT c.userId, c.username, c.score, c.timestamp
    FROM c
    WHERE c.gameMode = @mode
    ORDER BY c.score DESC
    OFFSET 0 LIMIT @limit
    """

    params = [
        {"name": "@mode", "value": game_mode},
        {"name": "@limit", "value": fetch_limit},
    ]

    try:
        rows = list(
            _container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )
    except CosmosHttpResponseError as e:
        log.exception("Cosmos get_top failed: %s", str(e))
        raise

    best_by_user: Dict[int, Dict[str, Any]] = {}

    for r in rows:
        uid = r.get("userId")
        if uid is None:
            continue
        try:
            uid_int = int(uid)
        except Exception:
            continue

        score = int(r.get("score", 0) or 0)
        ts = r.get("timestamp") or ""

        prev = best_by_user.get(uid_int)
        if prev is None:
            best_by_user[uid_int] = {
                "userId": uid_int,
                "username": r.get("username") or "",
                "score": score,
                "timestamp": ts,
            }
            continue

        prev_score = int(prev.get("score", 0) or 0)
        prev_ts = prev.get("timestamp") or ""

        if score > prev_score or (score == prev_score and ts < prev_ts):
            best_by_user[uid_int] = {
                "userId": uid_int,
                "username": r.get("username") or prev.get("username") or "",
                "score": score,
                "timestamp": ts,
            }

    unique = list(best_by_user.values())
    unique.sort(key=lambda x: (-int(x.get("score", 0) or 0), str(x.get("timestamp") or "")))
    return unique[:limit]
