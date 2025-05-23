
import os
# import time # No longer explicitly needed for sleeps
import random
import textwrap
import json
import re # <<< ADDED for LLM rating parsing
import traceback # Keep for error logging within tasks
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any # <--- ADD Optional HERE

# --- OpenAI Import ---
try:
    from openai import OpenAI, APIError, RateLimitError
except ImportError as e:
    print(f"FATAL ERROR: OpenAI library import failed. Install 'openai'. Error: {e}")
    OpenAI = None
    APIError = Exception
    RateLimitError = Exception
except Exception as e:
    print(f"FATAL ERROR: Unexpected error during OpenAI import: {e}")
    OpenAI = None
    APIError = Exception
    RateLimitError = Exception

# --- Constants ---
AGENT_RESPONSE_TEMP = 0.7
MAX_TOKENS = 250
RATING_LLM_MODEL = "gpt-4o-mini"
LLM_RATING_MAX_TOKENS = 600
PR_FEEDBACK_MAX_TOKENS = 400
# <<< REAL-TIME CHANGE >>>
# This constant is now more critical. Shorter interval = smoother time but more load.
BACKGROUND_THREAD_CHECK_INTERVAL_REALTIME_SECONDS = 10 # Affects granularity of real-time sync

# --- Simulation Timing & Intensity ---
# These intervals are now relative to SIMULATION time, which advances based on REAL time
BASE_IDLE_AGENT_UPDATE_INTERVAL_SECONDS = 240
BASE_ESCALATION_CHECK_INTERVAL_SECONDS = 150
BASE_AGENT_INITIATIVE_DELAY_SECONDS = {"Paul Kahn": 300}
DEFAULT_SIM_DURATION_MINUTES = 30 # This is the target SIMULATION duration
BACKGROUND_LOG_NOISE_INTERVAL_SECONDS = 60
AGENT_CONTACT_COOLDOWN_MINUTES = 3 # Simulation minutes

INTENSITY_TIME_THRESHOLD_MINUTES = [10, 20] # Simulation minutes
INTENSITY_ESCALATION_THRESHOLD = [2, 4]
INTENSITY_DECREASE_FACTOR = 0.90
MIN_INTENSITY_MOD = 0.3

# --- Log Generation Constants ---
LOG_SEVERITY = {"NOMINAL": "INFO", "UNKNOWN": "INFO", "DEGRADED": "WARN", "CONNECTING": "INFO",
                "HIGH_LOAD": "WARN", "ANOMALOUS_TRAFFIC": "WARN", "HIGH_FAILURES": "HIGH",
                "ENCRYPTING": "HIGH", "ISOLATING": "WARN", "ISOLATED": "WARN", "MITIGATING": "INFO",
                "UNDER_MITIGATION": "INFO", "LOCKING_ACCOUNT": "WARN", "ACCESS_REVIEW": "INFO",
                "ANOMALOUS_ACCESS": "HIGH", "HIGH_EGRESS": "HIGH", "TRAFFIC_SHAPING": "INFO",
                "OFFLINE": "CRITICAL", "OFFLINE (Manual)": "WARN", "ISOLATING (Manual)": "WARN",
                "ENCRYPTED (CRITICAL)": "CRITICAL", "COMPROMISED (CRITICAL)": "CRITICAL",
                "ANOMALOUS_ADMIN_LOGIN": "CRITICAL", "LOGIN_UNAVAILABLE": "WARN",
                "ISOLATION_INITIATED": "INFO", "ISOLATION_COMPLETE": "INFO",
                "BLOCK_RULE_APPLIED": "INFO",
                "AUTH_SUCCESS": "LOW", "AUTH_FAILURE": "MEDIUM", "FW_DENY": "MEDIUM",
                "WEB_ACCESS": "LOW", "DNS_QUERY": "LOW"
                }
LOG_SOURCES = {
    "Website_Public": ["web-prod-01", "web-prod-02", "lb-ext-main", "cdn-pop-3"],
    "Customer_Database": ["db-cust-prod-master", "db-cust-prod-replica", "db-api-svc"],
    "Auth_System": ["dc-prod-01", "dc-prod-02", "auth-api-svc", "sso-idp-prod"],
    "Network_Segment_Gamma7": ["fw-dmz-gamma7", "switch-dmz-g7-core", "ids-dmz-gamma7"],
    "Network_Segment_Internal": ["switch-corp-core-1", "switch-corp-access-.*", "wifi-ap-corp.*", "dhcp-srv-1"],
    "File_Servers": ["filesrv-prod-01", "filesrv-prod-02", "filesrv-prod-.*", "nas-backup-corp"],
    "VPN_Access": ["vpn-gw-external", "vpn-concentrator-prod", "radius-auth-vpn"],
    "Network_Edge": ["router-edge-primary", "router-edge-secondary", "fw-edge-main", "ips-edge-main"],
    "HR_System": ["hris-prod-app", "hris-prod-db"],
    "SOC_Console": ["siem-prod-01", "soar-platform-01"],
    "Workstation": ["ws-user-.*", "laptop-dev-.*"]
}
LOG_TEMPLATES = {
    "AUTH_SUCCESS": "user='{user}' src_ip='{src_ip}' domain='{domain}' status='success'",
    "AUTH_FAILURE": "user='{user}' src_ip='{src_ip}' reason='{reason}' status='failure'",
    "FW_DENY": "proto='{proto}' src_ip='{src_ip}' src_port='{src_port}' dst_ip='{dst_ip}' dst_port='{dst_port}' action='deny' policy='{policy}'",
    "WEB_ACCESS": "client_ip='{src_ip}' method='{method}' url='{url}' status='{status_code}' user_agent='{user_agent}'",
    "DNS_QUERY": "client_ip='{src_ip}' query='{domain}' type='{qtype}' result='{result_ip}'",
    "SYS_STATUS_CHANGE": "old_status='{old_status}' new_status='{new_status}' reason='{reason}' event_source='{event_source}'",
    "SERVICE_UNAVAILABLE": "service='{service_name}' reason='{reason}'",
    "NETWORK_CONGESTION": "interface='{interface}' bandwidth_util='{util}%' packets_dropped='{drops}'",
    "DATA_EXFIL_CONFIRMED": "src_ip='{src_ip}' dst_ip='{dst_ip}' volume_mb='{volume}' protocol='{proto}' confidence='high'",
    "DB_ANOMALOUS_QUERY": "user='{user}' src_ip='{src_ip}' target_table='{table}' query='{query_snippet}' risk_score='{risk}'",
    "HR_ANOMALOUS_ACCESS": "user='{user}' src_ip='{src_ip}' resource='{resource}' action='{action}' policy_violation='{policy}'",
    "DATA_COMPROMISE_INSIDER": "user='{user}' evidence='{evidence}' data_type='{data_type}'",
    "FILE_ACCESS_ENCRYPT": "user='{user}' process='{process}' file_path='{path}' action='encrypt_attempt' signature='{sig}'",
    "SYSTEM_STATE_CRITICAL": "component='{component}' message='{message}'",
    "SERVICE_SHUTDOWN_MANUAL": "service='{service_name}' requested_by='CTO Directive ({directive})'",
    "SYSTEM_ISOLATION_MANUAL": "system='{system_name}' requested_by='CTO Directive ({directive})'",
    "SYS_INITIAL_STATE": "system='{system_key}' status='{status}' reason='{reason}'", # Added for initial state
    "SYS_ISOLATION_INITIATED": "system='{system_name}' reason='{reason}'",
    "SYS_ISOLATION_COMPLETE": "system='{system_name}' result='success'",
    "BLOCK_RULE_APPLIED": "target_ip='{ip}' direction='{direction}' device='{device}' reason='Player Action'",
    "GENERIC_INFO": "message='{message}' details='{details}'",
    "GENERIC_WARN": "message='{message}' details='{details}'",
    "GENERIC_HIGH": "message='{message}' details='{details}'",
    "GENERIC_CRITICAL": "message='{message}' details='{details}'",
    "LOG_TEMPLATE_ERROR": "error='{error}' details='{details}'"
}

# --- Agent Personas ---
HAO_WANG_PERSONA = """
You are Hao Wang, Head of IT Security at CPM Security.
Personality: Technically proficient, calm under pressure but initially caught off-guard, cautious, focused on diagnosis, slightly informal.
Current Situation: Investigating a potential cyberattack. May have connection issues initially. Provide technical updates, advise caution against premature actions (like broad shutdowns unless absolutely necessary). Keep responses concise, focused on technicals. Remember conversation history (although it won't be persisted across tasks in this version).
"""
PAUL_KAHN_PERSONA = """
You are Paul Kahn, a non-technical executive at CPM Security.
Personality: Panics easily, focuses on immediate action, prioritizes perception, demanding, exaggerated language when stressed. Doesn't understand technical details.
Current Situation: Extremely anxious about a cyberattack's impact on business, reputation, upcoming meetings.
Your Goal: Repeatedly pressure the CTO (Jill) for drastic, immediate action (shutdowns) to 'control' the situation. Express urgency, frustration. Remember conversation history (although it won't be persisted across tasks in this version). Be demanding if you initiate contact.
"""
LYNDA_CARNEY_PERSONA = """
You are Lynda Carney, a senior Security Analyst on the IT Security team at CPM Security.
Personality: Detail-oriented, focused, 'boots-on-the-ground', professional but direct. Reports technical facts from the SOC.
Current Situation: Actively monitoring security consoles (SIEM, EDR, Firewall logs) during a cyberattack. Saw initial alerts.
Your Goal: Provide brief, factual updates on specific alerts or system statuses (e.g., "Seeing unusual RDP traffic from server X," "Web tier latency critical," "High auth failures persisting"). Reference associated log snippets or event IDs if applicable. Avoid speculation. Defer strategy to Hao/CTO. Keep responses concise and technical. Remember conversation history (although it won't be persisted across tasks in this version).
"""
CEO_PERSONA = """
You are Sarah Chen, the CEO of OnlineRetailCo.
Personality: Strategic, demands clarity, concerned about overall business impact and reputation, relies on CTO for technical leadership but needs high-level summaries and action plans. Impatient if updates are unclear.
Current Situation: Aware of a major incident, likely in high-level meetings. Limited availability.
Your Goal: If contacted, demand clear, concise summary: situation, actions, business impact (customer-facing), timeline. Need info for external stakeholders.
"""
LEGAL_PERSONA = """
You are David Rodriguez, General Counsel for OnlineRetailCo.
Personality: Methodical, risk-averse, focused on legal/compliance obligations (data privacy, regs like GDPR/CCPA), potential liability. Asks precise questions about data access/exfil and notification requirements.
Current Situation: Alerted to incident, reviewing potential legal ramifications.
Your Goal: If contacted, inquire about incident nature, specifically potential sensitive data access/exfil (PII, PCI, confidential). Advise caution in external comms. Determine breach notification triggers.
"""
PR_PERSONA = """
You are Maria Garcia, Head of Public Relations for OnlineRetailCo.
Personality: Focused on public perception, brand reputation, crisis communication strategy. Wants to control the narrative. Proactive in drafting statements but needs technical accuracy confirmed.
Current Situation: Aware of incident, preparing communication strategies.
Your Goal: If contacted, ask for confirmed facts for statements. Advise against speculation. Offer help shaping communications. If asked to review talking points ({talking_points}), provide feedback focusing on clarity, reassurance (without overpromising), managing perception, accuracy based on knowns ({final_status_summary}), and alignment with CTO decision ({shutdown_directive}).
"""

# Update personas
HAO_WANG_UPDATE_PERSONA = HAO_WANG_PERSONA + "\nGoal Now: Provide a *brief*, unsolicited status update on investigation (VPN status, findings, checks underway, lack of findings). Be concise (1-2 sentences)."
LYNDA_CARNEY_UPDATE_PERSONA = LYNDA_CARNEY_PERSONA + "\nGoal Now: Provide a *brief*, unsolicited update on *new* critical alerts or significant status changes observed in SOC (mention system/alert type/count). Or state 'monitoring continues, no major changes'. Concise (1-2 sentences)."

# --- Scenario Definitions ---
scenarios = {
    "Ransomware": {
        "description": "Critical systems encrypted. Negotiate, contain, recover under intense stakeholder pressure.",
        "initial_system_status": {"Website_Public": "NOMINAL", "Customer_Database": "UNKNOWN", "Auth_System": "HIGH_FAILURES", "Network_Segment_Gamma7": "UNKNOWN", "Network_Segment_Internal": "UNKNOWN", "File_Servers": "UNKNOWN", "VPN_Access": "DEGRADED"},
        "initial_agent_states": {"Lynda Carney": "busy_monitoring"},
        "escalation_rules": [
            {"condition": lambda sim, t_utc: sim.system_status.get("Auth_System") == "HIGH_FAILURES" and (t_utc - sim.simulation_start_time).total_seconds() > (300 / sim.current_intensity_mod) and not sim._check_player_action('isolate', 'Network_Segment_Internal', since_time=t_utc - timedelta(minutes=5/sim.current_intensity_mod)),
             "action": lambda sim: sim.update_system_status("Network_Segment_Internal", "ANOMALOUS_TRAFFIC", reason="(Esc Rule 1: Lateral Movement Suspected - No Isolation)", related_log_type="FW_DENY", log_details={"proto":"TCP", "dst_port":445})},
            {"condition": lambda sim, t_utc: sim.system_status.get("Network_Segment_Internal") == "ANOMALOUS_TRAFFIC" and (t_utc - sim.simulation_start_time).total_seconds() > (600 / sim.current_intensity_mod),
             "action": lambda sim: sim.update_system_status("File_Servers", "ENCRYPTING", reason="(Esc Rule 2: Encryption Activity Detected!)", related_log_type="FILE_ACCESS_ENCRYPT", log_details={"user":"SYSTEM", "process":"unknown.exe", "sig":"Ransom.Generic"})},
            {"condition": lambda sim, t_utc: sim.system_status.get("File_Servers") == "ENCRYPTING" and (t_utc - sim.simulation_start_time).total_seconds() > (900 / sim.current_intensity_mod),
             "action": lambda sim: sim.update_system_status("File_Servers", "ENCRYPTED (CRITICAL)", reason="(Esc Rule 3: Servers Encrypted!)", related_log_type="SYSTEM_STATE_CRITICAL", log_details={"component":"FS_DataVol", "message":"Filesystem inaccessible"})},
        ],
        "intensity_modifier": {"Low": 1.5, "Medium": 1.0, "High": 0.7}
    },
    "DDoS": {
        "description": "Services overwhelmed by malicious traffic. Mitigate, identify source, maintain availability.",
        "initial_system_status": {"Website_Public": "DEGRADED", "Customer_Database": "NOMINAL", "Auth_System": "NOMINAL", "Network_Segment_Gamma7": "NOMINAL", "Network_Edge": "HIGH_LOAD", "File_Servers": "NOMINAL", "VPN_Access": "NOMINAL"},
        "initial_agent_states": {"Lynda Carney": "busy_monitoring"},
        "escalation_rules": [
            {"condition": lambda sim, t_utc: sim.system_status.get("Network_Edge") == "HIGH_LOAD" and (t_utc - sim.simulation_start_time).total_seconds() > (300 / sim.current_intensity_mod) and not sim._check_player_action('block ip', None, since_time=t_utc - timedelta(minutes=5/sim.current_intensity_mod)),
             "action": lambda sim: sim.update_system_status("Website_Public", "OFFLINE", reason="(Esc Rule 1: DDoS Overload - Mitigation Delayed)", related_log_type="SERVICE_UNAVAILABLE", log_details={"service_name":"PublicWebsite"})},
            {"condition": lambda sim, t_utc: sim.system_status.get("Website_Public") == "OFFLINE" and (t_utc - sim.simulation_start_time).total_seconds() > (900 / sim.current_intensity_mod),
             "action": lambda sim: sim.update_system_status("VPN_Access", "DEGRADED", reason="(Esc Rule 2: Network Congestion)", related_log_type="NETWORK_CONGESTION", log_details={"interface":"core-gw-link", "util":95, "drops": random.randint(1000,5000)})},
        ],
        "intensity_modifier": {"Low": 1.5, "Medium": 1.0, "High": 0.6}
    },
    "Critical Data Breach": {
        "description": "Sensitive data exfiltrated. Manage response, compliance, forensics, and communication.",
        "initial_system_status": {"Website_Public": "NOMINAL", "Customer_Database": "ANOMALOUS_ACCESS", "Auth_System": "NOMINAL", "Network_Segment_Gamma7": "UNKNOWN", "Network_Segment_Internal": "UNKNOWN", "File_Servers": "NOMINAL", "VPN_Access": "NOMINAL", "Network_Edge": "HIGH_EGRESS"},
        "initial_agent_states": {"Lynda Carney": "busy_monitoring", "Legal Counsel": "available", "PR Head": "available"},
        "escalation_rules": [
             {"condition": lambda sim, t_utc: sim.system_status.get("Customer_Database") == "ANOMALOUS_ACCESS" and sim.system_status.get("Network_Edge") == "HIGH_EGRESS" and (t_utc - sim.simulation_start_time).total_seconds() > (480 / sim.current_intensity_mod) and not sim._check_player_action('isolate', 'Customer_Database', since_time=t_utc - timedelta(minutes=8/sim.current_intensity_mod)),
             "action": lambda sim: sim.update_system_status("Customer_Database", "COMPROMISED (CRITICAL)", reason="(Esc Rule 1: Data Exfiltration Confirmed! - No Isolation)", related_log_type="DATA_EXFIL_CONFIRMED", log_details={"dst_ip":"1.2.3.4", "volume":random.randint(50,500), "proto":"HTTPS"})},
             {"condition": lambda sim, t_utc: "COMPROMISED" in sim.system_status.get("Customer_Database", "") and (t_utc - sim.simulation_start_time).total_seconds() > (900 / sim.current_intensity_mod),
             "action": lambda sim: sim.update_system_status("Website_Public", "DEGRADED", reason="(Esc Rule 2: Distraction/Obfuscation?)", related_log_type="WEB_ACCESS", log_details={"status_code":503})},
        ],
        "intensity_modifier": {"Low": 1.5, "Medium": 1.0, "High": 0.8}
    },
     "Insider Threat": {
        "description": "Malicious activity detected from within. Identify the source, assess damage, manage internal fallout.",
        "initial_system_status": {"Website_Public": "NOMINAL", "Customer_Database": "UNKNOWN", "Auth_System": "ANOMALOUS_ADMIN_LOGIN", "Network_Segment_Internal": "ANOMALOUS_TRAFFIC", "File_Servers": "UNKNOWN", "VPN_Access": "NOMINAL", "HR_System": "UNKNOWN"},
        "initial_agent_states": {"Lynda Carney": "investigating", "Hao Wang": "available", "Legal Counsel": "available"},
        "escalation_rules": [
             {"condition": lambda sim, t_utc: sim.system_status.get("Auth_System") == "ANOMALOUS_ADMIN_LOGIN" and sim.system_status.get("Network_Segment_Internal") == "ANOMALOUS_TRAFFIC" and (t_utc - sim.simulation_start_time).total_seconds() > (420 / sim.current_intensity_mod),
              "action": lambda sim: sim.update_system_status("Customer_Database", "ANOMALOUS_ACCESS", reason="(Esc Rule 1: Insider Accessing Customer DB)", related_log_type="DB_ANOMALOUS_QUERY", log_details={"user":"admin_suspicious", "table":"customers_pii", "query_snippet":"SELECT * FROM ...", "risk":85})},
             {"condition": lambda sim, t_utc: sim.system_status.get("Auth_System") == "ANOMALOUS_ADMIN_LOGIN" and (t_utc - sim.simulation_start_time).total_seconds() > (720 / sim.current_intensity_mod),
              "action": lambda sim: sim.update_system_status("HR_System", "ANOMALOUS_ACCESS", reason="(Esc Rule 2: Insider Accessing HR System)", related_log_type="HR_ANOMALOUS_ACCESS", log_details={"user":"admin_suspicious", "resource":"salary_info", "action":"read", "policy":"Confidential Data Access"})},
             {"condition": lambda sim, t_utc: "ANOMALOUS_ACCESS" in sim.system_status.get("Customer_Database","") and (t_utc - sim.simulation_start_time).total_seconds() > (1080 / sim.current_intensity_mod) and not sim._check_player_action('isolate', 'Customer_Database', since_time=t_utc - timedelta(minutes=10/sim.current_intensity_mod)),
              "action": lambda sim: sim.update_system_status("Customer_Database", "COMPROMISED (CRITICAL)", reason="(Esc Rule 3: Sensitive Data Compromised by Insider! - No Action)", related_log_type="DATA_COMPROMISE_INSIDER", log_details={"user":"admin_suspicious", "evidence":"Excessive data export logs", "data_type":"PII/PCI"})},
        ],
        "intensity_modifier": {"Low": 1.5, "Medium": 1.0, "High": 0.7}
    }
}

