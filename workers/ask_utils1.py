# workers/task_utils.py (Create or add to this file)

import json
from redis import Redis
from app.db import get_worker_redis_connection # Assuming this provides sync connection

# (Keep load_simulation_state and save_simulation_state here)
def load_simulation_state(simulation_id: str) -> dict | None:
    # ... your existing implementation ...
    r = None
    try:
        r = get_worker_redis_connection()
        state_key = f"sim_state:{simulation_id}"
        state_json = r.get(state_key)
        if state_json:
            return json.loads(state_json)
        return None
    except Exception as e:
        print(f"[Task Utils] Error loading state for {simulation_id}: {e}")
        return None
    finally:
        if r: r.close()


def save_simulation_state(simulation_id: str, state_dict: dict) -> bool: # Return bool for success/failure
    """Saves the simulation state dictionary to Redis after JSON serialization."""
    r = None
    state_json = None # Initialize
    state_key = f"sim_state:{simulation_id}"
    log_prefix = "[Task Utils Save]" # Add prefix for clarity

    try:
        r = get_worker_redis_connection()

        # Add owner_user_id if not present - DO THIS *BEFORE* serialization
        # Ensure user_id exists and is not None before assigning
        owner_id = state_dict.get('user_id')
        if 'owner_user_id' not in state_dict and owner_id is not None:
            state_dict['owner_user_id'] = str(owner_id) # Convert to string just in case

        # --- Attempt JSON serialization ---
        try:
            state_json = json.dumps(state_dict)
        except TypeError as json_err:
            # --->> THIS IS THE CRITICAL ERROR <<---
            print(f"{log_prefix} Error saving state for {simulation_id}: {json_err}")
            print(f"{log_prefix} Failed object type: {type(json_err.__cause__ if hasattr(json_err, '__cause__') else None)}") # Try to find failing type
            # Optionally log the problematic part of the state_dict if possible
            # print(f"{log_prefix} State fragment near error: ...")
            raise # Re-raise the TypeError to stop the task properly
        except Exception as dump_err:
             print(f"{log_prefix} Unexpected error during json.dumps for {simulation_id}: {dump_err}")
             raise # Re-raise other dump errors too

        # --->> Only set if serialization succeeded <<---
        r.set(state_key, state_json, ex=3600) # Set expiry (e.g., 1 hour)
        # print(f"{log_prefix} Saved state for {simulation_id}") # Keep this log for success confirmation
        return True # Indicate success

    except Exception as e:
        # Catch errors from getting connection or the re-raised TypeError
        # Avoid printing the generic "Error saving state" again if it was a TypeError
        if not isinstance(e, TypeError): # Only print if it wasn't the JSON error
             print(f"{log_prefix} Error in save_simulation_state for {simulation_id}: {type(e).__name__} - {e}")
        # Optionally print traceback for non-TypeErrors
        # if not isinstance(e, TypeError): print(traceback.format_exc())
        return False # Indicate failure

    finally:
        if r:
            try:
                r.close()
            except Exception as close_e:
                 print(f"{log_prefix} Error closing save Redis conn: {close_e}")
# --- NEW ---
def publish_event(redis_client: Redis, simulation_id: str, event: dict):
    """Publishes a simulation event to the Redis Pub/Sub channel."""
    if not redis_client:
        print("[Task Utils Publish] ERROR: Redis client not provided.")
        return
    try:
        channel = f"sim_events:{simulation_id}"
        event_json = json.dumps(event)
        redis_client.publish(channel, event_json)
        # print(f"[Task Utils Publish] Published event type '{event.get('type')}' to {channel}") # Debug
    except Exception as e:
        print(f"[Task Utils Publish] ERROR publishing event for {simulation_id}: {type(e).__name__} - {e}")