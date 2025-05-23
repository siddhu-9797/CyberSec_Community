# workers/tasks.py

import json
import uuid
import traceback # For detailed error logging
import time # For retry delay
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, List, Dict, Any
import random

# --- Utilities assumed to exist (e.g., in ask_utils.py or similar) ---
# These helpers should ideally manage their own Redis connections via get_worker_redis_connection
# and handle JSON encoding/decoding and error logging internally.
try:
    from .ask_utils import load_simulation_state, save_simulation_state
except ImportError:
    print("WARNING: Could not import state helpers from ask_utils. Falling back to basic Redis calls if needed.")
    # Define dummy functions if needed, or let it fail later if calls are made
    def load_simulation_state(sim_id, redis_conn=None): return None
    def save_simulation_state(sim_id, state_dict, redis_conn=None): return False
# ---
from app.db import get_db_session_context
from app.crud import upsert_llm_rating_data
from rq.job import Job
# RQ imports
from rq import get_current_job, Queue
import redis # Need base redis for exceptions
from rq_scheduler import Scheduler

# Simulation and Config Imports (adjust paths if needed based on run context)
try:
    from .simulation_manager import (
        SimulationManager,
        scenarios, # Needed by load_simulation if it reconstructs manager fully
        default_agents, # Needed by load_simulation if it reconstructs manager fully
        BACKGROUND_THREAD_CHECK_INTERVAL_REALTIME_SECONDS
    )
    from .rq_config import default_queue # Import the default RQ Queue
    from app.db import get_worker_redis_connection # Function to get task-specific Redis connection
    from app.config import settings # App settings if needed (e.g., indirectly by SimManager)
    RQ_AVAILABLE = True
except ImportError as e:
    print(f"ERROR importing modules in tasks.py: {e}. Worker tasks may fail.")
    # Define dummies/fallbacks
    SimulationManager = None; scenarios = {}; default_agents = {}
    default_queue = None
    get_worker_redis_connection = lambda retries=1, delay=1: (_ for _ in ()).throw(RuntimeError("Redis connection function unavailable"))
    settings = None; BACKGROUND_THREAD_CHECK_INTERVAL_REALTIME_SECONDS = 10
    RQ_AVAILABLE = False


# --- Helper Functions ---

def publish_events(redis_publisher: redis.Redis, simulation_id: str, events: List[Dict[str, Any]]):
    """Publishes events to the Redis Pub/Sub channel for the simulation using the provided connection."""
    if not events or not simulation_id: return
    if not redis_publisher:
        print(f"[Worker Publish Error] Redis connection not provided for SimID {simulation_id}.")
        return

    channel = f"sim_events:{simulation_id}"
    published_count = 0
    log_prefix = f"[Worker Publish Sim={simulation_id[-8:]}]" # Add sim ID to log
    try:
        pipe = redis_publisher.pipeline()
        for i, event in enumerate(events):
            # Basic event structure validation
            if not isinstance(event, dict) or 'type' not in event or 'payload' not in event:
                print(f"{log_prefix} - WARNING: Event {i+1} has unexpected structure: {str(event)[:200]}")
                continue

            # Add simulation_id to payload if it's a dict
            if isinstance(event.get('payload'), dict):
                 event['payload']['simulation_id'] = simulation_id

            try:
                event_json = json.dumps(event, default=str) # Use default=str for datetimes etc.
                pipe.publish(channel, event_json)
                published_count += 1
            except TypeError as json_err:
                print(f"{log_prefix} - ERROR: Failed serializing event {i+1} for {channel}: {json_err}. Event: {str(event)[:200]}")
            except Exception as e_inner:
                print(f"{log_prefix} - ERROR: Processing event {i+1} for {channel}: {type(e_inner).__name__}")

        if published_count > 0:
            results = pipe.execute()
            # print(f"{log_prefix} - Published {published_count} events. Results: {results}") # Debug
    except redis.exceptions.ConnectionError as conn_err:
         print(f"{log_prefix} - ERROR: Redis connection error publishing to {channel}: {conn_err}")
    except Exception as e:
        print(f"{log_prefix} - ERROR: Failed publishing {len(events)} events to {channel}: {type(e).__name__} - {e}")
        print(traceback.format_exc())


