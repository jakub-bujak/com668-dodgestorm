from pydantic import BaseModel, Field

class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

class AuthResponse(BaseModel):
    token: str
    username: str
    user_id: int

class LeaderboardSubmitRequest(BaseModel):
    score: int = Field(ge=0)
    durationSeconds: float = Field(ge=0)

class LeaderboardEntry(BaseModel):
    username: str
    score: int
    timestamp: str
