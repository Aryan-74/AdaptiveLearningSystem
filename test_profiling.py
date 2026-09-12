import unittest
import os
import json
import sqlite3
from db import init_db, get_db, DB_PATH
from seed_data import seed_database
from profiling_engine import normalize_likert, process_survey_responses, process_baseline_attempt

class TestStudentProfilingModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except Exception:
                pass
        init_db()
        seed_database()

    def test_01_likert_normalization(self):
        self.assertEqual(normalize_likert(1), 0.0)
        self.assertEqual(normalize_likert(2), 0.25)
        self.assertEqual(normalize_likert(3), 0.50)
        self.assertEqual(normalize_likert(4), 0.75)
        self.assertEqual(normalize_likert(5), 1.00)
        # Reverse scored
        self.assertEqual(normalize_likert(5, reverse_scored=1), 0.0)
        self.assertEqual(normalize_likert(1, reverse_scored=1), 1.0)

    def test_02_survey_processing(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO students (student_id, name, email, password_hash) VALUES ('STU-TEST1', 'Test Student', 'test1@test.com', 'hash');")
        conn.commit()
        conn.close()

        # Simulate 24 survey responses
        responses = {
            "VARK_V1": 5, "VARK_V2": 4, # Visual mean = (1.0 + 0.75)/2 = 0.875
            "VARK_A1": 2, "VARK_A2": 3, # Aural mean = (0.25 + 0.50)/2 = 0.375
            "VARK_R1": 4, "VARK_R2": 4, # Read/Write mean = 0.75
            "VARK_K1": 1, "VARK_K2": 2, # Kinesthetic mean = (0 + 0.25)/2 = 0.125
            "MOT_INT1": 5, "MOT_INT2": 5, # Intrinsic = 1.0
            "MOT_EXT1": 3, "MOT_EXT2": 3, # Extrinsic = 0.5
            "MOT_LGO1": 4, "MOT_LGO2": 4, # LGO = 0.75
            "MOT_TV1": 5, "MOT_TV2": 4,  # Task value = 0.875
            "SR_GS1": 4, "SR_GS2": 4,    # Goal setting = 0.75
            "SR_PL1": 3, "SR_PL2": 3,    # Planning = 0.50
            "SR_SM1": 5, "SR_SM2": 5,    # Self monitoring = 1.00
            "SR_RB1": 2, "SR_RB2": 2     # Revision = 0.25
        }

        derived = process_survey_responses("STU-TEST1", responses)

        self.assertEqual(derived["VARK_visual"], 0.875)
        self.assertEqual(derived["VARK_aural"], 0.375)
        self.assertEqual(derived["intrinsic_motivation"], 1.0)
        self.assertEqual(derived["self_monitoring"], 1.0)

        # Check DB persistence
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM student_psychological_profile WHERE student_id = 'STU-TEST1';")
        prof = cursor.fetchone()
        self.assertIsNotNone(prof)
        self.assertEqual(prof["vark_visual"], 0.875)
        conn.close()

    def test_03_baseline_test_processing(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO students (student_id, name, email, password_hash) VALUES ('STU-TEST2', 'Test Student 2', 'test2@test.com', 'hash');")
        cursor.execute("INSERT OR REPLACE INTO baseline_attempts (attempt_id, student_id) VALUES ('ATT-TEST1', 'STU-TEST2');")
        
        # Get questions
        cursor.execute("SELECT question_id, correct_answer FROM knowledge_questions;")
        questions = cursor.fetchall()
        conn.commit()
        conn.close()

        responses_data = []
        # Answer half correctly, half incorrectly
        for i, q in enumerate(questions):
            ans = q["correct_answer"] if i % 2 == 0 else "WRONG_ANSWER"
            responses_data.append({
                "question_id": q["question_id"],
                "selected_answer": ans,
                "response_time_seconds": 15.5
            })

        results = process_baseline_attempt("STU-TEST2", "ATT-TEST1", responses_data)
        
        self.assertEqual(results["total_questions"], len(questions))
        self.assertEqual(results["correct_count"], len(questions) // 2)
        self.assertAlmostEqual(results["overall_performance"], 0.5, places=2)

        # Verify interaction logging in DB
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM baseline_responses WHERE attempt_id = 'ATT-TEST1';")
        resp_count = cursor.fetchone()[0]
        self.assertEqual(resp_count, len(questions))

        # Verify Knowledge Profile snapshot in DB
        cursor.execute("SELECT * FROM student_knowledge_profile WHERE attempt_id = 'ATT-TEST1';")
        kp = cursor.fetchone()
        self.assertIsNotNone(kp)
        self.assertAlmostEqual(kp["overall_performance"], 0.5, places=2)
        conn.close()

if __name__ == '__main__':
    unittest.main()
