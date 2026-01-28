import asyncio
import os
import secrets

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .config import CORS_ORIGINS
from .sql_db import Base, engine, get_db
from .models import User
from .schemas import RegisterRequest, LoginRequest, AuthResponse
from .auth import hash_password, verify_password, create_access_token
from .leaderboard import router as leaderboard_router
from .ws import ws_manager

app = FastAPI(title="DodgeStorm API")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")
UNITY_INDEX = os.path.join(STATIC_DIR, "index.html")

origins = [o.strip() for o in CORS_ORIGINS if o and o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.isdir(STATIC_DIR):
    build_dir = os.path.join(STATIC_DIR, "Build")
    templ_dir = os.path.join(STATIC_DIR, "TemplateData")

    if os.path.isdir(build_dir):
        app.mount("/Build", StaticFiles(directory=build_dir), name="Build")
    if os.path.isdir(templ_dir):
        app.mount("/TemplateData", StaticFiles(directory=templ_dir), name="TemplateData")

    app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    if os.path.exists(UNITY_INDEX):
        return FileResponse(UNITY_INDEX)
    return {"status": "ok", "message": "API running (Unity build not found)"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/debug/sql")
def debug_sql(db: Session = Depends(get_db)):
    count = db.query(User).count()
    return {"ok": True, "user_count": count}

app.include_router(leaderboard_router)

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
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.user_id, user.username)
    return AuthResponse(token=token, username=user.username, user_id=user.user_id)

@app.post("/auth/guest", response_model=AuthResponse)
def guest_login(db: Session = Depends(get_db)):
    username = f"Guest_{secrets.token_hex(4)}"
    user = User(username=username, password_hash=hash_password(secrets.token_urlsafe(12)))
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
