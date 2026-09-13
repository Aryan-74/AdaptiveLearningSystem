import json
import uuid
from typing import Dict, Any, Optional, List

from db import get_db
from services.profile_service import get_student_snapshot
from services.knowledge_service import get_domain_by_id, get_domain_curriculum
from services.ai_service import get_ai_provider, AIGenerationError
from services.resource_service import validate_resource_url, retrieve_real_resources_for_area
from models.recommendation import deduplicate_resources, validate_recommendation_json

def generate_learning_recommendation(
    student_id: str,
    domain_id: str,
    learning_goal: Optional[Dict[str, Any]] = None,
    force_mock: bool = False
) -> Dict[str, Any]:
    """
    Main domain-agnostic recommendation service pipeline.
    Retrieves single source of truth profile & domain curriculum, formats AI input,
    executes AI model, enforces single source of truth mastery & resource deduplication,
    validates output schema & resource URLs, and persists recommendation snapshot.
    Raises AIGenerationError if AI generation fails (NO fake fallback success).
    """
    # 1. Validate domain exists
    domain = get_domain_by_id(domain_id)
    if not domain:
        raise ValueError(f"Invalid learning domain ID: {domain_id}")

    # 2. Retrieve student snapshot (Learner Profile + Knowledge Profile)
    snapshot = get_student_snapshot(student_id, domain_id)

    # 3. Retrieve curriculum structure for domain
    curriculum = get_domain_curriculum(domain_id)

    # 4. Build structured input for AI using single source of truth profiles
    ai_input = {
        "learning_context": {
            "domain": domain.to_dict(),
            "learning_goal": learning_goal or {
                "type": "conceptual_understanding",
                "description": f"Master key foundational concepts in {domain.name}."
            },
            "curriculum": curriculum.to_dict()
        },
        "student": snapshot.to_dict()
    }

    # 5. Call AI Provider abstraction (raises AIGenerationError if call fails)
    provider = get_ai_provider(force_mock=force_mock)
    recommendation_json = provider.generate_structured_recommendation(ai_input)

    # 6. Validate & Override Single Source of Truth Mastery, Deduplicate Resources, Validate Area IDs
    recommendation_json = validate_recommendation_json(
        recommendation_json,
        domain_id=domain_id,
        snapshot=snapshot,
        curriculum=curriculum
    )

    # 7. Decoupled Adaptive Resource Retrieval Layer: Search catalog based on remedial focus areas, mastery weighting, and learner preferences
    from services.resource_service import select_adaptive_curated_resources, validate_canonical_resource
    
    l_profile_dict = snapshot.learner_profile.to_dict() if hasattr(snapshot, "learner_profile") else (snapshot.get("learner_profile", {}) if isinstance(snapshot, dict) else {})
    p_areas = recommendation_json.get("priority_areas", [])

    retrieved_resources = select_adaptive_curated_resources(
        priority_areas=p_areas,
        domain_id=domain_id,
        learner_profile=l_profile_dict,
        learning_goal=ai_input["learning_context"]["learning_goal"]
    )

    if retrieved_resources:
        recommendation_json["resources"] = deduplicate_resources(retrieved_resources)
    else:
        existing_res = recommendation_json.get("resources", [])
        canonical_resources = []
        for item in existing_res:
            validated = validate_canonical_resource(item)
            if validated:
                canonical_resources.append(validated)
        recommendation_json["resources"] = deduplicate_resources(canonical_resources)

    # 8. Persist recommendation snapshot to database
    rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
    model_name = recommendation_json.get("_model_name") or provider.__class__.__name__
    recommendation_json["id"] = rec_id
    recommendation_json["model_name"] = model_name

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recommendations (
            id, student_id, domain_id, model_name, learning_goal, profile_snapshot, recommendation_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed');
    """, (
        rec_id,
        student_id,
        domain_id,
        model_name,
        json.dumps(learning_goal) if learning_goal else None,
        json.dumps(snapshot.to_dict()),
        json.dumps(recommendation_json)
    ))
    conn.commit()
    conn.close()

    return recommendation_json

def get_latest_recommendation(student_id: str, domain_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the latest stored AI recommendation for a given student and domain.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, model_name, generated_at, recommendation_json 
        FROM recommendations 
        WHERE student_id = ? AND domain_id = ? AND status = 'completed'
        ORDER BY generated_at DESC LIMIT 1;
    """, (student_id, domain_id))
    row = cursor.fetchone()
    conn.close()

    if row and row["recommendation_json"]:
        rec = json.loads(row["recommendation_json"])
        rec["id"] = row["id"]
        rec["model_name"] = row["model_name"]
        rec["generated_at"] = row["generated_at"]
        return rec
    return None

def get_recommendation_history(student_id: str, domain_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches history of generated recommendations for a student.
    """
    conn = get_db()
    cursor = conn.cursor()
    if domain_id:
        cursor.execute("""
            SELECT id, domain_id, generated_at, model_name, learning_goal, recommendation_json 
            FROM recommendations 
            WHERE student_id = ? AND domain_id = ? AND status = 'completed'
            ORDER BY generated_at DESC;
        """, (student_id, domain_id))
    else:
        cursor.execute("""
            SELECT id, domain_id, generated_at, model_name, learning_goal, recommendation_json 
            FROM recommendations 
            WHERE student_id = ? AND status = 'completed'
            ORDER BY generated_at DESC;
        """, (student_id,))

    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        rec_data = json.loads(r["recommendation_json"]) if r["recommendation_json"] else {}
        rec_data["id"] = r["id"]
        rec_data["domain_id"] = r["domain_id"]
        rec_data["generated_at"] = r["generated_at"]
        rec_data["model_name"] = r["model_name"]
        rec_data["learning_goal"] = json.loads(r["learning_goal"]) if r["learning_goal"] else None
        history.append(rec_data)

    return history
