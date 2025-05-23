# workers/tasks.py

import json
import uuid
import traceback # For detailed error logging
import time # For retry delay
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, List, Dict, Any
import random

# --- Utilities assumed to exist (e.g., in ask_utils.py or similar) ---
try:
    from .ask_utils import load_simulation_state, save_simulation_state
except ImportError:
    print("WARNING: Could not import state helpers from ask_utils. Falling back to basic Redis calls if needed.")
    def load_simulation_state(sim_id, redis_conn=None): return None
    def save_simulation_state(sim_id, state_dict, redis_conn=None): return False
# ---

from rq.job import Job
from rq import get_current_job, Queue
import redis
from rq_scheduler import Scheduler

try:
    from .simulation_manager import (
        SimulationManager,
        scenarios,
        default_agents,
        BACKGROUND_THREAD_CHECK_INTERVAL_REALTIME_SECONDS
    )
    from .rq_config import default_queue
    from app.db import get_worker_redis_connection
    from app.config import settings
    RQ_AVAILABLE = True
except ImportError as e:
    print(f"ERROR importing modules in tasks.py: {e}. Worker tasks may fail.")
    SimulationManager = None; scenarios = {}; default_agents = {}
    default_queue = None
    get_worker_redis_connection = lambda retries=1, delay=1: (_ for _ in ()).throw(RuntimeError("Redis connection function unavailable"))
    settings = None; BACKGROUND_THREAD_CHECK_INTERVAL_REALTIME_SECONDS = 10
    RQ_AVAILABLE = False


# --- Helper Functions (publish_events, load_simulation, schedule_next_background_check) ---
# These remain unchanged from your provided code. I'll include them for completeness.

def publish_events(redis_publisher: redis.Redis, simulation_id: str, events: List[Dict[str, Any]]):
    """Publishes events to the Redis Pub/Sub channel for the simulation using the provided connection."""
    if not events or not simulation_id: return
    if not redis_publisher:
        print(f"[Worker Publish Error] Redis connection not provided for SimID {simulation_id}.")
        return

    channel = f"sim_events:{simulation_id}"
    published_count = 0
    log_prefix = f"[Worker Publish Sim={simulation_id[-8:]}]"
    try:
        pipe = redis_publisher.pipeline()
        for i, event in enumerate(events):
            if not isinstance(event, dict) or 'type' not in event or 'payload' not in event:
                print(f"{log_prefix} - WARNING: Event {i+1} has unexpected structure: {str(event)[:200]}")
                continue
            if isinstance(event.get('payload'), dict):
                 event['payload']['simulation_id'] = simulation_id
            try:
                event_json = json.dumps(event, default=str)
                pipe.publish(channel, event_json)
                published_count += 1
            except TypeError as json_err:
                print(f"{log_prefix} - ERROR: Failed serializing event {i+1} for {channel}: {json_err}. Event: {str(event)[:200]}")
            except Exception as e_inner:
                print(f"{log_prefix} - ERROR: Processing event {i+1} for {channel}: {type(e_inner).__name__}")
        if published_count > 0:
            results = pipe.execute()
    except redis.exceptions.ConnectionError as conn_err:
         print(f"{log_prefix} - ERROR: Redis connection error publishing to {channel}: {conn_err}")
    except Exception as e:
        print(f"{log_prefix} - ERROR: Failed publishing {len(events)} events to {channel}: {type(e).__name__} - {e}")
        print(traceback.format_exc())

