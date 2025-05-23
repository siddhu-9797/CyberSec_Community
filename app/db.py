# db.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from .config import settings
import redis
import time
from contextlib import contextmanager # For context manager


# Database Configuration
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# SQLAlchemy engine and session setup
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,      # <<< ADD THIS LINE
    pool_recycle=1800        # <<< ADD THIS LINE (e.g., 30 minutes)
    # You can add other options here if needed, like connect_args
    # connect_args={"options": "-c timezone=utc"} # Example
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() # Closes the session, returning connection to pool
@contextmanager
def get_db_session_context() -> Session: # Type hint for clarity
    db = SessionLocal()
    try:
        yield db
        db.commit() # Commit on successful block execution
    except Exception:
        db.rollback() # Rollback on error
        raise
    finally:
        db.close()
# --- Redis Connection ---
# (Your Redis code looks fine for establishing the connection)
try:
    print(f"Attempting to connect to Redis at: {settings.REDIS_URL}")
    redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client = redis.Redis(connection_pool=redis_pool)
    redis_client.ping()
    print("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"FATAL ERROR: Could not connect to Redis at {settings.REDIS_URL}")
    print(f"Error details: {e}")
    redis_client = None
except Exception as e:
    print(f"FATAL ERROR: An unexpected error occurred during Redis setup: {e}")
    redis_client = None

# Function for workers to create their own Redis connection (not shared)
# (This Redis worker connection logic looks reasonable with retries)
def get_worker_redis_connection(retries=3, delay=2):
    # ... (rest of your Redis worker function)
    last_exception = None
    for attempt in range(retries):
        try:
            redis_url = settings.REDIS_URL if settings else "redis://localhost:6379/0"
            r = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=5)
            r.ping()
            return r
        except redis.exceptions.ConnectionError as e:
            print(f"[Worker Redis Conn Warning] Attempt {attempt + 1}/{retries} failed: {e}")
            last_exception = e
            if attempt < retries - 1:
                time.sleep(delay)
        except Exception as e:
            print(f"[Worker Redis Conn Error] Unexpected error on attempt {attempt + 1}: {type(e).__name__} - {e}")
            last_exception = e
            if attempt < retries - 1:
                time.sleep(delay)

    print(f"[Worker Redis Conn Error] All {retries} connection attempts failed.")
    raise last_exception or ConnectionError(f"Failed to connect to Redis at {redis_url} after {retries} retries")