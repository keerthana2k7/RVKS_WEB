import unittest
import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from database.db import init_db
from database.seed_data import seed

class TestFarmAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        init_db()
        seed()
        
        # Authenticate Admin
        res = cls.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        data = res.get_json()
        cls.admin_token = data.get("token")
        
        # Authenticate Worker
        res_w = cls.client.post("/api/auth/login", json={"username": "worker1", "password": "worker123"})
        data_w = res_w.get_json()
        cls.worker_token = data_w.get("token")

    def test_login_success_and_invalid(self):
        # Valid login
        res = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("token", res.get_json())
        
        # Invalid password
        res_fail = self.client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
        self.assertEqual(res_fail.status_code, 401)

    def test_dashboard_summary_returns_valid_kpis(self):
        res = self.client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        self.assertIn("birds", data)
        self.assertIn("workers", data)
        self.assertIn("feed", data)
        self.assertIn("raw_materials", data)
        self.assertIn("eggs", data)
        self.assertIn("expenses", data)
        
        # Verify dynamic numbers
        self.assertGreater(data["birds"]["total_birds"], 0)
        self.assertGreater(data["birds"]["edd_batch_1"], 0)
        self.assertGreater(data["birds"]["edd_batch_2"], 0)
        self.assertGreater(data["birds"]["edd_batch_3"], 0)

    def test_role_based_access_worker_restriction(self):
        """Workers should NOT be able to view salary records or financial reports."""
        res_admin = self.client.get("/api/workers/payments", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_admin.status_code, 200)
        
        res_worker = self.client.get("/api/workers/payments", headers={"Authorization": f"Bearer {self.worker_token}"})
        self.assertEqual(res_worker.status_code, 403)
        
        res_fin_worker = self.client.get("/api/finance/summary", headers={"Authorization": f"Bearer {self.worker_token}"})
        self.assertEqual(res_fin_worker.status_code, 403)

    def test_feed_production_shortage_validation_api(self):
        """API must return error 400 with detailed shortage description when materials are insufficient."""
        # Request production of 1,000,000 kg feed (guaranteed to exceed available stock)
        payload = {
            "feed_type": "Layer Feed",
            "quantity_produced": 1000000.0,
            "recipe_id": 1,
            "produced_by": "Test Operator"
        }
        res = self.client.post("/api/feed/produce", json=payload, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertIn("Feed production cannot continue", data["error"])
        self.assertIn("shortages", data)

    def test_reports_api_json_and_csv(self):
        # JSON report
        res_json = self.client.get("/api/reports/complete", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_json.status_code, 200)
        data = res_json.get_json()
        self.assertIn("title", data)
        self.assertIn("data", data)
        
        # CSV export
        res_csv = self.client.get("/api/reports/complete?format=csv", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.mimetype, "text/csv")
        self.assertIn(b"RVKS WEB", res_csv.data)

if __name__ == "__main__":
    unittest.main()
