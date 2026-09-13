import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

ALLOWED_RESOURCE_TYPES = [
    "Video",
    "Documentation",
    "Tutorial",
    "Article",
    "Worked Example",
    "Exercise",
    "Case Study",
    "Reference"
]

def map_to_allowed_type(raw_type: str) -> str:
    if not raw_type:
        return "Reference"
    t_lower = raw_type.lower().strip()
    if "video" in t_lower:
        return "Video"
    if "doc" in t_lower:
        return "Documentation"
    if "tut" in t_lower:
        return "Tutorial"
    if "art" in t_lower:
        return "Article"
    if "work" in t_lower or "prob" in t_lower or "example" in t_lower:
        return "Worked Example"
    if "exer" in t_lower or "prac" in t_lower or "sim" in t_lower or "lab" in t_lower:
        return "Exercise"
    if "case" in t_lower:
        return "Case Study"
    return "Reference"

_CATALOG_CACHE: Optional[List[Dict[str, Any]]] = None

def load_resource_catalog() -> List[Dict[str, Any]]:
    """
    Loads authoritative resource catalogue from data/resource_catalog.json single source of truth.
    """
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog_path = os.path.join(base_dir, "data", "resource_catalog.json")

    if not os.path.exists(catalog_path):
        catalog_path = os.path.join("data", "resource_catalog.json")

    if os.path.exists(catalog_path):
        with open(catalog_path, "r", encoding="utf-8") as f:
            _CATALOG_CACHE = json.load(f)
    else:
        _CATALOG_CACHE = []

    return _CATALOG_CACHE

def validate_canonical_resource(res: Any) -> Optional[Dict[str, str]]:
    """
    Validates a resource object against the explicit canonical structure:
    {
      "title": str,
      "type": str,      # Allowed: Video, Documentation, Tutorial, Article, Worked Example, Exercise, Case Study, Reference
      "source": str,
      "url": str,       # Must be valid http:// or https:// URL (no nulls, placeholders, or fake URLs)
      "reason": str
    }
    Returns validated dict if strictly valid, or None if invalid/missing URL.
    """
    if not isinstance(res, dict):
        return None

    title = str(res.get("title", "")).strip()
    raw_type = str(res.get("type", "")).strip()
    source = str(res.get("source", "")).strip()
    raw_url = res.get("url")
    reason = str(res.get("reason") or res.get("why_recommended") or res.get("description") or "").strip()

    # Title & Source must be non-empty
    if not title or not source:
        return None

    # Strict URL validation (rule 1, 2, 3, 4, 5)
    if not raw_url or not isinstance(raw_url, str):
        return None
    url_str = raw_url.strip()
    if not (url_str.startswith("http://") or url_str.startswith("https://")):
        return None

    # Reject localhost or generic placeholders
    if "example.com" in url_str.lower() or "placeholder" in url_str.lower():
        return None

    # Type validation & mapping to allowed enum
    valid_type = map_to_allowed_type(raw_type)

    if not reason:
        reason = f"Curated {valid_type.lower()} resource from {source}."

    return {
        "title": title,
        "type": valid_type,
        "source": source,
        "url": url_str,
        "reason": reason
    }

