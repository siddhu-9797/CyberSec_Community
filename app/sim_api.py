# app/sim_api.py

import asyncio
import json
import uuid
import traceback # For logging unexpected errors
from fastapi import ( APIRouter, Depends, HTTPException, status, Body,
                      WebSocket, WebSocketDisconnect, Query, Request ) # Added Request
from fastapi.responses import HTMLResponse # For serving HTML if needed directly
from typing import Annotated, Optional, List, Dict, Any
from jose import JWTError, jwt # For manual JWT decoding in WebSocket auth
from datetime import datetime, timedelta, timezone
# Redis clients (async for WS, sync for helper - though helper could be async too)
import redis
import redis.asyncio as aioredis
from starlette.websockets import WebSocketState # For checking WS state
from pathlib import Path
from threading import Lock
# --- Project Imports ---
# Authentication & User Models
from .dependencies import get_current_user, get_optional_current_user # <<< MODIFIED: Added get_optional_current_user
from .models import User, StartSimulationRequest, StartSimulationResponse, \
                    SimulationActionRequest, SubmitBriefingRequest, ActionResponse, UserRatingRequest
from app.crud import upsert_user_star_rating_data
from app.db import get_db_session_context
# Tasks & Queue & Ownership Helper
# <<< MODIFIED: Import verify_simulation_access, removed verify_simulation_ownership
from workers.tasks import (start_simulation_task, handle_action_task,
                           handle_briefing_task, generate_rating_task,
                           verify_simulation_access # <<< CHANGED
                           )
from workers.rq_config import default_queue

# Database/Redis Connections & Config (for sync helper)
from app.db import get_worker_redis_connection # For synchronous initial state fetch
from .config import settings
from workers.simulation_manager import scenarios # Keep scenarios import for initial state construction


# --- Router Setup ---
router = APIRouter()

# --- Connection Manager (Simple In-Memory for MVP) ---
# WARNING: This simple manager does NOT scale beyond one API instance.
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {} # simulation_id -> [WebSocket]

    async def connect(self, websocket: WebSocket, simulation_id: str):
        await websocket.accept()
        if simulation_id not in self.active_connections:
            self.active_connections[simulation_id] = []
        # Avoid adding duplicates if client reconnects quickly
        if websocket not in self.active_connections[simulation_id]:
             self.active_connections[simulation_id].append(websocket)
        print(f"WS Connect: Client -> Sim {simulation_id[-8:]}. Total clients for sim: {len(self.active_connections[simulation_id])}")

    def disconnect(self, websocket: WebSocket, simulation_id: str):
        if simulation_id in self.active_connections:
            try:
                self.active_connections[simulation_id].remove(websocket)
                if not self.active_connections[simulation_id]: # If list is empty
                    del self.active_connections[simulation_id]
            except ValueError:
                 pass # Ignore if websocket already removed

    async def broadcast_to_simulation(self, simulation_id: str, message: str):
        if simulation_id in self.active_connections:
            connections_to_remove = []
            live_connections = list(self.active_connections.get(simulation_id, []))
            results = await asyncio.gather(
                *(connection.send_text(message) for connection in live_connections),
                return_exceptions=True
            )
            for i, result in enumerate(results):
                 if isinstance(result, Exception):
                     print(f"WS Send Error to client for sim {simulation_id[-8:]}: {result}. Marking for removal.")
                     connections_to_remove.append(live_connections[i])
            if connections_to_remove:
                for conn in connections_to_remove:
                    self.disconnect(conn, simulation_id)

manager = ConnectionManager()

# --- API Endpoints ---

