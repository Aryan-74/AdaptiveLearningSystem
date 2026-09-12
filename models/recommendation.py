import json
from typing import Dict, Any, List, Optional

def validate_recommendation_json(data: Dict[str, Any], domain_id: str) -> Dict[str, Any]:
    """
    Validates and normalizes recommendation JSON payload returned by AI provider.
    Ensures required fields exist, domain matches, and sets safe defaults.
    """
    if not isinstance(data, dict):
        raise ValueError("Recommendation output must be a JSON object.")

    # 1. Domain section
    domain_sec = data.get("domain", {})
    if not isinstance(domain_sec, dict):
        domain_sec = {}
    data["domain"] = {
        "id": str(domain_sec.get("id", domain_id)),
        "name": str(domain_sec.get("name", domain_id.capitalize()))
    }

    # 2. Executive Summary & Mastery Overview
    data["overall_mastery"] = float(data.get("overall_mastery", 0.0))
    data["summary"] = str(data.get("summary", "Personalized learning recommendation based on your current knowledge state and learner preferences."))

    # Mastered Areas (strengths)
    m_areas = data.get("mastered_areas", [])
    valid_m_areas = []
    if isinstance(m_areas, list):
        for item in m_areas:
            if isinstance(item, dict):
                valid_m_areas.append({
                    "area_id": str(item.get("area_id", "")),
                    "area_name": str(item.get("area_name", "")),
                    "mastery": float(item.get("mastery", 1.0))
                })
    data["mastered_areas"] = valid_m_areas

    # 3. Learner Approach
    l_app = data.get("learner_approach", {})
    if not isinstance(l_app, dict):
        l_app = {}
    data["learner_approach"] = {
        "preferences_considered": list(l_app.get("preferences_considered", [])),
        "recommended_approach": list(l_app.get("recommended_approach", [])),
        "reason": str(l_app.get("reason", "Tailored to your VARK modalities and self-regulation parameters."))
    }

    # 4. Priority Areas
    p_areas = data.get("priority_areas", [])
    valid_p_areas = []
    if isinstance(p_areas, list):
        for item in p_areas:
            if isinstance(item, dict):
                valid_p_areas.append({
                    "area_id": str(item.get("area_id", "area_001")),
                    "area_name": str(item.get("area_name", "Target Concept")),
                    "mastery": float(item.get("mastery", 0.0)),
                    "priority": str(item.get("priority", "high")),
                    "reason": str(item.get("reason", "Requires reinforcement.")),
                    "sub_concepts": list(item.get("sub_concepts", [])),
                    "prerequisites": list(item.get("prerequisites", [])),
                    "recommended_approach": list(item.get("recommended_approach", [])),
                    "recommended_resource_types": list(item.get("recommended_resource_types", []))
                })
    data["priority_areas"] = valid_p_areas

    # 5. Learning Sequence
    seq = data.get("learning_sequence", [])
    valid_seq = []
    if isinstance(seq, list):
        for idx, item in enumerate(seq, start=1):
            if isinstance(item, dict):
                valid_seq.append({
                    "step": int(item.get("step", idx)),
                    "area_id": str(item.get("area_id", "")),
                    "area_name": str(item.get("area_name", "")),
                    "objective": str(item.get("objective", "Achieve conceptual mastery.")),
                    "approach": str(item.get("approach", "Study and practice.")),
                    "practice_strategy": str(item.get("practice_strategy", "Targeted exercises."))
                })
    data["learning_sequence"] = valid_seq

    # 6. Resources
    res = data.get("resources", [])
    valid_res = []
    if isinstance(res, list):
        for item in res:
            if isinstance(item, dict):
                url_val = item.get("url")
                # Strict URL check: Nullify fabricated or unverified placeholder URLs
                if url_val and not (str(url_val).startswith("http://") or str(url_val).startswith("https://")):
                    url_val = None

                valid_res.append({
                    "area_id": str(item.get("area_id", "")),
                    "title": str(item.get("title", "Resource")),
                    "type": str(item.get("type", "Reference")),
                    "description": str(item.get("description", "")),
                    "url": url_val,
                    "why_recommended": str(item.get("why_recommended", "")),
                    "verification_status": str(item.get("verification_status", "unverified"))
                })
    data["resources"] = valid_res

    # 7. Practice Recommendations
    prac = data.get("practice_recommendations", [])
    valid_prac = []
    if isinstance(prac, list):
        for item in prac:
            if isinstance(item, dict):
                valid_prac.append({
                    "area_id": str(item.get("area_id", "")),
                    "activity_type": str(item.get("activity_type", "Practice Exercise")),
                    "description": str(item.get("description", "")),
                    "reason": str(item.get("reason", ""))
                })
    data["practice_recommendations"] = valid_prac

    return data
