# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert # For PostgreSQL
from datetime import datetime, timezone
from typing import Optional, Dict

from .models import LlmAndUserSimulationRating # Your combined model

def upsert_llm_rating_data(
    db: Session,
    simulation_id_str: str,
    llm_rating_data: Dict, # The dict from _call_llm_for_rating
    user_id_str: Optional[str] = None,
    scenario_key: Optional[str] = None
):
    """
    Inserts LLM rating data if no record exists for the simulation_id,
    or updates the LLM rating fields if a record already exists (e.g., user rated first).
    """
    insert_stmt = insert(LlmAndUserSimulationRating).values(
        simulation_id_str=simulation_id_str,
        user_id_str=user_id_str, # Player ID
        scenario_key=scenario_key,
        llm_overall_score=llm_rating_data.get("overall_score"),
        llm_timeliness_score=llm_rating_data.get("timeliness_score"),
        llm_contact_strategy_score=llm_rating_data.get("contact_strategy_score"),
        llm_decision_quality_score=llm_rating_data.get("decision_quality_score"),
        llm_efficiency_score=llm_rating_data.get("efficiency_score"),
        llm_qualitative_feedback=llm_rating_data.get("qualitative_feedback"),
        llm_rating_at=datetime.now(timezone.utc)
    )

    # Define what to do on conflict (if a row with the same simulation_id_str exists)
    # This assumes simulation_id_str has a UNIQUE constraint.
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['simulation_id_str'], # The column(s) that cause a conflict
        set_={ # Fields to update if conflict occurs
            "user_id_str": insert_stmt.excluded.user_id_str, # Use excluded to get incoming values
            "scenario_key": insert_stmt.excluded.scenario_key,
            "llm_overall_score": insert_stmt.excluded.llm_overall_score,
            "llm_timeliness_score": insert_stmt.excluded.llm_timeliness_score,
            "llm_contact_strategy_score": insert_stmt.excluded.llm_contact_strategy_score,
            "llm_decision_quality_score": insert_stmt.excluded.llm_decision_quality_score,
            "llm_efficiency_score": insert_stmt.excluded.llm_efficiency_score,
            "llm_qualitative_feedback": insert_stmt.excluded.llm_qualitative_feedback,
            "llm_rating_at": insert_stmt.excluded.llm_rating_at
            # IMPORTANT: Do NOT update user_rating_stars or user_feedback_text here
            # as this function is only for LLM data.
        }
    )
    db.execute(upsert_stmt)
    db.commit()
    print(f"CRUD: Upserted LLM rating data for sim_id {simulation_id_str}")

def upsert_user_star_rating_data(
    db: Session,
    simulation_id_str: str,
    user_rating_stars: int,
    user_feedback_text: Optional[str] = None,
    user_id_str: Optional[str] = None # Optional: who submitted the rating form
):
    """
    Inserts user star rating data if no record exists for the simulation_id,
    or updates the user star rating fields if a record already exists (e.g., LLM rated first).
    """
    insert_stmt = insert(LlmAndUserSimulationRating).values(
        simulation_id_str=simulation_id_str,
        user_id_str=user_id_str, # Could be different from player if admin rates, or player ID
        user_rating_stars=user_rating_stars,
        user_feedback_text=user_feedback_text,
        user_rated_at=datetime.now(timezone.utc)
        # Note: If the record is new, LLM fields will be NULL initially.
        # If user_id_str (player who played) is crucial, it should be set when the first piece of data (LLM or user rating) arrives.
        # The current upsert_llm_rating_data sets user_id_str (player).
    )

    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['simulation_id_str'],
        set_={
            "user_rating_stars": insert_stmt.excluded.user_rating_stars,
            "user_feedback_text": insert_stmt.excluded.user_feedback_text,
            "user_rated_at": insert_stmt.excluded.user_rated_at
            # IMPORTANT: Do NOT update LLM fields here.
        }
    )
    db.execute(upsert_stmt)
    db.commit()
    print(f"CRUD: Upserted user star rating data for sim_id {simulation_id_str}")