def load_simulation(redis_client: redis.Redis, simulation_id: str) -> Optional[SimulationManager]:
    log_prefix = f"[Worker Load Sim={simulation_id[-8:]}]"
    if not SimulationManager:
        print(f"{log_prefix} - ERROR: SimulationManager class not loaded.")
        return None
    state_data = load_simulation_state(simulation_id, redis_conn=redis_client)
    if not state_data:
        return None
    try:
        sim = SimulationManager(
            simulation_id=simulation_id,
            user_id=state_data.get('user_id'),
            guest_id=state_data.get('guest_id'),
            user_name=state_data.get('player_name')
        )
        sim.load_state(state_data)
        if not sim.client:
             sim.log_event("ERROR (Load Task): Failed to re-initialize OpenAI client after loading state.", level="error", store_for_rating=True)
             raise RuntimeError(f"Failed to initialize OpenAI client in SimulationManager after loading state for {simulation_id}")
        return sim
    except Exception as e:
        print(f"{log_prefix} - ERROR: Unexpected error initializing SimulationManager from state: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        return None

def schedule_next_background_check(simulation_id: str, current_intensity_mod: float):
    log_prefix = f"[Worker Schedule Sim={simulation_id[-8:]}]"
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
        scheduler = Scheduler(queue_name="default", connection=redis_conn_sched)
        interval_sec = BACKGROUND_THREAD_CHECK_INTERVAL_REALTIME_SECONDS
        jitter = random.uniform(0.8, 1.2)
        effective_intensity = max(0.1, current_intensity_mod)
        delay_seconds = max(5.0, interval_sec * effective_intensity * jitter)
        delay = timedelta(seconds=delay_seconds)
        job = scheduler.enqueue_in(delay, background_check_task, simulation_id)
    except Exception as e:
         print(f"{log_prefix} - ERROR: Failed scheduling bg check: {type(e).__name__} - {e}")
         print(traceback.format_exc())
    finally:
        if redis_conn_sched:
             try: redis_conn_sched.close()
             except Exception: pass

# --- Access Verification Function (verify_simulation_access) ---
# This remains unchanged from your provided code.

def verify_simulation_access(simulation_id: str, user_id_to_check: Optional[str]) -> bool:
    redis_conn_check = None
    log_prefix = f"[Access Check Sim={simulation_id[-8:]}]"
    try:
        redis_conn_check = get_worker_redis_connection(retries=2)
        state_data = load_simulation_state(simulation_id, redis_conn=redis_conn_check)
        if not state_data:
            print(f"{log_prefix} - Denied: Simulation state not found or failed to load.")
            return False
        owner_user_id = state_data.get("user_id")
        sim_guest_id = state_data.get("guest_id")
        if user_id_to_check is not None:
            user_id_str = str(user_id_to_check)
            owner_user_id_str = str(owner_user_id) if owner_user_id is not None else None
            if owner_user_id_str and owner_user_id_str == user_id_str:
                return True
            else:
                print(f"{log_prefix} - Denied: User {user_id_str} requested access to sim owned by {owner_user_id_str}.")
                return False
        else:
            is_guest_sim_in_state = (owner_user_id is None and sim_guest_id is not None)
            is_id_match = (sim_guest_id == simulation_id)
            if is_guest_sim_in_state and is_id_match:
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
    except Exception as e:
        print(f"{log_prefix} - ERROR: Unexpected error during access check: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        return False
    finally:
         if redis_conn_check:
             try: redis_conn_check.close()
             except Exception: pass

# --- RQ Task Definitions ---

def start_simulation_task(
    simulation_id: str, user_id: Optional[str], guest_id: Optional[str],
    user_name: Optional[str], scenario_key: str, intensity_key: str, duration_minutes_arg: int
) -> Optional[str]:
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker StartSim {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
    print(f"{log_prefix}: Received request. User={user_id}, GuestID={guest_id}, Name={user_name}, Scenario={scenario_key}")

    if not RQ_AVAILABLE:
        print(f"{log_prefix}: ERROR - RQ/Redis components unavailable.")
        return None
    try:
        redis_task_conn = get_worker_redis_connection()
        sim = SimulationManager(simulation_id=simulation_id, user_id=user_id, guest_id=guest_id, user_name=user_name)
        if not sim.client:
             sim.log_event("ERROR (Start Task): Failed to initialize OpenAI client.", level="error", store_for_rating=True)
             save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn)
             raise RuntimeError("Failed to initialize OpenAI client in SimulationManager.")
        sim._clear_current_events()
        success, _ = sim.start_simulation(scenario_key, intensity_key, duration_minutes_arg) # Adjusted to match sim.start_simulation return
        if not success:
            print(f"{log_prefix}: ERROR - SimulationManager.start_simulation returned failure.")
            save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn)
            return None
        initial_events = sim._get_and_clear_current_events()
        save_success = save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn)
        if not save_success:
            print(f"{log_prefix}: ERROR - Failed to save initial state to Redis.")
            error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": "Failed to save initial simulation state."}}
            try: publish_events(redis_task_conn, simulation_id, [error_event])
            except Exception: pass
            return None
        publish_events(redis_task_conn, simulation_id, initial_events)
        schedule_next_background_check(simulation_id, sim.current_intensity_mod)
        print(f"{log_prefix}: Initialization successful.")
        return "Simulation initialized successfully."
    except Exception as e:
        print(f"{log_prefix}: ERROR during simulation setup: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": f"Failed to initialize simulation task: {type(e).__name__}"}}
        try:
            if redis_task_conn:
                publish_events(redis_task_conn, simulation_id, [error_event])
        except Exception: pass
        return None
    finally:
        if redis_task_conn:
            try: redis_task_conn.close()
            except Exception: pass

