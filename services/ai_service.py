import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from models.recommendation import validate_recommendation_json
from services.resource_service import get_verified_url_for_area

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI-powered personalized learning recommendation engine.

You receive information about a learner, their current learning domain, their knowledge state, their learner preferences, and their available curriculum information.

Your task is to determine what the learner should focus on and recommend appropriate ways and resources for learning those areas.

The learning domain is provided dynamically. Do not assume a particular subject.
The domain provided in the input is the authoritative context for this recommendation.

CRITICAL INSTRUCTIONS:
1. Do NOT hard-code or assume subject-specific logic. Adapt all recommendation terms, strategies, and resource types to the supplied domain.
2. Prioritize learning areas based on mastery scores, prerequisite relationships (if provided), and structural importance.
3. Adapt HOW the learner should study based on their psychological/learner profile (VARK preferences, motivation, self-regulation).
4. Recommend domain-appropriate resource types (e.g., programming documentation/coding exercises for code, worked problem sets/proofs for math, simulations/experiments for physics).
5. DO NOT fabricate or hallucinate URLs. Set "url": null and "verification_status": "unverified" for suggested resources.
6. Focus priority_areas on distinct high-level topics. Do not duplicate a parent topic and its child sub-concepts as separate priority area entries; group child sub-concepts under "sub_concepts".
7. Return strictly VALID JSON following the specified schema without Markdown code fences or raw text wrapper.

