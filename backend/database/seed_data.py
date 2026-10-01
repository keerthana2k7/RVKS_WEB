import hashlib
import os
from datetime import datetime, timedelta
try:
    from database.db import get_db, init_db, log_audit
except ImportError:
    from db import get_db, init_db, log_audit

def hash_password(password: str) -> str:
    """Generates a secure SHA-256 hash with a salt."""
    salt = "rvks_poultry_salt_2026"
    return hashlib.sha256(f"{salt}_{password}".encode("utf-8")).hexdigest()

def seed():
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if already seeded
        cursor.execute("SELECT COUNT(*) as count FROM users")
        if cursor.fetchone()["count"] > 0:
            print("[SEED] Database already contains data. Skipping.")
            return

        print("[SEED] Seeding realistic farm data...")

        # 1. Users (Admin / Farm Owner ONLY - Workers do not have user accounts)
        users = [
            ("admin", hash_password("admin123"), "Farm Owner (Admin)", "owner_admin")
        ]
        cursor.executemany(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            users
        )

        # 2. Bird Types
        bird_types = [
            ("Chick", "Young chicks from 0 to 8 weeks old"),
            ("Layer", "Egg-laying hens in active production phase"),
            ("EDD", "Early Development / Dual-purpose specialized high-yield breed")
        ]
        cursor.executemany(
            "INSERT INTO bird_types (type_name, description) VALUES (?, ?)",
            bird_types
        )

        # 3. Bird Batches
        batches = [
            ("BATCH-001", "EDD Batch 1", "EDD", "2026-05-01", 3200, 3165, "Venkateshwara Hatcheries", "Shed 1 - East", 20, "Active", "High egg production batch"),
            ("BATCH-002", "EDD Batch 2", "EDD", "2026-06-15", 2800, 2780, "Suguna Poultry", "Shed 2 - Central", 14, "Active", "Second EDD flock"),
            ("BATCH-003", "EDD Batch 3", "EDD", "2026-08-01", 3000, 2990, "Venkateshwara Hatcheries", "Shed 3 - West", 7, "Active", "Recent EDD flock"),
            ("BATCH-004", "Chick Batch 2026-A", "Chick", "2026-09-01", 1500, 1492, "Kaveri Chicks", "Brooder Shed", 2, "Active", "Day-old chicks in brooding phase"),
            ("BATCH-005", "Layer Shed 4", "Layer", "2026-03-10", 4200, 4120, "Suguna Poultry", "Shed 4 - North", 27, "Active", "Peak laying cycle hens")
        ]
        cursor.executemany("""
            INSERT INTO bird_batches (batch_code, batch_name, bird_type, arrival_date, initial_quantity, current_quantity, source_supplier, shed_location, age_weeks, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batches)

        # 4. Bird Transactions (Initial Stock & Movements)
        for i in range(1, 6):
            b = batches[i-1]
            cursor.execute("""
                INSERT INTO bird_transactions (batch_id, date, tx_type, quantity, balance_after, reference_id, notes)
                VALUES (?, ?, 'Initial Stock', ?, ?, ?, 'Initial flock arrival')
            """, (i, b[3], b[4], b[4], b[0]))

        # 5. Mortality Records
        mortalities = [
            ("2026-09-15", 1, "EDD", 3, "Weakness", "Shed 1 - East", "Heat stress symptoms"),
            ("2026-09-16", 1, "EDD", 2, "Disease", "Shed 1 - East", "Respiratory infection isolated"),
            ("2026-09-17", 2, "EDD", 4, "Accident", "Shed 2 - Central", "Water nipple leakage trap"),
            ("2026-09-18", 4, "Chick", 5, "Weakness", "Brooder Shed", "Normal early chick culling"),
            ("2026-09-19", 5, "Layer", 2, "Other", "Shed 4 - North", "Egg bound complication")
        ]
        for m in mortalities:
            cursor.execute("""
                INSERT INTO mortality (date, batch_id, bird_type, number_of_birds, reason, shed_location, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, m)
            cursor.execute("""
                INSERT INTO bird_transactions (batch_id, date, tx_type, quantity, balance_after, reference_id, notes)
                VALUES (?, ?, 'Mortality', ?, (SELECT current_quantity FROM bird_batches WHERE id = ?), 'MORT', ?)
            """, (m[1], m[0], -m[3], m[1], m[5]))

        # 6. Workers (Data records managed by Admin ONLY)
        workers = [
            ("WRK-001", "Murugan K", "9842111222", "12 Farm Road, Rasipuram", "2024-01-10", "Farm Supervisor", "Monthly", 18000.00, "Paid", "2026-09-02", "Bank Transfer", "Active", "Overall supervisor and feed master"),
            ("WRK-002", "Selvam R", "9842133444", "45 North Street, Namakkal", "2024-03-15", "Feed Mill Operator", "Monthly", 15000.00, "Paid", "2026-09-03", "UPI", "Active", "Operates feed grinding and mixer units"),
            ("WRK-003", "Priya S", "9842155666", "7 West Kadu, Rasipuram", "2024-06-01", "Egg Collector & Grader", "Monthly", 12000.00, "Paid", "2026-09-03", "Cash", "Active", "Egg collection, grading and tray packing"),
            ("WRK-004", "Ramesh P", "9842177888", "18 Perumal Kovil St, Puduchatram", "2025-02-10", "Shed Caretaker", "Daily", 550.00, "Paid", "2026-09-08", "Cash", "Active", "Litter management and water inspection"),
            ("WRK-005", "Kumar M", "9842199000", "88 East Street, Rasipuram", "2025-05-20", "General Farm Hand", "Daily", 500.00, "Paid", "2026-09-15", "Cash", "Active", "Unloading grain bags and cleaning")
        ]
        cursor.executemany("""
            INSERT INTO workers (worker_code, name, phone, address, date_of_joining, job_role, salary_type, salary_amount, payment_status, payment_date, payment_method, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, workers)

        # 7. Attendance for last 3 days
        today = datetime.now().date()
        for offset in range(3, -1, -1):
            att_date = (today - timedelta(days=offset)).isoformat()
            cursor.execute("INSERT OR IGNORE INTO attendance (worker_id, date, status, check_in_time, check_out_time, notes) VALUES (1, ?, 'Present', '06:30', '18:00', 'Full day shift')", (att_date,))
            cursor.execute("INSERT OR IGNORE INTO attendance (worker_id, date, status, check_in_time, check_out_time, notes) VALUES (2, ?, 'Present', '07:00', '17:30', 'Feed mill operation')", (att_date,))
            cursor.execute("INSERT OR IGNORE INTO attendance (worker_id, date, status, check_in_time, check_out_time, notes) VALUES (3, ?, 'Present', '07:30', '16:00', 'Egg sorting done')", (att_date,))
            cursor.execute("INSERT OR IGNORE INTO attendance (worker_id, date, status, check_in_time, check_out_time, notes) VALUES (4, ?, 'Present', '07:00', '17:00', 'Shed 1 and 2 check')", (att_date,))
            if offset == 1:
                cursor.execute("INSERT OR IGNORE INTO attendance (worker_id, date, status, check_in_time, check_out_time, notes) VALUES (5, ?, 'Leave', NULL, NULL, 'Family function')", (att_date,))
            else:
                cursor.execute("INSERT OR IGNORE INTO attendance (worker_id, date, status, check_in_time, check_out_time, notes) VALUES (5, ?, 'Present', '08:00', '17:00', 'Unloaded raw materials')", (att_date,))

        # 8. Worker Payments
        payments = [
            ("PMT-001", 1, "Aug 2026", "2026-09-02", 18000.00, "Bank Transfer", "Paid", "Monthly salary paid on time"),
            ("PMT-002", 2, "Aug 2026", "2026-09-03", 15000.00, "UPI", "Paid", "Monthly salary transferred to GPay"),
            ("PMT-003", 3, "Aug 2026", "2026-09-03", 12000.00, "Cash", "Paid", "Cash paid to Priya"),
            ("PMT-004", 4, "01-09-2026 to 07-09-2026", "2026-09-08", 3850.00, "Cash", "Paid", "Weekly daily wage settled (7 days)"),
            ("PMT-005", 5, "08-09-2026 to 14-09-2026", "2026-09-15", 3500.00, "Cash", "Paid", "Weekly wage settled")
        ]
        cursor.executemany("""
            INSERT INTO worker_payments (payment_code, worker_id, salary_period, payment_date, amount, payment_method, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, payments)

        # 9. Suppliers
        suppliers = [
            ("SUP-001", "Tamil Nadu Agro Commodities", "9842123456", "Mettupalayam Road, Coimbatore", "Maize, Soybean Meal, Wheat", "Active", "Primary grain supplier with bulk delivery"),
            ("SUP-002", "Salem Rice & Oil Mills", "9443278901", "Shevapet, Salem", "De-oiled Rice Bran, Vegetable Oil", "Active", "Regular weekly supplier for bran"),
            ("SUP-003", "Namakkal Poultry Nutrition Ltd", "9789045678", "Paramathi Road, Namakkal", "Limestone, DCP, Minerals, Vitamins, Salt", "Active", "Certificated mineral premix provider")
        ]
        cursor.executemany("""
            INSERT INTO suppliers (supplier_code, supplier_name, phone, address, materials_supplied, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, suppliers)

        # 10. Raw Materials
        materials = [
            ("MAT-001", "Maize (Yellow Corn)", "Grains", "Kg", 2000.00, 8500.00, "Normal", "Key energy source for feed"),
            ("MAT-002", "Soybean Meal (46% Protein)", "Proteins", "Kg", 1000.00, 4200.00, "Normal", "Key protein supplement"),
            ("MAT-003", "De-oiled Rice Bran (DORB)", "Fiber/Energy", "Kg", 800.00, 3800.00, "Normal", "Digestible fiber and energy"),
            ("MAT-004", "Wheat", "Grains", "Kg", 500.00, 2000.00, "Normal", "Energy and carbohydrate grain"),
            ("MAT-005", "Calcite / Limestone Grit", "Minerals", "Kg", 400.00, 1500.00, "Normal", "Essential calcium for eggshell strength"),
            ("MAT-006", "Di-Calcium Phosphate (DCP)", "Minerals", "Kg", 200.00, 650.00, "Normal", "Bioavailable phosphorus and calcium"),
            ("MAT-007", "Trace Minerals & Vitamin Premix", "Supplements", "Kg", 100.00, 250.00, "Normal", "Essential micronutrients"),
            ("MAT-008", "Refined Salt", "Minerals", "Kg", 100.00, 300.00, "Normal", "Sodium chloride mineral balance"),
            ("MAT-009", "Vegetable Oil", "Liquids", "Litre", 150.00, 450.00, "Normal", "Calorie booster and dust binder")
        ]
        cursor.executemany("""
            INSERT INTO raw_materials (material_code, material_name, category, unit, minimum_stock_level, current_stock, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, materials)

        # 11. Raw Material Purchases
        purchases = [
            ("PUR-001", "2026-09-05", 1, 1, 5000.00, "Kg", 24.50, 122500.00, 3500.00, 500.00, 126500.00, "Paid", "2026-09-05", "INV-8891", "Bulk maize truck delivered"),
            ("PUR-002", "2026-09-08", 1, 2, 2500.00, "Kg", 48.00, 120000.00, 2000.00, 0.00, 122000.00, "Paid", "2026-09-08", "INV-8914", "Soybean meal 50kg bags"),
            ("PUR-003", "2026-09-10", 2, 3, 2000.00, "Kg", 16.50, 33000.00, 1500.00, 0.00, 34500.00, "Paid", "2026-09-10", "INV-341", "DORB delivered"),
            ("PUR-004", "2026-09-14", 3, 5, 1000.00, "Kg", 5.50, 5500.00, 500.00, 0.00, 6000.00, "Paid", "2026-09-14", "INV-552", "Limestone grit for layer sheds")
        ]
        cursor.executemany("""
            INSERT INTO raw_material_purchases (purchase_code, purchase_date, supplier_id, material_id, quantity, unit, rate_per_unit, material_cost, transport_cost, other_cost, total_cost, payment_status, payment_date, invoice_number, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, purchases)

        # Record purchases in expenses
        for p in purchases:
            cursor.execute("""
                INSERT INTO expenses (expense_code, date, category, description, amount, payment_method, paid_by, reference_id, notes)
                VALUES (?, ?, 'Raw Materials', ?, ?, 'Bank Transfer', 'Owner', ?, 'Automated purchase entry')
            """, (f"EXP-{p[0]}", p[1], f"Raw material purchase: {p[0]}", p[10], p[0]))

        # 12. Feed Types & Stock
        feed_types = [
            ("Chick Feed", "High-protein starter mash for chicks up to 8 weeks", 950.00, 300.00),
            ("Layer Feed", "Standard balanced mash for commercial egg layers", 2400.00, 500.00),
            ("EDD Feed", "High energy and nutrient-dense mash formulated for EDD flocks", 3100.00, 600.00),
            ("Custom Feed", "Experimental trial feed mixture", 150.00, 100.00)
        ]
        for ft in feed_types:
            cursor.execute("INSERT INTO feed_types (type_name, description) VALUES (?, ?)", (ft[0], ft[1]))
            cursor.execute("INSERT INTO feed_stock (feed_type, current_stock, minimum_stock_level) VALUES (?, ?, ?)", (ft[0], ft[2], ft[3]))

        # 13. Feed Recipes
        recipes = [
            ("RCP-001", "Layer Feed", "Standard Layer Mash (100kg Basis)", "Standard balanced formulation for regular layers"),
            ("RCP-002", "EDD Feed", "EDD High-Yield Formula (100kg Basis)", "Proprietary high-density recipe for EDD 1, 2, 3 batches"),
            ("RCP-003", "Chick Feed", "Chick Starter Mash (100kg Basis)", "High protein recipe for young growing chicks")
        ]
        cursor.executemany("""
            INSERT INTO feed_recipes (recipe_code, feed_type, recipe_name, description)
            VALUES (?, ?, ?, ?)
        """, recipes)

        # Recipe Items (Ingredients)
        # Layer Feed: Maize 55%, Soy 25%, Rice Bran 12%, Limestone 5%, DCP 1.5%, Minerals 1%, Salt 0.5%
        layer_items = [
            (1, 1, 55.00, 55.00),
            (1, 2, 25.00, 25.00),
            (1, 3, 12.00, 12.00),
            (1, 5, 5.00, 5.00),
            (1, 6, 1.50, 1.50),
            (1, 7, 1.00, 1.00),
            (1, 8, 0.50, 0.50)
        ]
        # EDD Feed: Maize 52%, Soy 28%, Rice Bran 10%, Limestone 6%, DCP 2%, Minerals 1.5%, Salt 0.5%
        edd_items = [
            (2, 1, 52.00, 52.00),
            (2, 2, 28.00, 28.00),
            (2, 3, 10.00, 10.00),
            (2, 5, 6.00, 6.00),
            (2, 6, 2.00, 2.00),
            (2, 7, 1.50, 1.50),
            (2, 8, 0.50, 0.50)
        ]
        # Chick Starter: Maize 58%, Soy 32%, Wheat 5%, DCP 2%, Minerals 2%, Salt 1%
        chick_items = [
            (3, 1, 58.00, 58.00),
            (3, 2, 32.00, 32.00),
            (3, 4, 5.00, 5.00),
            (3, 6, 2.00, 2.00),
            (3, 7, 2.00, 2.00),
            (3, 8, 1.00, 1.00)
        ]
        for itm in layer_items + edd_items + chick_items:
            cursor.execute("""
                INSERT INTO feed_recipe_items (recipe_id, material_id, percentage, quantity_per_100kg, unit)
                VALUES (?, ?, ?, ?, 'Kg')
            """, itm)

        # 14. Feed Production History
        feed_productions = [
            ("FPR-001", "2026-09-12", "Layer Feed", "PROD-2609-01", 1000.00, "Kg", 1, 28500.00, 400.00, 300.00, 100.00, 29300.00, 29.30, "Selvam R", "1 Ton Layer Feed batch produced"),
            ("FPR-002", "2026-09-16", "EDD Feed", "PROD-2609-02", 1500.00, "Kg", 2, 45200.00, 600.00, 450.00, 150.00, 46400.00, 30.93, "Selvam R", "1.5 Ton EDD feed produced for Batches 1, 2, 3")
        ]
        cursor.executemany("""
            INSERT INTO feed_production (production_code, date, feed_type, batch_number, quantity_produced, unit, recipe_id, raw_material_cost, labour_cost, electricity_cost, other_cost, total_cost, cost_per_kg, produced_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, feed_productions)

        # 15. Feed Usage History
        feed_usages = [
            ("FUS-001", "2026-09-17", 1, "EDD", "EDD Feed", 350.00, "Kg", "Morning and evening feed for EDD Batch 1"),
            ("FUS-002", "2026-09-17", 2, "EDD", "EDD Feed", 310.00, "Kg", "Feed for EDD Batch 2"),
            ("FUS-003", "2026-09-17", 3, "EDD", "EDD Feed", 330.00, "Kg", "Feed for EDD Batch 3"),
            ("FUS-004", "2026-09-18", 1, "EDD", "EDD Feed", 350.00, "Kg", "Daily feeding"),
            ("FUS-005", "2026-09-18", 5, "Layer", "Layer Feed", 460.00, "Kg", "Feeding for Layer Shed 4"),
            ("FUS-006", "2026-09-19", 1, "EDD", "EDD Feed", 350.00, "Kg", "Today's feed EDD Batch 1"),
            ("FUS-007", "2026-09-19", 2, "EDD", "EDD Feed", 310.00, "Kg", "Today's feed EDD Batch 2"),
            ("FUS-008", "2026-09-19", 3, "EDD", "EDD Feed", 330.00, "Kg", "Today's feed EDD Batch 3")
        ]
        cursor.executemany("""
            INSERT INTO feed_usage (usage_code, date, batch_id, bird_type, feed_type, quantity, unit, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, feed_usages)

        # 16. Egg Production History (past 7 days)
        egg_data = []
        selling_price = 5.50
        for day_offset in range(7, -1, -1):
            prod_date = (today - timedelta(days=day_offset)).isoformat()
            # EDD Batch 1 (~3165 birds -> ~2900 eggs)
            tot1 = 2920 - (day_offset * 10)
            good1 = tot1 - 25
            broken1 = 15
            dam1 = 10
            sold1 = good1 if day_offset > 0 else 2500
            rem1 = good1 - sold1
            inc1 = sold1 * selling_price
            egg_data.append((prod_date, 1, tot1, good1, broken1, dam1, sold1, rem1, selling_price, inc1, "EDD Batch 1 collection"))

            # EDD Batch 2 (~2780 birds -> ~2500 eggs)
            tot2 = 2510 - (day_offset * 8)
            good2 = tot2 - 20
            broken2 = 12
            dam2 = 8
            sold2 = good2 if day_offset > 0 else 2200
            rem2 = good2 - sold2
            inc2 = sold2 * selling_price
            egg_data.append((prod_date, 2, tot2, good2, broken2, dam2, sold2, rem2, selling_price, inc2, "EDD Batch 2 collection"))

            # EDD Batch 3 (~2990 birds -> ~2600 eggs)
            tot3 = 2650 - (day_offset * 12)
            good3 = tot3 - 22
            broken3 = 14
            dam3 = 8
            sold3 = good3 if day_offset > 0 else 2300
            rem3 = good3 - sold3
            inc3 = sold3 * selling_price
            egg_data.append((prod_date, 3, tot3, good3, broken3, dam3, sold3, rem3, selling_price, inc3, "EDD Batch 3 collection"))

            # Layer Shed 4 (~4120 birds -> ~3800 eggs)
            tot4 = 3820 - (day_offset * 15)
            good4 = tot4 - 30
            broken4 = 18
            dam4 = 12
            sold4 = good4 if day_offset > 0 else 3400
            rem4 = good4 - sold4
            inc4 = sold4 * selling_price
            egg_data.append((prod_date, 5, tot4, good4, broken4, dam4, sold4, rem4, selling_price, inc4, "Layer Shed 4 collection"))

        cursor.executemany("""
            INSERT INTO egg_production (date, batch_id, total_eggs, good_eggs, broken_eggs, damaged_eggs, sold_eggs, remaining_eggs, selling_price, total_income, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, egg_data)

        # Record egg income in income table
        for eg in egg_data:
            if eg[6] > 0:
                cursor.execute("""
                    INSERT INTO income (income_code, date, source, description, quantity, rate, amount, payment_method, notes)
                    VALUES (?, ?, 'Egg Sales', ?, ?, ?, ?, 'UPI', 'Egg buyer dispatch')
                """, (f"INC-EGG-{eg[0]}-{eg[1]}", eg[0], f"Egg sale: Batch {eg[1]} ({eg[6]} eggs)", eg[6], eg[8], eg[9]))

        # 17. Farm Expenses & Other Income
        other_expenses = [
            ("EXP-001", "2026-09-02", "Electricity", "TNEB Farm Power Bill for August", 14500.00, "Bank Transfer", "Owner", "Meter #4881"),
            ("EXP-002", "2026-09-06", "Medicine", "Vaccines and Vitamin Liquid for Brooder", 4200.00, "Cash", "Supervisor", "Veterinary pharmacy"),
            ("EXP-003", "2026-09-11", "Transport", "Diesel for Farm tractor and mini truck", 3500.00, "UPI", "Selvam R", "IOCL petrol pump"),
            ("EXP-004", "2026-09-15", "Packaging", "Egg paper trays 2000 nos", 5000.00, "Cash", "Supervisor", "Tray carton supply"),
            ("EXP-005", "2026-09-18", "Maintenance", "Water nipple line repair & fogger nozzle clean", 1800.00, "Cash", "Ramesh P", "Plumbing spares")
        ]
        cursor.executemany("""
            INSERT INTO expenses (expense_code, date, category, description, amount, payment_method, paid_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, other_expenses)

        # Add initial audit logs
        log_audit("System Initialized", "System", "INIT", "Pre-loaded real farm operational data", conn=conn)
        log_audit("Batches Configured", "Birds", "BATCH-001", "EDD Batches 1, 2, 3 registered", conn=conn)
        log_audit("Feed Recipes Activated", "Feed", "RCP-002", "EDD High-Yield Recipe configured", conn=conn)

        print("[SEED] Seeding completed successfully!")

if __name__ == "__main__":
    seed()
