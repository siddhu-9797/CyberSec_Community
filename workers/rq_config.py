from redis import Redis
from rq import Queue
import os
# Assuming config is accessible via relative import path if needed
# Or load REDIS_URL directly from env here
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create connection and queue instance
# Workers and API will import 'default_queue' from this file
redis_conn = Redis.from_url(REDIS_URL)
default_queue = Queue("default", connection=redis_conn) # Use the 'default' queue name
high_priority_queue = Queue("high", connection=redis_conn) # Example if needed later

print(f"RQ configured with Redis at: {REDIS_URL}")