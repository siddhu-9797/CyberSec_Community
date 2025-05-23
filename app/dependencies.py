# app/dependencies.py

from fastapi import Depends, HTTPException, status, Request # <<< Added Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, ValidationError
from typing import Optional # <<< Added Optional

# Import necessary components from sibling files
from . import models, db, config, auth # Need auth potentially if user model details change often

# Tells FastAPI where to look for the token if needed automatically for get_current_user
# Still useful for documentation even if get_optional_current_user reads header manually
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token") # Path of your token endpoint

class TokenData(BaseModel): # Defines expected data in the token
    email: EmailStr | None = None
    user_id: int | None = None

# --- Original Dependency: Requires Authentication ---
async def get_current_user(token: str = Depends(oauth2_scheme), db_session: Session = Depends(db.get_db)) -> models.User:
    """
    Dependency to get the current logged-in user from JWT.
    RAISES HTTPException if token is invalid, missing, or user not found.
    Use this for routes strictly requiring authentication.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.settings.SECRET_KEY, algorithms=[config.settings.ALGORITHM])
        user_id: int | None = payload.get("user_id")
        email: str | None = payload.get("email") # Optional: Check email too if needed

        if user_id is None: # Primary check is user_id
            print("Token missing user_id")
            raise credentials_exception

        # Optional: Validate payload structure more formally using TokenData
        # try:
        #     token_data = TokenData(user_id=user_id, email=email)
        # except ValidationError as e:
        #     print(f"Token data validation error: {e}")
        #     raise credentials_exception

    except JWTError as e:
         print(f"JWT Decode Error for required user: {e}")
         raise credentials_exception
    except Exception as e: # Catch broader errors during decode/validation
         print(f"Unexpected token decode error for required user: {e}")
         raise credentials_exception

    # Fetch user from DB based on ID from token
    user = db_session.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        print(f"User ID {user_id} from token not found in DB")
        raise credentials_exception

    # print(f"Authenticated user via token: {user.id} ({user.email})") # Debug log
    return user

# +++ NEW Dependency: Optional Authentication +++
async def get_optional_current_user(request: Request, db_session: Session = Depends(db.get_db)) -> Optional[models.User]:
    """
    Dependency that attempts to get the current user from JWT in the Authorization header.
    Returns the User object if authentication is successful, otherwise returns None.
    DOES NOT raise HTTPException on authentication failure.
    Use this for routes that can be accessed by both guests and logged-in users.
    """
    token: Optional[str] = None
    credentials_exception_detail = "Could not validate credentials" # For logging

    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        else:
            # Malformed header, treat as no token provided
            credentials_exception_detail = "Invalid Authorization header format"
            # print(f"Optional Auth Debug: {credentials_exception_detail}") # Debug

    if not token:
        # No token found in header
        # print("Optional Auth Debug: No bearer token found in header.") # Debug
        return None

    try:
        payload = jwt.decode(token, config.settings.SECRET_KEY, algorithms=[config.settings.ALGORITHM])
        user_id: int | None = payload.get("user_id")

        if user_id is None:
            credentials_exception_detail = "Token missing user_id"
            # print(f"Optional Auth Debug: {credentials_exception_detail}") # Debug
            return None # Treat missing user_id as invalid token for this purpose

        # Fetch user from DB
        user = db_session.query(models.User).filter(models.User.id == user_id).first()
        if user is None:
            credentials_exception_detail = f"User ID {user_id} from token not found in DB"
            # print(f"Optional Auth Debug: {credentials_exception_detail}") # Debug
            return None # User doesn't exist

        # print(f"Optional Auth Debug: User {user.id} authenticated successfully.") # Debug
        return user # Authentication successful, return user object

    except JWTError as e:
         credentials_exception_detail = f"JWT Decode Error: {e}"
         # print(f"Optional Auth Debug: {credentials_exception_detail}") # Debug
         return None # Token is invalid (expired, bad signature, etc.)
    except Exception as e:
         credentials_exception_detail = f"Unexpected token decode error: {e}"
         # print(f"Optional Auth Debug: {credentials_exception_detail}") # Debug
         return None # Catch broader errors

# --- Placeholder Dependency (Keep as is or remove if not needed) ---
# We don't need this for the guest login flow, but keeping it doesn't hurt unless
# you want to clean up unused code.
async def track_and_authorize_simulation_placeholder() -> tuple[str, str | None]:
    """
    PLACEHOLDER.
    Simulates allowing anyone for now. Returns a fake ID.
    Replace this with proper logic using Redis and JWT checks later if needed elsewhere.
    """
    import random # Import here if needed
    print("WARNING: Using placeholder authorization - allowing all simulation starts.")
    guest_id = f"guest_{random.randint(1000, 9999)}"
    user_id_if_known = None
    return guest_id, user_id_if_known