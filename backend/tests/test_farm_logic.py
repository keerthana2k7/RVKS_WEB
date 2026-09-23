import unittest
import os
import sys
import tempfile
import sqlite3

# Add backend directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from database import db

class TestFarmBusinessLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a dedicated temp database for isolated test execution
        cls.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.temp_db.close()
        os.environ["DATABASE_PATH"] = cls.temp_db.name
        db.DB_FILE = cls.temp_db.name
        db.init_db()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_db.name):
            try:
                os.remove(cls.temp_db.name)
            except Exception:
                pass

    def setUp(self):
        # Clear tables before each test
        with db.get_db() as conn:
            conn.execute("DELETE FROM attendance")
            conn.execute("DELETE FROM worker_payments")
            conn.execute("DELETE FROM mortality")
            conn.execute("DELETE FROM bird_transactions")
            conn.execute("DELETE FROM egg_production")
            conn.execute("DELETE FROM feed_usage")
            conn.execute("DELETE FROM feed_production")
            conn.execute("DELETE FROM feed_stock_movements")
            conn.execute("DELETE FROM raw_material_purchases")
            conn.execute("DELETE FROM raw_material_movements")
            conn.execute("DELETE FROM feed_recipe_items")
            conn.execute("DELETE FROM feed_recipes")
            conn.execute("DELETE FROM feed_stock")
            conn.execute("DELETE FROM raw_materials")
            conn.execute("DELETE FROM bird_batches")
            conn.execute("DELETE FROM suppliers")
            conn.execute("DELETE FROM workers")
            conn.execute("DELETE FROM users")
            
            # Insert basic test entities
            conn.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES ('admin', 'hash', 'Admin', 'owner_admin')")
            conn.execute("INSERT INTO bird_batches (id, batch_code, batch_name, bird_type, arrival_date, initial_quantity, current_quantity) VALUES (1, 'BATCH-001', 'EDD Batch 1', 'EDD', '2026-05-01', 1000, 1000)")
            conn.execute("INSERT INTO workers (id, worker_code, name, date_of_joining, job_role, salary_amount) VALUES (1, 'WRK-001', 'Test Worker', '2026-01-01', 'Hand', 500.0)")
            conn.execute("INSERT INTO suppliers (id, supplier_code, supplier_name) VALUES (1, 'SUP-001', 'Test Supplier')")
            conn.execute("INSERT INTO raw_materials (id, material_code, material_name, minimum_stock_level, current_stock) VALUES (1, 'MAT-001', 'Maize', 100.0, 500.0)")
            conn.execute("INSERT INTO raw_materials (id, material_code, material_name, minimum_stock_level, current_stock) VALUES (2, 'MAT-002', 'Soybean', 50.0, 200.0)")
            conn.execute("INSERT INTO feed_stock (id, feed_type, current_stock, minimum_stock_level) VALUES (1, 'Layer Feed', 100.0, 50.0)")
            conn.execute("INSERT INTO feed_recipes (id, recipe_code, feed_type, recipe_name) VALUES (1, 'RCP-001', 'Layer Feed', 'Standard Layer')")
            conn.execute("INSERT INTO feed_recipe_items (recipe_id, material_id, percentage, quantity_per_100kg) VALUES (1, 1, 60.0, 60.0)")
            conn.execute("INSERT INTO feed_recipe_items (recipe_id, material_id, percentage, quantity_per_100kg) VALUES (1, 2, 40.0, 40.0)")

    def test_prevent_duplicate_attendance(self):
        """Rule: One worker + one date = one record. Duplicates must be rejected or upserted."""
        with db.get_db() as conn:
            conn.execute("INSERT INTO attendance (worker_id, date, status) VALUES (1, '2026-09-19', 'Present')")
            
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO attendance (worker_id, date, status) VALUES (1, '2026-09-19', 'Absent')")

    def test_mortality_reduces_birds_and_prevents_negative(self):
        """Rule: Mortality reduces current bird count and never allows count to become negative."""
        with db.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_quantity FROM bird_batches WHERE id = 1")
            initial = cursor.fetchone()["current_quantity"]
            self.assertEqual(initial, 1000)
            
            # Normal mortality: 10 birds
            mortality_count = 10
            conn.execute("INSERT INTO mortality (date, batch_id, bird_type, number_of_birds, reason) VALUES ('2026-09-19', 1, 'EDD', ?, 'Weakness')", (mortality_count,))
            conn.execute("UPDATE bird_batches SET current_quantity = current_quantity - ? WHERE id = 1", (mortality_count,))
            
            cursor.execute("SELECT current_quantity FROM bird_batches WHERE id = 1")
            updated = cursor.fetchone()["current_quantity"]
            self.assertEqual(updated, 990)
            
            # Attempt mortality exceeding current birds: check constraint on balance_after or current_quantity >= 0
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE bird_batches SET current_quantity = -5 WHERE id = 1")

    def test_raw_material_purchase_stock_increase(self):
        """Rule: Purchasing raw materials accurately increments inventory stock."""
        with db.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_stock FROM raw_materials WHERE id = 1")
            initial_stock = cursor.fetchone()["current_stock"]
            self.assertEqual(initial_stock, 500.0)
            
            purchased_qty = 300.0
            conn.execute("UPDATE raw_materials SET current_stock = current_stock + ? WHERE id = 1", (purchased_qty,))
            
            cursor.execute("SELECT current_stock FROM raw_materials WHERE id = 1")
            new_stock = cursor.fetchone()["current_stock"]
            self.assertEqual(new_stock, 800.0)

    def test_feed_production_stock_deduction_and_finished_feed_increment(self):
        """Rule: Producing 100kg feed (60% Maize, 40% Soy) deducts 60kg Maize, 40kg Soy, and adds 100kg Layer Feed."""
        with db.get_db() as conn:
            cursor = conn.cursor()
            prod_qty = 100.0
            
            # Deduct ingredients
            conn.execute("UPDATE raw_materials SET current_stock = current_stock - 60.0 WHERE id = 1") # Maize was 500
            conn.execute("UPDATE raw_materials SET current_stock = current_stock - 40.0 WHERE id = 2") # Soy was 200
            # Increase finished feed
            conn.execute("UPDATE feed_stock SET current_stock = current_stock + 100.0 WHERE feed_type = 'Layer Feed'") # Was 100
            
            cursor.execute("SELECT current_stock FROM raw_materials WHERE id = 1")
            self.assertEqual(cursor.fetchone()["current_stock"], 440.0)
            
            cursor.execute("SELECT current_stock FROM raw_materials WHERE id = 2")
            self.assertEqual(cursor.fetchone()["current_stock"], 160.0)
            
            cursor.execute("SELECT current_stock FROM feed_stock WHERE feed_type = 'Layer Feed'")
            self.assertEqual(cursor.fetchone()["current_stock"], 200.0)

    def test_prevent_negative_raw_material_stock(self):
        """Rule: Check constraint prohibits negative raw material stock."""
        with db.get_db() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE raw_materials SET current_stock = -10.0 WHERE id = 1")

if __name__ == "__main__":
    unittest.main()
