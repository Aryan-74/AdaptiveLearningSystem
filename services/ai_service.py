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
from services.resource_service import retrieve_real_resources_for_area, validate_resource_url

logger = logging.getLogger(__name__)

class AIGenerationError(Exception):
    """
    Raised when AI generation fails. Prevents fake fallback recommendations.
    """
    def __init__(self, message: str = "Unable to generate your personalized learning plan.", code: str = "AI_GENERATION_FAILED"):
        super().__init__(message)
        self.message = message
        self.code = code

SYSTEM_PROMPT = """You are an AI-powered personalized learning recommendation engine for an Adaptive Learning System.

You receive information about a learner, their current learning domain, their assessed knowledge state (mastery levels), their learner preferences (VARK modalities, motivation, self-regulation), and their available curriculum information.

Your task is to analyze this data and generate a structured, personalized learning recommendation plan.

CRITICAL ARCHITECTURAL RULES:
1. DOMAIN AGNOSTIC: The learning domain is provided dynamically (e.g. Python, Mathematics, Physics, etc.). Do NOT assume a specific subject. Adapt all recommendation terms, strategies, and resource types to the supplied domain context.
2. DYNAMIC REASONING: Reason dynamically about topic priorities based on current mastery scores, prerequisite relationships, foundational importance, and the student's learning goal.
3. NO MECHANICAL REPETITION: Do NOT use mechanical sentence templates for learning sequence approaches (e.g., do NOT repeat "Review documentation for [TOPIC] incorporating [MODALITY] learning techniques" across multiple steps). The learning approach for each area MUST vary based on the specific concept, student mastery level, learner preferences, and domain nature.
4. RESOURCE UNIQUENESS & REALISM:
   - Do NOT construct fake resource titles by putting the topic name into a generic template like "Comprehensive [DOMAIN] Guide: [TOPIC]".
   - Every resource must be topic-specific and tailored to the student's need.
   - DO NOT fabricate URLs! Set "url": null and "verification_status": "unverified" for suggested resources unless a verified URL is provided.
   - Vary resource types naturally (e.g., Documentation, Interactive Tutorial, Worked Problems, Textbook Reference, Simulation, Video, Practice Set).
5. VARK AS PREFERENCE SIGNAL: Treat VARK modalities as preference signals (e.g., "Your profile indicates a stronger preference for visual explanations"), NOT as rigid labels ("You are a Visual Learner").
6. VARIABILITY IN PRACTICE ACTIVITIES: Practice recommendations MUST match the student's mastery level (e.g. low mastery = foundational practice/guided worked examples; moderate = problem solving/debugging; high = project/challenging applications).
7. STRICT JSON SCHEMA: Return strictly VALID JSON following the specified schema without Markdown code fences or extra text wrapper.

OUTPUT JSON SCHEMA:
{
    "domain": {
        "id": "<domain_id>",
        "name": "<domain_name>"
    },
    "overall_mastery": 0.0,
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
            "reason": "<specific rationale for why this area is prioritized>",
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
            "approach": "<varied study method>",
            "practice_strategy": "<practice method>"
        }
    ],
    "resources": [
        {
            "title": "<resource title>",
            "type": "Video | Documentation | Tutorial | Article | Worked Example | Exercise | Case Study | Reference",
            "source": "<publisher or source>",
            "url": "<verified http/https URL>",
            "reason": "<why recommended for student>"
        }
    ],
    "practice_recommendations": [
        {
            "area_id": "<topic_id>",
            "activity_type": "<exercise type>",
            "description": "<activity description>",
            "reason": "<rationale matching mastery level>"
        }
    ]
}"""

class AIProvider(ABC):
    @abstractmethod
    def generate_structured_recommendation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

