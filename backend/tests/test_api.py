import unittest
import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from database.db import init_db, get_db
from database.seed_data import seed
from routes.auth import create_token

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
        
        # Crafted Non-Admin / Worker Token to verify security rejection
        cls.non_admin_token = create_token(999, "worker_fake", "worker")

    def test_admin_login_success(self):
        """Admin can log in successfully and receive authentication token."""
        res = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["role"], "owner_admin")

    def test_worker_login_forbidden_or_rejected(self):
        """Workers must NOT have user login access. Any non-admin credentials must fail."""
        res = self.client.post("/api/auth/login", json={"username": "worker1", "password": "worker123"})
        self.assertIn(res.status_code, [401, 403])

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests to protected APIs must be rejected with 401."""
        res = self.client.get("/api/dashboard/summary")
        self.assertEqual(res.status_code, 401)
        
        res_workers = self.client.get("/api/workers")
        self.assertEqual(res_workers.status_code, 401)

    def test_non_admin_role_denied_access_to_all_resources(self):
        """If a non-admin token is presented, access must be strictly denied with 403 Forbidden."""
        protected_endpoints = [
            "/api/dashboard/summary",
            "/api/workers",
            "/api/workers/attendance",
            "/api/workers/payments",
            "/api/finance/summary",
            "/api/feed/stock",
            "/api/reports/complete",
            "/api/admin/status",
            "/api/materials"
        ]
        for ep in protected_endpoints:
            res = self.client.get(ep, headers={"Authorization": f"Bearer {self.non_admin_token}"})
            self.assertEqual(res.status_code, 403, f"Endpoint {ep} should have returned 403 Forbidden for non-admin")

    def test_dashboard_summary_returns_valid_kpis(self):
        """Admin dashboard returns complete real-time KPIs."""
        res = self.client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        self.assertIn("birds", data)
        self.assertIn("workers", data)
        self.assertIn("feed", data)
        self.assertIn("raw_materials", data)
        self.assertIn("eggs", data)
        self.assertIn("expenses", data)
        
        self.assertGreater(data["birds"]["total_birds"], 0)
        self.assertGreater(data["birds"]["edd_batch_1"], 0)

    def test_admin_worker_record_crud(self):
        """Admin has full control to create, view, edit, view history, and delete worker data records."""
        # 1. Add Worker Record
        worker_payload = {
            "name": "Arun Kumar",
            "job_role": "Feed Assistant",
            "phone": "9876543210",
            "address": "South Shed Quarters",
            "date_of_joining": "2026-02-01",
            "salary_type": "Monthly",
            "salary_amount": 14000.0,
            "payment_status": "Pending",
            "payment_method": "UPI",
            "notes": "Night shift feed assistant"
        }
        res_create = self.client.post("/api/workers", json=worker_payload, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_create.status_code, 201)
        created_data = res_create.get_json()
        worker_id = created_data["worker_id"]
        
        # 2. View Worker Details
        res_get = self.client.get(f"/api/workers/{worker_id}", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.get_json()["worker"]["name"], "Arun Kumar")
        
        # 3. Edit Worker Details
        update_payload = {
            "name": "Arun Kumar M",
            "job_role": "Senior Feed Assistant",
            "phone": "9876543210",
            "address": "South Shed Quarters",
            "date_of_joining": "2026-02-01",
            "salary_type": "Monthly",
            "salary_amount": 16000.0,
            "payment_status": "Pending",
            "payment_method": "Bank Transfer",
            "status": "Active",
            "notes": "Promoted to Senior"
        }
        res_update = self.client.put(f"/api/workers/{worker_id}", json=update_payload, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_update.status_code, 200)
        
        # 4. View Worker History
        res_history = self.client.get(f"/api/workers/{worker_id}/history", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_history.status_code, 200)
        self.assertIn("attendance", res_history.get_json())
        self.assertIn("payments", res_history.get_json())
        
        # 5. Delete Worker Record
        res_del = self.client.delete(f"/api/workers/{worker_id}", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_del.status_code, 200)

    def test_record_worker_attendance_and_payments(self):
        """Admin records attendance and payments for worker data records."""
        # Attendance recording
        att_payload = {
            "worker_id": 1,
            "date": "2026-09-20",
            "status": "Present",
            "check_in_time": "06:45",
            "check_out_time": "18:00",
            "notes": "Routine inspection"
        }
        res_att = self.client.post("/api/workers/attendance", json=att_payload, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_att.status_code, 200)

        # Payment recording
        pay_payload = {
            "worker_id": 1,
            "salary_period": "Sep 2026 Advance",
            "payment_date": "2026-09-21",
            "amount": 5000.0,
            "payment_method": "UPI",
            "status": "Paid",
            "notes": "Mid-month advance settlement"
        }
        res_pay = self.client.post("/api/workers/payments", json=pay_payload, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_pay.status_code, 201)

    def test_feed_production_shortage_validation_api(self):
        """API must return error 400 with detailed shortage description when materials are insufficient."""
        payload = {
            "feed_type": "Layer Feed",
            "quantity_produced": 1000000.0,
            "recipe_id": 1,
            "produced_by": "Farm Owner"
        }
        res = self.client.post("/api/feed/produce", json=payload, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertIn("Feed production cannot continue", data["error"])
        self.assertIn("shortages", data)

    def test_reports_api_json_and_csv(self):
        """Admin can generate full reports and export CSV."""
        res_json = self.client.get("/api/reports/complete", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_json.status_code, 200)
        
        res_csv = self.client.get("/api/reports/complete?format=csv", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.mimetype, "text/csv")
        self.assertIn(b"RVKS WEB", res_csv.data)

    def test_worker_payroll_calculations_and_advance_extra_tracking(self):
        """Test Worker Payroll automated balance calculations, advance tracking, extra bonus tracking, and status."""
        # 1. Fetch current payroll overview
        res = self.client.get("/api/workers/payroll?month=2026-10", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("payroll", data)
        self.assertIn("summary", data)
        
        summary = data["summary"]
        self.assertIn("total_workers", summary)
        self.assertIn("total_salary_due", summary)
        self.assertIn("total_paid", summary)
        self.assertIn("total_pending", summary)
        self.assertIn("total_advance_paid", summary)
        self.assertIn("total_extra_paid", summary)
        
        # 2. Add a new worker specifically to test lifecycle: Salary = 15,000
        new_worker_res = self.client.post("/api/workers", json={
            "name": "Ramesh Testing",
            "job_role": "Poultry Attendant",
            "phone": "9998887776",
            "salary_type": "Monthly",
            "salary_amount": 15000.0,
            "payment_status": "Pending",
            "payment_method": "Cash"
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(new_worker_res.status_code, 201)
        w_id = new_worker_res.get_json()["worker_id"]
        
        # Initial check: Remaining = 15,000, Status = Pending
        res_chk1 = self.client.get("/api/workers/payroll?month=2026-10", headers={"Authorization": f"Bearer {self.admin_token}"})
        w_record = next(w for w in res_chk1.get_json()["payroll"] if w["worker_id"] == w_id)
        self.assertEqual(w_record["regular_salary_due"], 15000.0)
        self.assertEqual(w_record["amount_already_paid"], 0.0)
        self.assertEqual(w_record["advance_paid"], 0.0)
        self.assertEqual(w_record["extra_amount_paid"], 0.0)
        self.assertEqual(w_record["remaining_amount"], 15000.0)
        self.assertEqual(w_record["payment_status"], "Pending")
        
        # 3. Pay ₹5,000 Advance on 15 October (before due date 30 October)
        adv_res = self.client.post("/api/workers/payments", json={
            "worker_id": w_id,
            "payment_date": "2026-10-15",
            "salary_period": "Oct 2026",
            "payment_type": "Advance",
            "amount": 5000.0,
            "payment_method": "UPI",
            "notes": "Pre-due date advance"
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(adv_res.status_code, 201)
        
        # Check: Advance = 5,000, Remaining = 10,000, Status = Partially Paid
        res_chk2 = self.client.get("/api/workers/payroll?month=2026-10", headers={"Authorization": f"Bearer {self.admin_token}"})
        w_record = next(w for w in res_chk2.get_json()["payroll"] if w["worker_id"] == w_id)
        self.assertEqual(w_record["advance_paid"], 5000.0)
        self.assertEqual(w_record["remaining_amount"], 10000.0)
        self.assertEqual(w_record["payment_status"], "Partially Paid")
        
        # 4. Pay regular ₹10,000 + Extra ₹2,000 (Diwali Bonus)
        extra_res = self.client.post("/api/workers/payments", json={
            "worker_id": w_id,
            "payment_date": "2026-10-30",
            "salary_period": "Oct 2026",
            "payment_type": "Salary",
            "amount": 10000.0,
            "extra_amount": 2000.0,
            "extra_reason": "Bonus",
            "payment_method": "Bank Transfer",
            "notes": "Salary settlement + festival bonus"
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(extra_res.status_code, 201)
        
        # Check: Regular Paid = 10,000, Advance = 5,000, Extra = 2,000, Total Received = 17,000, Remaining = 0, Status = Paid
        res_chk3 = self.client.get("/api/workers/payroll?month=2026-10", headers={"Authorization": f"Bearer {self.admin_token}"})
        w_record = next(w for w in res_chk3.get_json()["payroll"] if w["worker_id"] == w_id)
        self.assertEqual(w_record["amount_already_paid"], 10000.0)
        self.assertEqual(w_record["advance_paid"], 5000.0)
        self.assertEqual(w_record["extra_amount_paid"], 2000.0)
        self.assertEqual(w_record["total_amount_paid"], 17000.0)
        self.assertEqual(w_record["remaining_amount"], 0.0)
        self.assertEqual(w_record["payment_status"], "Paid")
        
        # 5. Check Worker Payment History Ledger
        res_hist = self.client.get(f"/api/workers/{w_id}/payments", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_hist.status_code, 200)
        hist_data = res_hist.get_json()
        self.assertEqual(len(hist_data["payments"]), 2)
        self.assertEqual(hist_data["stats"]["total_base_paid"], 15000.0)
        self.assertEqual(hist_data["stats"]["total_advance_paid"], 5000.0)
        self.assertEqual(hist_data["stats"]["total_extra_paid"], 2000.0)
        self.assertEqual(hist_data["stats"]["total_received"], 17000.0)

if __name__ == "__main__":
    unittest.main()

