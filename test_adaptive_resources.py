import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import init_db, get_db
from services.profile_service import get_student_snapshot
from services.recommendation_service import generate_learning_recommendation

class TestAdaptiveResources(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.student_id = "STU-ADAPT-TEST"
        self.domain_id = "python"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO students (student_id, name, email, password_hash) VALUES (?, 'Adaptive Test Student', 'adapt@test.com', 'hash');", (self.student_id,))
        cursor.execute("DELETE FROM student_psychological_profile WHERE student_id = ?", (self.student_id,))
        cursor.execute("DELETE FROM student_knowledge_profile WHERE student_id = ?", (self.student_id,))
        cursor.execute("DELETE FROM recommendations WHERE student_id = ?", (self.student_id,))
        conn.commit()
        conn.close()

    def set_profile(self, visual=0.5, aural=0.5, read_write=0.5, kinesthetic=0.5, topic_scores=None):
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
        cursor.execute("INSERT OR IGNORE INTO baseline_attempts (attempt_id, student_id) VALUES ('ATTEMPT-ADAPT', ?);", (self.student_id,))
        cursor.execute("""
            INSERT INTO student_knowledge_profile (student_id, attempt_id, overall_performance, topic_scores, kc_scores)
            VALUES (?, 'ATTEMPT-ADAPT', 0.3, ?, '{}');
        """, (self.student_id, t_json))
        conn.commit()
        conn.close()

    def test_a_conditions_visual_preference(self):
        """TEST A: Weakest area = Conditions (0.20), Visual Preference (0.9)"""
        print("\n==========================================")
        print("TEST A: Conditions Weakness + Visual Preference")
        print("==========================================")
        self.set_profile(visual=0.9, read_write=0.1, topic_scores={"conditions": 0.20, "variables": 0.80})
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, force_mock=True)
        resources = rec.get("resources", [])
        
        print(f"Total returned resources: {len(resources)}")
        for r in resources:
            print(f"  - [{r['type']}] {r['title']} -> {r['url']}")
            print(f"    Reason: {r['reason']}")
            # Verify URL
            self.assertTrue(r['url'].startswith("http"))
            self.assertIn("reason", r)

        # Check that conditions resources are prioritized and a video is present
        cond_res = [r for r in resources if "condition" in r['title'].lower() or "condition" in r['reason'].lower() or "branch" in r['reason'].lower() or "if" in r['title'].lower()]
        self.assertTrue(len(cond_res) >= 1)
        
        has_video = any(r['type'] == 'Video' and 'youtube.com' in r['url'] for r in resources)
        self.assertTrue(has_video)
        print("STATUS: TEST A PASSED")

    def test_b_dictionaries_read_write_preference(self):
        """TEST B: Weakest area = Dictionaries (0.25), Read/Write Preference (0.9)"""
        print("\n==========================================")
        print("TEST B: Dictionaries Weakness + Read/Write Preference")
        print("==========================================")
        self.set_profile(read_write=0.9, visual=0.1, topic_scores={"dictionaries": 0.25, "variables": 0.85})
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, force_mock=True)
        resources = rec.get("resources", [])
        
        print(f"Total returned resources: {len(resources)}")
        for r in resources:
            print(f"  - [{r['type']}] {r['title']} -> {r['url']}")
            print(f"    Reason: {r['reason']}")
            self.assertTrue(r['url'].startswith("http"))

        dict_res = [r for r in resources if "dict" in r['title'].lower() or "dict" in r['reason'].lower()]
        self.assertTrue(len(dict_res) >= 1)
        
        # Read/Write should prioritize Documentation / Tutorial
        has_doc_tut = any(r['type'] in ['Documentation', 'Tutorial'] for r in dict_res)
        self.assertTrue(has_doc_tut)
        print("STATUS: TEST B PASSED")

    def test_c_loops_kinesthetic_preference(self):
        """TEST C: Weakest area = Loops (0.20), Kinesthetic Preference (0.9)"""
        print("\n==========================================")
        print("TEST C: Loops Weakness + Kinesthetic Preference")
        print("==========================================")
        self.set_profile(kinesthetic=0.9, visual=0.1, topic_scores={"loops": 0.20, "variables": 0.90})
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, force_mock=True)
        resources = rec.get("resources", [])
        
        print(f"Total returned resources: {len(resources)}")
        for r in resources:
            print(f"  - [{r['type']}] {r['title']} -> {r['url']}")
            print(f"    Reason: {r['reason']}")
            self.assertTrue(r['url'].startswith("http"))

        loop_res = [r for r in resources if "loop" in r['title'].lower() or "loop" in r['reason'].lower()]
        self.assertTrue(len(loop_res) >= 1)
        print("STATUS: TEST C PASSED")

    def test_d_functions_weakness_shift(self):
        """TEST D: Knowledge Profile Shift -> Weakest area = Functions (0.15), Variables = (0.85)"""
        print("\n==========================================")
        print("TEST D: Functions Weakness Shift")
        print("==========================================")
        self.set_profile(visual=0.5, topic_scores={"functions": 0.15, "variables": 0.85})
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, force_mock=True)
        resources = rec.get("resources", [])
        
        print(f"Total returned resources: {len(resources)}")
        for r in resources:
            print(f"  - [{r['type']}] {r['title']} -> {r['url']}")
            print(f"    Reason: {r['reason']}")
            self.assertTrue(r['url'].startswith("http"))

        func_res = [r for r in resources if "func" in r['title'].lower() or "func" in r['reason'].lower()]
        var_res = [r for r in resources if "variable" in r['title'].lower() or "variable" in r['reason'].lower()]
        
        # Functions resources must dominate over Variables resources
        self.assertTrue(len(func_res) > len(var_res))
        print("STATUS: TEST D PASSED")

if __name__ == "__main__":
    unittest.main()
