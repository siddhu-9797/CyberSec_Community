# workers/task_utils.py (or ask_utils.py)

import json
import traceback
from redis import Redis
from app.db import get_worker_redis_connection # Assuming this provides sync connection
from typing import Dict, Any, Optional # Added Optional and type hints

# --- State Management Helpers ---

def load_simulation_state(simulation_id: str, redis_conn: Optional[Redis] = None) -> Optional[Dict[str, Any]]:
    """
    Loads simulation state dictionary from Redis.
    Manages its own connection if one is not provided.
    Returns the state dictionary or None if not found or on error.
    """
    r = None
    log_prefix = f"[Task Utils Load Sim={simulation_id[-8:]}]"
    conn_managed_internally = False
    try:
        if redis_conn:
            r = redis_conn
        else:
            r = get_worker_redis_connection(retries=2) # Allow a retry if getting new connection
            conn_managed_internally = True
            if not r: # Check if connection failed
                 print(f"{log_prefix} - ERROR: Failed to get Redis connection.")
                 return None

        state_key = f"sim_state:{simulation_id}"
        state_json = r.get(state_key)

        if not state_json:
            # print(f"{log_prefix} - State not found in Redis (key: {state_key}).") # Can be noisy
            return None

        # Ensure decoding if Redis client doesn't decode automatically
        if isinstance(state_json, bytes):
            state_data = json.loads(state_json.decode('utf-8'))
        else:
            state_data = json.loads(state_json)

        return state_data

    except json.JSONDecodeError as e:
         print(f"{log_prefix} - ERROR: Failed decoding JSON state: {e}")
         return None
    except redis.exceptions.ConnectionError as e:
         print(f"{log_prefix} - ERROR: Redis connection failed during load: {e}")
         return None
    except Exception as e:
        print(f"{log_prefix} - ERROR: Unexpected error loading state: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        return None
    finally:
        # Only close connection if it was managed internally by this function
        if conn_managed_internally and r:
            try:
                r.close()
            except Exception as close_e:
                 print(f"{log_prefix} - Error closing load Redis conn: {close_e}")


def save_simulation_state(simulation_id: str, state_dict: Dict[str, Any], redis_conn: Optional[Redis] = None, expiry_seconds: int = 3600) -> bool:
    """
    Saves the simulation state dictionary to Redis after JSON serialization.
    Manages its own connection if one is not provided.
    Returns True on success, False on failure.
    """
    r = None
    state_json = None
    state_key = f"sim_state:{simulation_id}"
    log_prefix = f"[Task Utils Save Sim={simulation_id[-8:]}]"
    conn_managed_internally = False

    try:
        if redis_conn:
            r = redis_conn
        else:
            r = get_worker_redis_connection(retries=2) # Allow retry
            conn_managed_internally = True
            if not r: # Check if connection failed
                 print(f"{log_prefix} - ERROR: Failed to get Redis connection.")
                 return False

        # --- Safety Check/Default: Add owner_user_id if missing and user_id exists ---
        # Ideally, SimulationManager.get_state() provides all needed fields consistently.
        owner_id = state_dict.get('user_id')
        if 'owner_user_id' not in state_dict and owner_id is not None:
            # print(f"{log_prefix} - WARNING: Adding 'owner_user_id' from 'user_id' during save.") # Debug
            state_dict['owner_user_id'] = str(owner_id) # Ensure string format

        # --- Attempt JSON serialization ---
        try:
            # Use default=str to handle potential non-serializable types like datetime
            state_json = json.dumps(state_dict, default=str)
        except TypeError as json_err:
            print(f"{log_prefix} - ERROR: Failed serializing state dictionary: {json_err}")
            # Attempt to identify the problematic type if possible
            # (This requires careful inspection and might not always work)
            # print(f"{log_prefix} - Debug info: Offending type might be near {type(json_err.__cause__ if hasattr(json_err, '__cause__') else None)}")
            raise # IMPORTANT: Re-raise TypeError to signal task failure
        except Exception as dump_err:
             print(f"{log_prefix} - ERROR: Unexpected error during json.dumps: {dump_err}")
             raise # Re-raise other serialization errors

        # --- Save to Redis with expiry ---
        # Ensure expiry is positive
        effective_expiry = max(60, expiry_seconds) if expiry_seconds is not None else None

        if effective_expiry:
            r.setex(state_key, effective_expiry, state_json)
        else:
            r.set(state_key, state_json) # Set without expiry if None or <= 0

        # print(f"{log_prefix} - State saved successfully (Expiry: {effective_expiry}s).") # Debug
        return True # Indicate success

    except redis.exceptions.ConnectionError as e:
         print(f"{log_prefix} - ERROR: Redis connection failed during save: {e}")
         return False
    except Exception as e:
        # Catch errors from getting connection or the re-raised TypeError/other dump errors
        if not isinstance(e, TypeError): # Avoid double-logging the specific serialization error
             print(f"{log_prefix} - ERROR: Unexpected error saving state: {type(e).__name__} - {e}")
             # print(traceback.format_exc()) # Optional: Log traceback for non-TypeErrors
        return False # Indicate failure
    finally:
        if conn_managed_internally and r:
            try:
                r.close()
            except Exception as close_e:
                 print(f"{log_prefix} - Error closing save Redis conn: {close_e}")


# --- Event Publishing Helper ---

def publish_event(redis_client: Redis, simulation_id: str, event: Dict[str, Any]):
    """
    Publishes a single simulation event dictionary to the Redis Pub/Sub channel.
    Requires an active Redis client connection to be passed.
    """
    log_prefix = f"[Task Utils Publish Sim={simulation_id[-8:]}]"
    if not redis_client:
        print(f"{log_prefix} - ERROR: Redis client not provided for publishing.")
        return
    if not isinstance(event, dict) or 'type' not in event:
         print(f"{log_prefix} - WARNING: Invalid event structure for publishing: {str(event)[:200]}")
         return

    try:
        channel = f"sim_events:{simulation_id}"
        # Add simulation_id to payload if it's a dict (safety check)
        if 'payload' in event and isinstance(event.get('payload'), dict):
            event['payload']['simulation_id'] = simulation_id

        # Use default=str for serialization robustness
        event_json = json.dumps(event, default=str)
        redis_client.publish(channel, event_json)
        # print(f"{log_prefix} - Published event type '{event.get('type')}' to {channel}") # Debug

    except redis.exceptions.ConnectionError as e:
        print(f"{log_prefix} - ERROR: Redis connection error publishing event: {e}")
    except TypeError as json_err:
         print(f"{log_prefix} - ERROR: Failed serializing event for publishing: {json_err}. Event: {str(event)[:200]}")
    except Exception as e:
        print(f"{log_prefix} - ERROR: Unexpected error publishing event: {type(e).__name__} - {e}")