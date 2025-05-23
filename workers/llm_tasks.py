# workers/llm_tasks.py

import json
import traceback
import random
from rq import get_current_job
from redis import Redis # For type hinting if needed
from datetime import datetime # <--- ADDED: Needed for sim_time_iso fallback

# --- Project Imports ---
# --->> REMOVE SimulationManager import from top level <<---
# from .simulation_manager import SimulationManager # REMOVED

# --->> Keep these top-level imports <<---
# Note: Corrected import path assuming task_utils.py exists
from .ask_utils import load_simulation_state, publish_event
from app.db import get_worker_redis_connection # For direct publishing
# from .rq_config import default_queue # Only if you directly use the queue inside the task

# --- Constants ---
GPT_LOG_MODEL = "gpt-4o-mini" # Or your preferred model
GPT_LOG_MAX_TOKENS = 150      # Adjust as needed per log batch
GPT_LOG_TEMPERATURE = 0.6   # Slightly creative but not wild

def generate_gpt_logs_task(simulation_id: str, context: dict):
    """
    RQ task to generate context-aware logs using an LLM.
    Context dictionary should contain info like:
    - triggering_event: "escalation_rule" / "status_change" / "player_action"
    - system_key: The system involved
    - old_status: Previous status (optional)
    - new_status: The new status that triggered this
    - reason: The reason provided for the change/escalation
    - current_intensity_mod: Current intensity modifier
    - status_summary: A compact summary of current system statuses
    - desired_log_count: How many logs to try generating (e.g., 1-3)
    """
    job = get_current_job()
    log_prefix = f"[Worker GPTLog {job.id[:6] if job else 'NoJob'}] SimID={simulation_id[-8:]}"
    print(f"{log_prefix} - Received request. Context: {context}")

    # --->> IMPORT SimulationManager INSIDE the task <<---
    from .simulation_manager import SimulationManager

    redis_conn_for_publish = None # For publishing results
    sim = None # SimulationManager instance

    try:
        # --- 1. Load Simulation State ---
        # Load state to get SimulationManager instance with its methods (LLM call, log generation)
        sim_state_dict = load_simulation_state(simulation_id)
        if not sim_state_dict:
            print(f"{log_prefix} - ERROR: Failed to load simulation state. Aborting.")
            return "Error: Simulation state not found"

        # --->> Instantiate SimulationManager now that it's imported <<---
        sim = SimulationManager(simulation_id=simulation_id)
        sim.load_state(sim_state_dict) # Load state into the instance

        # Ensure OpenAI client is initialized within the instance
        # (sim.load_state should call _initialize_openai_client if needed)
        if not sim.client:
            print(f"{log_prefix} - ERROR: OpenAI client not initialized in loaded SimManager. Aborting.")
            # Log the event via the sim instance if possible before returning
            sim.log_event("FATAL ERROR (GPTLog Task): OpenAI client not available.", level="error", store_for_rating=True)
            # Optionally save state back? Depends if this logging should persist
            # save_simulation_state(simulation_id, sim.get_state())
            return "Error: LLM client configuration issue"

        # --- 2. Construct the Prompt ---
        trigger_event = context.get("triggering_event", "status_change")
        system_key = context.get("system_key", "UnknownSystem")
        new_status = context.get("new_status", "UnknownStatus")
        reason = context.get("reason", "No reason provided")
        intensity = context.get("current_intensity_mod", 1.0)
        status_summary = context.get("status_summary", "Status unavailable")
        log_count = context.get("desired_log_count", random.randint(1, 2))

        # --- Be specific in the prompt! ---
        prompt = f"""
        You are a log generation engine for a cybersecurity simulation.
        Generate {log_count} realistic log entries reflecting the following event for the system '{system_key}':
        - Event Type: {trigger_event}
        - New Status: {new_status}
        - Reason: {reason}
        - Current Intensity Modifier (lower means more intense): {intensity:.2f}x
        - Broader System Status Summary: {status_summary}

        Instructions:
        - Logs should be plausible for the event and system type (e.g., '{system_key}' might be DB, FW, Auth).
        - Reflect the severity implied by the status '{new_status}'.
        - Use realistic but randomized details (IPs, usernames, ports, process names, etc.).
        - Output ONLY a JSON list of log entry objects. Each object must have keys: "source_key", "severity_level", "event_type", "log_details".
        - "source_key" should be the system involved ('{system_key}').
        - "severity_level" should match the implied severity of '{new_status}' (e.g., CRITICAL, HIGH, WARN, INFO). Use standard levels like CRITICAL, HIGH, WARN, INFO, LOW, MEDIUM.
        - "event_type" should be a short code from LOG_TEMPLATES if applicable (e.g., FW_DENY, AUTH_FAILURE, FILE_ACCESS_ENCRYPT) or a generic one (e.g., GENERIC_HIGH, SYS_STATUS_CHANGE).
        - "log_details" must be a dictionary containing placeholders used by the corresponding event_type's template (e.g., {{"src_ip": "1.2.3.4", "user": "svc_acct", "reason": "Connection reset"}}).

        Example JSON Output:
        [
          {{"source_key": "File_Servers", "severity_level": "HIGH", "event_type": "FILE_ACCESS_ENCRYPT", "log_details": {{"user": "SYSTEM", "process": "ransom.exe", "path": "C:\\Share\\important.docx", "sig": "Ransom.Generic.VariantX"}}}},
          {{"source_key": "Network_Edge", "severity_level": "WARN", "event_type": "FW_DENY", "log_details": {{"src_ip": "198.51.100.10", "dst_ip": "10.1.1.5", "dst_port": 445, "proto": "TCP", "policy": "Rule-103"}}}}
        ]

        Generate the JSON list now:
        """

        # --- 3. Call LLM API (using SimManager's method) ---
        print(f"{log_prefix} - Calling LLM ({GPT_LOG_MODEL}) to generate {log_count} logs for '{system_key}' -> '{new_status}'.")
        # Use the call_llm_api method from the loaded 'sim' instance
        raw_response = sim.call_llm_api(
            persona_prompt="You are a log generation engine.",
            history_list=[],
            user_input=prompt,
            agent_name="LogGenerator",
            model=GPT_LOG_MODEL,
            max_tokens=GPT_LOG_MAX_TOKENS * log_count,
            temperature=GPT_LOG_TEMPERATURE,
            response_format={"type": "json_object"}
        )

        # Check for errors returned by call_llm_api itself (e.g., "(LLM Client Error: ...)")
        if not raw_response or raw_response.startswith("("):
            error_msg = f"LLM call failed or returned internal error: {raw_response}"
            print(f"{log_prefix} - ERROR: {error_msg}")
            sim.log_event(f"ERROR (GPTLog Task): {error_msg}", level="error", store_for_rating=True)
            # save_simulation_state(simulation_id, sim.get_state()) # Save state with error logged
            return f"Error: LLM call failed ({raw_response})"

        # --- 4. Parse Response ---
        print(f"{log_prefix} - Parsing LLM response: {raw_response[:100]}...")
        generated_logs_data = []
        try:
            parsed_object = None
            try:
                parsed_object = json.loads(raw_response)
            except json.JSONDecodeError:
                start_index = raw_response.find('[')
                end_index = raw_response.rfind(']') + 1
                if start_index != -1 and end_index != -1 and end_index > start_index:
                    json_substring = raw_response[start_index:end_index]
                    parsed_object = json.loads(json_substring)
                    print(f"{log_prefix} - Note: Extracted JSON list from potentially noisy response.")
                else:
                     raise ValueError("Could not find JSON list markers [...] in response.")

            if isinstance(parsed_object, list):
                generated_logs_data = parsed_object
            elif isinstance(parsed_object, dict) and "logs" in parsed_object and isinstance(parsed_object["logs"], list):
                generated_logs_data = parsed_object["logs"]
                print(f"{log_prefix} - Note: Extracted list from 'logs' key in response dictionary.")
            else:
                print(f"{log_prefix} - WARNING: LLM response was not a JSON list as expected. Type: {type(parsed_object)}")
                generated_logs_data = []

            print(f"{log_prefix} - Parsed {len(generated_logs_data)} log entries from LLM.")

        except Exception as e:
            error_msg = f"Failed to parse LLM response JSON: {e}. Response: {raw_response[:500]}"
            print(f"{log_prefix} - ERROR: {error_msg}")
            sim.log_event(f"ERROR (GPTLog Task): {error_msg}", level="error", store_for_rating=True)
            # save_simulation_state(simulation_id, sim.get_state()) # Save state with error logged
            return f"Error: Parsing LLM response failed ({e})"

        # --- 5. Validate and Emit Logs ---
        if not generated_logs_data:
            print(f"{log_prefix} - No valid log data generated by LLM.")
            return "LLM generated no valid log data."

        redis_conn_for_publish = get_worker_redis_connection()
        # Fallback time if sim time somehow not set (shouldn't happen if state loaded)
        sim_time_iso = sim.simulation_time.isoformat() if sim.simulation_time else datetime.now().isoformat()
        emitted_count = 0

        for log_data in generated_logs_data:
            if not isinstance(log_data, dict): continue
            source = log_data.get("source_key")
            severity = log_data.get("severity_level")
            event_type = log_data.get("event_type")
            details = log_data.get("log_details")

            if not all([source, severity, event_type, isinstance(details, dict)]):
                print(f"{log_prefix} - WARNING: Skipping malformed log entry from LLM: {log_data}")
                continue

            # --- Re-use SimulationManager's log generation logic ---
            sim._clear_current_events() # Clear buffer in the sim instance
            # Call the log generator on the sim instance
            sim._generate_log_entry(event_type, severity, source, details)
            # Get the formatted event(s) from the sim instance's buffer
            generated_events = sim._get_and_clear_current_events()

            # Publish each generated event (usually just one log_feed_update)
            published_this_log = False
            for event in generated_events:
                if event.get("type") == "log_feed_update":
                    publish_event(redis_conn_for_publish, simulation_id, event)
                    published_this_log = True
                    # Optionally log the generated event details here if needed
                    # print(f"{log_prefix} - Published log event: {event['payload']}")
                else:
                    # If _generate_log_entry creates other event types (e.g., 'log'),
                    # decide if you want to publish those too, or just the log_feed_update
                    print(f"{log_prefix} - Note: _generate_log_entry produced non-log_feed event: {event.get('type')}")
                    # publish_event(redis_conn_for_publish, simulation_id, event) # Uncomment to publish all

            if published_this_log:
                emitted_count += 1
            else:
                 print(f"{log_prefix} - WARNING: _generate_log_entry did not produce expected 'log_feed_update' event for LLM data: {log_data}")
            # ---------------------------------------------------------

        print(f"{log_prefix} - Finished. Emitted {emitted_count} logs via Pub/Sub.")
        # We don't save state here as this task only *reads* state and generates logs
        return f"Generated and emitted {emitted_count} logs."

    except Exception as e:
        error_msg = f"Unhandled exception in task: {type(e).__name__} - {e}"
        print(f"{log_prefix} - ERROR: {error_msg}")
        print(traceback.format_exc())
        # Log error to sim state if possible
        if sim:
            try:
                sim.log_event(f"ERROR (GPTLog Task): {error_msg}", level="error", store_for_rating=True)
                # save_simulation_state(simulation_id, sim.get_state()) # Save state with error
            except Exception as log_err:
                 print(f"{log_prefix} - Error logging exception to sim state: {log_err}")
        return f"Error: Task failed unexpectedly ({type(e).__name__})"
    finally:
        if redis_conn_for_publish:
            try:
                redis_conn_for_publish.close()
            except Exception as close_err:
                 print(f"{log_prefix} - Error closing publishing Redis connection: {close_err}")