def load_simulation(redis_client: redis.Redis, simulation_id: str) -> Optional[SimulationManager]:
    """
    Loads simulation state from Redis using a helper and returns an initialized SimulationManager.
    Uses the provided redis_client connection.
    """
    log_prefix = f"[Worker Load Sim={simulation_id[-8:]}]"
    if not SimulationManager:
        print(f"{log_prefix} - ERROR: SimulationManager class not loaded.")
        return None

    # Use the state loading helper, passing the connection
    state_data = load_simulation_state(simulation_id, redis_conn=redis_client)

    if not state_data:
        # Helper should log non-existence or load errors
        return None

    try:
        # Rehydrate the SimulationManager instance
        # Assuming SimulationManager constructor can handle being called again,
        # or ideally has a specific load_state method.
        # Pass IDs from state_data back to constructor if needed, or let load_state handle it.
        sim = SimulationManager(
            simulation_id=simulation_id,
            user_id=state_data.get('user_id'),
            guest_id=state_data.get('guest_id'),
            user_name=state_data.get('player_name') # Or user_name if stored separately
        )
        sim.load_state(state_data) # This method should restore all internal attributes

        # Critical: Ensure OpenAI client is ready after loading state
        if not sim.client:
             sim.log_event("ERROR (Load Task): Failed to re-initialize OpenAI client after loading state.", level="error", store_for_rating=True)
             # State might be partially loaded, attempt saving the error log? Risky.
             # save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_client)
             raise RuntimeError(f"Failed to initialize OpenAI client in SimulationManager after loading state for {simulation_id}")

        # print(f"{log_prefix} - Simulation state loaded successfully.") # Debug
        return sim
    except Exception as e:
        print(f"{log_prefix} - ERROR: Unexpected error initializing SimulationManager from state: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        return None


def schedule_next_background_check(simulation_id: str, current_intensity_mod: float):
    """Schedules the next background check task using RQ Scheduler object."""
    log_prefix = f"[Worker Schedule Sim={simulation_id[-8:]}]" # Add sim ID
    if not RQ_AVAILABLE:
        print(f"{log_prefix} - ERROR: RQ components unavailable.")
        return

    redis_conn_sched = None
    scheduler = None
    try:
        redis_conn_sched = get_worker_redis_connection()
        if not redis_conn_sched:
             print(f"{log_prefix} - ERROR: Failed to get Redis connection for scheduling.")
             return

        # Ensure background_check_task is defined below or imported correctly
        scheduler = Scheduler(queue_name="default", connection=redis_conn_sched)

        interval_sec = BACKGROUND_THREAD_CHECK_INTERVAL_REALTIME_SECONDS
        jitter = random.uniform(0.8, 1.2)
        effective_intensity = max(0.1, current_intensity_mod) # Avoid zero/negative intensity
        delay_seconds = max(5.0, interval_sec * effective_intensity * jitter) # Min 5 sec delay
        delay = timedelta(seconds=delay_seconds)
        # print(f"{log_prefix} - Scheduling bg check via SCHEDULER in {delay}") # Debug

        job = scheduler.enqueue_in(
            delay,
            background_check_task, # The task function
            simulation_id          # Argument for the task
        )
        # print(f"{log_prefix} - Call to scheduler.enqueue_in finished. (Job obj: {job})") # Debug

        # --- Optional: Verify in Redis scheduler key ---
        # time.sleep(0.1)
        # verification_key_scheduler = "rq:scheduler:scheduled_jobs"
        # found_in_scheduler_key = False
        # try:
        #     current_timestamp = time.time()
        #     ready_jobs = redis_conn_sched.zrangebyscore(verification_key_scheduler, 0, current_timestamp + delay_seconds + 5, withscores=True)
        #     expected_timestamp = current_timestamp + delay_seconds
        #     for item_bytes, score in ready_jobs:
        #          if abs(score - expected_timestamp) < 5:
        #               job_id_from_redis = item_bytes.decode()
        #               print(f"{log_prefix} - VERIFIED: Found job {job_id_from_redis} in {verification_key_scheduler} near expected time {expected_timestamp:.0f}.")
        #               found_in_scheduler_key = True; break
        #     if not found_in_scheduler_key:
        #         print(f"{log_prefix} - WARNING: Verification failed - job not found near expected time in {verification_key_scheduler}")
        # except Exception as redis_check_err: print(f"{log_prefix} - WARNING: Error checking Redis scheduled keys: {redis_check_err}")
        # --- End Optional Verification ---

    except Exception as e:
         print(f"{log_prefix} - ERROR: Failed scheduling bg check: {type(e).__name__} - {e}")
         print(traceback.format_exc())
    finally:
        if redis_conn_sched:
             try: redis_conn_sched.close()
             except Exception as close_e: print(f"Sched Redis close error: {close_e}")


def enqueue_rating_task(simulation_id: str):
    """Enqueues the LLM rating task."""
    log_prefix = f"[Worker Enqueue Rating Sim={simulation_id[-8:]}]" # Add sim ID
    if not RQ_AVAILABLE or not default_queue:
        print(f"{log_prefix} - ERROR: RQ Queue unavailable.")
        return
    try:
        # Ensure generate_rating_task is defined below or imported
        print(f"{log_prefix} - Enqueuing rating task.")
        default_queue.enqueue(generate_rating_task, simulation_id, job_timeout=300) # 5 min timeout
    except Exception as e:
        print(f"{log_prefix} - ERROR: Failed enqueuing rating task: {type(e).__name__} - {e}")


# --- Access Verification Function ---

def verify_simulation_access(simulation_id: str, user_id_to_check: Optional[str]) -> bool:
    """
    Checks if access to the simulation is allowed for the given context.
    - If user_id_to_check is provided, checks for ownership.
    - If user_id_to_check is None, checks if it's a valid guest simulation.
    Returns True if access allowed, False otherwise.
    """
    redis_conn_check = None
    log_prefix = f"[Access Check Sim={simulation_id[-8:]}]"
    try:
        # Get a connection specific for this check
        redis_conn_check = get_worker_redis_connection(retries=2) # Allow a retry

        # Use the state loading helper, passing the connection
        state_data = load_simulation_state(simulation_id, redis_conn=redis_conn_check)

        if not state_data:
            # load_simulation_state logs "not found" or load errors.
            print(f"{log_prefix} - Denied: Simulation state not found or failed to load.")
            return False

        owner_user_id = state_data.get("user_id") # User who created it (can be None)
        sim_guest_id = state_data.get("guest_id") # Guest ID stored (should match sim_id for guests)

        if user_id_to_check is not None:
            # --- Authenticated user request: Check ownership ---
            user_id_str = str(user_id_to_check) # Ensure comparison is string vs string
            owner_user_id_str = str(owner_user_id) if owner_user_id is not None else None

            if owner_user_id_str and owner_user_id_str == user_id_str:
                # print(f"{log_prefix} - OK: User {user_id_str} owns simulation.") # Debug
                return True
            else:
                print(f"{log_prefix} - Denied: User {user_id_str} requested access to sim owned by {owner_user_id_str}.")
                return False
        else:
            # --- Guest user request (user_id_to_check is None): Check guest criteria ---
            is_guest_sim_in_state = (owner_user_id is None and sim_guest_id is not None)
            # Verify the simulation ID matches the guest ID stored in state
            is_id_match = (sim_guest_id == simulation_id)

            if is_guest_sim_in_state and is_id_match:
                # print(f"{log_prefix} - OK: Guest access granted.") # Debug
                return True
            elif is_guest_sim_in_state and not is_id_match:
                 print(f"{log_prefix} - Denied: Guest access attempt but simulation_id '{simulation_id}' != stored guest_id '{sim_guest_id}'.")
                 return False
            else:
                print(f"{log_prefix} - Denied: Guest access attempt, but state indicates not a guest simulation (owner={owner_user_id}, guest={sim_guest_id}).")
                return False

    except redis.exceptions.ConnectionError as e:
        print(f"{log_prefix} - ERROR: Redis connection failed during access check: {e}")
        return False
    # JSONDecodeError should be handled by load_simulation_state helper
    except Exception as e:
        # Catch any other unexpected errors during the check
        print(f"{log_prefix} - ERROR: Unexpected error during access check: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        return False
    finally:
         # Close the connection obtained specifically for this check
         if redis_conn_check:
             try: redis_conn_check.close()
             except Exception as close_e: print(f"{log_prefix}: Error closing check Redis conn: {close_e}")


# --- RQ Task Definitions ---

def start_simulation_task(
    simulation_id: str,              # Pre-generated ID (user_... or guest_...)
    user_id: Optional[str],          # ID of authenticated user, or None for guests
    guest_id: Optional[str],         # Should match simulation_id if guest, None otherwise
    user_name: Optional[str],        # User's first name or "Guest"
    scenario_key: str,
    intensity_key: str,
    duration_minutes_arg: int
    ) -> Optional[str]:              # Return success message or None
    """
    Task to initialize a new simulation state in Redis.
    Uses the simulation_id generated by the API. Saves state, publishes initial events,
    and schedules the first background check.
    """
    redis_task_conn = None # Connection for THIS task's operations
    job = get_current_job()
    log_prefix = f"[Worker StartSim {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
    print(f"{log_prefix}: Received request. User={user_id}, GuestID={guest_id}, Name={user_name}, Scenario={scenario_key}")

    if not RQ_AVAILABLE:
        print(f"{log_prefix}: ERROR - RQ/Redis components unavailable.")
        return None

    try:
        # Get connection for state R/W and publishing for THIS task
        redis_task_conn = get_worker_redis_connection()
        # print(f"{log_prefix}: Acquired task-specific Redis connection.") # Debug

        # Initialize SimulationManager instance - crucial it stores IDs/name correctly
        sim = SimulationManager(simulation_id=simulation_id, user_id=user_id, guest_id=guest_id, user_name=user_name)

        # Check if OpenAI client initialized correctly within SimulationManager
        if not sim.client:
             sim.log_event("ERROR (Start Task): Failed to initialize OpenAI client.", level="error", store_for_rating=True)
             save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn) # Save state with error log
             raise RuntimeError("Failed to initialize OpenAI client in SimulationManager.")

        sim._clear_current_events()

        # Call the method that encapsulates setup logic (scenario, time, agents, initial events)
        success = sim.start_simulation(scenario_key, intensity_key, duration_minutes_arg)

        if not success:
            # start_simulation should have logged the specific error
            print(f"{log_prefix}: ERROR - SimulationManager.start_simulation returned failure.")
            save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn) # Save state with failure log
            return None

        initial_events = sim._get_and_clear_current_events()
        # print(f"{log_prefix}: Got {len(initial_events)} initial events.") # Debug

        # Save the fully initialized state using the helper (passes task connection)
        save_success = save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn)
        if not save_success:
            print(f"{log_prefix}: ERROR - Failed to save initial state to Redis. Aborting further steps.")
            # Error logged by save_simulation_state. Optionally publish error event.
            error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": "Failed to save initial simulation state."}}
            try: publish_events(redis_task_conn, simulation_id, [error_event])
            except Exception: pass
            return None

        # print(f"{log_prefix}: Initial state saved to Redis.") # Debug

        # Publish the collected initial events using THIS task's connection
        publish_events(redis_task_conn, simulation_id, initial_events)
        # print(f"{log_prefix}: Initial events published.") # Debug

        # Schedule the first background check task
        schedule_next_background_check(simulation_id, sim.current_intensity_mod)

        print(f"{log_prefix}: Initialization successful.")
        return "Simulation initialized successfully."

    except Exception as e:
        print(f"{log_prefix}: ERROR during simulation setup: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": f"Failed to initialize simulation task: {type(e).__name__}"}}
        try:
            if redis_task_conn: # Only publish if connection was obtained
                publish_events(redis_task_conn, simulation_id, [error_event])
                # print(f"{log_prefix}: Published setup error event.") # Debug
            else:
                print(f"{log_prefix}: Cannot publish setup error event - Redis connection failed earlier.")
        except Exception as pub_e:
            print(f"{log_prefix}: ERROR - Additionally failed publishing setup error event: {pub_e}")
        return None
    finally:
        if redis_task_conn:
            try:
                redis_task_conn.close()
                # print(f"{log_prefix}: Closed task Redis connection.") # Debug
            except Exception as close_e:
                print(f"{log_prefix}: Error closing task Redis connection: {close_e}")