# Define default agents structure outside the class for load_state access
default_agents = {
    "Hao Wang": {"role": "Head of IT Security", "state": "available", "persona": HAO_WANG_PERSONA, "update_persona": HAO_WANG_UPDATE_PERSONA, "flags": {"has_advised_caution": False, "called_by_player": False, "attempted_call": False}},
    "Paul Kahn": {"role": "Executive", "state": "available", "persona": PAUL_KAHN_PERSONA, "update_persona": None, "flags": {"has_demanded_shutdown": False, "called_by_player": False, "attempted_call": False}},
    "Lynda Carney": {"role": "Sr. Security Analyst", "state": "busy_monitoring", "persona": LYNDA_CARNEY_PERSONA, "update_persona": LYNDA_CARNEY_UPDATE_PERSONA, "flags": {"has_reported": False, "called_by_player": False, "alerted_encryption": False, "alerted_critical": False, "alerted_compromise": False}},
    "CEO": {"role": "CEO", "state": "busy_external_call", "persona": CEO_PERSONA, "update_persona": None, "flags": {}},
    "Legal Counsel": {"role": "Legal Counsel", "state": "available", "persona": LEGAL_PERSONA, "update_persona": None, "flags": {}},
    "PR Head": {"role": "Head of PR", "state": "available", "persona": PR_PERSONA, "update_persona": None, "flags": {}}
}


