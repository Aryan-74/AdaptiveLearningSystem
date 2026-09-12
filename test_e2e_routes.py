import unittest
from app import app
from db import init_db
from seed_data import seed_database

class TestE2ERoutes(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        init_db()
        seed_database()
        from db import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE email = 'jane@example.com';")
        conn.commit()
        conn.close()

    def test_full_user_flow(self):
        # 1. Register
        res = self.client.post('/register', data={
            'name': 'Jane Student',
            'email': 'jane@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Welcome to Student Profiling', res.data)

        # 2. Survey Page
        res_survey = self.client.get('/survey')
        self.assertEqual(res_survey.status_code, 200)
        self.assertIn(b'Learner Characteristics Survey', res_survey.data)

        # 3. Post Survey
        survey_data = {}
        for i in range(1, 3):
            survey_data[f"VARK_V{i}"] = "4"
            survey_data[f"VARK_A{i}"] = "3"
            survey_data[f"VARK_R{i}"] = "5"
            survey_data[f"VARK_K{i}"] = "2"
            survey_data[f"MOT_INT{i}"] = "5"
            survey_data[f"MOT_EXT{i}"] = "3"
            survey_data[f"MOT_LGO{i}"] = "4"
            survey_data[f"MOT_TV{i}"] = "5"
            survey_data[f"SR_GS{i}"] = "4"
            survey_data[f"SR_PL{i}"] = "3"
            survey_data[f"SR_SM{i}"] = "4"
            survey_data[f"SR_RB{i}"] = "3"

        res_post_survey = self.client.post('/survey', data=survey_data, follow_redirects=True)
        self.assertEqual(res_post_survey.status_code, 200)
        self.assertIn(b'Survey Complete', res_post_survey.data)

        # 4. Survey Results Page
        res_sr = self.client.get('/survey/results')
        self.assertEqual(res_sr.status_code, 200)
        self.assertIn(b'VARK Continuous Preference Scores', res_sr.data)

        # 5. Baseline Knowledge Test Page
        res_test = self.client.get('/test')
        self.assertEqual(res_test.status_code, 200)
        self.assertIn(b'Python Baseline Knowledge Test', res_test.data)

        # 6. Post Baseline Test
        test_data = {}
        # Submit correct answers for questions
        from db import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT question_id, correct_answer FROM knowledge_questions;")
        q_rows = cursor.fetchall()
        conn.close()

        for q in q_rows:
            qid = q['question_id']
            test_data[qid] = q['correct_answer']
            test_data[f"time_{qid}"] = "12.5"

        res_post_test = self.client.post('/test', data=test_data, follow_redirects=True)
        self.assertEqual(res_post_test.status_code, 200)
        self.assertIn(b'Baseline Knowledge Assessment Complete', res_post_test.data)

        # 7. Student Profile Dashboard
        res_profile = self.client.get('/profile')
        self.assertEqual(res_profile.status_code, 200)
        self.assertIn(b'Psychological / Learner Characteristics Profile', res_profile.data)
        self.assertIn(b'Knowledge Profile', res_profile.data)
        self.assertIn(b'Overall Python Performance', res_profile.data)
        self.assertIn(b'100.0%', res_profile.data)

        # 8. Retake Baseline Test
        res_retake = self.client.post('/test/retake', follow_redirects=True)
        self.assertEqual(res_retake.status_code, 200)
        self.assertIn(b'Python Baseline Knowledge Test', res_retake.data)

if __name__ == '__main__':
    unittest.main()