def handle_action_task(simulation_id: str, action: str):
    """Task to process a player action."""
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker Action {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"

    if not RQ_AVAILABLE: print(f"{log_prefix}: ERROR - RQ components unavailable."); return
    try:
        redis_task_conn = get_worker_redis_connection()
    except Exception as e: print(f"{log_prefix}: ERROR - Failed getting task Redis connection: {e}"); return

    sim = load_simulation(redis_task_conn, simulation_id)
    if not sim:
        # load_simulation logs error/not found. Optionally publish generic error.
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": "Simulation not found or failed to load for action."}}
        try: publish_events(redis_task_conn, simulation_id, [error_event])
        except Exception: pass
        if redis_task_conn: redis_task_conn.close(); return

    if not sim.simulation_running:
         print(f"{log_prefix}: Simulation not running (State: {sim.simulation_state}). Action '{action[:30]}...' ignored.")
         if redis_task_conn: redis_task_conn.close(); return

    initial_state = sim.simulation_state

    try:
        sim._clear_current_events()
        sim.handle_player_input(action) # Execute action logic synchronously

        state_changed_to_debrief = (initial_state != "POST_INITIAL_CRISIS" and sim.simulation_state == "POST_INITIAL_CRISIS")
        state_changed_to_ended = (initial_state != "ENDED" and sim.simulation_state == "ENDED")

        # Save state unless simulation just ended (end_simulation handles final save/delete)
        if sim.simulation_running or state_changed_to_debrief:
            save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn)
        elif state_changed_to_ended:
             print(f"{log_prefix}: Simulation ended during action processing.")
             # SimulationManager.end_simulation should handle final save/delete

        events = sim._get_and_clear_current_events()
        publish_events(redis_task_conn, simulation_id, events) # Use task connection

        if state_changed_to_debrief:
            enqueue_rating_task(simulation_id)

    except Exception as e:
        print(f"{log_prefix}: ERROR handling action '{action[:50]}...': {type(e).__name__} - {e}")
        print(traceback.format_exc())
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": f"Error processing action: {type(e).__name__}"}}
        try: publish_events(redis_task_conn, simulation_id, [error_event])
        except Exception: pass
    finally:
         if redis_task_conn:
             try: redis_task_conn.close()
             except Exception as close_e: print(f"{log_prefix}: Error closing task Redis connection: {close_e}")