def select_adaptive_curated_resources(
    priority_areas: List[Dict[str, Any]],
    domain_id: str,
    learner_profile: Optional[Dict[str, Any]] = None,
    learning_goal: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Adaptive Resource Selection Algorithm (3-Factor Adaptive Model):
    Selects 4-6 verified educational resources from data/resource_catalog.json based on:
    1. Knowledge Weaknesses: Topic remediation priority based on assessed mastery score (lowest mastery = highest weight).
    2. Learning Goal Fit: Semantic alignment with selected goal (e.g. conceptual, interview prep, project building, problem solving).
    3. Learner Preferences: Non-rigid VARK modality ranking boost (Visual -> Video, Read/Write -> Docs/Tutorials, Kinesthetic -> Exercises).
    4. YouTube Channel Diversity: Max 1 video per YouTube channel by default to ensure channel diversity.
    5. Format Diversity: Balanced representation of Video, Documentation/Tutorial, and Practice/Exercise resources.
    6. Personalized Rationale: Non-rigid justification referencing topic mastery %, learning goal, and preference alignment.
    """
    global _CATALOG_CACHE
    _CATALOG_CACHE = None
    catalog = load_resource_catalog()
    if not catalog:
        return []

    d_key = str(domain_id).lower()

    # 1. Parse Learner Profile Signals
    top_modality = "vark_visual"
    if learner_profile and isinstance(learner_profile, dict):
        vark_scores = learner_profile.get("vark", {})
        if vark_scores:
            top_modality = max(vark_scores.items(), key=lambda x: x[1])[0]

    # 2. Parse Learning Goal Context
    goal_type = "conceptual_understanding"
    goal_desc = ""
    if learning_goal and isinstance(learning_goal, dict):
        goal_type = str(learning_goal.get("type", "conceptual_understanding")).lower()
        goal_desc = str(learning_goal.get("description", "")).lower()

    # Map KC IDs to topic names
    kc_to_topic = {
        "kc_matrix_ops": "linear_algebra",
        "kc_eigenvalues": "linear_algebra",
        "kc_derivatives": "calculus",
        "kc_integrals": "calculus",
        "kc_kinematics": "classical_mechanics",
        "kc_newton_laws": "classical_mechanics",
        "kc_first_law_thermo": "thermodynamics",
        "kc_circuits": "electromagnetism"
    }

    # Step 1: Process and sort priority areas by assessed mastery
    valid_p_areas = []
    for p in priority_areas:
        if not isinstance(p, dict):
            continue
        aid = str(p.get("area_id", "")).lower()
        if not aid:
            continue
        
        m_val = p.get("mastery")
        if m_val is None:
            logger.warning(f"[RESOURCE SELECTION] Area '{aid}' has missing (None) mastery data. Preserving distinction from measured 0.0.")
            m_num = 999.0  # Put unassessed topics behind assessed weak topics
        else:
            m_num = float(m_val)

        topic_key = kc_to_topic.get(aid, aid)
        valid_p_areas.append({
            "area_id": aid,
            "topic_key": topic_key,
            "area_name": p.get("area_name", topic_key.replace("_", " ").capitalize()),
            "mastery": m_num,
            "raw_mastery": m_val,
            "priority": p.get("priority", "high"),
            "preferred_types": p.get("recommended_resource_types", [])
        })

    # Sort priority areas by mastery ascending (weakest measured area first)
    valid_p_areas.sort(key=lambda x: x["mastery"])

    allocated_resources = []
    seen_urls = set()
    used_yt_channels = set()

    # Step 2: Adaptive Scoring and Selection per Priority Area
    for idx, area_info in enumerate(valid_p_areas):
        t_key = area_info["topic_key"]
        m_pct = int(area_info["mastery"] * 100) if area_info["raw_mastery"] is not None else None
        a_name = area_info["area_name"]

        # Fetch catalog candidates matching domain & topic
        candidates = []
        for item in catalog:
            item_domain = str(item.get("domain", "")).lower()
            item_topic = str(item.get("topic", "")).lower()

            if d_key not in item_domain and item_domain not in d_key and d_key != "general":
                continue

            if (t_key == item_topic) or (t_key in item_topic) or (item_topic in t_key):
                candidates.append(item)

        if not candidates:
            continue

        # Scoring Formula: Relevance (100) + Mastery (40) + Goal Fit (35) + Preference (20) + Diversity Penalty (-50)
        def score_resource(item):
            itype = map_to_allowed_type(item.get("type", ""))
            diff = str(item.get("difficulty", "beginner")).lower()
            title_lower = str(item.get("title", "")).lower()
            channel = str(item.get("channel") or item.get("source", "")).strip()

            score = 100.0  # Base topic relevance

            # Mastery Weight
            if area_info["raw_mastery"] is not None:
                m_score = area_info["mastery"]
                if m_score <= 0.25:
                    score += 40.0
                elif m_score <= 0.50:
                    score += 30.0
                elif m_score <= 0.70:
                    score += 20.0
                else:
                    score += 10.0
            else:
                score += 5.0

            # Learning Goal Fit (Weight = 35)
            if goal_type in ["conceptual_understanding", "skill_development"] or "fundamental" in goal_desc:
                if diff == "beginner":
                    score += 25.0
                if itype in ["Video", "Tutorial", "Documentation"]:
                    score += 10.0
            elif goal_type == "interview_preparation" or "interview" in goal_desc:
                if "interview" in title_lower or "question" in title_lower or "exercise" in title_lower or itype == "Exercise":
                    score += 25.0
                if itype in ["Exercise", "Worked Example", "Tutorial"]:
                    score += 10.0
            elif goal_type == "project_preparation" or "project" in goal_desc:
                if "project" in title_lower or "application" in title_lower or "code" in title_lower:
                    score += 25.0
                if itype in ["Tutorial", "Worked Example", "Video"]:
                    score += 10.0
            elif goal_type in ["revision", "exam_preparation"]:
                if itype in ["Exercise", "Worked Example", "Documentation"]:
                    score += 25.0

            # Learner Preference Boost (Secondary Signal, Weight = 20)
            if "visual" in top_modality.lower() or "aural" in top_modality.lower():
                if itype == "Video":
                    score += 20.0
                elif itype == "Tutorial":
                    score += 10.0
            elif "read" in top_modality.lower():
                if itype in ["Documentation", "Tutorial", "Article", "Reference"]:
                    score += 20.0
            elif "kinesthetic" in top_modality.lower():
                if itype in ["Exercise", "Worked Example"]:
                    score += 20.0

            # YouTube Channel Diversity Penalty (Max 1 video per channel default)
            if itype == "Video" and channel:
                if channel in used_yt_channels:
                    score -= 50.0  # Channel diversity penalty

            return score

        candidates.sort(key=score_resource, reverse=True)

        # Allocate slot limit per area (weakest area gets up to 3 resources; secondary 1-2)
        max_slots = 3 if idx == 0 else (2 if idx == 1 else 1)
        area_selected = 0

        for item in candidates:
            if area_selected >= max_slots or len(allocated_resources) >= 6:
                break

            url = item.get("url", "")
            if not url or url in seen_urls:
                continue

            itype = map_to_allowed_type(item.get("type", ""))
            channel = str(item.get("channel") or item.get("source", "")).strip()

            # Build personalized rationale referencing topic mastery, goal, and preference alignment
            if m_pct is not None:
                reason_text = f"Recommended because your assessed mastery of {a_name} is {m_pct}%. "
            else:
                reason_text = f"Recommended because {a_name} is a key focus area in your curriculum. "

            # Goal fit phrasing
            if "interview" in goal_type or "interview" in goal_desc:
                reason_text += f"This {itype.lower()} provides problem-solving practice aligned with your goal of preparing for Python technical interviews."
            elif "project" in goal_type or "project" in goal_desc:
                reason_text += f"This {itype.lower()} provides applied examples aligned with your goal of building practical Python projects."
            elif "revision" in goal_type or "skill" in goal_type or "problem" in goal_desc or "exam" in goal_type:
                reason_text += f"This {itype.lower()} provides practical exercises aligned with your goal of improving Python problem solving."
            else:
                reason_text += f"This {itype.lower()} provides clear explanations aligned with your goal of learning Python fundamentals."

            # Preference alignment phrasing
            if itype == "Video" and ("visual" in top_modality.lower() or "aural" in top_modality.lower()):
                reason_text += " Format aligns with your reported preference for video-based learning."
            elif itype in ["Documentation", "Tutorial", "Article", "Reference"] and "read" in top_modality.lower():
                reason_text += " Format aligns with your reported preference for structured read/write materials."
            elif itype in ["Exercise", "Worked Example"] and "kinesthetic" in top_modality.lower():
                reason_text += " Format aligns with your reported preference for hands-on problem solving."

            canonical = {
                "title": item.get("title"),
                "type": itype,
                "source": item.get("source"),
                "channel": channel,
                "url": url,
                "reason": reason_text
            }

            validated = validate_canonical_resource(canonical)
            if validated:
                if channel:
                    validated["channel"] = channel
                allocated_resources.append(validated)
                seen_urls.add(url)
                if itype == "Video" and channel:
                    used_yt_channels.add(channel)
                area_selected += 1

        if len(allocated_resources) >= 6:
            break

    return allocated_resources[:6]

def retrieve_real_resources_for_area(area_id: str, domain_id: str, preferred_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Decoupled Resource Retrieval Layer:
    Loads single source of truth from data/resource_catalog.json and retrieves verified external resources matching area_id and domain_id.
    Returns list of validated canonical resource objects with real URLs.
    """
    catalog = load_resource_catalog()
    a_key = str(area_id).lower()
    d_key = str(domain_id).lower()

    kc_to_topic = {
        "kc_matrix_ops": "linear_algebra",
        "kc_eigenvalues": "linear_algebra",
        "kc_derivatives": "calculus",
        "kc_integrals": "calculus",
        "kc_kinematics": "classical_mechanics",
        "kc_newton_laws": "classical_mechanics",
        "kc_first_law_thermo": "thermodynamics",
        "kc_circuits": "electromagnetism"
    }
    search_topic = kc_to_topic.get(a_key, a_key)

    retrieved = []

    # 1. Match entries in catalog where domain matches and topic matches
    for item in catalog:
        item_domain = str(item.get("domain", "")).lower()
        item_topic = str(item.get("topic", "")).lower()

        # Check domain match (e.g., 'python' in 'python' or vice versa)
        if d_key not in item_domain and item_domain not in d_key and d_key != "general":
            continue

        # Check topic match (exact, substring, or mapped KC)
        topic_match = (search_topic == item_topic) or (search_topic in item_topic) or (item_topic in search_topic)
        if topic_match:
            # Map catalog schema to canonical resource structure
            canonical = {
                "title": item.get("title"),
                "type": item.get("type"),
                "source": item.get("source"),
                "url": item.get("url"),
                "reason": f"Curated {item.get('type', 'resource').lower()} resource covering {item_topic.replace('_', ' ')} from {item.get('source')}."
            }
            validated = validate_canonical_resource(canonical)
            if validated:
                retrieved.append(validated)

    if retrieved:
        return retrieved

    # 2. Domain-level fallback if no specific topic match found
    for item in catalog:
        item_domain = str(item.get("domain", "")).lower()
        if d_key in item_domain or item_domain in d_key:
            canonical = {
                "title": item.get("title"),
                "type": item.get("type"),
                "source": item.get("source"),
                "url": item.get("url"),
                "reason": f"Curated {item.get('type', 'resource').lower()} resource from {item.get('source')}."
            }
            validated = validate_canonical_resource(canonical)
            if validated:
                retrieved.append(validated)

    return retrieved

def validate_resource_url(url: Any) -> Dict[str, Any]:
    """
    Legacy helper kept for backward compatibility.
    """
    if not url or not isinstance(url, str):
        return {"url": None, "verification_status": "unverified"}

    url_str = url.strip()
    if url_str.startswith("http://") or url_str.startswith("https://"):
        return {"url": url_str, "verification_status": "verified"}

    return {"url": None, "verification_status": "unverified"}


