import json
import unittest
from db import init_db, get_db
from services.profile_service import get_student_snapshot
from services.recommendation_service import generate_learning_recommendation
class TestRecommendationPass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.student_id = "STU-PASS-TEST"
        self.domain_id = "python"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO students (student_id, name, email, password_hash) VALUES (?, 'Test Pass Student', 'pass@test.com', 'hash');", (self.student_id,))
        cursor.execute("DELETE FROM student_psychological_profile WHERE student_id = ?", (self.student_id,))
        cursor.execute("DELETE FROM student_knowledge_profile WHERE student_id = ?", (self.student_id,))
        cursor.execute("DELETE FROM recommendations WHERE student_id = ?", (self.student_id,))
        conn.commit()
        conn.close()

    def set_student_profile(self, visual=0.5, aural=0.5, read_write=0.5, kinesthetic=0.5):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO student_psychological_profile (
                student_id, vark_visual, vark_aural, vark_read_write, vark_kinesthetic,
                intrinsic_motivation, extrinsic_motivation, learning_goal_orientation, task_value,
                goal_setting, planning, self_monitoring, revision_behavior
            ) VALUES (?, ?, ?, ?, ?, 0.8, 0.4, 0.9, 0.8, 0.7, 0.6, 0.8, 0.7);
        """, (self.student_id, visual, aural, read_write, kinesthetic))
        conn.commit()
        conn.close()

    def set_knowledge_profile(self, overall_perf=0.25, topic_scores=None, kc_scores=None):
        conn = get_db()
        cursor = conn.cursor()
        t_json = json.dumps(topic_scores or {})
        k_json = json.dumps(kc_scores or {})
        cursor.execute("INSERT OR IGNORE INTO baseline_attempts (attempt_id, student_id) VALUES ('ATTEMPT-PASS-TEST', ?);", (self.student_id,))
        cursor.execute("""
            INSERT INTO student_knowledge_profile (student_id, attempt_id, overall_performance, topic_scores, kc_scores)
            VALUES (?, 'ATTEMPT-PASS-TEST', ?, ?, ?);
        """, (self.student_id, overall_perf, t_json, k_json))
        conn.commit()
        conn.close()

    def print_execution_trace(self, test_name: str, snapshot, rec_json):
        print("\n" + "="*80)
        print(f"5-STAGE EXECUTION TRACE: {test_name}")
        print("="*80)
        print("\n--- STAGE 1: Student Data Sent to AI ---")
        print(json.dumps({
            "student_id": snapshot.student_id,
            "learner_profile": snapshot.learner_profile.to_dict(),
            "knowledge_profile": {
                "domain_id": snapshot.knowledge_profile.domain_id,
                "overall_mastery": snapshot.knowledge_profile.overall_mastery,
                "areas_count": len(snapshot.knowledge_profile.areas)
            }
        }, indent=2))

        print("\n--- STAGE 2: AI Recommendation Reasoning & Output ---")
        print(json.dumps({
            "summary": rec_json.get("summary", ""),
            "learner_approach": rec_json.get("learner_approach", {}),
            "priority_areas": [p.get("area_id") for p in rec_json.get("priority_areas", [])],
            "learning_sequence": [s.get("area_id") for s in rec_json.get("learning_sequence", [])]
        }, indent=2))

        print("\n--- STAGE 3: Decoupled Resource Catalog Retrieval ---")
        retrieved = [
            {"title": r.get("title"), "source": r.get("source"), "status": r.get("verification_status")}
            for r in rec_json.get("resources", []) if r.get("verification_status") == "verified"
        ]
        print(json.dumps(retrieved, indent=2))

        print("\n--- STAGE 4: Validated Educational Resources ---")
        print(json.dumps([{
            "title": r.get("title"),
            "type": r.get("type"),
            "url": r.get("url"),
            "source": r.get("source"),
            "verification_status": r.get("verification_status")
        } for r in rec_json.get("resources", [])], indent=2))

        print("\n--- STAGE 5: Final Recommendation JSON Payload ---")
        print(json.dumps({
            "id": rec_json.get("id"),
            "domain": rec_json.get("domain"),
            "overall_mastery": rec_json.get("overall_mastery"),
            "priority_areas_count": len(rec_json.get("priority_areas", [])),
            "sequence_count": len(rec_json.get("learning_sequence", [])),
            "resources_count": len(rec_json.get("resources", [])),
            "practice_count": len(rec_json.get("practice_recommendations", []))
        }, indent=2))
        print("="*80 + "\n")

    def test_a_visual_modality_profile(self):
        """TEST A: Visual Modality Profile"""
        print("\nRunning TEST A: Visual Modality Profile...")
        self.set_student_profile(visual=0.9, read_write=0.1)
        self.set_knowledge_profile(0.25, {"variables": 0.2, "conditions": 0.3})
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, force_mock=False)
        snapshot = get_student_snapshot(self.student_id, self.domain_id)
        
        self.print_execution_trace("TEST A: Visual Modality Profile", snapshot, rec)
        
        self.assertTrue(len(rec.get("resources", [])) > 0)

    def test_b_read_write_modality_profile(self):
        """TEST B: Read/Write Modality Profile"""
        print("\nRunning TEST B: Read/Write Modality Profile...")
        self.set_student_profile(visual=0.1, read_write=0.9)
        self.set_knowledge_profile(0.25, {"variables": 0.2, "conditions": 0.3})
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, force_mock=False)
        snapshot = get_student_snapshot(self.student_id, self.domain_id)
        
        self.print_execution_trace("TEST B: Read/Write Modality Profile", snapshot, rec)
        
        self.assertTrue(len(rec.get("resources", [])) > 0)

    def test_c_knowledge_change_impact(self):
        """TEST C: Knowledge Change Impact (Mastery Shift)"""
        print("\nRunning TEST C: Knowledge Change Impact...")
        self.set_student_profile(visual=0.7)
        # Shift: Student has high mastery in variables (0.95), low mastery in loops (0.10)
        self.set_knowledge_profile(0.50, {"variables": 0.95, "loops": 0.10})
        
        rec = generate_learning_recommendation(self.student_id, self.domain_id, force_mock=False)
        snapshot = get_student_snapshot(self.student_id, self.domain_id)
        
        self.print_execution_trace("TEST C: Knowledge Change Impact", snapshot, rec)
        
        priority_aids = [p.get("area_id") for p in rec.get("priority_areas", [])]
        mastered_aids = [m.get("area_id") for m in rec.get("mastered_areas", [])]
        
        self.assertIn("loops", priority_aids)
        self.assertIn("variables", mastered_aids)

    def test_d_mathematics_domain(self):
        """TEST D: Mathematics Domain Support"""
        print("\nRunning TEST D: Mathematics Domain...")
        math_domain = "mathematics"
        self.set_student_profile(visual=0.8)
        self.set_knowledge_profile(0.30, {"linear_algebra": 0.2, "calculus": 0.4})
        
        rec = generate_learning_recommendation(self.student_id, math_domain, force_mock=False)
        snapshot = get_student_snapshot(self.student_id, math_domain)
        
        self.print_execution_trace("TEST D: Mathematics Domain", snapshot, rec)
        
        self.assertEqual(rec.get("domain", {}).get("id"), math_domain)
        self.assertTrue(len(rec.get("resources", [])) > 0)
        sources = [r.get("source") for r in rec.get("resources", [])]
        self.assertTrue(any("Khan Academy" in s for s in sources if s))

if __name__ == "__main__":
    unittest.main()