def handle_briefing_task(simulation_id: str, talking_points: str):
    """Task to process submitted analyst briefing points."""
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker Briefing {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
    # print(f"{log_prefix}: Handling briefing points...") # Debug

    if not RQ_AVAILABLE: print(f"{log_prefix}: ERROR - RQ components unavailable."); return
    try:
        redis_task_conn = get_worker_redis_connection()
    except Exception as e: print(f"{log_prefix}: ERROR - Failed getting task Redis connection: {e}"); return

    sim = load_simulation(redis_task_conn, simulation_id)
    if not sim:
        # load_simulation logs error
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": "Simulation not found or failed to load for briefing."}}
        try: publish_events(redis_task_conn, simulation_id, [error_event])
        except Exception: pass
        if redis_task_conn: redis_task_conn.close(); return

    try:
        sim._clear_current_events()
        # Calls LLM synchronously and then calls end_simulation internally
        sim.handle_analyst_briefing(talking_points)

        # State saving/deletion handled within sim.handle_analyst_briefing -> sim.end_simulation
        events = sim._get_and_clear_current_events()
        publish_events(redis_task_conn, simulation_id, events) # Use task connection
        print(f"{log_prefix}: Briefing processed and simulation ended.")

    except Exception as e:
        print(f"{log_prefix}: ERROR handling briefing: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": f"Error processing briefing: {type(e).__name__}"}}
        try: publish_events(redis_task_conn, simulation_id, [error_event])
        except Exception: pass
    finally:
        if redis_task_conn:
            try: redis_task_conn.close()
            except Exception as close_e: print(f"{log_prefix}: Error closing task Redis connection: {close_e}")