OUTPUT JSON SCHEMA:
{
    "domain": {
        "id": "<domain_id>",
        "name": "<domain_name>"
    },
    "overall_mastery": 0.54,
    "summary": "<executive summary of learning recommendation>",
    "mastered_areas": [
        {
            "area_id": "<topic_id>",
            "area_name": "<topic_name>",
            "mastery": 1.0
        }
    ],
    "learner_approach": {
        "preferences_considered": ["<trait 1>", "<trait 2>"],
        "recommended_approach": ["<tactic 1>", "<tactic 2>"],
        "reason": "<explanation of approach tailored to learner profile>"
    },
    "priority_areas": [
        {
            "area_id": "<topic_id>",
            "area_name": "<topic_name>",
            "mastery": 0.0,
            "priority": "very_high | high | medium | low",
            "reason": "<why this area is prioritized>",
            "sub_concepts": ["<sub_concept 1>", "<sub_concept 2>"],
            "prerequisites": ["<prereq_id>"],
            "recommended_approach": ["<tactic>"],
            "recommended_resource_types": ["<type 1>", "<type 2>"]
        }
    ],
    "learning_sequence": [
        {
            "step": 1,
            "area_id": "<topic_id>",
            "area_name": "<topic_name>",
            "objective": "<step objective>",
            "approach": "<study method>",
            "practice_strategy": "<practice method>"
        }
    ],
    "resources": [
        {
            "area_id": "<topic_id>",
            "title": "<resource title>",
            "type": "<Documentation | Worked Problems | Simulation | Video | Tutorial | Exercise | Textbook>",
            "description": "<resource description>",
            "url": null,
            "why_recommended": "<why suited for student>",
            "verification_status": "unverified"
        }
    ],
    "practice_recommendations": [
        {
            "area_id": "<topic_id>",
            "activity_type": "<exercise type>",
            "description": "<activity description>",
            "reason": "<rationale>"
        }
    ]
}"""

class AIProvider(ABC):
    @abstractmethod
    def generate_structured_recommendation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

class MockAIProvider(AIProvider):
    """
    Offline/Fallback AI Provider that dynamically generates domain-agnostic,
    structured recommendations without external API dependencies.
    """
    def generate_structured_recommendation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        context = input_data.get("learning_context", {})
        domain = context.get("domain", {})
        domain_id = domain.get("id", "general")
        domain_name = domain.get("name", domain_id.capitalize())
        learning_goal = context.get("learning_goal", {})
        goal_desc = learning_goal.get("description") if isinstance(learning_goal, dict) else None

        curriculum = context.get("curriculum", {})
        areas = curriculum.get("areas", [])

        student = input_data.get("student", {})
        l_profile = student.get("learner_profile", {})
        k_profile = student.get("knowledge_profile", {})
        overall_mastery = k_profile.get("overall_mastery", 0.0)

        # Map knowledge areas from student profile or curriculum
        k_areas = k_profile.get("areas", [])
        mastery_map = {item.get("id"): item.get("mastery", 0.0) for item in k_areas}

        # Group curriculum into high-level topics and collect child KCs
        topic_areas = [a for a in areas if a.get("type") == "topic"]
        if not topic_areas:
            topic_areas = areas

        sorted_topics = []
        for area in topic_areas:
            tid = area.get("id")
            tname = area.get("name", tid)
            m_score = mastery_map.get(tid, 0.0)
            
            # Collect child concepts belonging to this topic
            child_kcs = [a.get("name") for a in areas if a.get("parent_id") == tid]
            
            sorted_topics.append({
                "id": tid,
                "name": tname,
                "mastery": m_score,
                "description": area.get("description", ""),
                "sub_concepts": child_kcs
            })

        sorted_topics.sort(key=lambda x: x["mastery"])

        # Determine learner approach signals
        vark = l_profile.get("vark", {})
        mot = l_profile.get("motivation", {})
        sr = l_profile.get("self_regulation", {})

        top_vark = max(vark.items(), key=lambda x: x[1])[0] if vark else "vark_visual"
        vark_clean = top_vark.replace("vark_", "").capitalize()

        prefs_considered = []
        rec_approach = []
        if "visual" in top_vark.lower():
            prefs_considered.append("Visual Learner Preference")
            rec_approach.extend(["Incorporate diagrams, flowcharts, and visual aids", "Use visual step-by-step concept maps"])
        elif "aural" in top_vark.lower():
            prefs_considered.append("Aural Learner Preference")
            rec_approach.extend(["Listen to audio explanations and discussions", "Verbalize concepts and teach back aloud"])
        elif "read" in top_vark.lower():
            prefs_considered.append("Read/Write Learner Preference")
            rec_approach.extend(["Read structured documentation and textbooks", "Write comprehensive notes and bullet summaries"])
        else:
            prefs_considered.append("Kinesthetic Learner Preference")
            rec_approach.extend(["Engage in hands-on practical exercises", "Build interactive projects and real-world experiments"])

        if mot.get("intrinsic_motivation", 0.0) >= 0.6:
            prefs_considered.append("High Intrinsic Motivation")
            rec_approach.append("Explore deep conceptual reasoning and underlying principles")
        if sr.get("goal_setting", 0.0) >= 0.6:
            prefs_considered.append("Strong Goal Setting")
            rec_approach.append("Follow structured milestone-driven learning steps")

        # Domain-appropriate resource types mapping
        domain_lower = domain_id.lower()
        if "python" in domain_lower or "code" in domain_lower or "program" in domain_lower:
            resource_types = ["Documentation", "Coding Exercises", "Interactive Tutorials", "Video Demonstrations"]
        elif "math" in domain_lower or "algebra" in domain_lower or "calculus" in domain_lower:
            resource_types = ["Worked Problems", "Concept Explanations", "Step-by-Step Proofs", "Practice Sets"]
        elif "physics" in domain_lower or "science" in domain_lower:
            resource_types = ["Interactive Simulations", "Worked Physics Problems", "Textbook Reference", "Lecture Videos"]
        else:
            resource_types = ["Textbook Reference", "Tutorial Articles", "Practice Sets", "Educational Videos"]

        # Build priority areas
        priority_areas = []
        learning_sequence = []
        resources = []
        practice_recs = []

        for idx, area in enumerate(sorted_topics[:4], start=1):
            m = area["mastery"]
            p_level = "very_high" if m < 0.4 else ("high" if m < 0.7 else "medium")
            reason = f"Mastery level is currently at {int(m * 100)}%. Focusing on this area establishes essential foundational competence."
            if idx == 1 and goal_desc:
                reason += f" Highly relevant for goal: '{goal_desc}'."

            priority_areas.append({
                "area_id": area["id"],
                "area_name": area["name"],
                "mastery": m,
                "priority": p_level,
                "reason": reason,
                "sub_concepts": area.get("sub_concepts", []),
                "prerequisites": [],
                "recommended_approach": rec_approach[:2],
                "recommended_resource_types": resource_types[:2]
            })

            learning_sequence.append({
                "step": idx,
                "area_id": area["id"],
                "area_name": area["name"],
                "objective": f"Achieve > 75% mastery in {area['name']}.",
                "approach": f"Review {resource_types[0].lower()} for {area['name']} incorporating {vark_clean} learning techniques.",
                "practice_strategy": f"Complete targeted {resource_types[1].lower()} focusing on core edge cases."
            })

            url_info = get_verified_url_for_area(area["id"], domain_id)

            resources.append({
                "area_id": area["id"],
                "title": f"Comprehensive {domain_name} Guide: {area['name']}",
                "type": resource_types[0],
                "description": f"Structured material covering foundational concepts and key principles of {area['name']} in {domain_name}.",
                "url": url_info["url"],
                "why_recommended": f"Matches your {vark_clean} preference and targets your key learning gap in {area['name']}.",
                "verification_status": url_info["verification_status"]
            })

            practice_recs.append({
                "area_id": area["id"],
                "activity_type": resource_types[1],
                "description": f"Solve step-by-step problem sets on {area['name']} with immediate self-monitoring feedback.",
                "reason": f"Reinforces retention for low-mastery area ({int(m * 100)}%)."
            })

        # Extract Mastered Areas (strengths with mastery >= 0.7)
        mastered_areas = []
        for area in sorted_topics:
            if area["mastery"] >= 0.7:
                mastered_areas.append({
                    "area_id": area["id"],
                    "area_name": area["name"],
                    "mastery": area["mastery"]
                })

        summary_text = (
            f"Personalized learning plan for {domain_name}. Your overall mastery is {int(overall_mastery * 100)}%. "
            f"Based on your {vark_clean} learning modality and psychological profile, we recommend focusing on "
            f"{len(priority_areas)} priority areas starting with {sorted_topics[0]['name'] if sorted_topics else 'foundational concepts'}."
        )

        result = {
            "domain": {"id": domain_id, "name": domain_name},
            "overall_mastery": overall_mastery,
            "summary": summary_text,
            "mastered_areas": mastered_areas,
            "learner_approach": {
                "preferences_considered": prefs_considered,
                "recommended_approach": rec_approach,
                "reason": f"Tailored strategy combining {vark_clean} presentation with your self-regulation habits."
            },
            "priority_areas": priority_areas,
            "learning_sequence": learning_sequence,
            "resources": resources,
            "practice_recommendations": practice_recs
        }

        return validate_recommendation_json(result, domain_id)

class GeminiAIProvider(AIProvider):
    """
    AI Provider using Google Gemini REST API.
    Supports model fallback across gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-flash.
    Falls back to MockAIProvider if API key is missing or call fails.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("AI_API_KEY")
        self.fallback = MockAIProvider()

    def generate_structured_recommendation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        domain_id = input_data.get("learning_context", {}).get("domain", {}).get("id", "general")

        if not self.api_key:
            logger.info("No Gemini/AI API key found in environment. Using MockAIProvider fallback.")
            return self.fallback.generate_structured_recommendation(input_data)

        models_to_try = [
            os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"),
            "gemini-1.5-pro",
            "gemini-2.0-flash-exp",
            "gemini-2.5-flash"
        ]

        # De-duplicate model names while preserving order
        seen = set()
        models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

        import urllib.request
        import urllib.error

        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "parts": [{"text": f"Generate a domain-agnostic personalized learning recommendation for the following input data:\n{json.dumps(input_data, indent=2)}"}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }

        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=15) as response:
                    res_body = response.read().decode("utf-8")
                    res_json = json.loads(res_body)
                    raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # Clean potential markdown block wrappers if present
                    clean_text = raw_text.strip()
                    if clean_text.startswith("```json"):
                        clean_text = clean_text[7:]
                    if clean_text.startswith("```"):
                        clean_text = clean_text[3:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]

                    parsed = json.loads(clean_text.strip())
                    logger.info(f"Successfully generated recommendation using Gemini model: {model_name}")
                    return validate_recommendation_json(parsed, domain_id)

            except urllib.error.HTTPError as he:
                logger.warning(f"Gemini API model {model_name} failed with HTTP {he.code}: {he.reason}. Trying next model...")
                continue
            except Exception as e:
                logger.warning(f"Error calling Gemini API with model {model_name}: {e}. Trying next model...")
                continue

        logger.warning("All Gemini API models failed. Falling back to MockAIProvider.")
        return self.fallback.generate_structured_recommendation(input_data)

def get_ai_provider() -> AIProvider:
    """
    Factory function returning GeminiAIProvider if API key present, else MockAIProvider.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("AI_API_KEY")
    if api_key:
        return GeminiAIProvider(api_key=api_key)
    return MockAIProvider()
