import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import init_db, get_db
from services.recommendation_service import generate_learning_recommendation

class TestCompleteAdaptiveResources(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.student_id = "STU-FULL-ADAPT"
        self.domain_id = "python"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO students (student_id, name, email, password_hash) VALUES (?, 'Full Adaptive Student', 'fulladapt@test.com', 'hash');", (self.student_id,))
        cursor.execute("DELETE FROM student_psychological_profile WHERE student_id = ?", (self.student_id,))
        cursor.execute("DELETE FROM student_knowledge_profile WHERE student_id = ?", (self.student_id,))
        cursor.execute("DELETE FROM recommendations WHERE student_id = ?", (self.student_id,))
        conn.commit()
        conn.close()

    def set_student_state(self, visual=0.5, aural=0.5, read_write=0.5, kinesthetic=0.5, topic_scores=None):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO student_psychological_profile (
                student_id, vark_visual, vark_aural, vark_read_write, vark_kinesthetic,
                intrinsic_motivation, extrinsic_motivation, learning_goal_orientation, task_value,
                goal_setting, planning, self_monitoring, revision_behavior
            ) VALUES (?, ?, ?, ?, ?, 0.8, 0.4, 0.9, 0.8, 0.7, 0.6, 0.8, 0.7);
        """, (self.student_id, visual, aural, read_write, kinesthetic))
        
        t_json = json.dumps(topic_scores or {})
        cursor.execute("INSERT OR IGNORE INTO baseline_attempts (attempt_id, student_id) VALUES ('ATTEMPT-FULL-ADAPT', ?);", (self.student_id,))
        cursor.execute("""
            INSERT INTO student_knowledge_profile (student_id, attempt_id, overall_performance, topic_scores, kc_scores)
            VALUES (?, 'ATTEMPT-FULL-ADAPT', 0.3, ?, '{}');
        """, (self.student_id, t_json))
        conn.commit()
        conn.close()

    def print_test_results(self, test_name, goal, resources):
        print(f"\n==========================================")
        print(f"{test_name}")
        print(f"Goal: {goal['description']}")
        print(f"Total Returned Resources: {len(resources)}")
        print(f"==========================================")
        for idx, r in enumerate(resources, start=1):
            ch = f" | Channel: {r.get('channel')}" if r.get('channel') else ""
            print(f" {idx}. [{r['type']}] {r['title']}{ch}")
            print(f"    Source: {r['source']} | URL: {r['url']}")
            print(f"    Reason: {r['reason']}")

    def test_a_conditions_fundamentals_visual(self):
        """TEST A: Weak Conditions (0.20), Goal: Fundamentals, Pref: Visual"""
        self.set_student_state(visual=0.9, read_write=0.1, topic_scores={"conditions": 0.20, "variables": 0.85})
        goal = {"type": "conceptual_understanding", "description": "Learn Python Fundamentals"}
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, learning_goal=goal, force_mock=True)
        resources = rec.get("resources", [])
        self.print_test_results("TEST A: Weak Conditions + Fundamentals Goal + Visual Pref", goal, resources)
        
        # Validations
        self.assertTrue(len(resources) >= 4)
        yt_videos = [r for r in resources if r['type'] == 'Video' and 'youtube.com' in r['url']]
        channels = [r.get('channel') or r.get('source') for r in yt_videos]
        
        # YouTube channel diversity check
        self.assertTrue(len(set(channels)) >= 2, "Expected multiple distinct YouTube channels")
        
        # Ensure at least 1 non-video resource exists
        non_videos = [r for r in resources if r['type'] != 'Video']
        self.assertTrue(len(non_videos) >= 1)

    def test_b_conditions_interview_visual(self):
        """TEST B: Weak Conditions (0.20), Goal: Interview Prep, Pref: Visual"""
        self.set_student_state(visual=0.9, read_write=0.1, topic_scores={"conditions": 0.20, "variables": 0.85})
        goal = {"type": "interview_preparation", "description": "Prepare for Python Interviews"}
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, learning_goal=goal, force_mock=True)
        resources = rec.get("resources", [])
        self.print_test_results("TEST B: Weak Conditions + Interview Goal + Visual Pref", goal, resources)
        
        self.assertTrue(len(resources) >= 4)
        has_interview_reasons = any("interview" in r['reason'].lower() for r in resources)
        self.assertTrue(has_interview_reasons)

    def test_c_dictionaries_project_read_write(self):
        """TEST C: Weak Dictionaries (0.25), Goal: Build Projects, Pref: Read/Write"""
        self.set_student_state(read_write=0.9, visual=0.1, topic_scores={"dictionaries": 0.25, "variables": 0.90})
        goal = {"type": "project_preparation", "description": "Build Python Projects"}
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, learning_goal=goal, force_mock=True)
        resources = rec.get("resources", [])
        self.print_test_results("TEST C: Weak Dictionaries + Project Goal + Read/Write Pref", goal, resources)
        
        self.assertTrue(len(resources) >= 4)
        dict_res = [r for r in resources if "dict" in r['title'].lower() or "dict" in r['reason'].lower()]
        self.assertTrue(len(dict_res) >= 2)
        has_doc_tut = any(r['type'] in ['Documentation', 'Tutorial'] for r in dict_res)
        self.assertTrue(has_doc_tut)

    def test_d_loops_problem_solving_kinesthetic(self):
        """TEST D: Weak Loops (0.20), Goal: Problem Solving, Pref: Kinesthetic"""
        self.set_student_state(kinesthetic=0.9, visual=0.1, topic_scores={"loops": 0.20, "variables": 0.90})
        goal = {"type": "revision", "description": "Improve Python Problem Solving"}
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, learning_goal=goal, force_mock=True)
        resources = rec.get("resources", [])
        self.print_test_results("TEST D: Weak Loops + Problem Solving Goal + Kinesthetic Pref", goal, resources)
        
        self.assertTrue(len(resources) >= 4)
        has_exercise = any(r['type'] == 'Exercise' for r in resources)
        self.assertTrue(has_exercise)

    def test_e_loops_problem_solving_read_write_shift(self):
        """TEST E: Same Loops (0.20) & Goal as TEST D, but Preference = Read/Write"""
        self.set_student_state(read_write=0.9, visual=0.1, topic_scores={"loops": 0.20, "variables": 0.90})
        goal = {"type": "revision", "description": "Improve Python Problem Solving"}
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, learning_goal=goal, force_mock=True)
        resources = rec.get("resources", [])
        self.print_test_results("TEST E: Weak Loops + Problem Solving Goal + Read/Write Pref (Shift from Test D)", goal, resources)
        
        self.assertTrue(len(resources) >= 4)
        top_type = resources[0]['type']
        # Read/Write preference should prioritize Documentation / Tutorial over Exercise
        self.assertIn(top_type, ['Documentation', 'Tutorial'])

if __name__ == "__main__":
    unittest.main()