class SimulationManager:
    def __init__(self, simulation_id=None, user_id=None, guest_id=None, user_name: Optional[str] = None):
        # --- Core State ---
        self.simulation_id = simulation_id
        self.user_id = user_id
        self.guest_id = guest_id
        base_player_name = user_name if user_name else "Player"
        self.player_name = f"{base_player_name} (CTO)"
        self.player_role = "CTO"
        self.current_location = "War Room"
        self.simulation_state = "SETUP" # Initial state
        self.simulation_running = False

        # --- Simulation Configuration ---
        self.selected_scenario_key = None
        self.selected_scenario = None
        self.initial_intensity_mod = 1.0
        self.current_intensity_mod = 1.0
        self._custom_agents_to_add = {} # For setup phase only

        # --- Time Management (Ensure initialized to None) ---
        self.simulation_start_time: datetime | None = None
        self.simulation_time: datetime | None = None # THIS IS SIMULATION TIME
        self.simulation_end_time: datetime | None = None
        self.last_escalation_check_time: datetime | None = None # Based on sim time
        self.last_background_event_check_time: datetime | None = None # Based on sim time
        self.last_intensity_check_time: datetime | None = None # Based on sim time
        self.last_log_noise_time: datetime | None = None # Based on sim time
        # <<< ADDED for Real-Time Sync >>>
        self.last_real_time_sync: datetime | None = None # Stores REAL UTC time of last sync

        # --- Dynamic State ---
        self.active_conversation_partner = None
        self.waiting_call_agent_name = None
        self.missed_calls = []
        self.system_status = {}
        self.escalation_level = 0
        self.player_decisions = {"shutdown_directive": "pending"}
        self.agents = {} # Agent data (state, flags - history not persisted)

        # --- Metrics & Logging History ---
        self.metrics = {}
        self.player_action_log = [] # Stores tuples: (timestamp_iso, action, target, details)
        self.event_log_history = [] # For rating context (persisted)

        # --- Event Handling (for current task) ---
        self._current_events = [] # Temporary storage for events generated in one call

        # --- External Services ---
        self.client = None # OpenAI client

        # --- Initialization ---
        self._initialize_openai_client()
        self._reset_metrics() # Ensure metrics structure is created even before start

    def _initialize_openai_client(self):
        # Keep exactly as before - crucial for operation
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.log_event("FATAL ERROR: OPENAI_API_KEY environment variable not set.", level="error", store_for_rating=True)
            return
        if OpenAI is None:
             self.log_event("FATAL ERROR: OpenAI library not imported.", level="error", store_for_rating=True)
             return
        try:
            self.client = OpenAI(api_key=api_key, timeout=30.0, max_retries=2)
        except Exception as e:
            print(f"FATAL ERROR: Failed to initialize OpenAI client during init: {e}") # Print for immediate feedback
            self.client = None

    def _reset_metrics(self):
        # Reset metrics structure - Ensure datetimes are None initially
        self.metrics = {
            "time_to_first_critical": None, # Expect datetime or None
            "systems_compromised_count": 0, # Expect int
            "key_actions_taken": [], # Expect list of tuples/lists: (timestamp_str, action, target)
            "time_wasted_waiting": timedelta(0), # Expect timedelta
            "escalations_triggered": 0, # Expect int
            "agents_contacted": set(), # Expect set of strings
            "critical_agent_contact_time": {}, # Expect dict[str, datetime]
            "_compromised_set": set() # Internal helper
        }
        # Reset logs associated with metrics/rating context
        self.event_log_history = []
        self.player_action_log = []

    # --- Event Handling Methods ---
    def _clear_current_events(self):
        self._current_events = []

    def _get_and_clear_current_events(self):
        events = list(self._current_events)
        self._current_events = []
        return events

    def emit_event(self, event_type, payload):
        event_payload = payload.copy()
        event_payload['simulation_id'] = self.simulation_id
        event = {"type": event_type, "payload": event_payload}
        self._current_events.append(event)

    def log_event(self, message, level="info", data=None, store_for_rating=False):
        # Use current UTC time for the real timestamp
        real_timestamp_utc = datetime.now(timezone.utc)
        # Use simulation time if available and aware, otherwise use real time
        sim_time_aware = self.simulation_time if self.simulation_time and self.simulation_time.tzinfo else real_timestamp_utc
        sim_time_str = sim_time_aware.strftime("%H:%M:%S") # Format is local to the timezone (UTC)

        log_entry = {
            "type": "log",
            "payload": {
                "simulation_id": self.simulation_id,
                "timestamp": real_timestamp_utc.isoformat(), # Store real time as UTC ISO
                "sim_time": sim_time_str, # Display time
                "message": message,
                "level": level,
                "data": data
            }
        }
        self._current_events.append(log_entry)

        if store_for_rating and self.simulation_state != "SETUP":
            # Store log with sim_time_str for readability in rating context
            self.event_log_history.append(f"[{sim_time_str} / {level.upper()}] {message}")
            # Limit history size
            if len(self.event_log_history) > 100:
                self.event_log_history = self.event_log_history[-80:]

    # --- State Management Methods ---

    def get_state(self) -> dict:
        """Returns JSON serializable state, ensuring datetimes are UTC aware ISO strings."""

        def ensure_aware_iso(dt):
            if dt and isinstance(dt, datetime):
                aware_dt = dt
                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                    print(f"Warning: Converting naive datetime {dt} to UTC in get_state.")
                    aware_dt = dt.replace(tzinfo=timezone.utc)
                return aware_dt.astimezone(timezone.utc).isoformat()
            return None

        # Apply helper to all datetime attributes
        start_time_iso = ensure_aware_iso(self.simulation_start_time)
        end_time_iso = ensure_aware_iso(self.simulation_end_time)
        sim_time_iso = ensure_aware_iso(self.simulation_time)
        last_esc_check_iso = ensure_aware_iso(self.last_escalation_check_time)
        last_bg_check_iso = ensure_aware_iso(self.last_background_event_check_time)
        last_int_check_iso = ensure_aware_iso(self.last_intensity_check_time)
        last_log_noise_iso = ensure_aware_iso(self.last_log_noise_time)
        # <<< ADDED for Real-Time Sync >>>
        last_sync_iso = ensure_aware_iso(self.last_real_time_sync)

        agent_simple_state = {}
        for name, data in self.agents.items():
             last_contact_iso = ensure_aware_iso(data.get('last_contact_time'))
             last_update_iso = ensure_aware_iso(data.get('last_update_time'))
             last_initiative_iso = ensure_aware_iso(data.get('last_initiative_check_time'))

             agent_simple_state[name] = {
                 "state": data.get('state'),
                 "flags": data.get('flags', {}),
                 "last_contact_time_iso": last_contact_iso,
                 "last_update_time_iso": last_update_iso,
                 "last_initiative_check_time_iso": last_initiative_iso,
             }

        state = {
            # --- Identifiers & Basic Info ---
            "simulation_id": self.simulation_id,
            "user_id": getattr(self, 'user_id', None),
            "guest_id": getattr(self, 'guest_id', None),
            "player_name": self.player_name,
            "player_role": self.player_role,
            "current_location": self.current_location,
            "simulation_running": self.simulation_running,
            "simulation_state": self.simulation_state,

            # --- Dynamic State ---
            "active_conversation_partner": self.active_conversation_partner,
            "waiting_call_agent_name": self.waiting_call_agent_name,
            "missed_calls": self.missed_calls,
            "system_status": self.system_status,
            "escalation_level": self.escalation_level,
            "player_decisions": self.player_decisions,
            "agents_simple_state": agent_simple_state,

            # --- Configuration ---
            "selected_scenario_key": self.selected_scenario_key,
            "initial_intensity_mod": self.initial_intensity_mod,
            "current_intensity_mod": self.current_intensity_mod,

            # --- Time Management (Serialized) ---
            "simulation_start_time_iso": start_time_iso,
            "simulation_end_time_iso": end_time_iso,
            "simulation_time_iso": sim_time_iso,
            "last_escalation_check_time_iso": last_esc_check_iso,
            "last_background_event_check_time_iso": last_bg_check_iso,
            "last_intensity_check_time_iso": last_int_check_iso,
            "last_log_noise_time_iso": last_log_noise_iso,
            # <<< ADDED for Real-Time Sync >>>
            "last_real_time_sync_iso": last_sync_iso,

            # --- Logs & Metrics (Serialized) ---
            "player_action_log": self.player_action_log[-20:],
            "metrics": self._serialize_metrics(self.metrics),
            "event_log_history": self.event_log_history,
        }
        return state

    def _serialize_metrics(self, metrics_input):
        # Keep exactly as before - already handles robust serialization
        serialized = metrics_input.copy() if metrics_input else {}

        def ensure_aware_iso(dt): # Inner helper for metrics datetimes
             if dt and isinstance(dt, datetime):
                 aware_dt = dt
                 if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                     aware_dt = dt.replace(tzinfo=timezone.utc)
                 return aware_dt.astimezone(timezone.utc).isoformat()
             elif dt is not None:
                  print(f"Warning: Metric datetime field has unexpected type {type(dt)}. Setting to None.")
             return None

        serialized['time_to_first_critical'] = ensure_aware_iso(serialized.get('time_to_first_critical'))

        t_wasted = serialized.get('time_wasted_waiting')
        if isinstance(t_wasted, timedelta):
            serialized['time_wasted_waiting'] = t_wasted.total_seconds()
        elif isinstance(t_wasted, (int, float)):
             serialized['time_wasted_waiting'] = float(t_wasted) # Ensure float
        else:
            if t_wasted is not None:
                 print(f"Warning: Metric 'time_wasted_waiting' has unexpected type {type(t_wasted)}. Setting to 0.0.")
            serialized['time_wasted_waiting'] = 0.0

        agents_set = serialized.get('agents_contacted')
        if isinstance(agents_set, set):
            serialized['agents_contacted'] = sorted(list(agents_set))
        elif isinstance(agents_set, list):
             serialized['agents_contacted'] = sorted(agents_set)
        else:
             if agents_set is not None: print(f"Warning: Metric 'agents_contacted' has unexpected type {type(agents_set)}. Setting to [].")
             serialized['agents_contacted'] = []

        crit_contact_dict = serialized.get('critical_agent_contact_time')
        if isinstance(crit_contact_dict, dict):
            new_crit_dict = {}
            for agent, dt in crit_contact_dict.items():
                iso_dt = ensure_aware_iso(dt)
                if iso_dt:
                    new_crit_dict[agent] = iso_dt
                elif dt is not None:
                     print(f"Warning: Skipping non-datetime value for agent '{agent}' in 'critical_agent_contact_time'. Type: {type(dt)}")
            serialized['critical_agent_contact_time'] = new_crit_dict
        else:
             if crit_contact_dict is not None: print(f"Warning: Metric 'critical_agent_contact_time' has unexpected type {type(crit_contact_dict)}. Setting to {{}}.")
             serialized['critical_agent_contact_time'] = {}

        key_actions = serialized.get('key_actions_taken')
        if isinstance(key_actions, list):
             sanitized_actions = []
             for action in key_actions:
                 if isinstance(action, (tuple, list)) and len(action) > 0:
                      sanitized_actions.append(list(action))
                 elif action is not None:
                      print(f"Warning: Unexpected item type {type(action)} in 'key_actions_taken'. Skipping.")
             serialized['key_actions_taken'] = sanitized_actions
        else:
             if key_actions is not None: print(f"Warning: Metric 'key_actions_taken' has unexpected type {type(key_actions)}. Setting to [].")
             serialized['key_actions_taken'] = []

        for key in ["systems_compromised_count", "escalations_triggered"]:
            val = serialized.get(key)
            if not isinstance(val, int):
                 print(f"Warning: Metric '{key}' has non-integer type {type(val)}. Setting to 0.")
                 serialized[key] = 0

        if '_compromised_set' in serialized:
            del serialized['_compromised_set']

        return serialized


    def load_state(self, state_dict: dict):
        """Populates the simulation instance, ensuring datetimes are loaded as aware UTC."""
        if not state_dict:
            print("Warning: load_state received empty state_dict.")
            return

        def load_aware_datetime(iso_string):
            if not iso_string or not isinstance(iso_string, str):
                return None
            try:
                if iso_string.endswith('Z'):
                    iso_string = iso_string[:-1] + '+00:00'
                dt = datetime.fromisoformat(iso_string)

                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                    print(f"Warning: Loaded naive datetime string '{iso_string}'. Assuming UTC.")
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (ValueError, TypeError) as e:
                print(f"Error parsing datetime string '{iso_string}': {e}")
                return None

        try:
            # --- Load Basic Info & Config ---
            self.simulation_id = state_dict.get("simulation_id")
            self.user_id = state_dict.get("user_id")
            self.guest_id = state_dict.get("guest_id")
            self.player_name = state_dict.get("player_name", "CTO")
            self.player_role = state_dict.get("player_role", "CTO")
            self.current_location = state_dict.get("current_location", "War Room")
            self.simulation_running = state_dict.get("simulation_running", False)
            self.simulation_state = state_dict.get("simulation_state", "ENDED")
            self.selected_scenario_key = state_dict.get("selected_scenario_key")
            self.selected_scenario = scenarios.get(self.selected_scenario_key) if self.selected_scenario_key else None
            if not self.selected_scenario and self.selected_scenario_key:
                 print(f"Warning: Could not load scenario definition for key '{self.selected_scenario_key}' during state load.")
                 self.simulation_running = False

            self.initial_intensity_mod = state_dict.get("initial_intensity_mod", 1.0)
            self.current_intensity_mod = state_dict.get("current_intensity_mod", 1.0)

            # --- Load Dynamic State (Non-Time) ---
            self.active_conversation_partner = state_dict.get("active_conversation_partner")
            self.waiting_call_agent_name = state_dict.get("waiting_call_agent_name")
            self.missed_calls = state_dict.get("missed_calls", [])
            self.system_status = state_dict.get("system_status", {})
            self.escalation_level = state_dict.get("escalation_level", 0)
            self.player_decisions = state_dict.get("player_decisions", {"shutdown_directive": "pending"})
            self.event_log_history = state_dict.get("event_log_history", [])
            self.player_action_log = state_dict.get("player_action_log", [])

            # --- Load Time Fields (Using Helper) ---
            self.simulation_start_time = load_aware_datetime(state_dict.get("simulation_start_time_iso"))
            self.simulation_end_time = load_aware_datetime(state_dict.get("simulation_end_time_iso"))
            self.simulation_time = load_aware_datetime(state_dict.get("simulation_time_iso"))
            self.last_escalation_check_time = load_aware_datetime(state_dict.get("last_escalation_check_time_iso"))
            self.last_background_event_check_time = load_aware_datetime(state_dict.get("last_background_event_check_time_iso"))
            self.last_intensity_check_time = load_aware_datetime(state_dict.get("last_intensity_check_time_iso"))
            self.last_log_noise_time = load_aware_datetime(state_dict.get("last_log_noise_time_iso"))
            # <<< ADDED for Real-Time Sync >>>
            self.last_real_time_sync = load_aware_datetime(state_dict.get("last_real_time_sync_iso"))

            if self.simulation_running and not self.simulation_time:
                print(f"ERROR: Simulation time failed to load. Stopping simulation.")
                self.simulation_running = False

            # --- Load Agent States ---
            self.agents = {}
            base_agent_definitions = default_agents
            agent_simple_state = state_dict.get("agents_simple_state", {})
            for name, base_data in base_agent_definitions.items():
                agent_state_data = agent_simple_state.get(name, {})
                last_contact_time = load_aware_datetime(agent_state_data.get("last_contact_time_iso"))
                last_update_time = load_aware_datetime(agent_state_data.get("last_update_time_iso"))
                last_initiative_time = load_aware_datetime(agent_state_data.get("last_initiative_check_time_iso"))

                if not last_initiative_time and self.simulation_time:
                    last_initiative_time = self.simulation_time

                self.agents[name] = {
                    **base_data.copy(),
                    "state": agent_state_data.get("state", base_data.get("state", "available")),
                    "flags": agent_state_data.get("flags", base_data.get("flags", {})).copy(),
                    "conversation_history": [],
                    "last_contact_time": last_contact_time,
                    "last_update_time": last_update_time,
                    "last_initiative_check_time": last_initiative_time,
                }

            # --- Load Metrics ---
            self.metrics = self._deserialize_metrics(state_dict.get("metrics", {}))

            # --- Final Checks ---
            if not self.client:
                 self._initialize_openai_client()

            self._clear_current_events()

        except Exception as e:
             print(f"ERROR during state loading: {type(e).__name__} - {e}")
             print(traceback.format_exc())
             self.simulation_running = False
             self.simulation_state = "ERROR"

    def _deserialize_metrics(self, metrics_dict):
        # Keep exactly as before - already handles robust deserialization
        deserialized = metrics_dict.copy() if metrics_dict else {}

        def load_aware_datetime(iso_string): # Inner helper for metrics datetimes
            if iso_string and isinstance(iso_string, str):
                try:
                    if iso_string.endswith('Z'):
                        iso_string = iso_string[:-1] + '+00:00'
                    dt = datetime.fromisoformat(iso_string)
                    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                         return dt.replace(tzinfo=timezone.utc)
                    return dt.astimezone(timezone.utc) # Convert to UTC
                except (ValueError, TypeError):
                     print(f"Warning: Failed to parse datetime string '{iso_string}' in metrics. Setting to None.")
                     return None
            return None

        try:
            deserialized['time_to_first_critical'] = load_aware_datetime(deserialized.get('time_to_first_critical'))

            crit_contact_times = {}
            raw_crit_dict = deserialized.get('critical_agent_contact_time', {})
            if isinstance(raw_crit_dict, dict):
                for agent, dt_str in raw_crit_dict.items():
                    loaded_dt = load_aware_datetime(dt_str)
                    if loaded_dt: crit_contact_times[agent] = loaded_dt
            deserialized['critical_agent_contact_time'] = crit_contact_times

            time_wasted_val = deserialized.get('time_wasted_waiting')
            if isinstance(time_wasted_val, (int, float)):
                 try:
                     deserialized['time_wasted_waiting'] = timedelta(seconds=float(time_wasted_val))
                 except ValueError:
                      print(f"Warning: Invalid numeric value '{time_wasted_val}' for time_wasted_waiting. Setting to 0.")
                      deserialized['time_wasted_waiting'] = timedelta(0)
            elif not isinstance(time_wasted_val, timedelta):
                 if time_wasted_val is not None: print(f"Warning: Unexpected type {type(time_wasted_val)} for time_wasted_waiting. Setting to 0.")
                 deserialized['time_wasted_waiting'] = timedelta(0)

            agents_list = deserialized.get('agents_contacted')
            if isinstance(agents_list, list):
                 deserialized['agents_contacted'] = set(agents_list)
            elif not isinstance(agents_list, set):
                 if agents_list is not None: print(f"Warning: Unexpected type {type(agents_list)} for agents_contacted. Setting to empty set.")
                 deserialized['agents_contacted'] = set()

            key_actions_list = deserialized.get('key_actions_taken')
            if isinstance(key_actions_list, list):
                converted_actions = []
                for action in key_actions_list:
                     if isinstance(action, list) and len(action) > 0 :
                         converted_actions.append(tuple(action))
                     elif isinstance(action, tuple) and len(action) > 0:
                          converted_actions.append(action)
                     elif action is not None:
                          print(f"Warning: Skipping invalid item {action} in key_actions_taken during deserialization.")
                deserialized['key_actions_taken'] = converted_actions
            elif not isinstance(key_actions_list, list):
                 if key_actions_list is not None: print(f"Warning: Unexpected type {type(key_actions_list)} for key_actions_taken. Setting to empty list.")
                 deserialized['key_actions_taken'] = []

            for key in ["systems_compromised_count", "escalations_triggered"]:
                 val = deserialized.get(key)
                 if not isinstance(val, int):
                      try: deserialized[key] = int(val) if val is not None else 0
                      except (ValueError, TypeError): deserialized[key] = 0
                 if deserialized[key] < 0: deserialized[key] = 0

        except Exception as e:
             print(f"Error during _deserialize_metrics processing: {type(e).__name__} - {e}. Metrics dict: {metrics_dict}")
             deserialized = {}

        # Recreate internal set based on *current* system status after loading state
        deserialized['_compromised_set'] = set()
        if self.system_status:
            deserialized['_compromised_set'] = set(k for k, v in self.system_status.items() if any(crit in v for crit in ["CRITICAL", "COMPROMISED", "ENCRYPTED"]))

        # Ensure all standard metric keys exist with correct default types
        deserialized.setdefault('time_to_first_critical', None)
        deserialized.setdefault('systems_compromised_count', 0)
        deserialized.setdefault('key_actions_taken', [])
        deserialized.setdefault('time_wasted_waiting', timedelta(0))
        deserialized.setdefault('escalations_triggered', 0)
        deserialized.setdefault('agents_contacted', set())
        deserialized.setdefault('critical_agent_contact_time', {})
        deserialized.setdefault('_compromised_set', set())

        return deserialized


    # --- Core Simulation Logic ---

    def _get_random_ip(self, ip_type="any"):
        # Keep exactly as before
        if ip_type == "internal":
            return f"10.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(2, 254)}"
        elif ip_type == "external":
            first = random.choice([i for i in range(1, 224) if i not in [10, 127, 172, 192]])
            if first == 172: second = random.randint(16, 31)
            elif first == 192: second = 168
            else: second = random.randint(0, 255)
            return f"{first}.{second}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        else: # Mix
            return self._get_random_ip(random.choice(["internal", "external"]))

    def _generate_log_entry(self, event_type, severity_level, source_key, details_dict):
        # Uses aware simulation time UTC time for log timestamp
        if not self.simulation_time or not self.simulation_time.tzinfo:
             current_time_utc = datetime.now(timezone.utc) # Fallback to real UTC time
        else:
             current_time_utc = self.simulation_time.astimezone(timezone.utc)

        sim_time_iso = current_time_utc.isoformat() # Store UTC ISO time
        possible_sources = LOG_SOURCES.get(source_key, ["unknown_system"])
        source_identifier = random.choice(possible_sources).replace(".*", str(random.randint(1, 9)))

        log_template = LOG_TEMPLATES.get(event_type)
        full_details = details_dict.copy() # Avoid modifying original dict

        if not log_template:
            fallback_map = {"INFO": "GENERIC_INFO", "WARN": "GENERIC_WARN", "HIGH": "GENERIC_HIGH", "CRITICAL": "GENERIC_CRITICAL", "LOW": "GENERIC_INFO", "MEDIUM": "GENERIC_WARN"}
            severity_str_lookup = LOG_SEVERITY.get(severity_level, "INFO")
            log_template_key = fallback_map.get(severity_str_lookup, "GENERIC_INFO")
            log_template = LOG_TEMPLATES.get(log_template_key, "{message}")
            full_details.setdefault('message', full_details.get('reason', f"Generic {severity_str_lookup} event"))
            full_details.setdefault('details', str({k:v for k,v in full_details.items() if k not in ['message', 'reason']}))
            event_type = log_template_key

        # (Keep placeholder filling logic)
        full_details.setdefault('src_ip', self._get_random_ip("any"))
        full_details.setdefault('user', 'n/a')
        full_details.setdefault('domain', 'onlineretailco.com')
        full_details.setdefault('reason', 'n/a')
        full_details.setdefault('proto', 'tcp')
        full_details.setdefault('src_port', random.randint(1024, 65535))
        full_details.setdefault('dst_ip', self._get_random_ip("internal"))
        full_details.setdefault('dst_port', random.choice([80, 443, 22, 3389, 445, 135]))
        full_details.setdefault('policy', f'pol-{random.randint(100,999)}')
        full_details.setdefault('method', random.choice(['GET', 'POST']))
        full_details.setdefault('url', f'/path/{random.choice(["api", "images", "data"])}/{random.randint(1,100)}')
        full_details.setdefault('status_code', random.choice([200, 404, 500, 401, 403]))
        full_details.setdefault('user_agent', 'Generic Bot/1.0')
        full_details.setdefault('qtype', 'A')
        full_details.setdefault('result_ip', self._get_random_ip("external"))
        full_details.setdefault('old_status', 'UNKNOWN')
        full_details.setdefault('new_status', 'UNKNOWN')
        full_details.setdefault('event_source', 'system')
        full_details.setdefault('service_name', 'unknown_service')
        full_details.setdefault('interface', 'eth0')
        full_details.setdefault('util', random.randint(80, 100))
        full_details.setdefault('drops', random.randint(100, 10000))
        full_details.setdefault('volume', random.randint(1, 1000))
        full_details.setdefault('table', 'generic_table')
        full_details.setdefault('query_snippet', 'SELECT ...')
        full_details.setdefault('risk', random.randint(50, 100))
        full_details.setdefault('resource', 'generic_resource')
        full_details.setdefault('action', 'read')
        full_details.setdefault('evidence', 'log anomaly')
        full_details.setdefault('data_type', 'PII')
        full_details.setdefault('process', 'malware.exe')
        full_details.setdefault('path', '/data/sensitive')
        full_details.setdefault('sig', 'Ransom.Variant')
        full_details.setdefault('component', 'kernel')
        full_details.setdefault('message', 'Critical error detected')
        full_details.setdefault('directive', 'Emergency Containment')
        full_details.setdefault('system_name', 'unknown_system')
        full_details.setdefault('ip', '1.2.3.4')
        full_details.setdefault('direction', 'ingress')
        full_details.setdefault('device', 'firewall-01')
        full_details.setdefault('details', 'N/A')
        full_details.setdefault('system_key', source_key)
        full_details.setdefault('status', 'N/A')

        try:
            log_message = log_template.format(**full_details)
        except KeyError as e:
            error_msg = f"Log template error for type '{event_type}': Missing key {e}. Check LOG_TEMPLATES."
            log_message = LOG_TEMPLATES["LOG_TEMPLATE_ERROR"].format(error=error_msg, details=str(full_details))
            self.log_event(error_msg, level="error") # Log the template error itself
            event_type = "LOG_TEMPLATE_ERROR"
            severity_level = "WARN"

        severity_str = LOG_SEVERITY.get(severity_level, "INFO")

        log_feed_entry = {
            "timestamp": sim_time_iso, # UTC ISO format
            "severity": severity_str,
            "source": source_identifier,
            "type": event_type,
            "message": log_message,
            "details": full_details
        }
        self.emit_event("log_feed_update", log_feed_entry)

        if event_type not in ["AUTH_SUCCESS", "WEB_ACCESS", "DNS_QUERY", "GENERIC_INFO"]:
             self.log_event(f"Generated Log: {log_message[:120]}...", level="debug", store_for_rating=False)

    def _generate_background_noise_logs(self):
        """Generates random low-severity logs. Uses aware simulation time UTC."""
        if not self.simulation_running or not self.simulation_time or not self.simulation_time.tzinfo: return

        now_sim_utc = self.simulation_time.astimezone(timezone.utc)
        interval_met = True
        # Check against last log time using simulation time
        if self.last_log_noise_time and self.last_log_noise_time.tzinfo:
             try:
                 last_noise_sim_utc = self.last_log_noise_time.astimezone(timezone.utc)
                 if (now_sim_utc - last_noise_sim_utc).total_seconds() < BACKGROUND_LOG_NOISE_INTERVAL_SECONDS:
                     interval_met = False
             except (TypeError, ValueError):
                 print("Warning: Type/Value error during background noise interval check.")
                 interval_met = True
        # else: interval_met = True

        if interval_met:
            num_logs = random.randint(2, 5)
            for _ in range(num_logs):
                source_sys = random.choice(list(LOG_SOURCES.keys()))
                noise_type = random.choice(["AUTH_SUCCESS", "WEB_ACCESS", "DNS_QUERY"])
                severity_level_str = noise_type
                details = {}
                if noise_type == "AUTH_SUCCESS": details['user'] = f"user{random.randint(100,999)}"
                if noise_type == "WEB_ACCESS": details['status_code'] = 200
                self._generate_log_entry(noise_type, severity_level_str, source_sys, details)
            self.last_log_noise_time = now_sim_utc # Store the aware simulation UTC time


    def call_llm_api(self, persona_prompt, history_list, user_input, agent_name="AI Agent", model="gpt-4o-mini", max_tokens=MAX_TOKENS, temperature=AGENT_RESPONSE_TEMP, response_format=None):
        """Synchronous LLM call. Logs use aware UTC time."""
        # Keep exactly as before
        if not self.client:
            self.log_event(f"LLM call skipped for {agent_name}: Client not initialized.", level="error", store_for_rating=True)
            return "(LLM Client Error: Not Initialized)"

        self.log_event(f"[Worker] Calling OpenAI ({model}) for {agent_name}...", level="debug")

        contextual_input = user_input
        if agent_name in ["Hao Wang", "Lynda Carney"] and self.system_status:
             status_summary = self.get_status_summary(compact=True)
             if status_summary != "All systems NOMINAL.":
                  try: contextual_input += f"\n(Current relevant system status context: {status_summary})"
                  except Exception as e: self.log_event(f"Warning: Error accessing system status for context: {e}", level="warning")

        if not isinstance(history_list, list):
            self.log_event(f"Warning: Invalid history_list type ({type(history_list)}) passed for {agent_name}. Using empty history.", level="warning")
            history_list = []

        messages = [{"role": "system", "content": persona_prompt}]
        history_limit = 2
        messages.extend(history_list[-history_limit:])
        messages.append({"role": "user", "content": contextual_input})

        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if response_format and isinstance(response_format, dict) and ("gpt-4" in model or "gpt-3.5" in model): # Added 3.5 check
            request_params["response_format"] = response_format

        try:
            completion = self.client.chat.completions.create(**request_params)
            response_text = completion.choices[0].message.content.strip() or "(Received empty response from AI)"
            self.log_event(f"[Worker] Response received from {agent_name}.", level="debug")
            return response_text
        except RateLimitError as e:
            self.log_event(f"ERROR: OpenAI Rate Limit Exceeded for {agent_name}. {e}", level="error", store_for_rating=True)
            return f"({agent_name} is experiencing high call volume - Rate Limit)"
        except APIError as e:
            self.log_event(f"ERROR: OpenAI API Error for {agent_name}: Status={getattr(e, 'status_code', 'N/A')}, Message={getattr(e, 'message', str(e))}", level="error", store_for_rating=True)
            return f"({agent_name} experiencing connection difficulties - API Error: {getattr(e, 'status_code', 'N/A')})"
        except Exception as e:
            err_type = type(e).__name__
            err_str = str(e).lower()
            if "timed out" in err_str or "timeout" in err_str or "timedout" in err_str:
                 self.log_event(f"ERROR: OpenAI Timeout Error for {agent_name}: {e}", level="error", store_for_rating=True)
                 return f"({agent_name} connection timed out)"
            self.log_event(f"ERROR: Unexpected OpenAI error for {agent_name}: {err_type} - {e}", level="error", store_for_rating=True)
            self.log_event(traceback.format_exc(), level="error")
            return f"({agent_name} experienced an unexpected connection error: {err_type})"


    def add_to_agent_history(self, agent_name, role, content):
        # Keep exactly as before - modifies in-memory history only
        if agent_name in self.agents:
            try:
                if "conversation_history" not in self.agents[agent_name] or not isinstance(self.agents[agent_name]["conversation_history"], list):
                    self.agents[agent_name]["conversation_history"] = []

                history = self.agents[agent_name]["conversation_history"]
                history.append({"role": role, "content": content})
                if len(history) > 6:
                    self.agents[agent_name]["conversation_history"] = history[-4:]
            except KeyError:
                 self.log_event(f"Warning: Agent {agent_name} found but 'conversation_history' access failed unexpectedly.", level="warning")
            except Exception as e:
                 self.log_event(f"Error adding to in-memory history for {agent_name}: {e}", level="error")
        else:
            self.log_event(f"Warning: Attempted history add for unknown agent: {agent_name}", level="warning")

    def update_agent_state(self, agent_name, new_state):
        # Keep exactly as before - modifies state that WILL be saved
        if agent_name in self.agents:
            try:
                old_state = self.agents[agent_name].get('state', 'unknown')
                if old_state != new_state:
                    self.agents[agent_name]['state'] = new_state
                    self.log_event(f"Agent State Change: {agent_name} '{old_state}' -> '{new_state}'")
                    self.emit_event("agent_status_update", {"agent_name": agent_name, "state": new_state})
                    return True
                return False
            except KeyError:
                self.log_event(f"Warning: KeyError accessing state for known agent {agent_name}.", level="warning")
                return False
            except Exception as e:
                self.log_event(f"Error updating agent state for {agent_name}: {e}", level="error")
                return False
        else:
            self.log_event(f"Warning: Update state called for unknown agent: {agent_name}", level="warning")
            return False

    def update_system_status(self, system_key, new_status, reason="", related_log_type=None, log_details=None):
        # Modifies state, uses aware simulation time for metrics.
        changed = False
        if not self.system_status: self.system_status = {}
        old_status = self.system_status.get(system_key, "UNKNOWN")

        if old_status != new_status:
            self.system_status[system_key] = new_status
            log_msg = f"System Status Change: {system_key} '{old_status}' -> '{new_status}' {reason}"
            level = "info"
            severity_str = LOG_SEVERITY.get(new_status.split(" ")[0], "INFO")
            if severity_str == "WARN": level = "warning"
            elif severity_str in ["HIGH", "CRITICAL"]: level = "alert"
            self.log_event(log_msg, level=level, store_for_rating=True)
            self.emit_event("system_status_update", {"system_key": system_key, "status": new_status, "reason": reason})
            changed = True

            # --- Metric Update (Using aware simulation time) ---
            if self.simulation_time and self.simulation_time.tzinfo:
                now_sim_utc = self.simulation_time.astimezone(timezone.utc)

                if not self.metrics: self._reset_metrics()

                is_critical = any(crit in new_status for crit in ["CRITICAL", "COMPROMISED", "ENCRYPTED"])
                was_critical = any(crit in old_status for crit in ["CRITICAL", "COMPROMISED", "ENCRYPTED"])

                if is_critical and not was_critical:
                    if self.metrics.get("time_to_first_critical") is None and self.simulation_start_time and self.simulation_start_time.tzinfo:
                        self.metrics["time_to_first_critical"] = now_sim_utc # Store aware sim time

                    if '_compromised_set' not in self.metrics or not isinstance(self.metrics['_compromised_set'], set):
                         self.metrics['_compromised_set'] = set()

                    if system_key not in self.metrics["_compromised_set"]:
                        current_count = self.metrics.get("systems_compromised_count", 0)
                        self.metrics["systems_compromised_count"] = current_count + 1 if isinstance(current_count, int) else 1
                        self.metrics["_compromised_set"].add(system_key)

            # --- Log Generation ---
            log_severity_level = new_status.split(" ")[0]
            log_event_type = related_log_type or "SYS_STATUS_CHANGE"
            full_log_details = {
                "old_status": old_status, "new_status": new_status,
                "reason": reason.strip("()"), "event_source": "simulation_engine"
            }
            if log_details: full_log_details.update(log_details)
            self._generate_log_entry(log_event_type, log_severity_level, system_key, full_log_details) # Uses sim time

        return changed

    def advance_time(self, minutes=1):
        """
        <<< DEPRECATED for main time flow in Real-Time mode >>>
        Manually advances simulation time. Primarily for very specific, small, action-related costs
        if the hybrid approach is chosen. In the pure real-time approach, this method is not called
        by most game logic; time advances via the background task's synchronization.
        """
        if not self.simulation_running or not self.simulation_time or not self.simulation_time.tzinfo: return

        try:
             minutes_val = max(0.1, float(minutes)) # Allow fractional minutes for small costs
             advance_delta = timedelta(minutes=minutes_val)
             previous_time_utc = self.simulation_time.astimezone(timezone.utc)

             # Check if advancing exceeds end time
             potential_new_time = self.simulation_time + advance_delta
             if self.simulation_end_time and potential_new_time > self.simulation_end_time:
                 advance_delta = self.simulation_end_time - self.simulation_time
                 if advance_delta < timedelta(0): advance_delta = timedelta(0) # Don't go backward

             # Add timedelta to the aware datetime object
             self.simulation_time += advance_delta
             current_time_utc = self.simulation_time.astimezone(timezone.utc)

             sim_time_str = current_time_utc.strftime('%H:%M:%S')
             end_time_str = "N/A"
             if self.simulation_end_time and self.simulation_end_time.tzinfo:
                 end_time_str = self.simulation_end_time.astimezone(timezone.utc).strftime('%H:%M:%S')

             # Log only if time actually advanced
             if advance_delta > timedelta(0):
                 self.log_event(f"(Manual) Time advances by {minutes_val:.1f} min from {previous_time_utc.strftime('%H:%M:%S')} to {sim_time_str}", level="debug")
                 self.emit_event("time_update", {"sim_time_str": sim_time_str, "end_time_str": end_time_str})

                 # Check end conditions immediately after time advance
                 self.check_end_conditions() # Uses the now-updated self.simulation_time

                 # Update 'time_wasted_waiting' metric if applicable
                 if self.simulation_state == "AWAITING_PLAYER_CHOICE" and self.player_action_log and self.player_action_log[-1][1] == "wait":
                     if not self.metrics: self._reset_metrics()

                     if 'time_wasted_waiting' not in self.metrics or not isinstance(self.metrics['time_wasted_waiting'], timedelta):
                          self.metrics['time_wasted_waiting'] = timedelta(0)

                     self.metrics["time_wasted_waiting"] += advance_delta
                     self.log_event(f"Adding {minutes_val:.1f} mins to time_wasted_waiting metric.", level="debug")

        except (ValueError, TypeError) as e:
             self.log_event(f"Error advancing time manually: {e}", level="error", store_for_rating=True)
             print(f"Error in advance_time: {e}")


    def add_custom_agent(self, agent_name, role, persona, state="available", update_persona=None, flags=None, initiative_delay=None):
        # Keep exactly as before - used only during setup phase
        if self.simulation_running:
            self.log_event("Cannot add custom agent while simulation is running.", level="warning")
            return False
        if agent_name in self._custom_agents_to_add or any(name == agent_name for name in default_agents):
            self.log_event(f"Warning: Agent name '{agent_name}' conflicts with an existing or default agent. Overwriting/Ignoring possible.", level="warning")

        self._custom_agents_to_add[agent_name] = {
            "role": role, "persona": persona, "state": state,
            "update_persona": update_persona, "flags": flags if flags is not None else {},
            "initiative_delay": initiative_delay
        }
        self.log_event(f"Custom agent '{agent_name}' definition stored.", level="info")
        return True

    def start_simulation(self, scenario_key, intensity_key, duration_minutes):
        # Uses UTC time. Initializes real-time sync.
        if self.simulation_running:
            self.log_event("Cannot start simulation: Already running.", level="warning")
            return False, "Simulation already running."
        if scenario_key not in scenarios:
            self.log_event(f"Error: Invalid scenario key '{scenario_key}'.", level="error", store_for_rating=True)
            return False, f"Invalid scenario key: {scenario_key}"
        if not self.client:
            self.log_event("Error: OpenAI client not initialized. Cannot start simulation.", level="error", store_for_rating=True)
            return False, "OpenAI client not available."

        # --- Reset State ---
        self.simulation_state = "SETUP"
        self.active_conversation_partner = None
        self.waiting_call_agent_name = None
        self.missed_calls = []
        self.escalation_level = 0
        self.player_decisions = {"shutdown_directive": "pending"}
        self.agents = {}
        self._reset_metrics()
        self.event_log_history = []
        self.player_action_log = []
        self.last_real_time_sync = None # Reset sync time

        # --- Config Setup ---
        self.selected_scenario_key = scenario_key
        self.selected_scenario = scenarios[scenario_key]
        valid_intensities = self.selected_scenario.get("intensity_modifier", {"Medium": 1.0})
        if intensity_key not in valid_intensities:
             print(f"Warning: Invalid intensity '{intensity_key}'. Defaulting.")
             intensity_key = "Medium" if "Medium" in valid_intensities else list(valid_intensities.keys())[0]
        self.initial_intensity_mod = valid_intensities[intensity_key]
        self.current_intensity_mod = self.initial_intensity_mod
        try:
            duration_minutes_val = int(duration_minutes)
            if duration_minutes_val <= 0: duration_minutes_val = DEFAULT_SIM_DURATION_MINUTES
        except (ValueError, TypeError):
            duration_minutes_val = DEFAULT_SIM_DURATION_MINUTES
            print(f"Warning: Invalid duration '{duration_minutes}'. Using default: {duration_minutes_val} mins.")

        # --- Time Init (Using Aware UTC Time) ---
        real_start_time_utc = datetime.now(timezone.utc) # <<< REAL-TIME CHANGE: Capture real start
        self.simulation_start_time = real_start_time_utc # Sim starts at real start time
        self.simulation_time = self.simulation_start_time
        self.simulation_end_time = self.simulation_time + timedelta(minutes=duration_minutes_val)
        # Initialize all tracking times to the start time
        self.last_escalation_check_time = self.simulation_start_time
        self.last_background_event_check_time = self.simulation_start_time
        self.last_intensity_check_time = self.simulation_start_time
        self.last_log_noise_time = self.simulation_start_time
        self.last_real_time_sync = real_start_time_utc # <<< REAL-TIME CHANGE: Initialize sync time

        # --- System Status Init ---
        self.system_status = self.selected_scenario.get("initial_system_status", {}).copy()

        # --- Agents Init ---
        self.agents = {}
        start_time_for_agents = self.simulation_start_time # Use aware start time
        for name, data in default_agents.items():
            self.agents[name] = {
                **data.copy(),
                "conversation_history": [],
                "last_update_time": None,
                "last_initiative_check_time": start_time_for_agents,
                "last_contact_time": None
            }

        # --- Add custom agents if defined ---
        if self._custom_agents_to_add:
            print(f"Adding {len(self._custom_agents_to_add)} custom agent(s)...")
            for name, data in self._custom_agents_to_add.items():
                if name in self.agents:
                    print(f"Warning: Custom agent name '{name}' conflicts. Skipping.")
                    continue
                self.agents[name] = {
                    **data.copy(),
                    "conversation_history": [],
                    "last_update_time": None,
                    "last_initiative_check_time": start_time_for_agents,
                    "last_contact_time": None
                }
                if data.get("initiative_delay") is not None:
                     try:
                         if 'BASE_AGENT_INITIATIVE_DELAY_SECONDS' in globals():
                            BASE_AGENT_INITIATIVE_DELAY_SECONDS[name] = data["initiative_delay"]
                         else: print("Warning: BASE_AGENT_INITIATIVE_DELAY_SECONDS not defined globally?")
                     except Exception as e: print(f"Warning: Could not set initiative delay for {name}: {e}")
            self._custom_agents_to_add = {}

        # --- Apply scenario initial agent states ---
        initial_states = self.selected_scenario.get("initial_agent_states", {})
        for agent, state in initial_states.items():
            if agent in self.agents:
                 self.agents[agent]['state'] = state
            else: print(f"Warning: Initial state defined for unknown agent '{agent}'.")

        # --- Final Setup & Start Logging ---
        start_log_msg = f"Simulation Setup Complete. Scenario: {self.selected_scenario_key} ({intensity_key}). Duration: {duration_minutes_val} mins. Initial Intensity: {self.initial_intensity_mod:.2f}x"
        self.log_event(start_log_msg, store_for_rating=True)
        self.log_event(f"Initial System Status: {self.system_status}", store_for_rating=True)
        for sys_key, status in self.system_status.items():
            if status not in ["NOMINAL", "UNKNOWN"]:
                 log_severity_level = status.split(" ")[0]
                 self._generate_log_entry("SYS_INITIAL_STATE", log_severity_level, sys_key, {"status": status, "reason": "Initial Scenario State"})

        self.simulation_running = True
        self.simulation_state = "INITIAL_ALERT"

        # --- Emit start event ---
        # start_time_utc = self.simulation_start_time.astimezone(timezone.utc)
        # end_time_utc = self.simulation_end_time.astimezone(timezone.utc)
        start_iso = self.simulation_start_time.isoformat() if self.simulation_start_time else None
        end_iso = self.simulation_end_time.isoformat() if self.simulation_end_time else None
        current_sim_iso = self.simulation_time.isoformat() if self.simulation_time else None # Send current time too
        self.emit_event("simulation_started", {
            "scenario": self.selected_scenario_key, "description": self.selected_scenario["description"],
            "intensity_key": intensity_key, "current_intensity_mod": self.current_intensity_mod,
            "duration": duration_minutes_val, "player_name": self.player_name, "player_role": self.player_role,
            "start_time_iso": start_iso,
            "end_time_iso": end_iso,
            "current_sim_time_iso": current_sim_iso,
            "initial_system_status": self.system_status,
            "initial_agent_status": {name: data['state'] for name, data in self.agents.items()}
        })

        # Trigger initial alert AFTER setting state and emitting start
        self.trigger_initial_alert()

        return True, "Simulation started successfully."


    def check_dynamic_intensity(self):
        """Checks and updates simulation intensity. Uses aware simulation time UTC."""
        if not self.simulation_running or not self.simulation_time or not self.simulation_time.tzinfo or not self.simulation_start_time or not self.simulation_start_time.tzinfo:
             return

        now_sim_utc = self.simulation_time.astimezone(timezone.utc)
        start_sim_utc = self.simulation_start_time.astimezone(timezone.utc)

        # Check interval using simulation time
        interval_met = True
        if self.last_intensity_check_time and self.last_intensity_check_time.tzinfo:
            last_check_sim_utc = self.last_intensity_check_time.astimezone(timezone.utc)
            # Intensity checks don't need their own interval, they run with background checks
            # Let the background task scheduler handle the overall check frequency
        # else: interval_met = True

        if not interval_met: return # Not strictly needed if relying on background task freq

        try:
            time_since_start_seconds = (now_sim_utc - start_sim_utc).total_seconds()
            time_since_start_minutes = time_since_start_seconds / 60.0
        except TypeError:
             print("Warning: Invalid time objects during intensity check.")
             return

        updated = False
        old_intensity = self.current_intensity_mod
        reason = ""

        # Keep calculation logic exactly as before (based on sim time elapsed)
        target_mod_time = self.initial_intensity_mod
        if time_since_start_minutes >= INTENSITY_TIME_THRESHOLD_MINUTES[1]: target_mod_time *= (INTENSITY_DECREASE_FACTOR ** 2)
        elif time_since_start_minutes >= INTENSITY_TIME_THRESHOLD_MINUTES[0]: target_mod_time *= INTENSITY_DECREASE_FACTOR

        target_mod_esc = self.initial_intensity_mod
        current_escalation_level = self.escalation_level if isinstance(self.escalation_level, int) else 0
        if current_escalation_level >= INTENSITY_ESCALATION_THRESHOLD[1]: target_mod_esc *= (INTENSITY_DECREASE_FACTOR ** 2)
        elif current_escalation_level >= INTENSITY_ESCALATION_THRESHOLD[0]: target_mod_esc *= INTENSITY_DECREASE_FACTOR

        target_mod = min(target_mod_time, target_mod_esc)

        if target_mod < self.current_intensity_mod:
            new_mod = max(MIN_INTENSITY_MOD, target_mod)
            if not abs(new_mod - self.current_intensity_mod) < 0.001:
                self.current_intensity_mod = new_mod
                updated = True
                reason_time = ""
                if target_mod_time < self.initial_intensity_mod:
                    if time_since_start_minutes >= INTENSITY_TIME_THRESHOLD_MINUTES[1]: reason_time = f"Time passed {INTENSITY_TIME_THRESHOLD_MINUTES[1]}m"
                    elif time_since_start_minutes >= INTENSITY_TIME_THRESHOLD_MINUTES[0]: reason_time = f"Time passed {INTENSITY_TIME_THRESHOLD_MINUTES[0]}m"
                reason_esc = ""
                if target_mod_esc < self.initial_intensity_mod:
                    if current_escalation_level >= INTENSITY_ESCALATION_THRESHOLD[1]: reason_esc = f"Esc Lvl {INTENSITY_ESCALATION_THRESHOLD[1]}"
                    elif current_escalation_level >= INTENSITY_ESCALATION_THRESHOLD[0]: reason_esc = f"Esc Lvl {INTENSITY_ESCALATION_THRESHOLD[0]}"

                if reason_time and reason_esc:
                    if abs(target_mod_time - target_mod_esc) < 0.01 : reason = f"{reason_time} & {reason_esc}"
                    elif target_mod_time < target_mod_esc: reason = reason_time
                    else: reason = reason_esc
                elif reason_time: reason = reason_time
                elif reason_esc: reason = reason_esc
                if new_mod == MIN_INTENSITY_MOD and target_mod < MIN_INTENSITY_MOD: reason += " (Hit Min)" if reason else "(Hit Min)"

        if updated:
            self.log_event(f"Dynamic Intensity Change! {old_intensity:.2f}x -> {self.current_intensity_mod:.2f}x. Reason: {reason}", level="alert", store_for_rating=True)
            self.emit_event("intensity_update", {"current_intensity_mod": self.current_intensity_mod, "reason": reason})
        # Always update check time when this function runs
        self.last_intensity_check_time = now_sim_utc # Store aware sim time


    def trigger_initial_alert(self):
        # Generates events. Time advance removed.
        self.log_event(f"{self.player_name} ({self.player_role}) starts sim at {self.current_location}.", store_for_rating=True)
        alert_msg = f"URGENT // IOC DETECTED // SigMatch: {self.selected_scenario_key.upper()} // Potential Severity: HIGH // Monitor Feeds. Awaiting Action."
        self.emit_event("display_message", {
            "speaker": "System Alert", "message": alert_msg, "notification": "INITIAL ALERT"
        })
        self.log_event(f"Initial Alert Sent: {alert_msg}", level="alert", store_for_rating=True)
        # self.advance_time(minutes=1) # <<< REMOVED: Time advances via background task
        self.simulation_state = "AWAITING_PLAYER_CHOICE" # Set state after alert
        self.emit_event("state_change", {"new_state": self.simulation_state})


    def handle_agent_contact(self, agent_name, initiated_by="player", is_update=False):
        # Uses aware simulation time UTC for state changes and LLM calls. Time advance removed.
        if agent_name not in self.agents:
            self.log_event(f"Error: Contact attempt for unknown agent '{agent_name}'", level="error")
            self.emit_event("display_message", {"speaker": "System", "message": f"Error: Agent '{agent_name}' not found."})
            return

        agent_data = self.agents[agent_name]
        agent_current_state = agent_data.get('state', 'unknown')

        if not self.simulation_time or not self.simulation_time.tzinfo:
             self.log_event(f"Error: Cannot handle contact for {agent_name}, simulation time invalid or naive.", level="error")
             self.emit_event("display_message", {"speaker": "System", "message": "Error: Simulation time invalid."})
             return
        now_sim_utc = self.simulation_time.astimezone(timezone.utc) # Use current aware sim time

        # --- Update Contact Metrics ---
        if not self.metrics: self._reset_metrics()
        if 'agents_contacted' not in self.metrics or not isinstance(self.metrics['agents_contacted'], set):
            self.metrics['agents_contacted'] = set()
        self.metrics["agents_contacted"].add(agent_name)
        if agent_name in ["Hao Wang", "Legal Counsel"]:
            if 'critical_agent_contact_time' not in self.metrics or not isinstance(self.metrics['critical_agent_contact_time'], dict):
                self.metrics['critical_agent_contact_time'] = {}
            if agent_name not in self.metrics["critical_agent_contact_time"]:
                self.metrics["critical_agent_contact_time"][agent_name] = now_sim_utc # Store aware sim time
                self.log_event(f"Metric updated: First contact time for {agent_name}.", level="debug")

        call_established = False

        # --- Agent Initiated ---
        if initiated_by == "agent":
            if self.active_conversation_partner:
                if not self.waiting_call_agent_name:
                    self.waiting_call_agent_name = agent_name
                    self.update_agent_state(agent_name, "waiting_cto_response")
                    self.log_event(f"Agent {agent_name} calling, player busy with {self.active_conversation_partner}. Call waiting.")
                    self.emit_event("call_waiting", {"agent_name": agent_name, "current_call": self.active_conversation_partner})
                else:
                    self.log_event(f"Agent {agent_name} call ignored (player busy, {self.waiting_call_agent_name} waiting). Missed.")
                    if agent_name not in self.missed_calls: self.missed_calls.append(agent_name)
                    self.emit_event("missed_calls_update", {"missed_calls": self.missed_calls})
                    self.update_agent_state(agent_name, "available")
                return
            else:
                display_msg = f"*** Incoming Contact: {agent_name} {'(Update)' if is_update else ''} ***"
                self.emit_event("display_message", {"speaker": "System", "message": display_msg, "notification": "INCOMING CALL"})
                self.active_conversation_partner = agent_name
                self.update_agent_state(agent_name, "on_call_with_cto")
                self.agents[agent_name]["last_contact_time"] = now_sim_utc # Store aware sim time
                self.simulation_state = "IN_CONVERSATION"
                self.emit_event("conversation_started", {"agent_name": agent_name})
                self.emit_event("state_change", {"new_state": self.simulation_state})
                call_established = True

        # --- Player Initiated ---
        elif initiated_by == "player":
            if self.active_conversation_partner:
                 self.emit_event("display_message", {"speaker": "System", "message": f"Cannot call {agent_name}. Already talking to {self.active_conversation_partner}."})
                 return
            if agent_current_state == "waiting_cto_response":
                 self.log_event(f"Player answering waiting call from {agent_name}.")
                 self.waiting_call_agent_name = None
                 self.emit_event("call_answered", {"agent_name": agent_name})
                 self.active_conversation_partner = agent_name
                 self.update_agent_state(agent_name, "on_call_with_cto")
                 self.agents[agent_name]["last_contact_time"] = now_sim_utc # Store aware sim time
                 self.simulation_state = "IN_CONVERSATION"
                 self.emit_event("conversation_started", {"agent_name": agent_name})
                 self.emit_event("state_change", {"new_state": self.simulation_state})
                 initiated_by = "agent"
                 call_established = True
            elif agent_current_state not in ["available", "investigating", "busy_monitoring"]:
                 self.emit_event("display_message", {"speaker": "System", "message": f"Contacting {agent_name}... Status: '{agent_current_state}'. Unavailable."})
                 self.log_event(f"Call failed: {agent_name} is '{agent_current_state}'.")
                 # self.advance_time(1) # <<< REMOVED: Time advances via background task
                 return
            else:
                 self.emit_event("display_message", {"speaker": "System", "message": f"Contacting {agent_name} ({agent_data.get('role','?')})... [Connecting...]"})
                 self.active_conversation_partner = agent_name
                 self.update_agent_state(agent_name, "on_call_with_cto")
                 self.agents[agent_name]["last_contact_time"] = now_sim_utc # Store aware sim time
                 self.simulation_state = "IN_CONVERSATION"
                 self.emit_event("conversation_started", {"agent_name": agent_name})
                 self.emit_event("state_change", {"new_state": self.simulation_state})
                 if agent_name in self.missed_calls:
                     self.log_event(f"Returning missed call to {agent_name}.")
                     self.missed_calls.remove(agent_name)
                     self.emit_event("missed_calls_update", {"missed_calls": self.missed_calls})
                 call_established = True

        # --- If Call Established, Trigger SYNCHRONOUS LLM Response ---
        if call_established:
            persona = agent_data["persona"]
            initial_trigger = ""
            agent_flags = agent_data.get("flags", {}).copy()

            if initiated_by == "player":
                initial_trigger = f"Hi {agent_name.split()[0]}, it's {self.player_name}. Need an update on the '{self.selected_scenario_key}' situation."
                agent_flags["called_by_player"] = True
            elif initiated_by == "agent":
                agent_flags["attempted_call"] = True
                if is_update:
                    persona = agent_data.get("update_persona") or persona
                    initial_trigger = "This is a quick status update regarding the incident."
                    agent_data["last_update_time"] = now_sim_utc # Store aware sim time
                else:
                     if agent_name == "Paul Kahn": initial_trigger = f"Jill! We need to talk NOW! What's happening? This silence is killing me! Shut it down!"; agent_flags["has_demanded_shutdown"] = True
                     elif agent_name == "Lynda Carney": initial_trigger = f"{self.player_name}, Lynda. Urgent update based on SOC alerts."
                     elif agent_name == "Hao Wang": initial_trigger = f"{self.player_name}, Hao calling. Need to sync up / give you the latest on my end."
                     elif agent_name == "CEO": initial_trigger = f"Jill, Sarah. Give me the bottom line. What's the damage? What's the plan?"
                     elif agent_name == "Legal Counsel": initial_trigger = f"Jill, David Rodriguez. Calling regarding potential data implications. Need facts."
                     elif agent_name == "PR Head": initial_trigger = f"Jill, Maria. Need confirmed details ASAP for comms strategy."
                     else: initial_trigger = f"This is {agent_name}. Calling {self.player_role} {self.player_name} regarding the incident."

            self.agents[agent_name]["flags"] = agent_flags

            if not persona:
                self.log_event(f"Error: No persona for agent {agent_name}. Cannot generate response.", level="error", store_for_rating=True)
                self.emit_event("display_message", {"speaker": agent_name, "message": "(Error: Agent persona missing)"})
                self._hang_up_call(); return

            self.add_to_agent_history(agent_name, "user", f"[Simulation Trigger: {initial_trigger}]")

            self.log_event(f"Calling LLM synchronously for {agent_name}'s initial response.", level="debug")
            current_history = self.agents[agent_name].get("conversation_history", [])
            ai_response = self.call_llm_api(
                persona_prompt=persona,
                history_list=current_history,
                user_input=initial_trigger,
                agent_name=agent_name
            )

            self.log_event(f"LLM response received for {agent_name}. Processing.", level="debug")
            self.add_to_agent_history(agent_name, "assistant", ai_response)
            self.emit_event("display_message", {"speaker": agent_name, "message": ai_response})

            response_lower = ai_response.lower() if isinstance(ai_response, str) else ""
            agent_flags = self.agents[agent_name].get("flags", {}).copy()
            if agent_name == "Hao Wang":
                if "caution" in response_lower or "diagnose" in response_lower or "don't shutdown" in response_lower:
                    if not agent_flags.get("has_advised_caution"):
                         agent_flags["has_advised_caution"] = True; self.log_event(f"Flag set: Hao cautious=True")
            elif agent_name == "Paul Kahn":
                if "shut down" in response_lower or "drastic action" in response_lower or "take control" in response_lower:
                    if not agent_flags.get("has_demanded_shutdown"):
                        agent_flags["has_demanded_shutdown"] = True; self.log_event(f"Flag set: Paul demands_shutdown=True")
            self.agents[agent_name]["flags"] = agent_flags

            # Advance time after the exchange? NO - time advances via background task
            # self.advance_time(minutes=random.randint(1, 2)) # <<< REMOVED


    def _hang_up_call(self):
        # Modifies state. Time advance removed.
        if not self.active_conversation_partner: return

        agent_name = self.active_conversation_partner
        self.log_event(f"Ending conversation with {agent_name}")
        self.emit_event("display_message", {"speaker": "System", "message": f"[Ending conversation with {agent_name}]"})

        prev_state = "available"
        if agent_name in self.agents:
            if agent_name == "Lynda Carney": prev_state = "busy_monitoring"
            elif agent_name == "Hao Wang":
                 vpn_status = self.system_status.get("VPN_Access")
                 if vpn_status == "NOMINAL": prev_state = "investigating"
                 elif vpn_status == "CONNECTING": prev_state = "available"
                 else: prev_state = "available"
            self.update_agent_state(agent_name, prev_state)
        else:
            self.log_event(f"Warning: Cannot reset state for unknown agent {agent_name} on hangup.", level="warning")

        if self.waiting_call_agent_name:
            missed_agent = self.waiting_call_agent_name
            self.log_event(f"Call from {missed_agent} was missed while talking to {agent_name}.")
            if missed_agent not in self.missed_calls: self.missed_calls.append(missed_agent)
            self.emit_event("missed_calls_update", {"missed_calls": self.missed_calls})
            self.update_agent_state(missed_agent, "available")
            self.emit_event("call_ignored", {"agent_name": missed_agent})
            self.waiting_call_agent_name = None

        self.active_conversation_partner = None
        self.simulation_state = "AWAITING_PLAYER_CHOICE"
        self.emit_event("conversation_ended", {"agent_name": agent_name})
        self.emit_event("state_change", {"new_state": self.simulation_state})
        # self.advance_time(1) # <<< REMOVED: Time advances via background task

    def _log_player_action(self, action_type, target=None, details=None):
        # Modifies state. Stores aware simulation time UTC ISO timestamp.
        if not self.simulation_time or not self.simulation_time.tzinfo: return

        now_sim_utc = self.simulation_time.astimezone(timezone.utc)
        timestamp_iso = now_sim_utc.isoformat() # Store sim time

        serializable_details = details
        if isinstance(details, dict):
             try: json.dumps(details)
             except TypeError: serializable_details = str(details)
        elif details is not None:
             serializable_details = str(details)

        action_entry = (timestamp_iso, action_type, target, serializable_details)
        self.player_action_log.append(action_entry)
        if len(self.player_action_log) > 50:
            self.player_action_log = self.player_action_log[-40:]

        if action_type in ['isolate', 'block ip', 'decide_shutdown']:
            if not self.metrics: self._reset_metrics()

            if 'key_actions_taken' not in self.metrics or not isinstance(self.metrics['key_actions_taken'], list):
                self.metrics['key_actions_taken'] = []

            time_str = now_sim_utc.strftime("%H:%M:%S") # Store sim time H:M:S
            self.metrics["key_actions_taken"].append((time_str, action_type, target))


    def _check_player_action(self, action_type, target=None, since_time=None):
        # Reads persisted state. Compares against aware simulation time UTC.
        log_copy = list(self.player_action_log)

        since_time_utc = None
        if since_time and isinstance(since_time, datetime):
             if since_time.tzinfo is None or since_time.tzinfo.utcoffset(since_time) is None:
                  print("Warning: _check_player_action received naive since_time. Assuming UTC.")
                  since_time_utc = since_time.replace(tzinfo=timezone.utc)
             else:
                  since_time_utc = since_time.astimezone(timezone.utc)

        for entry in reversed(log_copy):
            if not isinstance(entry, (list, tuple)) or len(entry) < 3:
                continue

            timestamp_iso, p_action, p_target = entry[0], entry[1], entry[2]

            if not isinstance(timestamp_iso, str):
                 continue

            try:
                action_time_utc = datetime.fromisoformat(timestamp_iso)
                if action_time_utc.tzinfo is None or action_time_utc.tzinfo.utcoffset(action_time_utc) is None:
                    action_time_utc = action_time_utc.replace(tzinfo=timezone.utc)
                else:
                    action_time_utc = action_time_utc.astimezone(timezone.utc)

                if since_time_utc and action_time_utc < since_time_utc:
                    return False

                if p_action == action_type:
                    if target is None or p_target == target:
                        return True

            except (ValueError, TypeError):
                 continue
        return False


    def handle_player_input(self, action):
        # Handles player input, uses aware simulation time for actions. Time advances removed.
        if not self.simulation_running or self.simulation_state == "ENDED":
            self.log_event("Input received while sim not active/ended.", level="warning")
            return
        if not action or not isinstance(action, str):
            self.log_event("Invalid player input received (empty or wrong type).", level="warning")
            return

        if not self.simulation_time or not self.simulation_time.tzinfo:
             self.log_event("Cannot handle player input, simulation time invalid or naive.", level="error")
             self.emit_event("display_message", {"speaker": "System", "message": "Error: Simulation time invalid."})
             return
        # now_sim_utc = self.simulation_time.astimezone(timezone.utc) # Use current aware sim time if needed directly

        is_chat_action = False
        if self.simulation_state == "IN_CONVERSATION":
             non_chat_commands = ["hang up", "end call", "bye", "end", "status", "check status", "answer call", "ignore call"]
             if action.lower().strip() not in non_chat_commands:
                  is_chat_action = True

        store_rating = not is_chat_action
        self.log_event(f"Player action in state '{self.simulation_state}': {action[:100]}", store_for_rating=store_rating)

        action_lower = action.lower().strip()

        # --- State: AWAITING_PLAYER_CHOICE ---
        if self.simulation_state == "AWAITING_PLAYER_CHOICE":
            if action_lower.startswith("call "):
                target = action[5:].strip()
                matched_agent = self._find_agent_by_name(target)
                if matched_agent:
                     self._log_player_action("call", target=matched_agent) # Uses aware sim time
                     self.handle_agent_contact(matched_agent, initiated_by="player") # Uses aware sim time
                else:
                     self.emit_event("display_message", {"speaker": "System", "message": f"Agent '{target}' not found."})
                     # self.advance_time(1) # <<< REMOVED
            elif action_lower.startswith("isolate "):
                 target = action[8:].strip()
                 matched_system = self._find_system_by_name(target)
                 if matched_system:
                      self._log_player_action("isolate", target=matched_system) # Uses aware sim time
                      self._handle_isolate_system(matched_system) # Uses aware sim time
                 else:
                      self.emit_event("display_message", {"speaker": "System", "message": f"System '{target}' not found."})
                      # self.advance_time(1) # <<< REMOVED
            elif action_lower == "wait":
                # Wait no longer advances time itself, time flows automatically
                # It just signifies inaction for the next background tick interval
                self.log_event("Player waits (time continues).")
                self.emit_event("display_message", {"speaker": "System", "message": f"Acknowledged. Time continues to pass..."})
                self._log_player_action("wait", details={"duration_minutes": 0}) # Log wait action, but duration is now implicit
                # NO self.advance_time(wait_duration) # <<< REMOVED
            elif action_lower == "status" or action_lower == "check status":
                 self._log_player_action("check_status")
                 summary = self.get_status_summary(compact=False)
                 self.emit_event("display_message", {"speaker": "System Status", "message": summary})
                 # self.advance_time(1) # <<< REMOVED
            elif action_lower.startswith("status check "):
                 target = action[13:].strip()
                 matched_system = self._find_system_by_name(target)
                 if matched_system:
                      self._log_player_action("status_check", target=matched_system)
                      self._handle_status_check(matched_system) # Uses aware sim time
                 else:
                      self.emit_event("display_message", {"speaker": "System", "message": f"System '{target}' not found."})
                      # self.advance_time(1) # <<< REMOVED
            elif action_lower == "missed" or action_lower == "missed calls":
                 self._log_player_action("check_missed_calls")
                 msg = f"Missed calls from: {', '.join(self.missed_calls)}" if self.missed_calls else "No missed calls."
                 self.emit_event("display_message", {"speaker": "System", "message": msg})
                 # self.advance_time(1) # <<< REMOVED
            elif action_lower == "decide":
                 self._log_player_action("force_decision")
                 self.enter_decision_point_shutdown(player_forced=True) # Uses aware sim time
            elif action_lower == "answer call":
                 if self.waiting_call_agent_name:
                     agent_to_answer = self.waiting_call_agent_name
                     self._log_player_action("answer_call", target=agent_to_answer)
                     self.handle_agent_contact(agent_to_answer, initiated_by="player")
                 else:
                     self.emit_event("display_message", {"speaker": "System", "message": "No call waiting."})
                     # self.advance_time(1) # <<< REMOVED
            elif action_lower == "ignore call":
                 if self.waiting_call_agent_name:
                     ignored_agent = self.waiting_call_agent_name
                     self._log_player_action("ignore_call", target=ignored_agent)
                     self.log_event(f"Player ignores waiting call from {ignored_agent}.")
                     if ignored_agent not in self.missed_calls: self.missed_calls.append(ignored_agent)
                     self.emit_event("missed_calls_update", {"missed_calls": self.missed_calls})
                     self.update_agent_state(ignored_agent, "available")
                     self.emit_event("call_ignored", {"agent_name": ignored_agent})
                     self.waiting_call_agent_name = None
                     # self.advance_time(1) # <<< REMOVED
                 else:
                     self.emit_event("display_message", {"speaker": "System", "message": "No call waiting."})
                     # self.advance_time(1) # <<< REMOVED
            elif action_lower.startswith("block ip "):
                 ip_address = action[9:].strip()
                 parts = ip_address.split('.')
                 if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                     self._log_player_action("block ip", target=ip_address)
                     self._handle_block_ip(ip_address) # Uses aware sim time
                 else:
                     self.emit_event("display_message", {"speaker": "System", "message": f"Invalid IP format: '{ip_address}'."})
                     # self.advance_time(1) # <<< REMOVED
            else:
                 options = ["'call [Name]'", "'status'", "'status check [System]'", "'missed'", "'wait'", "'decide'", "'isolate [System]'", "'block ip [IP]'"]
                 if self.waiting_call_agent_name: options.extend(["'answer call'", "'ignore call'"])
                 self.emit_event("display_message", {"speaker": "System", "message": f"Command unclear/unavailable. Try: {', '.join(options)}."})
                 # self.advance_time(1) # <<< REMOVED

        # --- State: IN_CONVERSATION ---
        elif self.simulation_state == "IN_CONVERSATION":
            if not self.active_conversation_partner or self.active_conversation_partner not in self.agents:
                self.log_event("Error: In conversation state but no active/valid partner.", level="error", store_for_rating=True)
                self.simulation_state = "AWAITING_PLAYER_CHOICE"; self.emit_event("state_change", {"new_state": self.simulation_state}); return

            agent_name = self.active_conversation_partner
            agent_data = self.agents[agent_name]

            if action_lower in ["hang up", "end call", "bye", "end"]:
                self._log_player_action("hang_up", target=agent_name) # Uses aware sim time
                self._hang_up_call() # Uses aware sim time
            elif action_lower == "status" or action_lower == "check status":
                 self._log_player_action("check_status_midcall")
                 summary = self.get_status_summary(compact=False)
                 self.emit_event("display_message", {"speaker": "System Status", "message": summary})
                 # self.advance_time(1) # <<< REMOVED
            elif action_lower == "answer call": # Switch call
                 if self.waiting_call_agent_name:
                     current_agent = self.active_conversation_partner
                     agent_to_answer = self.waiting_call_agent_name
                     self._log_player_action("switch_call", target=agent_to_answer, details={"from": current_agent})
                     self.log_event(f"Player switching call from {current_agent} to answer {agent_to_answer}.")
                     self._hang_up_call() # Hang up uses aware sim time
                     self.handle_agent_contact(agent_to_answer, initiated_by="player") # Connect uses aware sim time
                 else:
                     self.emit_event("display_message", {"speaker": "System", "message": "No call waiting."})
                     # self.advance_time(1) # <<< REMOVED
            elif action_lower == "ignore call": # Ignore waiting call while on another
                 if self.waiting_call_agent_name:
                     ignored_agent = self.waiting_call_agent_name
                     self._log_player_action("ignore_call_midcall", target=ignored_agent)
                     self.log_event(f"Player ignores waiting call from {ignored_agent} while talking to {agent_name}.")
                     if ignored_agent not in self.missed_calls: self.missed_calls.append(ignored_agent)
                     self.emit_event("missed_calls_update", {"missed_calls": self.missed_calls})
                     self.update_agent_state(ignored_agent, "available")
                     self.emit_event("call_ignored", {"agent_name": ignored_agent})
                     self.waiting_call_agent_name = None
                     # self.advance_time(1) # <<< REMOVED
                 else:
                     self.emit_event("display_message", {"speaker": "System", "message": "No call waiting."})
                     # self.advance_time(1) # <<< REMOVED

            # --- Regular Chat Message -> Run Synchronously in Worker ---
            else:
                 self.log_event(f"Worker processing chat for {agent_name}: {action[:50]}...", level="debug")
                 self.add_to_agent_history(agent_name, "user", action)

                 current_history = agent_data.get("conversation_history",[])
                 ai_response = self.call_llm_api(
                     persona_prompt=agent_data["persona"],
                     history_list=current_history,
                     user_input=action,
                     agent_name=agent_name
                 )

                 self.add_to_agent_history(agent_name, "assistant", ai_response)
                 self.emit_event("display_message", {"speaker": agent_name, "message": ai_response})

                 response_lower = ai_response.lower() if isinstance(ai_response, str) else ""
                 agent_flags = agent_data.get("flags", {}).copy()
                 if agent_name == "Hao Wang":
                    if "caution" in response_lower or "diagnose" in response_lower or "don't shutdown" in response_lower:
                        if not agent_flags.get("has_advised_caution"):
                            agent_flags["has_advised_caution"] = True; self.log_event(f"Flag set: Hao cautious=True")
                 elif agent_name == "Paul Kahn":
                    if "shut down" in response_lower or "drastic action" in response_lower or "take control" in response_lower:
                        if not agent_flags.get("has_demanded_shutdown"):
                             agent_flags["has_demanded_shutdown"] = True; self.log_event(f"Flag set: Paul demands_shutdown=True")
                 agent_data["flags"] = agent_flags

                 # Advance time after AI response processed? NO
                 # self.advance_time(random.randint(1, 2)) # <<< REMOVED

        # --- State: DECISION_POINT_SHUTDOWN ---
        elif self.simulation_state == "DECISION_POINT_SHUTDOWN":
            made_decision = False; decision_value = None; outcome_text = ""; comm_text = ""; systems_affected = []
            if "hold" in action_lower:
                decision_value = 'hold'; made_decision = True
                outcome_text = "Directive: HOLD Action."; comm_text = "[Internal Comm: HOLD. Prioritize diagnosis.]"
            elif "targeted" in action_lower:
                decision_value = 'targeted'; made_decision = True
                outcome_text = "Directive: TARGETED Isolation."; comm_text = "[Internal Comm: TARGETED Isolation. Affected systems only.]"
                systems_to_isolate = []
                # Logic to determine targets remains the same
                if self.selected_scenario_key == "Ransomware":
                    if "HIGH_FAILURES" in self.system_status.get("Auth_System", ""): systems_to_isolate.append("Auth_System")
                    if "ANOMALOUS_TRAFFIC" in self.system_status.get("Network_Segment_Internal", ""): systems_to_isolate.append("Network_Segment_Internal")
                    if any(s in self.system_status.get("File_Servers", "") for s in ["ENCRYPTING", "ENCRYPTED"]): systems_to_isolate.append("File_Servers")
                elif self.selected_scenario_key == "Critical Data Breach":
                    if any(s in self.system_status.get("Customer_Database","") for s in ["ANOMALOUS_ACCESS", "COMPROMISED"]): systems_to_isolate.append("Customer_Database")
                    if "HIGH_EGRESS" in self.system_status.get("Network_Edge",""): systems_to_isolate.append("Network_Edge")
                elif self.selected_scenario_key == "Insider Threat":
                     if any(s in self.system_status.get("Customer_Database","") for s in ["ANOMALOUS_ACCESS", "COMPROMISED"]): systems_to_isolate.append("Customer_Database")
                     if "ANOMALOUS_ACCESS" in self.system_status.get("HR_System", ""): systems_to_isolate.append("HR_System")
                     if "ANOMALOUS_TRAFFIC" in self.system_status.get("Network_Segment_Internal", ""): systems_to_isolate.append("Network_Segment_Internal")

                affected_after_update = []
                for sys_key in systems_to_isolate:
                     if sys_key in self.system_status:
                         if self.update_system_status(sys_key, "ISOLATING (Manual)", reason=f"(Targeted SD by {self.player_name})", related_log_type="SYSTEM_ISOLATION_MANUAL"):
                             affected_after_update.append(sys_key)
                systems_affected = affected_after_update

            elif "broad" in action_lower:
                decision_value = 'broad'; made_decision = True
                outcome_text = "Directive: BROAD Containment."; comm_text = "[Internal Comm: BROAD Shutdown. Non-essentials & affected systems NOW.]"
                systems_to_shutdown = ["Website_Public", "Auth_System", "Network_Segment_Internal", "Customer_Database", "File_Servers", "HR_System", "VPN_Access"]
                affected_after_update = []
                for sys_key in systems_to_shutdown:
                     if sys_key in self.system_status:
                         current_sys_status = self.system_status[sys_key]
                         if not any(s in current_sys_status for s in ["OFFLINE", "ISOLATED"]):
                             if self.update_system_status(sys_key, "OFFLINE (Manual)", reason=f"(Broad SD by {self.player_name})", related_log_type="SERVICE_SHUTDOWN_MANUAL"):
                                 affected_after_update.append(sys_key)
                systems_affected = affected_after_update

            if made_decision:
                self.player_decisions["shutdown_directive"] = decision_value
                self._log_player_action("decide_shutdown", target=decision_value, details={"systems_affected": systems_affected}) # Uses sim time
                self.log_event(f"Decision Recorded: {decision_value.upper()}. Systems affected: {systems_affected}", level="alert", store_for_rating=True)
                self.emit_event("display_message", {"speaker": "System Decision", "message": outcome_text, "notification": "DECISION RECORDED"})
                self.emit_event("display_message", {"speaker": "Internal Comm", "message": comm_text})
                self.simulation_state = "POST_INITIAL_CRISIS"
                self.emit_event("state_change", {"new_state": self.simulation_state})
                # self.advance_time(5) # <<< REMOVED: Time advances via background task
                self.trigger_debrief() # Uses aware sim time
            else:
                self.emit_event("display_message", {"speaker": "System", "message": "Invalid decision. Enter 'Hold', 'Targeted', or 'Broad'."})
                # self.advance_time(1) # <<< REMOVED

        # --- State: POST_INITIAL_CRISIS ---
        elif self.simulation_state == "POST_INITIAL_CRISIS":
             if action_lower == 'yes':
                 self._log_player_action("prep_analyst_briefing", details="agreed")
                 self.log_event("Player opts to prep analyst briefing.")
                 analyst_question = f"Regarding the '{self.selected_scenario_key}' incident and our '{self.player_decisions.get('shutdown_directive', 'N/A')}' response..."
                 clarification_message = (
                     "Understood. Prepare your points for the analyst briefing. "
                     "Imagine this is like preparing for a press conference or analyst call; "
                     "your words carry weight and could impact public perception and market confidence. "
                     "Be accurate and concise. Provide your talking points now:"
                 )
                 self.emit_event("display_message", {"speaker": "System", "message": clarification_message})
                 self.emit_event("request_analyst_input", {"prompt": "Provide concise talking points:", "context_question": analyst_question})
                 self.simulation_state = "AWAITING_ANALYST_BRIEFING"
                 self.emit_event("state_change", {"new_state": self.simulation_state})
                 # self.advance_time(1) # <<< REMOVED
             elif action_lower == 'no':
                 self._log_player_action("prep_analyst_briefing", details="skipped")
                 self.log_event("Player skips analyst briefing prep.")
                 self.emit_event("display_message", {"speaker": "System", "message": "Skipping analyst briefing prep. Simulation ending."})
                 self.end_simulation() # Uses aware sim time
             else:
                 self.emit_event("display_message", {"speaker": "System", "message": "Please enter 'yes' or 'no'."})
                 # self.advance_time(1) # <<< REMOVED

        # --- State: AWAITING_ANALYST_BRIEFING ---
        elif self.simulation_state == "AWAITING_ANALYST_BRIEFING":
            self.handle_analyst_briefing(action) # Uses aware sim time

        # --- Other States ---
        else:
             self.log_event(f"Player input '{action[:50]}' received in unexpected state '{self.simulation_state}'. Ignoring.", level="warning")
             self.emit_event("display_message", {"speaker": "System", "message": f"Action '{action[:20]}...' not applicable in current state ({self.simulation_state})."})
             # self.advance_time(1) # <<< REMOVED


    def handle_analyst_briefing(self, talking_points):
        # Processes talking points, calls PR LLM. Uses aware sim time. Time advance removed.
        if self.simulation_state != "AWAITING_ANALYST_BRIEFING":
             self.log_event(f"Warning: handle_analyst_briefing called in incorrect state: {self.simulation_state}", level="warning")
             return

        if not talking_points or not isinstance(talking_points, str) or len(talking_points.strip()) < 5:
            self.log_event("No valid talking points provided. Skipping PR review.", store_for_rating=True)
            self.emit_event("display_message", {"speaker": "System", "message": "No valid points provided. Skipping PR review."})
            self.end_simulation()
            return

        self._log_player_action("submit_analyst_briefing", details=talking_points[:100]) # Uses sim time
        self.log_event("Player submitted analyst points. Requesting PR feedback.", store_for_rating=True)
        self.emit_event("display_message", {"speaker":"System", "message":"Processing talking points with PR Head..."})

        final_status_summary = self.get_status_summary(compact=True)
        shutdown_directive = self.player_decisions.get('shutdown_directive', 'pending')
        pr_persona_template = PR_PERSONA

        feedback_prompt = textwrap.dedent(f"""
            You are Maria Garcia, Head of PR. Review the CTO's draft talking points below for the upcoming analyst briefing on the '{self.selected_scenario_key}' incident.
            Our chosen containment strategy was '{shutdown_directive}'. The final key system status is: {final_status_summary}.
            Focus your feedback on: Accuracy, Clarity & Tone, Perception Management, and offer specific improvements. Be concise.

            CTO's Draft Points:
            ---
            {talking_points}
            ---
            Provide your feedback clearly. Start with "PR Feedback:".
        """)

        pr_agent_name = "PR Head"
        if pr_agent_name in self.agents:
             pr_agent_persona = self.agents[pr_agent_name].get("persona", PR_PERSONA)
             self.log_event(f"Calling LLM synchronously for PR feedback.", level="debug")
             feedback_response = self.call_llm_api(
                 persona_prompt=pr_agent_persona,
                 history_list=[],
                 user_input=feedback_prompt,
                 agent_name=pr_agent_name,
                 model="gpt-4o-mini",
                 max_tokens=PR_FEEDBACK_MAX_TOKENS,
                 temperature=0.5
             )

             self.emit_event("display_message", {
                 "speaker": f"{pr_agent_name} (Feedback)",
                 "message": feedback_response,
                 "notification": "PR REVIEW FEEDBACK"
             })
             self.log_event(f"PR Feedback generated and processed.", level="debug", store_for_rating=True)
        else:
            self.log_event("PR Head agent not found, cannot get feedback.", level="warning", store_for_rating=True)
            self.emit_event("display_message", {"speaker": "System", "message": "[PR Head unavailable for feedback.]"})

        self.end_simulation() # Uses aware sim time


    def _find_agent_by_name(self, name_fragment):
        # Keep exactly as before
        if not name_fragment or not isinstance(name_fragment, str): return None
        name_lower = name_fragment.lower().strip()
        for name in self.agents:
            if name_lower == name.lower(): return name
        for name in self.agents:
            if name_lower in name.lower(): return name
        for name in self.agents:
            if name_lower == name.split()[0].lower(): return name
        return None

    def _find_system_by_name(self, name_fragment):
        # Keep exactly as before
        if not name_fragment or not isinstance(name_fragment, str): return None
        name_lower = name_fragment.lower().replace(" ", "_").strip()
        if name_lower in self.system_status: return name_lower
        for key in self.system_status:
            if name_lower in key.lower(): return key
        return None

    def _handle_isolate_system(self, system_key):
        # Uses aware simulation time. Time advances removed.
        self.log_event(f"Executing: Isolate {system_key}")
        current_status = self.system_status.get(system_key)

        if not current_status:
            self.emit_event("display_message", {"speaker": "System", "message": f"System '{system_key}' status not found internally."})
            # self.advance_time(1) # <<< REMOVED
            return

        if "ISOLAT" in current_status or "OFFLINE" in current_status:
            self.emit_event("display_message", {"speaker": "System", "message": f"System '{system_key}' is already {current_status}."})
            # self.advance_time(1) # <<< REMOVED
            return

        self.emit_event("display_message", {"speaker": "System Command", "message": f"Initiating isolation for '{system_key}'..."})
        # Isolation state change is immediate in sim time now
        # The *effect* might be checked later by escalation rules based on sim time
        if self.update_system_status(system_key, "ISOLATING (Manual)", reason=f"Player Action ({self.player_name})", related_log_type="SYS_ISOLATION_INITIATED"):
             # Consider if ISOLATING should automatically become ISOLATED after a short *sim time* delay, handled by an escalation rule maybe?
             # For now, make it immediate for simplicity after action.
             if self.update_system_status(system_key, "ISOLATED (Manual)", reason="Player Action Complete", related_log_type="SYS_ISOLATION_COMPLETE"):
                  self.emit_event("display_message", {"speaker": "System Command", "message": f"Isolation of '{system_key}' complete."})
        # isolation_time = random.randint(2, 5) # <<< REMOVED Delay
        # self.advance_time(isolation_time) # <<< REMOVED


    def _handle_block_ip(self, ip_address):
        # Uses aware simulation time. Time advances removed.
        self.log_event(f"Executing: Block IP {ip_address}")
        # block_time = random.randint(1, 3) # <<< REMOVED Delay
        self.emit_event("display_message", {"speaker": "System Command", "message": f"Applying block rule for IP {ip_address}..."})
        self._generate_log_entry("BLOCK_RULE_APPLIED", "INFO", "Network_Edge",
                                 {"ip": ip_address, "direction": "in/out", "device": "fw-edge-main"}) # Uses sim time
        # self.advance_time(block_time) # <<< REMOVED
        self.emit_event("display_message", {"speaker": "System Command", "message": f"Block rule for {ip_address} applied."})


    def _handle_status_check(self, system_key):
        # Reads state. Uses aware sim time. Time advances removed.
        self.log_event(f"Executing: Status Check {system_key}")
        status = self.system_status.get(system_key, "UNKNOWN")
        self.emit_event("display_message", {"speaker": "System Status", "message": f"Status of '{system_key}': {status}"})
        # self.advance_time(1) # <<< REMOVED

    def check_end_conditions(self):
        # Checks end conditions using aware simulation time comparison.
        # This is now called more proactively by the background task after time sync.
        if not self.simulation_running or self.simulation_state in ["ENDED", "POST_INITIAL_CRISIS", "DECISION_POINT_SHUTDOWN", "AWAITING_ANALYST_BRIEFING"]:
            return False
        if not self.simulation_time or not self.simulation_time.tzinfo or not self.simulation_end_time or not self.simulation_end_time.tzinfo:
            self.log_event("Warning: Cannot check end conditions due to invalid/naive time objects.", level="warning")
            return False

        end_triggered = False; reason = ""
        now_sim_utc = self.simulation_time.astimezone(timezone.utc)
        end_time_sim_utc = self.simulation_end_time.astimezone(timezone.utc)

        # 1. Time Limit Reached (Simulation Time)
        if now_sim_utc >= end_time_sim_utc:
            reason = "Simulation time limit reached."; end_triggered = True
            # Ensure sim time doesn't exceed end time
            self.simulation_time = end_time_sim_utc

        # 2. Critical Failure Conditions (No change needed here)
        current_status_copy = self.system_status.copy() if isinstance(self.system_status, dict) else {}
        critical_systems_now = {
            k: v for k, v in current_status_copy.items()
            if isinstance(v, str) and any(crit in v for crit in ["CRITICAL", "COMPROMISED", "ENCRYPTED"])
        }
        if not end_triggered and critical_systems_now:
            scenario = self.selected_scenario_key
            if scenario == "Ransomware" and "File_Servers" in critical_systems_now:
                 fs_status = critical_systems_now["File_Servers"]
                 if "ENCRYPTED (CRITICAL)" in fs_status: reason = f"Critical Failure: {fs_status} on File_Servers!"; end_triggered = True
            elif scenario == "Critical Data Breach" and "Customer_Database" in critical_systems_now:
                 db_status = critical_systems_now["Customer_Database"]
                 if "COMPROMISED (CRITICAL)" in db_status: reason = f"Critical Failure: {db_status} on Customer_Database!"; end_triggered = True
            elif scenario == "Insider Threat" and "Customer_Database" in critical_systems_now:
                 db_status = critical_systems_now["Customer_Database"]
                 if "COMPROMISED (CRITICAL)" in db_status: reason = f"Critical Failure: {db_status} on Customer_Database (Insider)!"; end_triggered = True

        if end_triggered:
            self.log_event(f"End Condition Met: {reason}", level="alert", store_for_rating=True)
            self.emit_event("display_message", {"speaker": "System", "message": f"NOTICE: {reason} - Transitioning to debrief phase.", "notification": "SIMULATION ENDING"})
            self.simulation_state = "POST_INITIAL_CRISIS"
            self.emit_event("state_change", {"new_state": self.simulation_state})
            self.trigger_debrief() # Uses sim time
            # The calling task (background_check_task) is responsible for saving state and maybe stopping further checks.
            return True

        return False


    def check_background_events(self):
        """
        Checks agent initiative & system escalations based on CURRENT simulation time.
        Assumes simulation time has ALREADY been advanced by the background task.
        Uses aware simulation time UTC for all comparisons.
        """
        if not self.simulation_running or not self.simulation_time or not self.simulation_time.tzinfo or not self.simulation_start_time or not self.simulation_start_time.tzinfo:
             return
        if self.simulation_state in ["SETUP", "ENDED", "POST_INITIAL_CRISIS", "DECISION_POINT_SHUTDOWN", "AWAITING_ANALYST_BRIEFING"]:
             return

        now_sim_utc = self.simulation_time.astimezone(timezone.utc)
        start_sim_utc = self.simulation_start_time.astimezone(timezone.utc)
        time_since_start_seconds = (now_sim_utc - start_sim_utc).total_seconds()

        # --- 1. Agent Initiative Checks (Using Sim Time) ---
        agent_wants_to_call = []
        contact_cooldown = timedelta(minutes=AGENT_CONTACT_COOLDOWN_MINUTES) # Sim minutes cooldown

        for agent_name, agent_data in self.agents.items():
           if agent_data.get("state") not in ["available", "investigating", "busy_monitoring"]: continue
           if self.active_conversation_partner == agent_name or self.waiting_call_agent_name == agent_name: continue

           last_contact = agent_data.get("last_contact_time") # Aware sim UTC time
           if last_contact and isinstance(last_contact, datetime) and last_contact.tzinfo:
               last_contact_sim_utc = last_contact.astimezone(timezone.utc)
               if (now_sim_utc - last_contact_sim_utc) < contact_cooldown:
                   continue # Still in cooldown (based on sim time)

           should_agent_call = False; is_update = False; reason = ""
           effective_intensity_mod = self.current_intensity_mod if isinstance(self.current_intensity_mod, (float, int)) and self.current_intensity_mod > 0 else 1.0
           agent_flags = agent_data.get("flags", {}).copy() # Work on copy

           # Specific Agent Logic (Using aware sim time comparisons)
           if agent_name == "Paul Kahn" and not agent_flags.get("called_by_player"):
               paul_delay_base = BASE_AGENT_INITIATIVE_DELAY_SECONDS.get("Paul Kahn", 300)
               paul_delay_sim_secs = paul_delay_base * effective_intensity_mod # Delay in sim seconds
               if not agent_flags.get("attempted_call") and time_since_start_seconds >= paul_delay_sim_secs:
                   reason = f"Paul's panic timer ({paul_delay_sim_secs:.0f}s sim time)"; should_agent_call = True
           elif agent_name == "Hao Wang" and agent_data.get("state") == "investigating":
                update_interval_base = BASE_IDLE_AGENT_UPDATE_INTERVAL_SECONDS
                update_interval_sim_secs = update_interval_base * effective_intensity_mod
                last_comm = agent_data.get("last_update_time") or agent_data.get("last_contact_time") # Aware sim time
                if last_comm and isinstance(last_comm, datetime) and last_comm.tzinfo:
                     last_comm_sim_utc = last_comm.astimezone(timezone.utc)
                     if (now_sim_utc - last_comm_sim_utc).total_seconds() >= update_interval_sim_secs:
                         reason = f"Hao's idle update ({update_interval_sim_secs:.0f}s sim)"; should_agent_call = True; is_update = True
                elif not last_comm and time_since_start_seconds > (update_interval_sim_secs / 2):
                     reason = f"Hao's initial update"; should_agent_call = True; is_update = True
           elif agent_name == "Lynda Carney" and agent_data.get("state") == "busy_monitoring":
                status_copy = self.system_status.copy()
                crit_sys = {k:v for k,v in status_copy.items() if isinstance(v,str) and any(s in v for s in ["CRITICAL", "COMPROMISED"])}
                enc_sys = {k:v for k,v in status_copy.items() if isinstance(v,str) and "ENCRYPTING" in v}
                enc_crit_sys = {k:v for k,v in status_copy.items() if isinstance(v,str) and "ENCRYPTED (CRITICAL)" in v}

                if enc_sys and not agent_flags.get("alerted_encryption"):
                     reason = f"Lynda alert: Encryption DETECTED on {list(enc_sys.keys())}!"; should_agent_call = True; is_update = True; agent_flags["alerted_encryption"] = True
                elif (crit_sys or enc_crit_sys) and not agent_flags.get("alerted_critical"):
                    alert_keys = list(crit_sys.keys()) + list(enc_crit_sys.keys())
                    reason = f"Lynda alert: CRITICAL status on {list(set(alert_keys))}!"; should_agent_call = True; is_update = True; agent_flags["alerted_critical"] = True
                else:
                     update_interval_base = (BASE_IDLE_AGENT_UPDATE_INTERVAL_SECONDS / 1.5)
                     update_interval_sim_secs = update_interval_base * effective_intensity_mod
                     last_comm = agent_data.get("last_update_time") or agent_data.get("last_contact_time") # Aware sim time
                     if last_comm and isinstance(last_comm, datetime) and last_comm.tzinfo:
                          last_comm_sim_utc = last_comm.astimezone(timezone.utc)
                          if (now_sim_utc - last_comm_sim_utc).total_seconds() >= update_interval_sim_secs:
                              reason = f"Lynda's idle update ({update_interval_sim_secs:.0f}s sim)"; should_agent_call = True; is_update = True
                     elif not last_comm and time_since_start_seconds > (update_interval_sim_secs / 2):
                          reason = f"Lynda's initial update"; should_agent_call = True; is_update = True
                # Save updated flags back immediately
                self.agents[agent_name]["flags"] = agent_flags

           if should_agent_call:
                self.log_event(f"Agent Initiative Check: {agent_name} wants to call. Reason: {reason}", level="info")
                agent_wants_to_call.append({"name": agent_name, "is_update": is_update, "reason": reason})

        # Trigger at most one agent call per background check cycle
        if agent_wants_to_call:
            critical_callers = [c for c in agent_wants_to_call if "critical" in c.get("reason", "").lower() or "alert" in c.get("reason", "").lower()]
            caller_info = random.choice(critical_callers) if critical_callers else random.choice(agent_wants_to_call)

            self.log_event(f"Triggering agent contact from background check: {caller_info['name']}", level="debug")
            self.update_agent_state(caller_info["name"], "trying_to_call_cto")
            self.handle_agent_contact(caller_info["name"], initiated_by="agent", is_update=caller_info["is_update"]) # Uses sim time

        # --- 2. System Escalation Check (Using Sim Time) ---
        escalated_this_tick = False
        interval_met = True
        effective_intensity_mod = self.current_intensity_mod if isinstance(self.current_intensity_mod, (float, int)) and self.current_intensity_mod > 0 else 1.0
        if self.last_escalation_check_time and self.last_escalation_check_time.tzinfo:
             try:
                 last_check_sim_utc = self.last_escalation_check_time.astimezone(timezone.utc)
                 effective_interval_sim_secs = BASE_ESCALATION_CHECK_INTERVAL_SECONDS * effective_intensity_mod
                 if (now_sim_utc - last_check_sim_utc).total_seconds() < effective_interval_sim_secs:
                     interval_met = False
             except (TypeError, ValueError):
                  print("Warning: Error calculating escalation check interval.")
                  interval_met = True
        # else: interval_met = True # Allow first run

        if interval_met and self.selected_scenario and "escalation_rules" in self.selected_scenario:
             for rule_index, rule in enumerate(self.selected_scenario["escalation_rules"]):
                 condition_met = False
                 try:
                     condition_met = rule["condition"](self, now_sim_utc) # Pass current sim time
                 except Exception as e:
                     self.log_event(f"Error eval esc rule #{rule_index+1}: {e}", level="error", store_for_rating=True); print(f"Esc rule condition error: {e}")
                     continue

                 if condition_met:
                     self.log_event(f"Esc Rule #{rule_index+1} Condition Met.", level="info", store_for_rating=True)
                     status_changed = False
                     try:
                         action_result = rule["action"](self)
                         status_changed = False if action_result is False else True
                     except Exception as e:
                         self.log_event(f"Error exec esc rule action #{rule_index+1}: {e}", level="error", store_for_rating=True); print(f"Esc rule action error: {e}")
                         break

                     if status_changed:
                         current_level = self.escalation_level if isinstance(self.escalation_level, int) else 0
                         self.escalation_level = current_level + 1

                         if not self.metrics: self._reset_metrics()
                         self.metrics["escalations_triggered"] = self.escalation_level

                         escalated_this_tick = True
                         esc_msg = f"** Attack Escalated! (Level {self.escalation_level}) **"
                         self.log_event(esc_msg, level="alert", store_for_rating=True)
                         self.emit_event("display_message", {"speaker": "System Alert", "message": f"ESCALATION DETECTED (Lvl {self.escalation_level})!", "notification": "ESCALATION ALERT"})

                         self.check_dynamic_intensity() # Check intensity immediately (uses sim time)
                         break # Only one escalation per check
             # Update last check time if interval was met
             self.last_escalation_check_time = now_sim_utc

        # Update last overall background check time based on sim time
        self.last_background_event_check_time = now_sim_utc


    def enter_decision_point_shutdown(self, player_forced=False):
        # Uses aware simulation time for comparisons and logging. Time advance removed.
        if self.simulation_state == "DECISION_POINT_SHUTDOWN": return

        if not self.simulation_time or not self.simulation_time.tzinfo or not self.simulation_start_time or not self.simulation_start_time.tzinfo:
             self.log_event("Warning: Cannot enter decision point due to invalid/naive time.", level="warning")
             return

        now_sim_utc = self.simulation_time.astimezone(timezone.utc)
        start_sim_utc = self.simulation_start_time.astimezone(timezone.utc)

        hao_advised = self.agents.get("Hao Wang", {}).get("flags", {}).get("has_advised_caution", False)
        paul_demanded = self.agents.get("Paul Kahn", {}).get("flags", {}).get("has_demanded_shutdown", False)

        time_elapsed_min = 0
        try: time_elapsed_min = (now_sim_utc - start_sim_utc).total_seconds() / 60.0
        except TypeError: pass

        is_critical = False
        if isinstance(self.system_status, dict):
             is_critical = any(crit in v for crit in ["CRITICAL", "COMPROMISED", "ENCRYPTED"] for k, v in self.system_status.items() if isinstance(v, str))

        ready_for_decision = False; decision_reason = ""
        if player_forced: ready_for_decision = True; decision_reason = "Player override"
        elif is_critical: ready_for_decision = True; decision_reason = "Critical system state reached"
        elif (hao_advised and paul_demanded): ready_for_decision = True; decision_reason = "Key inputs received (Hao & Paul)"
        elif time_elapsed_min > (DEFAULT_SIM_DURATION_MINUTES * 0.6): ready_for_decision = True; decision_reason = f"Sufficient sim time elapsed ({time_elapsed_min:.0f}m)"


        if ready_for_decision:
            self.log_event(f"Entering shutdown decision phase. Reason: {decision_reason}", level="info", store_for_rating=True)
            self.simulation_state = "DECISION_POINT_SHUTDOWN"; self.emit_event("state_change", {"new_state": self.simulation_state})
            summary_lines = [ f"Decision Point: Containment Strategy for '{self.selected_scenario_key}'", f"Reason: {decision_reason}",
                "--- Inputs ---", f"- Hao Advised Caution? {'YES' if hao_advised else 'NO'}", f"- Paul Urged Shutdown? {'YES' if paul_demanded else 'NO'}",
                 "--- Status ---", self.get_status_summary(compact=True) ]
            self.emit_event("decision_point_info", {
                "title": "Decision Required: Containment Directive", "summary": "\n".join(summary_lines), "current_status_dict": self.system_status,
                "options": [ {"value": "Hold", "label": "Hold Action (Diagnosis)"}, {"value": "Targeted", "label": "Targeted Isolation (Affected)"}, {"value": "Broad", "label": "Broad Shutdown (Non-Essentials)"} ]
            })
            self.emit_event("display_message", {"speaker": "System", "message": "Directive Required: Enter 'Hold', 'Targeted', or 'Broad'."})
            # self.advance_time(1) # <<< REMOVED
        else:
             missing = []
             if not hao_advised: missing.append("Hao Wang (Caution Advice)")
             if not paul_demanded: missing.append("Paul Kahn (Shutdown Urgency)")
             msg = f"Decision point not yet triggered automatically."
             if missing: msg += f" Consider consulting: {', '.join(missing)}."
             msg += f" Available actions: 'wait', 'call ...', 'status', etc., or use 'decide' to force the decision now."
             self.emit_event("display_message", {"speaker": "System", "message": msg})
             if self.simulation_state == "DECISION_POINT_SHUTDOWN":
                 self.simulation_state = "AWAITING_PLAYER_CHOICE"; self.emit_event("state_change", {"new_state": self.simulation_state})


    def _call_llm_for_rating(self) -> dict:
        """
        [RUNS SYNCHRONOUSLY INSIDE A WORKER TASK]
        Compiles context, calls LLM for performance rating, parses the response.
        Uses aware simulation time UTC for calculations.
        Returns the rating dictionary or an error dictionary.
        """
        # Keep exactly as before - uses sim time for duration calc
        if not self.client:
            log_msg = "LLM rating skipped: Client not available."
            print(f"[Worker Rating Error] {log_msg}")
            self.log_event(log_msg, level="warning", store_for_rating=True)
            return {"error": "LLM client not available."}

        self.log_event("Preparing data for LLM performance rating...", level="debug")

        try:
            serializable_metrics = self._serialize_metrics(self.metrics)
        except Exception as e:
            log_msg = f"Failed to serialize metrics for rating: {type(e).__name__} - {e}"
            print(f"[Worker Rating Error] {log_msg}")
            self.log_event(f"ERROR: {log_msg}", level="error", store_for_rating=True)
            self.log_event(traceback.format_exc(), level="error")
            return {"error": "Failed to prepare metrics for rating."}

        scenario_desc = "N/A"
        if not self.selected_scenario and self.selected_scenario_key:
             self.selected_scenario = scenarios.get(self.selected_scenario_key)
        if self.selected_scenario:
            scenario_desc = self.selected_scenario.get("description", "N/A")

        duration_seconds = 0
        # Use SIMULATION start and end times for duration calculation
        if self.simulation_start_time and self.simulation_start_time.tzinfo and self.simulation_time and self.simulation_time.tzinfo:
             try:
                 duration_seconds = (self.simulation_time.astimezone(timezone.utc) - self.simulation_start_time.astimezone(timezone.utc)).total_seconds()
             except TypeError: pass

        rating_context = {
            "scenario": self.selected_scenario_key or "Unknown",
            "description": scenario_desc,
            "intensity": f"{self.initial_intensity_mod:.1f}x -> {self.current_intensity_mod:.1f}x",
            "duration_seconds": duration_seconds, # Based on sim time elapsed
            "final_status_summary": self.get_status_summary(compact=False),
            "player_directive": self.player_decisions.get('shutdown_directive', 'Pending/Not Reached'),
            "metrics": serializable_metrics,
            "event_highlights": list(self.event_log_history[-30:])
        }

        try:
            metric_data = rating_context['metrics']

            time_crit_iso = metric_data.get('time_to_first_critical')
            time_crit_str = "N/A"
            if time_crit_iso and isinstance(time_crit_iso, str):
                 try:
                     crit_dt_utc = datetime.fromisoformat(time_crit_iso)
                     if crit_dt_utc.tzinfo is None: crit_dt_utc = crit_dt_utc.replace(tzinfo=timezone.utc)
                     else: crit_dt_utc = crit_dt_utc.astimezone(timezone.utc)

                     if self.simulation_start_time and self.simulation_start_time.tzinfo:
                          start_dt_utc = self.simulation_start_time.astimezone(timezone.utc)
                          time_crit_str = f"{(crit_dt_utc - start_dt_utc).total_seconds():.0f}s" # Sim time delta
                     else: time_crit_str = f"(Recorded: {crit_dt_utc.strftime('%H:%M:%S UTC')})"
                 except (ValueError, TypeError): time_crit_str = "(Invalid Time)"
            elif time_crit_iso is not None:
                 print(f"[Worker Rating Warning] time_to_first_critical in serialized metrics is not a string or None: {type(time_crit_iso)}")

            time_wasted_seconds = metric_data.get('time_wasted_waiting', 0.0)
            time_wasted_str = f"{time_wasted_seconds:.0f}s"

            compromised_count = metric_data.get('systems_compromised_count', 0)
            escalations_count = metric_data.get('escalations_triggered', 0)
            agents_contacted_list = metric_data.get('agents_contacted', [])
            key_actions_list = metric_data.get('key_actions_taken', [])

        except Exception as fmt_e:
             log_msg = f"Internal error preparing metrics for prompt string: {type(fmt_e).__name__} - {fmt_e}"
             print(f"[Worker Rating Error] {log_msg}")
             self.log_event(f"ERROR: {log_msg}", level="error", store_for_rating=True)
             self.log_event(traceback.format_exc(), level="error")
             return {"error": log_msg}

        prompt = textwrap.dedent(f"""
        Analyze CTO simulation performance. Scenario: '{rating_context['scenario']}'. Goal: {rating_context['description']}.
        Context: Intensity: {rating_context['intensity']}. Sim Duration Elapsed: {rating_context['duration_seconds']:.0f}s. Directive: {rating_context['player_directive']}.
        Final Status Summary:
        {rating_context['final_status_summary']}
        ---
        Key Metrics:
        - SimTimeToCritical: {time_crit_str}
        - CompromisedSystems: {compromised_count}
        - EscalationsTriggered: {escalations_count}
        - SimTimeWastedWaiting: {time_wasted_str}
        - AgentsContacted: {agents_contacted_list}
        - KeyActionsTaken: {key_actions_list}
        ---
        Recent Event Highlights (Last ~30, times are SIMULATION TIME):
        {chr(10).join(f"  - {line}" for line in rating_context['event_highlights'])}
        ---
        Instructions: Provide rating as JSON object ONLY. Scale 1-10. Required keys: "timeliness_score", "contact_strategy_score", "decision_quality_score", "efficiency_score", "overall_score", "qualitative_feedback" (concise 1-2 sentence summary of strengths/weaknesses/advice). Ensure scores are integers between 1 and 10.
        Example JSON: {{"timeliness_score": 7, "contact_strategy_score": 8, "decision_quality_score": 6, "efficiency_score": 5, "overall_score": 6, "qualitative_feedback": "Responded quickly but decision was delayed. Improve risk assessment under pressure."}}
        """)

        try:
            response_format_param = {"type": "json_object"} if "gpt-4" in RATING_LLM_MODEL or "gpt-3.5" in RATING_LLM_MODEL else None
            llm_model_to_use = RATING_LLM_MODEL

            raw_response = self.call_llm_api(
                persona_prompt="You are an expert cyber incident response simulation performance assessor.",
                history_list=[],
                user_input=prompt,
                agent_name="RatingAgent",
                model=llm_model_to_use,
                max_tokens=LLM_RATING_MAX_TOKENS,
                temperature=0.2,
                response_format=response_format_param
            )

            if not raw_response or (isinstance(raw_response, str) and raw_response.startswith("(")):
                raise ValueError(f"LLM call for rating failed internally: {raw_response}")

            rating_json = None; parse_error_detail = None
            try:
                json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
                if json_match:
                    json_substring = json_match.group(0)
                    try: rating_json = json.loads(json_substring)
                    except json.JSONDecodeError as extract_e: parse_error_detail = f"Extracted JSON invalid: {extract_e}. Substring: {json_substring[:100]}"
                else:
                    try: rating_json = json.loads(raw_response)
                    except json.JSONDecodeError as direct_e: parse_error_detail = f"Direct JSON parse failed: {direct_e}. No JSON markers found."
                if rating_json is None: raise json.JSONDecodeError(parse_error_detail or "Could not parse JSON from LLM response", raw_response, 0)
            except Exception as parse_e: raise json.JSONDecodeError(f"Unexpected parsing error: {parse_e}", raw_response, 0)

            required_keys = ["timeliness_score", "contact_strategy_score", "decision_quality_score", "efficiency_score", "overall_score", "qualitative_feedback"]
            validated_rating = {}; errors = []
            if not isinstance(rating_json, dict): errors.append("LLM response was not a JSON object.")
            else:
                for key in required_keys:
                    if key not in rating_json: errors.append(f"Missing required key: '{key}'")
                    else:
                        value = rating_json[key]
                        if "score" in key:
                            if not isinstance(value, int) or not (1 <= value <= 10):
                                errors.append(f"Invalid value for '{key}': got '{value}', expected integer 1-10.")
                                try: validated_rating[key] = max(1, min(10, int(value)))
                                except: validated_rating[key] = 5
                            else: validated_rating[key] = value
                        elif key == "qualitative_feedback":
                            if not isinstance(value, str) or not value.strip():
                                errors.append(f"Invalid value for '{key}': expected non-empty string.")
                                validated_rating[key] = "(Feedback not provided or invalid)"
                            else: validated_rating[key] = value.strip()

            if errors:
                error_msg = f"LLM rating validation failed: {'; '.join(errors)}. Got: {rating_json}"
                print(f"[Worker Rating Error] {error_msg}")
                self.log_event(f"ERROR: {error_msg}", level="error", store_for_rating=True)
                return {"error": error_msg, "partial_rating": validated_rating or rating_json}

            self.log_event("LLM performance rating generated and validated successfully.", level="info", store_for_rating=True)
            return validated_rating

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse LLM rating JSON response: {e}"
            print(f"[Worker Rating Error] {error_msg}\nRaw Response Snippet:\n{raw_response[:500]}")
            self.log_event(f"ERROR: {error_msg}", level="error", store_for_rating=True)
            return {"error": error_msg, "raw_response": raw_response[:500]}
        except ValueError as e:
            error_msg = f"Error during rating generation or validation: {e}"
            print(f"[Worker Rating Error] {error_msg}")
            self.log_event(f"ERROR: {error_msg}", level="error", store_for_rating=True)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error during rating generation: {type(e).__name__} - {e}"
            print(f"[Worker Rating Error] {error_msg}")
            self.log_event(f"ERROR: {error_msg}", level="error", store_for_rating=True)
            self.log_event(traceback.format_exc(), level="error")
            return {"error": error_msg}


