import json
from typing import Dict, Any, Optional

from db import get_db
from models.student import LearnerProfile, KnowledgeProfile, KnowledgeAreaScore, StudentSnapshot

def get_learner_profile(student_id: str) -> LearnerProfile:
    """
    Retrieves psychological/learner characteristics profile for student.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_psychological_profile WHERE student_id = ?;", (student_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return LearnerProfile(
            vark={"vark_visual": 0.5, "vark_aural": 0.5, "vark_read_write": 0.5, "vark_kinesthetic": 0.5},
            motivation={"intrinsic_motivation": 0.5, "extrinsic_motivation": 0.5, "learning_goal_orientation": 0.5, "task_value": 0.5},
            self_regulation={"goal_setting": 0.5, "planning": 0.5, "self_monitoring": 0.5, "revision_behavior": 0.5}
        )

    p = dict(row)
    return LearnerProfile(
        vark={
            "vark_visual": float(p.get("vark_visual", 0.0)),
            "vark_aural": float(p.get("vark_aural", 0.0)),
            "vark_read_write": float(p.get("vark_read_write", 0.0)),
            "vark_kinesthetic": float(p.get("vark_kinesthetic", 0.0))
        },
        motivation={
            "intrinsic_motivation": float(p.get("intrinsic_motivation", 0.0)),
            "extrinsic_motivation": float(p.get("extrinsic_motivation", 0.0)),
            "learning_goal_orientation": float(p.get("learning_goal_orientation", 0.0)),
            "task_value": float(p.get("task_value", 0.0))
        },
        self_regulation={
            "goal_setting": float(p.get("goal_setting", 0.0)),
            "planning": float(p.get("planning", 0.0)),
            "self_monitoring": float(p.get("self_monitoring", 0.0)),
            "revision_behavior": float(p.get("revision_behavior", 0.0))
        }
    )

def get_knowledge_profile(student_id: str, domain_id: str) -> KnowledgeProfile:
    """
    Retrieves student knowledge profile for a specific domain.
    Reads latest assessment attempt or maps domain topics & KCs.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get domain topics and KCs
    cursor.execute("SELECT topic_id, topic_name FROM knowledge_topics WHERE domain_id = ?;", (domain_id,))
    topics = cursor.fetchall()
    topic_map = {t["topic_id"]: t["topic_name"] for t in topics}

    cursor.execute("""
        SELECT k.kc_id, k.kc_name, k.topic_id 
        FROM knowledge_components k
        JOIN knowledge_topics t ON k.topic_id = t.topic_id
        WHERE t.domain_id = ?;
    """, (domain_id,))
    kcs = cursor.fetchall()
    kc_map = {k["kc_id"]: k["kc_name"] for k in kcs}

    # Get latest knowledge profile snapshot for student
    cursor.execute("""
        SELECT overall_performance, topic_scores, kc_scores 
        FROM student_knowledge_profile 
        WHERE student_id = ? 
        ORDER BY calculated_at DESC LIMIT 1;
    """, (student_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        area_scores = [
            KnowledgeAreaScore(id=tid, name=tname, type="topic", mastery=None)
            for tid, tname in topic_map.items()
        ] + [
            KnowledgeAreaScore(id=kcid, name=kname, type="concept", mastery=None)
            for kcid, kname in kc_map.items()
        ]
        return KnowledgeProfile(domain_id=domain_id, overall_mastery=0.0, areas=area_scores)

    overall_mastery = float(row["overall_performance"])
    t_scores = json.loads(row["topic_scores"]) if row["topic_scores"] else {}
    k_scores = json.loads(row["kc_scores"]) if row["kc_scores"] else {}

    area_scores = []
    domain_topic_masteries = []
    # Include topics belonging to this domain
    for tid, tname in topic_map.items():
        if tid in t_scores:
            m = float(t_scores[tid])
            domain_topic_masteries.append(m)
        else:
            m = None
        area_scores.append(KnowledgeAreaScore(id=tid, name=tname, type="topic", mastery=m))

    # Include KCs belonging to this domain
    for kcid, kname in kc_map.items():
        if kcid in k_scores:
            m = float(k_scores[kcid])
        else:
            m = None
        area_scores.append(KnowledgeAreaScore(id=kcid, name=kname, type="concept", mastery=m))

    # Compute domain-specific overall mastery if assessed domain topics exist
    if domain_topic_masteries:
        domain_overall = round(sum(domain_topic_masteries) / len(domain_topic_masteries), 4)
    else:
        domain_overall = 0.0

    return KnowledgeProfile(
        domain_id=domain_id,
        overall_mastery=domain_overall,
        areas=area_scores
    )

def serialize_knowledge_profile(student_id: str, domain_id: str) -> Dict[str, Any]:
    """
    Single source of truth serialization for student knowledge profile.
    Used across Dashboard, AI Prompt, Recommendation Generation, and UI.
    """
    return get_knowledge_profile(student_id, domain_id).to_dict()

def serialize_learner_profile(student_id: str) -> Dict[str, Any]:
    """
    Single source of truth serialization for psychological/learner characteristics profile.
    """
    return get_learner_profile(student_id).to_dict()

def get_student_snapshot(student_id: str, domain_id: str) -> StudentSnapshot:
    """
    Constructs full student snapshot combining student name, learner profile, and domain knowledge profile.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM students WHERE student_id = ?;", (student_id,))
    row = cursor.fetchone()
    conn.close()

    name = row["name"] if row else "Student"
    l_prof = get_learner_profile(student_id)
    k_prof = get_knowledge_profile(student_id, domain_id)

    return StudentSnapshot(
        student_id=student_id,
        student_name=name,
        learner_profile=l_prof,
        knowledge_profile=k_prof
    )

