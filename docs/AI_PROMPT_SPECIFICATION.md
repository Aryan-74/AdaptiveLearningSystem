# AI Prompt & Output Specification (V2)

## 1. Generalized System Prompt

```text
You are an AI-powered personalized learning recommendation engine.

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
6. Return strictly VALID JSON following the specified schema without Markdown code fences or raw text wrapper.
```

---

## 2. Structured Input Schema

```json
{
    "learning_context": {
        "domain": {
            "id": "python",
            "name": "Python Programming",
            "description": "Programming using the Python language"
        },
        "learning_goal": {
            "type": "conceptual_understanding",
            "description": "Targeting Conceptual Understanding for python"
        },
        "curriculum": {
            "domain_id": "python",
            "areas": [
                {
                    "id": "variables",
                    "name": "Variables",
                    "type": "topic",
                    "description": "Storing, naming, and reassigning data values in memory",
                    "parent_id": null,
                    "prerequisites": []
                }
            ]
        }
    },
    "student": {
        "student_id": "STU-12345678",
        "student_name": "Jane Student",
        "learner_profile": {
            "vark": {
                "vark_visual": 0.875,
                "vark_aural": 0.375,
                "vark_read_write": 0.75,
                "vark_kinesthetic": 0.125
            },
            "motivation": {
                "intrinsic_motivation": 1.0,
                "extrinsic_motivation": 0.5,
                "learning_goal_orientation": 0.75,
                "task_value": 0.875
            },
            "self_regulation": {
                "goal_setting": 0.75,
                "planning": 0.5,
                "self_monitoring": 1.0,
                "revision_behavior": 0.25
            }
        },
        "knowledge_profile": {
            "domain_id": "python",
            "overall_mastery": 0.5,
            "areas": [
                {
                    "id": "variables",
                    "name": "Variables",
                    "type": "topic",
                    "mastery": 0.35
                }
            ]
        }
    }
}
```

---

## 3. Strict Output JSON Schema

```json
{
    "domain": {
        "id": "python",
        "name": "Python Programming"
    },
    "summary": "Executive summary explaining prioritized areas based on mastery and learner traits.",
    "learner_approach": {
        "preferences_considered": ["Visual Learner Preference", "High Intrinsic Motivation"],
        "recommended_approach": ["Incorporate diagrams and visual aids", "Use visual step-by-step concept maps"],
        "reason": "Tailored strategy combining Visual presentation with self-regulation habits."
    },
    "priority_areas": [
        {
            "area_id": "variables",
            "area_name": "Variables",
            "mastery": 0.35,
            "priority": "very_high",
            "reason": "Mastery level is currently at 35%. Focusing on this area establishes essential foundational competence.",
            "prerequisites": [],
            "recommended_approach": ["Incorporate diagrams and visual aids"],
            "recommended_resource_types": ["Documentation", "Coding Exercises"]
        }
    ],
    "learning_sequence": [
        {
            "step": 1,
            "area_id": "variables",
            "area_name": "Variables",
            "objective": "Achieve > 75% mastery in Variables.",
            "approach": "Review documentation for Variables incorporating Visual learning techniques.",
            "practice_strategy": "Complete targeted coding exercises focusing on core edge cases."
        }
    ],
    "resources": [
        {
            "area_id": "variables",
            "title": "Comprehensive Python Programming Guide: Variables",
            "type": "Documentation",
            "description": "Structured material covering foundational concepts of Variables.",
            "url": null,
            "why_recommended": "Matches your Visual preference and targets low mastery.",
            "verification_status": "unverified"
        }
    ],
    "practice_recommendations": [
        {
            "area_id": "variables",
            "activity_type": "Coding Exercises",
            "description": "Solve step-by-step problem sets on Variables.",
            "reason": "Reinforces retention for low-mastery area (35%)."
        }
    ]
}
```

---

## 4. Multi-Domain Generalization Rules
1. **WHAT TO LEARN**: Determined by knowledge profile mastery levels, curriculum dependencies, and learning goals.
2. **HOW TO LEARN**: Determined by psychological learner profile signals (VARK modalities, intrinsic/extrinsic motivation, goal setting, planning, self-monitoring, revision behavior).
3. **RESOURCE TYPES BY DOMAIN**:
   - **Programming Domains**: Documentation, Coding Exercises, Tutorials, Project Specifications.
   - **Mathematical Domains**: Worked Problems, Concept Explanations, Step-by-Step Proofs, Practice Sets.
   - **Physical/Natural Science Domains**: Interactive Simulations, Worked Physics Problems, Textbook References, Lab Experiments.
   - **General/Liberal Arts Domains**: Case Studies, Primary Source Documents, Structured Reading Notes, Analytical Essays.
