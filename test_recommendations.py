import unittest
import os
import json
from app import app
from db import init_db, get_db, DB_PATH
from seed_data import seed_database
from services.recommendation_service import generate_learning_recommendation, get_latest_recommendation, get_recommendation_history
from profiling_engine import process_survey_responses

class TestAIRecommendationsV2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except Exception:
                pass
        init_db()
        seed_database()

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        # Ensure test student exists
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO students (student_id, name, email, password_hash) VALUES ('STU-REC-TEST', 'Recommendation Student', 'rec_test@example.com', 'hash');")
        conn.commit()
        conn.close()

        # Seed psychological profile for test student
        responses = {
            "VARK_V1": 5, "VARK_V2": 5,
            "VARK_A1": 2, "VARK_A2": 2,
            "VARK_R1": 4, "VARK_R2": 4,
            "VARK_K1": 1, "VARK_K2": 1,
            "MOT_INT1": 5, "MOT_INT2": 5,
            "MOT_EXT1": 3, "MOT_EXT2": 3,
            "MOT_LGO1": 4, "MOT_LGO2": 4,
            "MOT_TV1": 5, "MOT_TV2": 5,
            "SR_GS1": 4, "SR_GS2": 4,
            "SR_PL1": 3, "SR_PL2": 3,
            "SR_SM1": 5, "SR_SM2": 5,
            "SR_RB1": 2, "SR_RB2": 2
        }
        process_survey_responses("STU-REC-TEST", responses)

    def test_01_multi_domain_recommendations(self):
        """
        Tests domain-agnostic recommendation service across 3 distinct domains:
        Python Programming, Mathematics, and Physics.
        """
        domains_to_test = ["python", "mathematics", "physics"]

        for d_id in domains_to_test:
            rec = generate_learning_recommendation("STU-REC-TEST", d_id)
            
            # Assertions on returned structure
            self.assertIsNotNone(rec)
            self.assertIn("domain", rec)
            self.assertEqual(rec["domain"]["id"], d_id)
            self.assertIn("summary", rec)
            self.assertIn("learner_approach", rec)
            self.assertIn("priority_areas", rec)
            self.assertIn("learning_sequence", rec)
            self.assertIn("resources", rec)
            self.assertIn("practice_recommendations", rec)

            # Assert priority areas match domain curriculum
            p_areas = rec["priority_areas"]
            self.assertGreater(len(p_areas), 0)

            # Assert resource URLs are not fabricated (null or valid http/https)
            for res in rec["resources"]:
                if res["url"] is not None:
                    self.assertTrue(res["url"].startswith("http://") or res["url"].startswith("https://"))
                self.assertIn("verification_status", res)

    def test_02_database_persistence(self):
        """
        Verifies profile snapshot and JSON recommendation are stored in database.
        """
        rec = generate_learning_recommendation("STU-REC-TEST", "python")
        rec_id = rec["id"]

        latest = get_latest_recommendation("STU-REC-TEST", "python")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["id"], rec_id)

        history = get_recommendation_history("STU-REC-TEST", "python")
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0]["id"], rec_id)

    def test_03_api_endpoints(self):
        """
        Tests API endpoints for generate, latest, history, and domains list.
        """
        with self.client.session_transaction() as sess:
            sess['student_id'] = 'STU-REC-TEST'
            sess['student_name'] = 'Recommendation Student'

        # 1. GET /api/domains
        res_domains = self.client.get('/api/domains')
        self.assertEqual(res_domains.status_code, 200)
        d_data = json.loads(res_domains.data)
        self.assertIn("domains", d_data)
        domain_ids = [d["id"] for d in d_data["domains"]]
        self.assertIn("python", domain_ids)
        self.assertIn("mathematics", domain_ids)
        self.assertIn("physics", domain_ids)

        # 2. POST /api/recommendations/generate for Mathematics
        res_gen = self.client.post('/api/recommendations/generate', json={
            "domain_id": "mathematics",
            "learning_goal": {
                "type": "exam_preparation",
                "description": "Prepare for Linear Algebra & Calculus exam"
            }
        })
        self.assertEqual(res_gen.status_code, 200)
        gen_json = json.loads(res_gen.data)
        self.assertTrue(gen_json["success"])
        self.assertEqual(gen_json["recommendation"]["domain"]["id"], "mathematics")

        # 3. GET /api/recommendations/latest?domain_id=mathematics
        res_latest = self.client.get('/api/recommendations/latest?domain_id=mathematics')
        self.assertEqual(res_latest.status_code, 200)
        latest_json = json.loads(res_latest.data)
        self.assertTrue(latest_json["success"])
        self.assertEqual(latest_json["recommendation"]["domain"]["id"], "mathematics")

        # 4. GET /recommendations view page
        res_view = self.client.get('/recommendations?domain_id=mathematics')
        self.assertEqual(res_view.status_code, 200)
        self.assertIn(b'Learning Plan', res_view.data)
        self.assertIn(b'Mathematics', res_view.data)

    def test_04_graceful_error_handling(self):
        """
        Tests invalid domain or missing data returns clean error JSON without crashing.
        """
        with self.client.session_transaction() as sess:
            sess['student_id'] = 'STU-REC-TEST'

        res_err = self.client.post('/api/recommendations/generate', json={"domain_id": "invalid_domain_xyz"})
        self.assertEqual(res_err.status_code, 400)
        err_json = json.loads(res_err.data)
        self.assertFalse(err_json["success"])
        self.assertIn("error", err_json)

if __name__ == '__main__':
    unittest.main()
