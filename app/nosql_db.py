import uuid
from typing import Any, Dict, List

from azure.cosmos import CosmosClient, PartitionKey
from .config import COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DB_NAME, COSMOS_CONTAINER

if not COSMOS_ENDPOINT or not COSMOS_KEY:
    raise RuntimeError("COSMOS_ENDPOINT / COSMOS_KEY not set")

_client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
_db = _client.create_database_if_not_exists(id=COSMOS_DB_NAME)

_container = _db.create_container_if_not_exists(
    id=COSMOS_CONTAINER,
    partition_key=PartitionKey(path="/gameMode"),
)

def insert_score(doc: Dict[str, Any]) -> None:
    """
    Inserts a score document. Must include the partition key: gameMode.
    """
    doc = dict(doc)
    doc.setdefault("id", str(uuid.uuid4()))
    doc.setdefault("gameMode", "classic")
    _container.create_item(body=doc)

def get_top(limit: int = 100, game_mode: str = "classic") -> List[Dict[str, Any]]:
    """
    Returns top scores for a given game mode.
    Uses OFFSET/LIMIT instead of TOP @limit (more reliable in Cosmos queries).
    """
    limit = max(1, min(int(limit), 100))

    query = """
    SELECT c.username, c.score, c.timestamp
    FROM c
    WHERE c.gameMode = @mode
    ORDER BY c.score DESC, c.timestamp ASC
    OFFSET 0 LIMIT @limit
    """

    params = [
        {"name": "@mode", "value": game_mode},
        {"name": "@limit", "value": limit},
    ]

    return list(
        _container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        )
    )