# Inside class SimulationManager:

    def trigger_debrief(self):
        """
        Generates the *initial* debrief summary (metrics, status) and emits it.
        The prompt for the next step is now triggered separately AFTER rating.
        Uses aware simulation time UTC for calculations.
        """
        self.log_event("Generating Initial Debrief Summary...", level="info", store_for_rating=True)
        self.emit_event("display_message", {"speaker": "System", "message": "--- Crisis Management Phase Over ---", "notification": "PHASE CHANGE"})

        final_status_report = "--- Final System Status ---\n" + self.get_status_summary(compact=False)
        metrics_summary = []

        try:
            # ... (Code to calculate metrics_summary remains exactly the same) ...
            # Time to Critical (Sim Time)
            time_to_crit_sec = 'N/A'
            t_crit = self.metrics.get('time_to_first_critical') # Aware sim time or None
            if isinstance(t_crit, datetime) and t_crit.tzinfo and \
               self.simulation_start_time and isinstance(self.simulation_start_time, datetime) and self.simulation_start_time.tzinfo:
                try:
                    t_crit_sim_utc = t_crit.astimezone(timezone.utc)
                    start_sim_utc = self.simulation_start_time.astimezone(timezone.utc)
                    time_to_crit_sec = f"{(t_crit_sim_utc - start_sim_utc).total_seconds():.0f}s (sim)"
                except (TypeError, ValueError): pass

            # Time Wasted Waiting (Sim Time)
            time_wasted_val = self.metrics.get('time_wasted_waiting', timedelta(0))
            time_wasted_sec = 'N/A'
            if isinstance(time_wasted_val, timedelta):
                time_wasted_sec = f"{time_wasted_val.total_seconds():.0f}s (sim)"

            compromised_count = self.metrics.get('systems_compromised_count', 0)
            escalations = self.metrics.get('escalations_triggered', 0)
            agents_contacted_iter = self.metrics.get('agents_contacted', set())
            agents_contacted_list = sorted(list(agents_contacted_iter)) if isinstance(agents_contacted_iter, set) else []
            key_actions_list = self.metrics.get('key_actions_taken', [])
            key_actions_display = []
            if isinstance(key_actions_list, list):
                for action in key_actions_list:
                    if isinstance(action, (list, tuple)) and len(action) >= 3:
                        key_actions_display.append(f"{action[1]} ({action[2]}) @ {action[0]} sim") # Mark time as sim time
                    elif isinstance(action, (list, tuple)) and len(action) == 2:
                         key_actions_display.append(f"{action[1]} @ {action[0]} sim")

            metrics_summary = [
                f"- Time to Critical: {time_to_crit_sec}",
                f"- Systems Compromised: {compromised_count}",
                f"- Escalations Triggered: {escalations}",
                f"- Time Wasted Waiting: {time_wasted_sec}",
                f"- Agents Contacted: {len(agents_contacted_list)} ({', '.join(agents_contacted_list)})",
                f"- Key Actions Taken: {len(key_actions_list)}",
                # f"- Key Actions Details: {key_actions_display}" # Optionally show more detail
             ]

        except Exception as e:
             print(f"ERROR formatting metrics in trigger_debrief: {type(e).__name__} - {e}")
             self.log_event(f"ERROR formatting metrics: {e}", level="error", store_for_rating=True)
             self.log_event(traceback.format_exc(), level="error")
             metrics_summary = ["- Error retrieving metrics data."]

        debrief_lines = [
            f"Scenario: {self.selected_scenario_key}",
            f"Intensity: {self.initial_intensity_mod:.1f}x -> {self.current_intensity_mod:.1f}x",
            f"Player Decision: '{self.player_decisions.get('shutdown_directive', 'Pending/Not Reached')}'",
            "--- Performance Metrics (Simulation Time) ---", *metrics_summary
        ]

        self.emit_event("debrief_info", {
            "title": "-- Simulation Debrief --",
            "final_status_report": final_status_report,
            "summary_points": debrief_lines,
            "performance_rating": None # Rating comes separately
        })
        self.log_event("Initial Debrief Summary Generated.", store_for_rating=True)

        # --- vvv REMOVED vvv ---
        # self.emit_event("request_yes_no", {
        #     "prompt": "Optional: Prepare analyst briefing points based on this outcome? (yes/no)",
        #     "action_context": "prepare_analyst_briefing"
        # })
        # --- ^^^ REMOVED ^^^ ---

    def end_simulation(self):
        # Marks simulation as ended. Uses aware sim time for final log.
        if not self.simulation_running: return

        end_msg = "****** Simulation Ending Process ******"
        self.log_event(end_msg, level="alert", store_for_rating=True) # Log uses current sim time

        self.simulation_running = False
        self.simulation_state = "ENDED"

        self.log_event("****** Simulation Run Ended ******", level="alert")
        self.emit_event("simulation_ended", {"message": "Simulation Complete. Review the debrief information."})


    def get_status_summary(self, compact=True):
        # Keep exactly as before - reads state
        status_copy = self.system_status.copy() if isinstance(self.system_status, dict) else {}
        if not status_copy:
            return "No system status available."

        if compact:
            non_nominal = {k: v for k, v in status_copy.items() if isinstance(v, str) and v not in ["NOMINAL", "UNKNOWN"]}
            if not non_nominal:
                return "All systems NOMINAL."
            severity_order = {"CRITICAL": 0, "HIGH": 1, "WARN": 2, "INFO": 3, "LOW": 4}
            def sort_key(item):
                key, value = item
                sev_word = value.split(" ")[0]
                sev_level_str = LOG_SEVERITY.get(sev_word, "INFO")
                sev_score = severity_order.get(sev_level_str, 99)
                return (sev_score, key)

            sorted_items = sorted(non_nominal.items(), key=sort_key)
            return ", ".join([f"{k}: {v}" for k, v in sorted_items])
        else:
            sorted_items = sorted(status_copy.items())
            return "\n".join([f"- {key}: {value}" for key, value in sorted_items])

    def cleanup(self):
        # Keep exactly as before
        self.log_event("Cleanup called for SimulationManager instance.")
        if self.simulation_running:
             self.simulation_running = False
             self.simulation_state = "ENDED"
        self._clear_current_events()
