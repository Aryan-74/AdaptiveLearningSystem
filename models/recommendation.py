import json
import re
from typing import Dict, Any, List, Optional

def normalize_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', title.lower())

def normalize_url(url: Optional[str]) -> str:
    if not url:
        return ""
    u = str(url).lower().strip()
    if u.endswith('/'):
        u = u[:-1]
    return u

def deduplicate_resources(resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicates resources based on normalized URL and normalized title.
    """
    seen_urls = set()
    seen_titles = set()
    unique_resources = []

    for res in resources:
        url_norm = normalize_url(res.get("url"))
        title_norm = normalize_title(res.get("title"))

        if url_norm and url_norm in seen_urls:
            continue
        if title_norm and title_norm in seen_titles:
            continue

        if url_norm:
            seen_urls.add(url_norm)
        if title_norm:
            seen_titles.add(title_norm)

        unique_resources.append(res)

    return unique_resources

def sort_sequence_by_prerequisites(sequence: List[Dict[str, Any]], priority_areas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    prereqs = {}
    for p in priority_areas:
        if isinstance(p, dict):
            prereqs[p.get("area_id")] = set(p.get("prerequisites", []))
    
    seq_areas = [item.get("area_id") for item in sequence if isinstance(item, dict) and item.get("area_id")]
    
    result = []
    placed = set()
    remaining = [item for item in sequence if isinstance(item, dict)]
    
    max_passes = len(remaining) + 1
    for _ in range(max_passes):
        progress = False
        next_remaining = []
        for item in remaining:
            aid = item.get("area_id")
            item_prereqs = prereqs.get(aid, set())
            unmet_prereqs = [p for p in item_prereqs if p in seq_areas and p not in placed]
            if not unmet_prereqs:
                result.append(item)
                if aid:
                    placed.add(aid)
                progress = True
            else:
                next_remaining.append(item)
        remaining = next_remaining
        if not remaining or not progress:
            result.extend(remaining)
            break

    for idx, item in enumerate(result, start=1):
        item["step"] = idx
        
    return result

def validate_recommendation_json(
    data: Dict[str, Any],
    domain_id: str,
    snapshot: Optional[Any] = None,
    curriculum: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Validates and normalizes recommendation JSON payload returned by AI provider.
    Ensures required fields exist, domain matches, overrides mastery values from single source of truth snapshot,
    deduplicates resources, and validates area IDs against curriculum.
    """
    if isinstance(data, list) and len(data) > 0:
        data = data[0]
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

    # Extract authoritative DB mastery scores if snapshot provided
    db_mastery_map = {}
    db_overall_mastery = None
    if snapshot:
        if hasattr(snapshot, "knowledge_profile"):
            kp = snapshot.knowledge_profile
            db_overall_mastery = getattr(kp, "overall_mastery", 0.0)
            if hasattr(kp, "areas"):
                for a in kp.areas:
                    db_mastery_map[a.id] = a.mastery
        elif isinstance(snapshot, dict):
            kp = snapshot.get("knowledge_profile", {})
            db_overall_mastery = kp.get("overall_mastery", 0.0)
            for a in kp.get("areas", []):
                if isinstance(a, dict) and "id" in a:
                    db_mastery_map[a["id"]] = a.get("mastery", 0.0)

    # Extract curriculum area IDs if provided
    valid_area_ids = set()
    if curriculum:
        if hasattr(curriculum, "areas"):
            valid_area_ids = {a.id for a in curriculum.areas}
        elif isinstance(curriculum, dict):
            valid_area_ids = {a.get("id") for a in curriculum.get("areas", []) if isinstance(a, dict) and "id" in a}

    # 2. Executive Summary & Mastery Overview
    if db_overall_mastery is not None:
        data["overall_mastery"] = float(db_overall_mastery)
    else:
        data["overall_mastery"] = float(data.get("overall_mastery", 0.0))

    data["summary"] = str(data.get("summary", "Personalized learning recommendation based on your current knowledge state and learner preferences."))

    # Mastered Areas (strengths)
    m_areas = data.get("mastered_areas", [])
    valid_m_areas = []
    if isinstance(m_areas, list):
        for item in m_areas:
            if isinstance(item, dict):
                aid = str(item.get("area_id", ""))
                if valid_area_ids and aid not in valid_area_ids:
                    continue
                db_val = db_mastery_map.get(aid)
                mastery_val = float(db_val) if db_val is not None else (float(item.get("mastery")) if item.get("mastery") is not None else 1.0)
                valid_m_areas.append({
                    "area_id": aid,
                    "area_name": str(item.get("area_name", "")),
                    "mastery": float(mastery_val)
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
                aid = str(item.get("area_id", "area_001"))
                if valid_area_ids and aid not in valid_area_ids:
                    continue
                db_val = db_mastery_map.get(aid)
                mastery_val = float(db_val) if db_val is not None else (float(item.get("mastery")) if item.get("mastery") is not None else None)
                valid_p_areas.append({
                    "area_id": aid,
                    "area_name": str(item.get("area_name", "Target Concept")),
                    "mastery": float(mastery_val) if mastery_val is not None else None,
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
                aid = str(item.get("area_id", ""))
                if valid_area_ids and aid and aid not in valid_area_ids:
                    continue
                valid_seq.append({
                    "step": int(item.get("step", idx)),
                    "area_id": aid,
                    "area_name": str(item.get("area_name", "")),
                    "objective": str(item.get("objective", "Achieve conceptual mastery.")),
                    "approach": str(item.get("approach", "Study and practice.")),
                    "practice_strategy": str(item.get("practice_strategy", "Targeted exercises."))
                })
    data["learning_sequence"] = sort_sequence_by_prerequisites(valid_seq, valid_p_areas)

    # 6. Resources & Deduplication (Canonical Structure Enforcement)
    from services.resource_service import validate_canonical_resource
    res = data.get("resources", [])
    valid_res = []
    if isinstance(res, list):
        for item in res:
            validated = validate_canonical_resource(item)
            if validated:
                valid_res.append(validated)
    
    # Run backend deduplication on canonical resources
    data["resources"] = deduplicate_resources(valid_res)

    # 7. Practice Recommendations
    prac = data.get("practice_recommendations", [])
    valid_prac = []
    if isinstance(prac, list):
        for item in prac:
            if isinstance(item, dict):
                aid = str(item.get("area_id", ""))
                if valid_area_ids and aid and aid not in valid_area_ids:
                    continue
                valid_prac.append({
                    "area_id": aid,
                    "activity_type": str(item.get("activity_type", "Practice Exercise")),
                    "description": str(item.get("description", "")),
                    "reason": str(item.get("reason", ""))
                })
    data["practice_recommendations"] = valid_prac

    return data