@router.post("/start", response_model=StartSimulationResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_new_simulation(
    start_request: StartSimulationRequest,
    current_user: User = Depends(get_current_user) # <<< REQUIRE authentication for this endpoint
):
    """
    Starts a new simulation session FOR AN AUTHENTICATED USER.
    Enqueues the start task in the background. Returns generated simulation ID.
    """
    user_id = str(current_user.id)
    user_name = current_user.first_name
    guest_id = None # Explicitly None for authenticated route

    log_prefix = f"API Start [AUTH]: User={user_id}, Sim=N/A"
    print(f"{log_prefix} - Request: Scenario={start_request.scenario}, Intensity={start_request.intensity}")

    # Generate simulation ID (API generates it for users)
    pre_generated_simulation_id = f"user_{user_id}_{uuid.uuid4().hex[:8]}"
    log_prefix = f"API Start [AUTH]: User={user_id}, Sim={pre_generated_simulation_id[-8:]}" # Update log prefix
    print(f"{log_prefix} - Generated SimID: {pre_generated_simulation_id}")

    if not default_queue:
         print(f"{log_prefix} - ERROR: Task queue not available.")
         raise HTTPException(status_code=503, detail="Simulation service unavailable")

    try:
        job = default_queue.enqueue(
            start_simulation_task,
            args=( # Pass args as a tuple
                pre_generated_simulation_id,
                user_id,    # Authenticated user ID
                guest_id,   # None
                user_name,  # Authenticated user's name
                start_request.scenario,
                start_request.intensity,
                max(1, start_request.duration),
            ),
            job_timeout=60,
            result_ttl=10
        )
        print(f"{log_prefix} - Enqueued Task ID: {job.id}")
    except Exception as e:
         print(f"{log_prefix} - ERROR: Failed to enqueue start task: {type(e).__name__} - {e}")
         print(traceback.format_exc())
         raise HTTPException(status_code=500, detail="Failed to queue simulation start")

    return StartSimulationResponse(message="Simulation starting...", simulation_id=pre_generated_simulation_id)


# +++ NEW ENDPOINT for Guests +++
@router.post("/start_guest", response_model=StartSimulationResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_guest_simulation(
    # Use the same request model, duration default applies
    start_request: StartSimulationRequest,
    # NO Depends(get_current_user) here
):
    """
    Starts a new simulation session for a GUEST user.
    Enqueues the start task in the background. Returns generated simulation ID.
    """
    user_id = None # No user ID for guests
    user_name = "Guest" # Default name for guests

    # Generate a unique ID that serves as BOTH the simulation ID and the guest identifier
    guest_sim_id = f"guest_{uuid.uuid4().hex[:12]}"

    log_prefix = f"API Start [GUEST]: GuestSimID={guest_sim_id[-8:]}"
    print(f"{log_prefix} - Request: Scenario={start_request.scenario}, Intensity={start_request.intensity}")

    # Use the guest_id as the simulation_id for guests
    pre_generated_simulation_id = guest_sim_id

    if not default_queue:
         print(f"{log_prefix} - ERROR: Task queue not available.")
         raise HTTPException(status_code=503, detail="Simulation service unavailable")

    try:
        job = default_queue.enqueue(
            start_simulation_task,
            args=(
                pre_generated_simulation_id, # Pass the guest ID as the simulation ID
                user_id,                     # None
                pre_generated_simulation_id, # Pass guest ID again as guest_id field for state
                user_name,                   # "Guest"
                start_request.scenario,
                start_request.intensity,
                max(1, start_request.duration),
            ),
            job_timeout=60,
            result_ttl=10
        )
        print(f"{log_prefix} - Enqueued Task ID: {job.id}")
    except Exception as e:
         print(f"{log_prefix} - ERROR: Failed to enqueue start task: {type(e).__name__} - {e}")
         print(traceback.format_exc())
         raise HTTPException(status_code=500, detail="Failed to queue simulation start")

    # Return the generated guest simulation ID
    return StartSimulationResponse(message="Guest simulation starting...", simulation_id=pre_generated_simulation_id)
# +++ END NEW ENDPOINT +++


@router.post("/{simulation_id}/action", response_model=ActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def perform_simulation_action(
    simulation_id: str,
    action_request: Annotated[dict, Body(embed=True)], # Use Body embedding
    # <<< MODIFIED: Use optional dependency >>>
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Receives a player action for a specific simulation and enqueues it.
    Verifies access for EITHER authenticated users OR guests.
    """
    # Determine user ID if authenticated, otherwise None
    user_id = str(current_user.id) if current_user else None
    log_user_part = f"User={user_id}" if user_id else "Guest"
    log_prefix = f"API Action [{log_user_part}]: Sim={simulation_id[-8:]}"

    # Validate input action structure
    if "action" not in action_request or not isinstance(action_request["action"], str):
         print(f"{log_prefix} - ERROR: Invalid request body structure.")
         raise HTTPException(status_code=422, detail="Invalid request body: 'action' string is required.")
    action = action_request["action"]
    print(f"{log_prefix} - Action='{action[:50]}...'")

    # --- MODIFIED: Verify Access (handles both users and guests) ---
    # Calls the function imported from workers.tasks
    if not verify_simulation_access(simulation_id, user_id):
        print(f"{log_prefix} - ERROR: Access verification failed.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this simulation.")
    # print(f"{log_prefix} - Access verified.") # Can be noisy

    if not default_queue:
        print(f"{log_prefix} - ERROR: Task queue not available.")
        raise HTTPException(status_code=503, detail="Simulation service unavailable")

    try:
        job = default_queue.enqueue(
            handle_action_task,
            args=(simulation_id, action),
            job_timeout=180,
            result_ttl=10
        )
        print(f"{log_prefix} - Enqueued Task ID: {job.id}")
    except Exception as e:
        print(f"{log_prefix} - ERROR: Failed to enqueue action task: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to queue simulation action")

    return ActionResponse(status="action processing")


@router.post("/{simulation_id}/briefing", response_model=ActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_simulation_briefing(
    simulation_id: str,
    briefing_request: SubmitBriefingRequest, # Uses Pydantic model for validation
    # <<< MODIFIED: Use optional dependency >>>
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Submits analyst briefing points and enqueues processing. Verifies access for EITHER authenticated users OR guests.
    """
    # Determine user ID if authenticated, otherwise None
    user_id = str(current_user.id) if current_user else None
    log_user_part = f"User={user_id}" if user_id else "Guest"
    log_prefix = f"API Briefing [{log_user_part}]: Sim={simulation_id[-8:]}"

    talking_points = briefing_request.talking_points
    print(f"{log_prefix} - Submitting briefing points.")

    # --- MODIFIED: Verify Access (handles both users and guests) ---
    if not verify_simulation_access(simulation_id, user_id):
         print(f"{log_prefix} - ERROR: Access verification failed.")
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this simulation.")
    # print(f"{log_prefix} - Access verified.")

    if not default_queue:
        print(f"{log_prefix} - ERROR: Task queue not available.")
        raise HTTPException(status_code=503, detail="Simulation service unavailable")

    try:
        job = default_queue.enqueue(
            handle_briefing_task,
            args=(simulation_id, talking_points),
            job_timeout=180,
            result_ttl=10
        )
        print(f"{log_prefix} - Enqueued Task ID: {job.id}")
    except Exception as e:
         print(f"{log_prefix} - ERROR: Failed to enqueue briefing task: {type(e).__name__} - {e}")
         print(traceback.format_exc())
         raise HTTPException(status_code=500, detail="Failed to queue briefing processing")

    return ActionResponse(status="briefing processing")


RATINGS_JSONL_FILE_DIR = Path(__file__).resolve().parent.parent / "sim_data"
RATINGS_JSONL_FILE_PATH = RATINGS_JSONL_FILE_DIR / "simulation_ratings.jsonl"
jsonl_file_lock = Lock()

RATINGS_JSONL_FILE_DIR.mkdir(parents=True, exist_ok=True)

# @router.post("/rate", status_code=status.HTTP_201_CREATED, summary="Submit User Rating for a Simulation")
# async def submit_user_simulation_rating(
#     rating_request: UserRatingRequest,
#     current_user: Optional[User] = Depends(get_optional_current_user)
# ):
#     user_id_for_rating = str(current_user.id) if current_user else None
#     simulation_id = rating_request.simulation_id

#     log_user_part = f"User={user_id_for_rating}" if user_id_for_rating else "Guest"
#     log_prefix = f"API RateSim [{log_user_part}, Sim={simulation_id[-8:]}]"

#     print(f"{log_prefix} - Received Rating: {rating_request.rating} stars.")
#     if rating_request.feedback:
#         print(f"{log_prefix} - Feedback: \"{rating_request.feedback[:100]}...\"")

#     rating_data_obj = {
#         "timestamp_utc": datetime.now(timezone.utc).isoformat(),
#         "simulation_id": simulation_id,
#         "user_identifier": user_id_for_rating if user_id_for_rating else "GUEST",
#         "rating_stars": rating_request.rating,
#         "feedback_text": rating_request.feedback
#     }

#     try:
#         with jsonl_file_lock:
#             with open(RATINGS_JSONL_FILE_PATH, mode='a', encoding='utf-8') as f:
#                 f.write(json.dumps(rating_data_obj) + '\n')
#         print(f"{log_prefix} - Rating data appended to {RATINGS_JSONL_FILE_PATH}")
#     except IOError as e:
#         print(f"{log_prefix} - ERROR writing rating to JSONL file: {e}")
#         # raise HTTPException(status_code=500, detail="Could not store rating due to a server error.")
#     except Exception as e_general:
#         print(f"{log_prefix} - UNEXPECTED ERROR writing rating to JSONL file: {e_general}")
#         # raise HTTPException(status_code=500, detail="An unexpected error occurred while storing rating.")

#     return {"message": "Thank you for your feedback!"}


@router.post("/rate", status_code=status.HTTP_201_CREATED, summary="Submit User Rating for a Simulation")
async def submit_user_simulation_rating(
    rating_request: UserRatingRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    user_id_for_rating_submission = str(current_user.id) if current_user else None # User submitting the form
    simulation_id = rating_request.simulation_id

    log_user_part = f"User={user_id_for_rating_submission}" if user_id_for_rating_submission else "GuestForm"
    log_prefix = f"API RateSim [{log_user_part}, Sim={simulation_id[-8:]}]"

    print(f"{log_prefix} - Received User Rating: {rating_request.rating} stars.")
    if rating_request.feedback:
        print(f"{log_prefix} - User Feedback: \"{rating_request.feedback[:100]}...\"")

    try:
        with get_db_session_context() as db: # Get DB session
            upsert_user_star_rating_data(
                db=db,
                simulation_id_str=simulation_id,
                user_rating_stars=rating_request.rating,
                user_feedback_text=rating_request.feedback,
                user_id_str=user_id_for_rating_submission # Optional, if you track who submitted the rating
            )
        print(f"{log_prefix} - User rating and feedback stored in database for simulation {simulation_id}")
        return {"message": "Thank you for your feedback!"}
    except Exception as e:
        print(f"{log_prefix} - ERROR storing user rating in database: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        # Depending on how critical this is, you might just log or raise HTTP error
        raise HTTPException(status_code=500, detail="Could not store your rating due to a server error.")

# --- WebSocket Endpoint ---
@router.websocket("/ws/{simulation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    simulation_id: str,
    token: Optional[str] = Query(None) # Get token from query param: ?token=xxx (Optional)
):
    """Handles WebSocket connections for real-time simulation events for authenticated users OR guests."""
    user_id: Optional[str] = None
    is_authenticated = False
    auth_error_reason: Optional[str] = None
    log_prefix_user = "Guest" # Default log part

    # 1. Attempt Authentication if token is provided
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id_from_token = payload.get("user_id")
            if user_id_from_token:
                user_id = str(user_id_from_token)
                is_authenticated = True
                log_prefix_user = f"User={user_id}" # Update log prefix part
                # print(f"WS Auth OK: User={user_id}, Sim={simulation_id[-8:]}") # Debug
            else:
                 auth_error_reason = "Invalid token payload (missing user_id)"
                 print(f"WS Auth Fail: Sim={simulation_id[-8:]} - {auth_error_reason}")
        except JWTError as e:
            auth_error_reason = f"Invalid token ({type(e).__name__})"
            print(f"WS Auth Fail: Sim={simulation_id[-8:]} - {auth_error_reason}")
        except Exception as e:
             auth_error_reason = "Authentication error during token decode"
             print(f"WS Auth Fail: Sim={simulation_id[-8:]} - {auth_error_reason}: {e}")
    # else: No token provided, proceed assuming guest attempt


    # 2. Verify Access (Handles both users and guests)
    # Calls the function imported from workers.tasks, passing user_id (or None)
    if not verify_simulation_access(simulation_id, user_id):
        # If access denied, use auth_error_reason if available, otherwise generic message
        reason = auth_error_reason or "Simulation access denied"
        log_prefix = f"WS [{log_prefix_user}] Sim={simulation_id[-8:]}" # Construct full log prefix
        print(f"{log_prefix} - Access Denied. Reason: {reason}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=reason)
        return

    # --- Access Granted ---
    log_prefix = f"WS [{log_prefix_user}] Sim={simulation_id[-8:]}" # Construct full log prefix
    print(f"{log_prefix} - Access verified.")

    # 3. Accept & Manage Connection
    await manager.connect(websocket, simulation_id)
    pubsub_client: Optional[aioredis.client.PubSub] = None
    async_redis_conn: Optional[aioredis.Redis] = None
    sync_redis_conn_for_state = None # For initial state fetch

    try:
        # 4. SEND INITIAL STATE (Using synchronous connection helper)
        print(f"{log_prefix} - Fetching initial state from Redis...")
        # (Keep the initial state sending logic from your latest version, it uses get_worker_redis_connection)
        initial_state_payload = None
        try:
             sync_redis_conn_for_state = get_worker_redis_connection()
             state_key = f"sim_state:{simulation_id}"
             state_json = sync_redis_conn_for_state.get(state_key)
             if state_json:
                  state_data = json.loads(state_json)
                  try:
                      intensity_key = "Unknown"
                      scenario_def = scenarios.get(state_data.get("selected_scenario_key"), {})
                      intensity_modifiers = scenario_def.get("intensity_modifier", {})
                      stored_intensity_mod = state_data.get("initial_intensity_mod")
                      if stored_intensity_mod is not None:
                           for k, v in intensity_modifiers.items():
                                if abs(v - stored_intensity_mod) < 0.001: intensity_key = k; break

                      sim_duration = 0
                      start_iso = state_data.get("simulation_start_time_iso")
                      end_iso = state_data.get("simulation_end_time_iso")
                      if start_iso and end_iso:
                           try:
                               start_dt = datetime.fromisoformat(start_iso); end_dt = datetime.fromisoformat(end_iso)
                               sim_duration = int((end_dt - start_dt).total_seconds() / 60)
                           except ValueError: pass

                      initial_state_payload = {
                          "simulation_id": simulation_id,
                          "scenario": state_data.get("selected_scenario_key"),
                          "description": scenario_def.get("description", ""), "intensity_key": intensity_key,
                          "current_intensity_mod": state_data.get("current_intensity_mod"), "duration": sim_duration,
                          "player_name": state_data.get("player_name"), "player_role": state_data.get("player_role"),
                          "start_time_iso": start_iso, "end_time_iso": end_iso,
                          "current_sim_time_iso": state_data.get("simulation_time_iso"),
                          "initial_system_status": state_data.get("system_status"),
                          "initial_agent_status": { name: agent_info.get("state", "unknown")
                              for name, agent_info in state_data.get("agents_simple_state", {}).items() },
                          "current_state": state_data.get("simulation_state"),
                          "missed_calls": state_data.get("missed_calls", []) }

                      print(f"{log_prefix} - Sending initial_state event to client.")
                      await websocket.send_json({"type": "initial_state", "payload": initial_state_payload})
                  except Exception as payload_err:
                       print(f"{log_prefix} - ERROR constructing initial_state payload: {payload_err}")
                       print(traceback.format_exc())
                       await websocket.send_json({"type": "error", "payload": {"message": "Error processing initial state data."}})
             else:
                  print(f"{log_prefix} - WARNING: State not found in Redis when sending initial state.")
                  # Optionally send a 'waiting_for_start' event? Or rely on pubsub event later.
                  # await websocket.send_json({"type": "info", "payload": {"message": "Simulation state initializing..."}})

        except redis.exceptions.ConnectionError as e_state_conn:
             print(f"{log_prefix} - ERROR fetching initial state (Redis Conn): {e_state_conn}")
             await websocket.send_json({"type": "error", "payload": {"message": "Error connecting to retrieve initial state."}})
        except Exception as e_state:
             print(f"{log_prefix} - ERROR fetching/sending initial state: {type(e_state).__name__} - {e_state}")
             print(traceback.format_exc())
             await websocket.send_json({"type": "error", "payload": {"message": "Error fetching initial state."}})
        finally:
              if sync_redis_conn_for_state: sync_redis_conn_for_state.close()

        # 5. Subscribe to Redis Pub/Sub for LIVE updates
        async_redis_conn = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub_client = async_redis_conn.pubsub(ignore_subscribe_messages=True)
        channel = f"sim_events:{simulation_id}"
        await pubsub_client.subscribe(channel)
        print(f"{log_prefix} - Subscribed to {channel} for live events.")

        # 6. Concurrently Listen to Client and Redis
        async def client_reader(ws: WebSocket, sim_id_short: str):
            """Listens for messages FROM the client (e.g., pings)"""
            try:
                while True:
                    data = await ws.receive_text()
                    if data.lower() == 'ping': await ws.send_text('pong')
                    # Add handling for other client messages if needed
            except WebSocketDisconnect: pass # Handled in main finally block
            except Exception as e_client:
                if "Connection closed" not in str(e_client): # Avoid logging normal disconnects here
                     print(f"WS Error (client reader) Sim={sim_id_short}: {type(e_client).__name__} - {e_client}")

        async def pubsub_reader(ps: aioredis.client.PubSub, sim_id: str, sim_id_short: str):
            """Listens for messages FROM Redis Pub/Sub and broadcasts"""
            # print(f"WS PubSub Listener STARTED for {sim_id_short}") # Debug
            try:
                while True:
                    try:
                        message = await asyncio.wait_for(ps.get_message(timeout=1.0), timeout=1.5)
                        if message and message["type"] == "message":
                            event_data_str = message["data"]
                            # print(f"WS PubSub Received for {sim_id_short}: {event_data_str[:150]}...") # Debug
                            await manager.broadcast_to_simulation(sim_id, event_data_str)
                        if websocket.client_state != WebSocketState.CONNECTED: break
                    except asyncio.TimeoutError:
                        if websocket.client_state != WebSocketState.CONNECTED: break; continue
                    except redis.exceptions.ConnectionError as e_redis_conn_loop:
                         print(f"WS PubSub REDIS CONNECTION ERROR ({sim_id_short}): {e_redis_conn_loop} - Breaking loop.")
                         break
            except asyncio.CancelledError: pass # Task cancelled during cleanup
            except Exception as e_pubsub:
                print(f"WS Error (PubSub reader) Sim={sim_id_short}: {type(e_pubsub).__name__} - {e_pubsub}")
                print(traceback.format_exc())
            # finally: print(f"WS PubSub Listener EXITED for {sim_id_short}") # Debug


        sim_id_short = simulation_id[-8:]
        client_task = asyncio.create_task(client_reader(websocket, sim_id_short))
        pubsub_task = asyncio.create_task(pubsub_reader(pubsub_client, simulation_id, sim_id_short))

        # Keep connection alive while tasks run
        done, pending = await asyncio.wait(
            [client_task, pubsub_task], return_when=asyncio.FIRST_COMPLETED )
        for task in pending:
            if not task.done(): task.cancel()

    except WebSocketDisconnect:
        print(f"{log_prefix} - Disconnect detected (main loop).")
    except Exception as e:
        print(f"{log_prefix} - Unexpected error in WS endpoint: {type(e).__name__} - {e}")
        print(traceback.format_exc())
    finally:
        # 7. Cleanup
        print(f"{log_prefix} - Cleaning up WebSocket connection.")
        # Cancel running tasks explicitly if they haven't finished
        if 'pubsub_task' in locals() and pubsub_task and not pubsub_task.done(): pubsub_task.cancel()
        if 'client_task' in locals() and client_task and not client_task.done(): client_task.cancel()
        # Cleanup PubSub
        if pubsub_client and pubsub_client.connection: # Check connection exists
             try: await pubsub_client.unsubscribe(channel)
             except NameError: pass
             except Exception as e_clean_ps: print(f"{log_prefix} - Error during PubSub unsubscribe: {e_clean_ps}")
        # Close the dedicated async connection used for PubSub
        if async_redis_conn:
             try: await async_redis_conn.close(); await async_redis_conn.connection_pool.disconnect()
             except Exception as e_clean_conn: print(f"{log_prefix} - Error closing async Redis connection: {e_clean_conn}")
        # Disconnect from manager
        manager.disconnect(websocket, simulation_id)
        # Ensure WebSocket is closed server-side if not already
        if websocket.client_state == WebSocketState.CONNECTED:
             await websocket.close(code=status.WS_1001_GOING_AWAY)
        print(f"{log_prefix} - WebSocket connection fully closed.")