class MockAIProvider(AIProvider):
    """
    Offline AI Provider used exclusively in explicit test fixtures.
    Generates dynamic domain-agnostic recommendation structures based on input context.
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

        # Map knowledge areas
        k_areas = k_profile.get("areas", [])
        mastery_map = {item.get("id"): item.get("mastery", 0.0) for item in k_areas}

        # Group curriculum into high-level topics
        topic_areas = [a for a in areas if a.get("type") == "topic"]
        if not topic_areas:
            topic_areas = areas

        sorted_topics = []
        for area in topic_areas:
            tid = area.get("id")
            tname = area.get("name", tid)
            m_score = mastery_map.get(tid)
            child_kcs = [a.get("name") for a in areas if a.get("parent_id") == tid]
            sorted_topics.append({
                "id": tid,
                "name": tname,
                "mastery": m_score,
                "description": area.get("description", ""),
                "sub_concepts": child_kcs
            })

        sorted_topics.sort(key=lambda x: x["mastery"] if x["mastery"] is not None else 999.0)

        # Determine learner approach signals
        vark = l_profile.get("vark", {})
        mot = l_profile.get("motivation", {})
        sr = l_profile.get("self_regulation", {})

        top_vark = max(vark.items(), key=lambda x: x[1])[0] if vark else "vark_visual"
        vark_clean = top_vark.replace("vark_", "").capitalize()

        prefs_considered = [f"Preference for {vark_clean} learning modality"]
        rec_approach = []
        if "visual" in top_vark.lower():
            rec_approach.extend(["Incorporate diagrams and visual concept maps", "Study graphical walkthroughs"])
        elif "aural" in top_vark.lower():
            rec_approach.extend(["Listen to audio explanations", "Verbalize concepts aloud"])
        elif "read" in top_vark.lower():
            rec_approach.extend(["Read structured documentation", "Write concise summary notes"])
        else:
            rec_approach.extend(["Engage in hands-on practical exercises", "Build interactive trial applications"])

        if mot.get("intrinsic_motivation", 0.0) >= 0.6:
            prefs_considered.append("High intrinsic interest in underlying principles")
        if sr.get("goal_setting", 0.0) >= 0.6:
            prefs_considered.append("Structured goal-setting habits")

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

        priority_areas = []
        learning_sequence = []
        resources = []
        practice_recs = []

        # Distinct sequence tactics per step to avoid mechanical repetition
        sequence_tactics = [
            ("Foundational Overview", "Focus on core principles and worked examples"),
            ("Guided Practice", "Solve step-by-step problem sets with hints"),
            ("Practical Application", "Implement hands-on scenarios and edge cases"),
            ("Synthesis & Review", "Complete comprehensive review problems and self-explanation tasks")
        ]

        for idx, area in enumerate(sorted_topics[:4], start=1):
            m = area["mastery"]
            m_num = m if m is not None else 0.5
            p_level = "very_high" if m_num < 0.4 else ("high" if m_num < 0.7 else "medium")
            reason = f"Current assessed mastery is {int(m_num * 100)}%. Reinforcing {area['name']} establishes essential foundational competence for subsequent topics." if m is not None else f"Reinforcing {area['name']} establishes essential foundational competence."
            if idx == 1 and goal_desc:
                reason += f" Directly supports your goal: '{goal_desc}'."

            tactic_title, tactic_desc = sequence_tactics[(idx - 1) % len(sequence_tactics)]

            priority_areas.append({
                "area_id": area["id"],
                "area_name": area["name"],
                "mastery": m,
                "priority": p_level,
                "reason": reason,
                "sub_concepts": area.get("sub_concepts", []),
                "prerequisites": [],
                "recommended_approach": [tactic_desc],
                "recommended_resource_types": resource_types[:2]
            })

            learning_sequence.append({
                "step": idx,
                "area_id": area["id"],
                "area_name": area["name"],
                "objective": f"Achieve > 75% mastery in {area['name']}.",
                "approach": f"{tactic_title}: {tactic_desc} tailored for {area['name']}.",
                "practice_strategy": f"Targeted practice on {area['name']} focusing on key edge cases."
            })

            real_res = retrieve_real_resources_for_area(area["id"], domain_id)
            if real_res:
                resources.extend(real_res)

            practice_recs.append({
                "area_id": area["id"],
                "activity_type": resource_types[1],
                "description": f"Practice activity tailored to {area['name']} with self-monitoring feedback.",
                "reason": f"Matches assessed mastery level ({int(m_num * 100)}%)." if m is not None else "Targeted practice for core curriculum concept."
            })

        mastered_areas = [
            {"area_id": a["id"], "area_name": a["name"], "mastery": a["mastery"]}
            for a in sorted_topics if a["mastery"] is not None and a["mastery"] >= 0.7
        ]

        summary_text = (
            f"Personalized learning plan for {domain_name}. Overall domain mastery is {int(overall_mastery * 100)}%. "
            f"Your profile indicates a preference for {vark_clean} learning modality. "
            f"We recommend focusing on {len(priority_areas)} priority areas starting with {sorted_topics[0]['name'] if sorted_topics else 'foundational concepts'}."
        )

        result = {
            "domain": {"id": domain_id, "name": domain_name},
            "overall_mastery": overall_mastery,
            "summary": summary_text,
            "mastered_areas": mastered_areas,
            "learner_approach": {
                "preferences_considered": prefs_considered,
                "recommended_approach": rec_approach,
                "reason": f"Tailored strategy balancing {vark_clean} preference with structured self-regulation."
            },
            "priority_areas": priority_areas,
            "learning_sequence": learning_sequence,
            "resources": resources,
            "practice_recommendations": practice_recs,
            "_model_name": "MockAIProvider"
        }

        return validate_recommendation_json(result, domain_id, snapshot=student, curriculum=curriculum)

class GeminiAIProvider(AIProvider):
    """
    Production AI Provider using Google Gemini REST API.
    Supports model fallback across active models: gemini-3.6-flash, gemini-3.5-flash, gemini-flash-latest, gemini-3.1-flash-lite.
    Enforces Strict No-Fake-AI-Success Rule: raises AIGenerationError if API key missing or calls fail.
    """
    def __init__(self, api_key: Optional[str] = None):
        # If api_key parameter is explicitly passed (even if "" or None in direct testing), respect it; otherwise read from env.
        self.api_key = api_key if api_key is not None else (os.environ.get("GEMINI_API_KEY") or os.environ.get("AI_API_KEY"))

    def generate_structured_recommendation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        context = input_data.get("learning_context", {})
        domain = context.get("domain", {})
        domain_id = domain.get("id", "general")
        student = input_data.get("student", {})
        curriculum = context.get("curriculum", {})

        logger.info(f"[AI DEBUG] Generation requested for Student ID: '{student.get('student_id', 'unknown')}'")
        logger.info(f"[AI DEBUG] Domain: '{domain_id}', Goal: '{context.get('learning_goal', {}).get('type', 'general')}'")
        logger.info(f"[AI DEBUG] Profile loaded: {bool(student.get('learner_profile'))}")
        logger.info(f"[AI DEBUG] Knowledge profile loaded: {bool(student.get('knowledge_profile'))}")

        if not self.api_key:
            logger.error("[AI DEBUG] API key configured: false. Raising AIGenerationError.")
            raise AIGenerationError(
                message="AI API key is not configured. Unable to generate personalized learning plan.",
                code="AI_GENERATION_FAILED"
            )

        logger.info("[AI DEBUG] API key configured: true")

        models_to_try = [
            os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
            "gemini-3.6-flash",
            "gemini-flash-latest",
            "gemini-3.1-flash-lite"
        ]

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
                    "parts": [{"text": f"Generate a personalized learning recommendation JSON for the following input data:\n{json.dumps(input_data, indent=2)}"}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }

        logger.info("[AI DEBUG] Prompt constructed: true")

        last_error_msg = ""
        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            safe_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            logger.info(f"[AI DEBUG] Calling AI provider endpoint: {safe_endpoint}")
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=30) as response:
                    res_body = response.read().decode("utf-8")
                    res_status = response.status
                    logger.info(f"[AI DEBUG] Provider response status: {res_status} OK")
                    logger.info(f"[AI DEBUG] Provider response received: true for model '{model_name}'")

                    res_json = json.loads(res_body)
                    raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"\n[AI RAW DEBUG] Gemini text snippet: {raw_text[:300]}")

                    import re
                    json_match = re.search(r'(\{[\s\S]*\})', raw_text)
                    clean_text = json_match.group(1) if json_match else raw_text.strip()

                    parsed = json.loads(clean_text)
                    print(f"[AI RAW DEBUG] Parsed object type: {type(parsed)}")

                    if isinstance(parsed, list) and len(parsed) > 0:
                        parsed = parsed[0]
                    if isinstance(parsed, dict) and "recommendation" in parsed and isinstance(parsed["recommendation"], dict):
                        parsed = parsed["recommendation"]

                    parsed["_model_name"] = model_name
                    logger.info(f"[AI DEBUG] Successfully parsed structured JSON output from Gemini model: {model_name}")
                    
                    return validate_recommendation_json(parsed, domain_id, snapshot=student, curriculum=curriculum)

            except urllib.error.HTTPError as he:
                last_error_msg = f"HTTP {he.code}: {he.reason}"
                logger.warning(f"[AI DEBUG] Provider model '{model_name}' returned status: {last_error_msg}. Trying next model...")
                if he.code == 429:
                    import time
                    time.sleep(2)
                continue
            except Exception as e:
                last_error_msg = str(e)
                logger.warning(f"[AI DEBUG] Error calling provider model '{model_name}': {e}. Trying next model...")
                continue

        logger.error(f"[AI DEBUG] All Gemini API models failed. Last error: {last_error_msg}")
        raise AIGenerationError(
            message=f"Unable to generate personalized learning plan via AI. Details: {last_error_msg}",
            code="AI_GENERATION_FAILED"
        )

def get_ai_provider(force_mock: bool = False) -> AIProvider:
    """
    Factory function returning GeminiAIProvider by default.
    Returns MockAIProvider ONLY if force_mock=True is explicitly requested for offline unit tests.
    """
    if force_mock:
        return MockAIProvider()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("AI_API_KEY")
    return GeminiAIProvider(api_key=api_key)