def background_check_task(simulation_id: str):
    """
    Task for periodic background checks (time sync, intensity, events, noise).
    Reschedules itself if the simulation is still active.
    """
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker BGCheck {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"

    if not RQ_AVAILABLE: print(f"{log_prefix}: ERROR - RQ components unavailable."); return
    try:
        redis_task_conn = get_worker_redis_connection()
    except Exception as e: print(f"{log_prefix}: ERROR - Failed getting task Redis connection: {e}"); return

    sim = load_simulation(redis_task_conn, simulation_id)
    if not sim:
        # load_simulation logs error
        if redis_task_conn: redis_task_conn.close(); return

    initial_state = sim.simulation_state
    sim_was_running = sim.simulation_running

    try:
        # Check if sim should have background processing run
        if not sim_was_running or sim.simulation_state in ["ENDED", "SETUP", "POST_INITIAL_CRISIS", "DECISION_POINT_SHUTDOWN", "AWAITING_ANALYST_BRIEFING"]:
            # print(f"{log_prefix}: Skipping background logic - Sim state '{sim.simulation_state}' running={sim_was_running}.") # Debug
            if redis_task_conn: redis_task_conn.close(); return # Don't process or reschedule

        sim._clear_current_events()
        sim_time_updated = False

        # --- Real-Time Synchronization Logic ---
        # (Keep the logic exactly as in the previous version - it seems correct)
        now_real_utc = datetime.now(timezone.utc)
        if sim.last_real_time_sync and sim.last_real_time_sync.tzinfo and \
           sim.simulation_time and sim.simulation_time.tzinfo and \
           sim.simulation_end_time and sim.simulation_end_time.tzinfo:
            last_sync_real_utc = sim.last_real_time_sync.astimezone(timezone.utc)
            real_delta = now_real_utc - last_sync_real_utc
            if real_delta > timedelta(seconds=0.1):
                remaining_sim_duration = sim.simulation_end_time - sim.simulation_time
                if remaining_sim_duration < timedelta(0): remaining_sim_duration = timedelta(0)
                advance_amount = min(real_delta, remaining_sim_duration)
                if advance_amount > timedelta(seconds=0):
                    sim.simulation_time += advance_amount
                    sim_time_updated = True
                    sim_time_iso = sim.simulation_time.isoformat()
                    end_time_iso = sim.simulation_end_time.isoformat()
                    # print(f"{log_prefix}: Auto-advanced sim time by {advance_amount} to {sim_time_iso}") # Debug
                    sim.emit_event("time_update", {"sim_time_iso": sim_time_iso, "end_time_iso": end_time_iso})
                    sim.check_end_conditions() # Check immediately
        sim.last_real_time_sync = now_real_utc
        # --- End Real-Time Sync ---

        # --- Run Other Background Checks (if still active) ---
        if sim.simulation_running and sim.simulation_state not in ["ENDED", "POST_INITIAL_CRISIS", "DECISION_POINT_SHUTDOWN", "AWAITING_ANALYST_BRIEFING"]:
            sim.check_dynamic_intensity()
            sim._generate_background_noise_logs()
            sim.check_background_events() # This might change state and call end_simulation
        # --- End Other Checks ---

        # --- Process Results & Reschedule ---
        state_changed_to_debrief = (initial_state != "POST_INITIAL_CRISIS" and sim.simulation_state == "POST_INITIAL_CRISIS")
        state_changed_to_ended = (initial_state != "ENDED" and sim.simulation_state == "ENDED")
        reschedule_next = False

        # Determine if rescheduling needed BEFORE saving state
        if sim.simulation_running and sim.simulation_state not in ["ENDED", "POST_INITIAL_CRISIS", "DECISION_POINT_SHUTDOWN", "AWAITING_ANALYST_BRIEFING"]:
             reschedule_next = True

        # Save state if it changed, time updated, or state transitioned
        if sim_time_updated or (sim.simulation_state != initial_state) or state_changed_to_debrief or state_changed_to_ended:
            save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn)

        events = sim._get_and_clear_current_events()
        publish_events(redis_task_conn, simulation_id, events) # Use task connection

        if state_changed_to_debrief:
            print(f"{log_prefix}: State changed to POST_INITIAL_CRISIS, enqueuing rating task.")
            enqueue_rating_task(simulation_id)

        if reschedule_next:
            schedule_next_background_check(simulation_id, sim.current_intensity_mod)
        # else: print(f"{log_prefix}: Not rescheduling background check.") # Debug

    except Exception as e:
        print(f"{log_prefix}: ERROR during background check execution: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": f"Error during background processing: {type(e).__name__}"}}
        try: publish_events(redis_task_conn, simulation_id, [error_event])
        except Exception: pass
        print(f"{log_prefix}: Stopping background checks due to error.")
    finally:
        if redis_task_conn:
            try: redis_task_conn.close()
            except Exception as close_e: print(f"{log_prefix}: Error closing task Redis connection: {close_e}")