def handle_action_task(simulation_id: str, action: str):
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker Action {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
    if not RQ_AVAILABLE: print(f"{log_prefix}: ERROR - RQ components unavailable."); return
    try:
        redis_task_conn = get_worker_redis_connection()
    except Exception as e: print(f"{log_prefix}: ERROR - Failed getting task Redis connection: {e}"); return
    sim = load_simulation(redis_task_conn, simulation_id)
    if not sim:
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
        sim.handle_player_input(action)
        state_changed_to_debrief = (initial_state != "POST_INITIAL_CRISIS" and sim.simulation_state == "POST_INITIAL_CRISIS")
        state_changed_to_ended = (initial_state != "ENDED" and sim.simulation_state == "ENDED")
        if sim.simulation_running or state_changed_to_debrief: # Save if still running or just hit debrief
            save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn)
        elif state_changed_to_ended:
             print(f"{log_prefix}: Simulation ended during action processing.")
             # If end_simulation in sim_manager handles final save/cleanup, this is okay.
             # Otherwise, might need a final save here too if state not saved by sim.end_simulation() itself.
        events = sim._get_and_clear_current_events()
        publish_events(redis_task_conn, simulation_id, events)
        if state_changed_to_debrief:
            # This now starts the multi-step debrief flow
            if default_queue:
                default_queue.enqueue(generate_rating_task, simulation_id, job_timeout=300)
            else:
                print(f"{log_prefix} - ERROR: Default queue not available to enqueue LLM rating task.")
    except Exception as e:
        print(f"{log_prefix}: ERROR handling action '{action[:50]}...': {type(e).__name__} - {e}")
        print(traceback.format_exc())
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": f"Error processing action: {type(e).__name__}"}}
        try: publish_events(redis_task_conn, simulation_id, [error_event])
        except Exception: pass
    finally:
         if redis_task_conn:
             try: redis_task_conn.close()
             except Exception: pass

def handle_briefing_task(simulation_id: str, talking_points: str):
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker Briefing {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
    if not RQ_AVAILABLE: print(f"{log_prefix}: ERROR - RQ components unavailable."); return
    try:
        redis_task_conn = get_worker_redis_connection()
    except Exception as e: print(f"{log_prefix}: ERROR - Failed getting task Redis connection: {e}"); return
    sim = load_simulation(redis_task_conn, simulation_id)
    if not sim:
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": "Simulation not found or failed to load for briefing."}}
        try: publish_events(redis_task_conn, simulation_id, [error_event])
        except Exception: pass
        if redis_task_conn: redis_task_conn.close(); return
    try:
        sim._clear_current_events()
        sim.handle_analyst_briefing(talking_points) # This calls end_simulation internally
        events = sim._get_and_clear_current_events()
        publish_events(redis_task_conn, simulation_id, events)
        print(f"{log_prefix}: Briefing processed and simulation likely ended.")
        # No explicit save here as handle_analyst_briefing -> end_simulation should manage final state.
    except Exception as e:
        print(f"{log_prefix}: ERROR handling briefing: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": f"Error processing briefing: {type(e).__name__}"}}
        try: publish_events(redis_task_conn, simulation_id, [error_event])
        except Exception: pass
    finally:
        if redis_task_conn:
            try: redis_task_conn.close()
            except Exception: pass

