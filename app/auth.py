from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, EmailStr

# Import necessary components from sibling files
from . import models, db, config

router = APIRouter()

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Password Utilities ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password): # Needed if you add registration later
    return pwd_context.hash(password)

# --- JWT Utilities ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.settings.SECRET_KEY, algorithm=config.settings.ALGORITHM)
    return encoded_jwt

# --- Database User Retrieval ---
def get_user_by_email(db_session: Session, email: str) -> models.User | None:
    return db_session.query(models.User).filter(models.User.email == email.lower()).first()

# --- API Endpoint ---
# This uses a standard form for username/password required by OAuth2PasswordBearer
@router.post("/token", summary="Get access token via form data")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db_session: Session = Depends(db.get_db)):
    user = get_user_by_email(db_session, form_data.username) # Use username field for email

    if not user or not verify_password(form_data.password, user.password_hash):
        print(f"Login failed for: {form_data.username}") # Log failed attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}, # Standard header for 401
        )

    # Create the token payload
    token_payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.first_name,
        # "sub": user.email # Often 'sub' (subject) is used for email/username
    }
    access_token = create_access_token(data=token_payload)

    # Update last login (best effort)
    try:
        user.last_login = datetime.now(timezone.utc)
        db_session.commit()
        print(f"Login successful for user ID: {user.id}, Email: {user.email}")
    except Exception as e:
        print(f"Warning: Failed to update last login for {user.id}: {e}")
        db_session.rollback()

    return {"access_token": access_token, "token_type": "bearer"}