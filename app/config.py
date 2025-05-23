from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field # Need this for computed DATABASE_URL
import os
from dotenv import load_dotenv

load_dotenv() # Load .env file

class Settings(BaseSettings):
    # Read individual DB parts from environment
    DB_NAME: str = os.getenv("DB_NAME", "")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: str = os.getenv("DB_PORT", "5432")

    # Read other specific keys
    # IMPORTANT: Use a STRONG, RANDOM key here in your actual .env or environment
    # The FLASK_SECRET_KEY from your example is NOT secure for JWT.
    # We'll read a variable named SECRET_KEY but you need to set it properly.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change_this_to_a_real_random_secret_in_env")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", 60)) # Read JWT expiry
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "") # Needed later

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ALGORITHM: str = "HS256"

    # Use model_config for compatibility if needed, or just direct assignment
    # model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @computed_field # Decorator to create a property based on others
    @property
    def DATABASE_URL(self) -> str:
        if not all([self.DB_USER, self.DB_PASSWORD, self.DB_HOST, self.DB_NAME]):
             # Return None or raise error if parts are missing
             # print("Warning: Missing database connection details in environment variables.")
             return "" # Or raise ValueError("Missing DB connection details")
        # Construct the SQLAlchemy URL
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()

# Add checks for essential runtime settings
if not settings.DATABASE_URL:
    raise ValueError("Could not construct DATABASE_URL. Check DB_* environment variables.")
if settings.SECRET_KEY == "change_this_to_a_real_random_secret_in_env":
    print("\n" + "="*60)
    print("WARNING: Using default SECRET_KEY. This is INSECURE.")
    print("Please set a strong, random SECRET_KEY environment variable.")
    print("="*60 + "\n")
# Check for OpenAI key later when SimulationManager is fully used
# if not settings.OPENAI_API_KEY:
#     print("WARNING: OPENAI_API_KEY environment variable not set. Simulations will fail.")