# def generate_rating_task(simulation_id: str):
#     """Task to generate the LLM performance rating and then trigger the briefing prompt."""
#     redis_task_conn = None
#     job = get_current_job()
#     log_prefix = f"[Worker Rating {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
#     # print(f"{log_prefix}: Generating rating...") # Debug

#     if not RQ_AVAILABLE or not default_queue:
#          print(f"{log_prefix}: ERROR - RQ Queue unavailable."); return
#     try:
#         redis_task_conn = get_worker_redis_connection()
#     except Exception as e: print(f"{log_prefix}: ERROR - Failed getting task Redis connection: {e}"); return

#     sim = load_simulation(redis_task_conn, simulation_id)
#     if not sim:
#          # load_simulation logs error
#          if redis_task_conn: redis_task_conn.close(); return

#     rating_result = {"error": "Rating generation failed unexpectedly."} # Default error
#     try:
#         rating_result = sim._call_llm_for_rating() # Calls LLM synchronously
#         # print(f"{log_prefix}: Rating generation finished.") # Debug
#                 # Check if the LLM call was successful (i.e., no 'error' key from LLM, or if present, not the default)
#         # A more robust check might be to look for expected keys from a successful LLM response.
#         if "error" not in rating_result:
#              llm_rating_successfully_generated = True
#              print(f"{log_prefix}: Rating generation finished successfully from LLM.")
#         else:
#              # LLM itself returned an error structure
#              print(f"{log_prefix}: Rating generation finished, but LLM returned an error: {rating_result.get('error')}")

