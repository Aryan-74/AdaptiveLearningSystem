# AI Personalized Recommendation Engine Architecture (V2)

## 1. Executive Overview
The **AI Personalized Recommendation Engine (V2)** is a modular, domain-agnostic recommendation service for the Adaptive Learning System. It synthesizes a student's psychological learner profile (VARK modalities, motivation, self-regulation) with their domain-specific knowledge state and dynamic curriculum hierarchy to generate a personalized learning plan.

Crucially, **the recommendation engine contains zero hardcoded subject rules**. The learning domain is passed strictly as dynamic input context (`python`, `mathematics`, `physics`, etc.), allowing the exact same backend service and AI prompts to serve any learning domain.

---

## 2. High-Level Architecture & Data Flow

```
Student
   │
   ├── Student Psychological Profile (VARK, Motivation, Self-Regulation)
   └── Student Knowledge Profile (Overall & Topic/KC Mastery)
            +
   Current Learning Context (Domain ID, Name, Description, Curriculum Hierarchy, Learning Goal)
            │
            ▼
     Recommendation Service (`services/recommendation_service.py`)
            │
            ├─► Profile Service (`services/profile_service.py`)
            ├─► Knowledge Service (`services/knowledge_service.py`)
            └─► Resource Service (`services/resource_service.py`)
            │
            ▼
     AI Provider Abstraction (`AIProvider` / `GeminiAIProvider` / `MockAIProvider`)
            │
            ▼
     Structured JSON Validation & Resource URL Accuracy Verification (`models/recommendation.py`)
            │
            ▼
     Database Persistence (`recommendations` table with profile snapshot)
            │
            ▼
     Dynamic UI View (`templates/recommendations.html`)
```

---

## 3. Core Modules & Service Responsibilities

### `models/` Layer
* **`models/domain.py`**: Encapsulates `Domain` metadata (`id`, `name`, `description`).
* **`models/curriculum.py`**: Generalized curriculum tree structure (`CurriculumArea` topics, concepts, skills, parent IDs, prerequisites).
* **`models/student.py`**: Unified student profile snapshot (`LearnerProfile`, `KnowledgeProfile`, `KnowledgeAreaScore`, `StudentSnapshot`).
* **`models/recommendation.py`**: Strict schema validator and normalizer for AI recommendation JSON outputs.

### `services/` Layer
* **`services/ai_service.py`**:
  * Abstract base class `AIProvider`.
  * `GeminiAIProvider`: Connects to Google Gemini API via `GEMINI_API_KEY` or `AI_API_KEY`.
  * `MockAIProvider`: Rule-assisted offline engine providing deterministic, high-quality, domain-agnostic structured JSON recommendations when API keys are absent or network errors occur.
* **`services/profile_service.py`**: Fetches student psychological traits and domain-specific knowledge state from database.
* **`services/knowledge_service.py`**: Fetches registered domains and domain curriculum trees.
* **`services/resource_service.py`**: Validates URL strings to prevent AI link hallucination and maps domain-appropriate resource types.
* **`services/recommendation_service.py`**: Core pipeline orchestrator (`generate_learning_recommendation`, `get_latest_recommendation`, `get_recommendation_history`).

---

## 4. Database Schema

### `domains` Table
```sql
CREATE TABLE IF NOT EXISTS domains (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);
```

### `recommendations` Table
```sql
CREATE TABLE IF NOT EXISTS recommendations (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_name TEXT NOT NULL,
    learning_goal TEXT,
    profile_snapshot TEXT NOT NULL, -- Full JSON snapshot of learner + knowledge state
    recommendation_json TEXT NOT NULL, -- Strict JSON recommendation output
    status TEXT NOT NULL DEFAULT 'completed',
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);
```

---

## 5. Security & Graceful Error Handling
* **API Credentials**: Stored securely server-side in environment variables (`GEMINI_API_KEY`). Never exposed to client JS.
* **URL Hallucination Guard**: All resource URLs returned by AI are inspected by `resource_service.validate_resource_url`. Unverified URLs are converted to `null` with `verification_status: "unverified"`.
* **Fallback Guarantee**: If external AI calls fail or time out, `GeminiAIProvider` automatically falls back to `MockAIProvider`, guaranteeing zero runtime crashes or broken UI states for students.