def background_check_task(simulation_id: str):
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker BGCheck {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
    if not RQ_AVAILABLE: print(f"{log_prefix}: ERROR - RQ components unavailable."); return
    try:
        redis_task_conn = get_worker_redis_connection()
    except Exception as e: print(f"{log_prefix}: ERROR - Failed getting task Redis connection: {e}"); return
    sim = load_simulation(redis_task_conn, simulation_id)
    if not sim:
        if redis_task_conn: redis_task_conn.close(); return
    initial_state = sim.simulation_state
    sim_was_running = sim.simulation_running
    try:
        if not sim_was_running or sim.simulation_state in ["ENDED", "SETUP", "POST_INITIAL_CRISIS", "DECISION_POINT_SHUTDOWN", "AWAITING_ANALYST_BRIEFING", "AWAITING_USER_RATING"]: # Added AWAITING_USER_RATING
            if redis_task_conn: redis_task_conn.close(); return
        sim._clear_current_events()
        sim_time_updated = False
        now_real_utc = datetime.now(timezone.utc)
        if sim.last_real_time_sync and sim.simulation_time and sim.simulation_end_time: # Simplified tzinfo checks for brevity
            real_delta = now_real_utc - sim.last_real_time_sync.astimezone(timezone.utc)
            if real_delta > timedelta(seconds=0.1):
                remaining_sim_duration = sim.simulation_end_time - sim.simulation_time
                advance_amount = min(real_delta, max(timedelta(0), remaining_sim_duration))
                if advance_amount > timedelta(seconds=0):
                    sim.simulation_time += advance_amount
                    sim_time_updated = True
                    sim.emit_event("time_update", {"sim_time_iso": sim.simulation_time.isoformat(), "end_time_iso": sim.simulation_end_time.isoformat()})
                    sim.check_end_conditions()
        sim.last_real_time_sync = now_real_utc
        if sim.simulation_running and sim.simulation_state not in ["ENDED", "POST_INITIAL_CRISIS", "DECISION_POINT_SHUTDOWN", "AWAITING_ANALYST_BRIEFING", "AWAITING_USER_RATING"]:
            sim.check_dynamic_intensity()
            sim._generate_background_noise_logs()
            sim.check_background_events()
        state_changed_to_debrief = (initial_state != "POST_INITIAL_CRISIS" and sim.simulation_state == "POST_INITIAL_CRISIS")
        reschedule_next = sim.simulation_running and sim.simulation_state not in ["ENDED", "POST_INITIAL_CRISIS", "DECISION_POINT_SHUTDOWN", "AWAITING_ANALYST_BRIEFING", "AWAITING_USER_RATING"]
        if sim_time_updated or (sim.simulation_state != initial_state) or state_changed_to_debrief:
            save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn)
        events = sim._get_and_clear_current_events()
        publish_events(redis_task_conn, simulation_id, events)
        if state_changed_to_debrief:
            print(f"{log_prefix}: State changed to POST_INITIAL_CRISIS, enqueuing LLM rating task.")
            if default_queue:
                default_queue.enqueue(generate_llm_rating_task, simulation_id, job_timeout=300)
            else:
                print(f"{log_prefix} - ERROR: Default queue not available for LLM rating task.")
        if reschedule_next:
            schedule_next_background_check(simulation_id, sim.current_intensity_mod)
    except Exception as e:
        print(f"{log_prefix}: ERROR during background check: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        error_event = {"type": "error", "payload": {"simulation_id": simulation_id, "message": f"Error during background processing: {type(e).__name__}"}}
        try: publish_events(redis_task_conn, simulation_id, [error_event])
        except Exception: pass
    finally:
        if redis_task_conn:
            try: redis_task_conn.close()
            except Exception: pass

# Renamed original generate_rating_task to avoid conflict
def generate_rating_task(simulation_id: str):
    """Task to generate the LLM performance rating."""
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker LLMRating {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
    if not RQ_AVAILABLE or not default_queue:
         print(f"{log_prefix}: ERROR - RQ Queue unavailable."); return
    try:
        redis_task_conn = get_worker_redis_connection()
    except Exception as e: print(f"{log_prefix}: ERROR - Failed getting task Redis connection: {e}"); return
    sim = load_simulation(redis_task_conn, simulation_id)
    if not sim:
         if redis_task_conn: redis_task_conn.close(); return
    rating_result = {"error": "LLM Rating generation failed unexpectedly."}
    try:
        rating_result = sim._call_llm_for_rating()
    except AttributeError:
         rating_result = {"error": "Rating function missing in SimulationManager."}
         print(f"{log_prefix}: ERROR - {rating_result['error']}")
    except Exception as e:
         rating_result = {"error": f"Error generating LLM rating: {type(e).__name__} - {e}"}
         print(f"{log_prefix}: ERROR - {rating_result['error']}")
         print(traceback.format_exc())
    finally:
        try:
            rating_event = {"type": "debrief_rating_update", "payload": {"simulation_id": simulation_id, "performance_rating": rating_result}}
            publish_events(redis_task_conn, simulation_id, [rating_event])
        except Exception as pub_e:
            print(f"{log_prefix}: ERROR publishing LLM rating result: {pub_e}")
        # After LLM rating is published, enqueue the task to request user's own rating
        try:
            print(f"{log_prefix}: Enqueuing request_user_rating_task.")
            default_queue.enqueue(request_user_rating_task, simulation_id, job_timeout=60)
        except Exception as e_enqueue:
            print(f"{log_prefix}: ERROR enqueuing request_user_rating_task: {e_enqueue}")
        if redis_task_conn:
            try: redis_task_conn.close()
            except Exception: pass

def request_user_rating_task(simulation_id: str):
    """
    Task to emit an event to the client, prompting them to provide their star rating and feedback.
    This task runs after the LLM-generated performance rating has been sent.
    """
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker ReqUserRating {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
    if not RQ_AVAILABLE: print(f"{log_prefix}: ERROR - RQ components unavailable."); return
    try:
        redis_task_conn = get_worker_redis_connection()
        sim = load_simulation(redis_task_conn, simulation_id)
        if not sim:
            if redis_task_conn: redis_task_conn.close(); return

        if sim.simulation_state == "POST_INITIAL_CRISIS" or sim.simulation_state == "AWAITING_USER_RATING": # Or just ended
            sim._clear_current_events()
            sim.simulation_state = "AWAITING_USER_RATING" # Explicitly set state
            sim.log_event("System prompting user for simulation rating.", store_for_rating=False)
            sim.emit_event("request_user_rating", {
                "message": "Please rate your experience and provide feedback.",
                # The frontend already handles showing feedback input for low ratings,
                # but you could pass a flag if you want more backend control/emphasis.
                # "show_feedback_prompt_on_low_rating": True
            })
            events = sim._get_and_clear_current_events()
            publish_events(redis_task_conn, simulation_id, events)
            save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn) # Save new state

            # After requesting user rating, THEN enqueue the analyst briefing prompt
            # This gives the user time to rate before seeing the next "yes/no" question.
            # The actual submission of the rating is via a separate API call from the frontend.
            try:
                print(f"{log_prefix}: Enqueuing trigger_briefing_prompt_task (after requesting user rating).")
                default_queue.enqueue_in(
                    timedelta(seconds=10), # Delay to allow user to see rating UI
                    trigger_briefing_prompt_task,
                    simulation_id,
                    job_timeout=60
                )
            except Exception as e_enqueue:
                print(f"{log_prefix}: ERROR enqueuing trigger_briefing_prompt_task: {e_enqueue}")
        else:
            print(f"{log_prefix}: Skipping user rating prompt - Sim state is '{sim.simulation_state}'.")

    except Exception as e:
        print(f"{log_prefix}: ERROR emitting user rating prompt: {type(e).__name__} - {e}")
        print(traceback.format_exc())
    finally:
        if redis_task_conn:
            try: redis_task_conn.close()
            except Exception: pass

def trigger_briefing_prompt_task(simulation_id: str):
    """
    Task to emit the prompt asking the user if they want to prepare analyst briefing points.
    Runs AFTER the user has been prompted for their own rating.
    """
    redis_task_conn = None
    job = get_current_job()
    log_prefix = f"[Worker BriefPrompt {job.id[:6] if job else 'N/A'}] SimID={simulation_id[-8:]}"
    if not RQ_AVAILABLE: print(f"{log_prefix}: ERROR - RQ components unavailable."); return
    try:
        redis_task_conn = get_worker_redis_connection()
        sim = load_simulation(redis_task_conn, simulation_id)
        if not sim:
            if redis_task_conn: redis_task_conn.close(); return

        # Only send prompt if in the correct state (e.g., after rating was requested)
        # Or if the sim moved from POST_INITIAL_CRISIS directly here if rating prompt was skipped for some reason.
        if sim.simulation_state in ["POST_INITIAL_CRISIS", "AWAITING_USER_RATING"]:
            sim._clear_current_events()
            sim.simulation_state = "AWAITING_USER_RATING" # Or a new state like "AWAITING_ANALYST_BRIEFING_CHOICE"
            sim.emit_event("request_yes_no", {
                "prompt": "Optional: Prepare analyst briefing points based on this outcome? (yes/no)",
                "action_context": "prepare_analyst_briefing"
            })
            events = sim._get_and_clear_current_events()
            publish_events(redis_task_conn, simulation_id, events)
            save_simulation_state(simulation_id, sim.get_state(), redis_conn=redis_task_conn) # Save new state
        else:
            print(f"{log_prefix}: Skipping analyst briefing prompt - Sim state is '{sim.simulation_state}'.")
    except Exception as e:
        print(f"{log_prefix}: ERROR emitting analyst briefing prompt: {type(e).__name__} - {e}")
        print(traceback.format_exc())
    finally:
        if redis_task_conn:
            try: redis_task_conn.close()
            except Exception: pass

# Note: You'll also need the `store_user_rating_task` if you choose
# to enqueue the rating storage from the API, or the logic to store the rating
# directly in the `/sim/rate` API endpoint.
# For this rewrite, I've focused on the task chaining for prompting the user.
# The actual storage of the user's submitted rating happens via the separate API call
# from the frontend to your `/api/sim/rate` endpoint (which you'd implement in sim_api.py).