#     except AttributeError:
#          err_msg = "Rating function missing in SimulationManager."
#          print(f"{log_prefix}: ERROR - {err_msg}")
#          rating_result = {"error": err_msg}
#     except Exception as e:
#          err_msg = f"Error generating rating: {type(e).__name__} - {e}"
#          print(f"{log_prefix}: ERROR - {err_msg}")
#          print(traceback.format_exc())
#          rating_result = {"error": err_msg}

#     # --- <<< NEW: SAVE LLM RATING TO BACKEND (conditionally) >>> ---
#     if llm_rating_successfully_generated:
#         try:
#             # Option A: Save to a simple log file (append mode)
#             log_file_path = f"./llm_ratings_log.txt" # Define your path
#             with open(log_file_path, "a", encoding="utf-8") as f_log: # Added encoding
#                 log_entry_data = {
#                     "simulation_id": simulation_id,
#                     "timestamp_utc": datetime.now(timezone.utc).isoformat(),
#                     "llm_rating": rating_result # This is the actual successful rating
#                 }
#                 f_log.write(json.dumps(log_entry_data) + "\n")
#             print(f"{log_prefix}: LLM Performance Rating saved to log file: {log_file_path}")
#         except Exception as save_e:
#             print(f"{log_prefix}: ERROR saving LLM rating to log file: {type(save_e).__name__} - {save_e}")
#             # Optionally, you might want to update rating_result to indicate saving failed
#             # or handle this error in a more sophisticated way.
#             # For now, we just print the error. The original rating_result (from LLM) is still intact.

#     # This 'finally' block now handles publishing the (potentially updated) rating_result
#     # and enqueuing the next task, regardless of whether the LLM call or saving succeeded.
#     try:
#         # Always attempt to publish the rating result (even if it's an error dict from LLM call or default)
#         rating_event = {"type": "debrief_rating_update", "payload": {"simulation_id": simulation_id, "performance_rating": rating_result}}
#         publish_events(redis_task_conn, simulation_id, [rating_event])
#         print(f"{log_prefix}: Published rating result/error to events.")
#     except Exception as pub_e:
#         print(f"{log_prefix}: ERROR publishing rating result/error to events: {pub_e}")
#     finally: # Nested finally to ensure next step enqueue and redis close
#         # Always attempt to publish the rating result (even if it's an error dict)
#         try:
#             rating_event = {"type": "debrief_rating_update", "payload": {"simulation_id": simulation_id, "performance_rating": rating_result}}
#             publish_events(redis_task_conn, simulation_id, [rating_event]) # Use task connection
#             # print(f"{log_prefix}: Published rating result/error.") # Debug
#         except Exception as pub_e:
#             print(f"{log_prefix}: ERROR publishing rating result: {pub_e}")

#         # ALWAYS enqueue the next step (triggering the prompt)
#         try:
#             # print(f"{log_prefix}: Enqueuing trigger_briefing_prompt_task.") # Debug
#             # Ensure trigger_briefing_prompt_task is defined below or imported
#             default_queue.enqueue(trigger_briefing_prompt_task, simulation_id, job_timeout=30)
#         except Exception as e_enqueue:
#             print(f"{log_prefix}: ERROR enqueuing trigger_briefing_prompt_task: {e_enqueue}")

#         if redis_task_conn:
#             try: redis_task_conn.close()
#             except Exception as close_e: print(f"{log_prefix}: Error closing task Redis connection: {close_e}")

