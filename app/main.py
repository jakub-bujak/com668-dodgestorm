import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import CORS_ORIGINS
from .sql_db import Base, engine, get_db
from .models import User
from .schemas import RegisterRequest, LoginRequest, AuthResponse
from .auth import hash_password, verify_password, create_access_token
from .leaderboard import router as leaderboard_router
from .ws import ws_manager

app = FastAPI(title="DodgeStorm API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(leaderboard_router)


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(username=username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.user_id, user.username)
    return AuthResponse(token=token, username=user.username, user_id=user.user_id)


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.user_id, user.username)
    return AuthResponse(token=token, username=user.username, user_id=user.user_id)


@app.post("/auth/guest", response_model=AuthResponse)
def guest_login(db: Session = Depends(get_db)):
    username = "Guest"

    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            username=username,
            password_hash=hash_password("guest_placeholder_password")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user.user_id, user.username)
    return AuthResponse(token=token, username=user.username, user_id=user.user_id)


@app.websocket("/ws/leaderboard")
async def leaderboard_ws(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({"type": "hello", "message": "connected"})
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
