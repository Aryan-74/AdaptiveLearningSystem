import json

from db import get_db

def normalize_likert(raw_score, reverse_scored=0):
    """
    Normalizes 1-5 Likert scale to 0.0 - 1.0.
    1 -> 0.00, 2 -> 0.25, 3 -> 0.50, 4 -> 0.75, 5 -> 1.00
    Reverse scored: 5 -> 0.00, 1 -> 1.00
    """
    norm = (float(raw_score) - 1.0) / 4.0
    if reverse_scored:
        norm = 1.0 - norm
    return round(norm, 4)

def process_survey_responses(student_id, raw_responses):
    """
    Processes raw survey responses (dict mapping question_id to raw_score 1..5).
    Saves raw responses to survey_responses table and calculates derived parameter means.
    Updates student_psychological_profile table.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get question metadata
    cursor.execute("SELECT question_id, parameter, reverse_scored FROM survey_questions;")
    questions_meta = {row["question_id"]: row for row in cursor.fetchall()}

    # Parameter lists to aggregate
    param_scores = {
        "VARK_visual": [],
        "VARK_aural": [],
        "VARK_read_write": [],
        "VARK_kinesthetic": [],
        "intrinsic_motivation": [],
        "extrinsic_motivation": [],
        "learning_goal_orientation": [],
        "task_value": [],
        "goal_setting": [],
        "planning": [],
        "self_monitoring": [],
        "revision_behavior": []
    }

    # Delete past responses for this student if re-taking survey
    cursor.execute("DELETE FROM survey_responses WHERE student_id = ?;", (student_id,))

    for qid, raw_val in raw_responses.items():
        if qid not in questions_meta:
            continue
        qmeta = questions_meta[qid]
        param = qmeta["parameter"]
        rev = qmeta["reverse_scored"]
        
        raw_score = int(raw_val)
        norm_score = normalize_likert(raw_score, rev)

        cursor.execute(
            """INSERT INTO survey_responses (student_id, question_id, raw_score, normalized_score)
               VALUES (?, ?, ?, ?);""",
            (student_id, qid, raw_score, norm_score)
        )

        if param in param_scores:
            param_scores[param].append(norm_score)

    # Compute parameter means
    derived = {}
    for param, scores in param_scores.items():
        if scores:
            derived[param] = round(sum(scores) / len(scores), 4)
        else:
            derived[param] = 0.0

    # Upsert into student_psychological_profile
    cursor.execute(
        """INSERT INTO student_psychological_profile (
            student_id, vark_visual, vark_aural, vark_read_write, vark_kinesthetic,
            intrinsic_motivation, extrinsic_motivation, learning_goal_orientation, task_value,
            goal_setting, planning, self_monitoring, revision_behavior, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(student_id) DO UPDATE SET
            vark_visual=excluded.vark_visual,
            vark_aural=excluded.vark_aural,
            vark_read_write=excluded.vark_read_write,
            vark_kinesthetic=excluded.vark_kinesthetic,
            intrinsic_motivation=excluded.intrinsic_motivation,
            extrinsic_motivation=excluded.extrinsic_motivation,
            learning_goal_orientation=excluded.learning_goal_orientation,
            task_value=excluded.task_value,
            goal_setting=excluded.goal_setting,
            planning=excluded.planning,
            self_monitoring=excluded.self_monitoring,
            revision_behavior=excluded.revision_behavior,
            updated_at=CURRENT_TIMESTAMP;""",
        (
            student_id,
            derived["VARK_visual"],
            derived["VARK_aural"],
            derived["VARK_read_write"],
            derived["VARK_kinesthetic"],
            derived["intrinsic_motivation"],
            derived["extrinsic_motivation"],
            derived["learning_goal_orientation"],
            derived["task_value"],
            derived["goal_setting"],
            derived["planning"],
            derived["self_monitoring"],
            derived["revision_behavior"]
        )
    )

    # Update student current step
    cursor.execute("UPDATE students SET current_step = 'knowledge_test' WHERE student_id = ?;", (student_id,))

    conn.commit()
    conn.close()
    return derived

def process_baseline_attempt(student_id, attempt_id, responses_data):
    """
    Processes baseline knowledge test responses for a specific attempt_id.
    Logs individual question interaction data to baseline_responses.
    Calculates overall, topic-wise, and KC-level performance.
    Saves snapshot to student_knowledge_profile.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Load questions metadata
    cursor.execute("SELECT question_id, topic_id, kc_id, difficulty, correct_answer FROM knowledge_questions;")
    questions_meta = {row["question_id"]: row for row in cursor.fetchall()}

    total_questions = 0
    correct_count = 0

    topic_totals = {}
    topic_correct = {}

    kc_totals = {}
    kc_correct = {}

    for item in responses_data:
        qid = item.get("question_id")
        sel_ans = item.get("selected_answer", "").strip()
        resp_time = float(item.get("response_time_seconds", 0.0))

        if qid not in questions_meta:
            continue

        qmeta = questions_meta[qid]
        topic_id = qmeta["topic_id"]
        kc_id = qmeta["kc_id"]
        difficulty = qmeta["difficulty"]
        correct_ans = qmeta["correct_answer"].strip()

        is_correct = 1 if sel_ans == correct_ans else 0

        # Log individual response
        cursor.execute(
            """INSERT INTO baseline_responses 
               (attempt_id, student_id, question_id, topic_id, kc_id, selected_answer, correct, difficulty, response_time_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (attempt_id, student_id, qid, topic_id, kc_id, sel_ans, is_correct, difficulty, resp_time)
        )

        total_questions += 1
        correct_count += is_correct

        # Aggregate per topic
        topic_totals[topic_id] = topic_totals.get(topic_id, 0) + 1
        topic_correct[topic_id] = topic_correct.get(topic_id, 0) + is_correct

        # Aggregate per KC
        kc_totals[kc_id] = kc_totals.get(kc_id, 0) + 1
        kc_correct[kc_id] = kc_correct.get(kc_id, 0) + is_correct

    overall_score = round(correct_count / total_questions, 4) if total_questions > 0 else 0.0

    # Update attempt summary
    cursor.execute(
        """UPDATE baseline_attempts 
           SET completed_at = CURRENT_TIMESTAMP, total_questions = ?, correct_count = ?, overall_score = ?
           WHERE attempt_id = ?;""",
        (total_questions, correct_count, overall_score, attempt_id)
    )

    # Compute topic scores
    topic_scores = {}
    for tid, t_total in topic_totals.items():
        c = topic_correct.get(tid, 0)
        topic_scores[tid] = round(c / t_total, 4)

    # Compute KC scores
    kc_scores = {}
    for kcid, k_total in kc_totals.items():
        c = kc_correct.get(kcid, 0)
        kc_scores[kcid] = round(c / k_total, 4)

    # Save to student_knowledge_profile
    cursor.execute(
        """INSERT INTO student_knowledge_profile (student_id, attempt_id, overall_performance, topic_scores, kc_scores)
           VALUES (?, ?, ?, ?, ?);""",
        (student_id, attempt_id, overall_score, json.dumps(topic_scores), json.dumps(kc_scores))
    )

    # Update student step to completed
    cursor.execute("UPDATE students SET current_step = 'completed' WHERE student_id = ?;", (student_id,))

    conn.commit()
    conn.close()

    return {
        "attempt_id": attempt_id,
        "overall_performance": overall_score,
        "correct_count": correct_count,
        "total_questions": total_questions,
        "topic_scores": topic_scores,
        "kc_scores": kc_scores
    }