def generate_rating_task(simulation_id: str): # This is the one called when debrief starts
    """
    Task to generate the LLM performance rating, SAVE IT, publish it,
    and then trigger the analyst briefing prompt task.
    """
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker GenRating {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"

    if not RQ_AVAILABLE or not default_queue:
         print(f"{log_prefix}: ERROR - RQ Queue unavailable."); return

    llm_rating_successfully_generated = False
    rating_result = {"error": "Rating generation failed unexpectedly."}

    try:
        redis_task_conn = get_worker_redis_connection()
        sim = load_simulation(redis_task_conn, simulation_id)
        if not sim:
             if redis_task_conn: redis_task_conn.close()
             return

        try:
            rating_result = sim._call_llm_for_rating()
            if "error" not in rating_result:
                 llm_rating_successfully_generated = True
                 print(f"{log_prefix}: LLM Performance Rating generated: {rating_result}")
            else:
                 print(f"{log_prefix}: LLM Performance Rating generation returned error: {rating_result.get('error')}")
        except AttributeError:
             rating_result = {"error": "Rating function missing in SimulationManager."}
             print(f"{log_prefix}: ERROR - {rating_result['error']}")
        except Exception as e_llm:
             rating_result = {"error": f"Error generating LLM rating: {type(e_llm).__name__} - {e_llm}"}
             print(f"{log_prefix}: ERROR - {rating_result['error']}\n{traceback.format_exc()}")

        # --- SAVE LLM RATING TO DATABASE (if successful) ---
        if llm_rating_successfully_generated:
            try:
                with get_db_session_context() as db_session:
                    upsert_llm_rating_data(
                        db=db_session,
                        simulation_id_str=simulation_id,
                        llm_rating_data=rating_result,
                        user_id_str=sim.user_id,
                        scenario_key=sim.selected_scenario_key
                    )
                    print(f"{log_prefix}: LLM Performance Rating saved to database.")
            except Exception as save_e:
                print(f"{log_prefix}: ERROR saving LLM Performance Rating to database: {type(save_e).__name__} - {save_e}")
                print(traceback.format_exc())
        # --- END SAVE LLM RATING ---

    except Exception as outer_e:
        print(f"{log_prefix}: Outer error during LLM rating generation/saving: {type(outer_e).__name__} - {outer_e}")
        # rating_result will contain the error from LLM call or the default one
    finally:
        # Always attempt to publish the rating result to the frontend
        try:
            if redis_task_conn: # Ensure connection was obtained
                rating_event = {"type": "debrief_rating_update", "payload": {"simulation_id": simulation_id, "performance_rating": rating_result}}
                publish_events(redis_task_conn, simulation_id, [rating_event])
        except Exception as pub_e:
            print(f"{log_prefix}: ERROR publishing LLM rating result to events: {pub_e}")

        # THEN, ALWAYS enqueue the next step: triggering the analyst briefing prompt
        try:
            if default_queue:
                print(f"{log_prefix}: Enqueuing trigger_briefing_prompt_task.")
                default_queue.enqueue(trigger_briefing_prompt_task, simulation_id, job_timeout=60) # Increased timeout slightly
            else:
                print(f"{log_prefix}: ERROR - Default queue not available for trigger_briefing_prompt_task.")
        except Exception as e_enqueue:
            print(f"{log_prefix}: ERROR enqueuing trigger_briefing_prompt_task: {e_enqueue}")

        if redis_task_conn:
            try: redis_task_conn.close()
            except Exception: pass


def trigger_briefing_prompt_task(simulation_id: str):
    """
    Task to emit the prompt asking the user if they want to prepare briefing points.
    Runs AFTER the rating task has attempted to generate/publish its result.
    """
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker BriefPrompt {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
    # print(f"{log_prefix}: Triggering briefing prompt.") # Debug

    if not RQ_AVAILABLE: print(f"{log_prefix}: ERROR - RQ components unavailable."); return
    try:
        redis_task_conn = get_worker_redis_connection()
    except Exception as e: print(f"{log_prefix}: ERROR - Failed getting task Redis connection: {e}"); return

    sim = load_simulation(redis_task_conn, simulation_id)
    if not sim:
        # load_simulation logs error
        if redis_task_conn: redis_task_conn.close(); return

    try:
        # Only send prompt if in the correct state
        if sim.simulation_state == "POST_INITIAL_CRISIS":
            # print(f"{log_prefix}: Sim state is '{sim.simulation_state}'. Emitting prompt.") # Debug
            sim._clear_current_events()
            sim.emit_event("request_yes_no", {
                "prompt": "Optional: Prepare analyst briefing points based on this outcome? (yes/no)",
                "action_context": "prepare_analyst_briefing"
            })
            events = sim._get_and_clear_current_events()
            publish_events(redis_task_conn, simulation_id, events) # Use task connection
        # else: print(f"{log_prefix}: Skipping prompt - Sim state is '{sim.simulation_state}'.") # Debug

    except Exception as e:
        print(f"{log_prefix}: ERROR emitting briefing prompt: {type(e).__name__} - {e}")
        print(traceback.format_exc())
    finally:
        if redis_task_conn:
            try: redis_task_conn.close()
            except Exception as close_e: print(f"{log_prefix}: Error closing task Redis connection: {close_e}")