import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "farm.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(raw_material_purchases)")
    cols = [r[1] for r in cursor.fetchall()]

    new_cols = [
        ("deal_date", "DATE"),
        ("expected_delivery_date", "DATE"),
        ("actual_delivery_date", "DATE"),
        ("advance_paid", "DECIMAL(10, 2) DEFAULT 0.00"),
        ("amount_paid", "DECIMAL(10, 2) DEFAULT 0.00"),
        ("amount_pending", "DECIMAL(10, 2) DEFAULT 0.00"),
        ("payment_due_date", "DATE"),
        ("payment_method", "VARCHAR(30) DEFAULT 'Bank Transfer'")
    ]

    for col_name, col_type in new_cols:
        if col_name not in cols:
            cursor.execute(f"ALTER TABLE raw_material_purchases ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name}")

    cursor.execute("UPDATE raw_material_purchases SET deal_date = purchase_date WHERE deal_date IS NULL")

    cursor.execute("""
        UPDATE raw_material_purchases 
        SET amount_paid = CASE 
                WHEN payment_status = 'Paid' THEN total_cost 
                WHEN payment_status IN ('Partial', 'Partially Paid') THEN ROUND(total_cost * 0.5, 2)
                ELSE 0.00 
            END,
            payment_status = CASE
                WHEN payment_status = 'Partial' THEN 'Partially Paid'
                ELSE payment_status
            END
    """)

    cursor.execute("UPDATE raw_material_purchases SET amount_pending = MAX(0, total_cost - amount_paid)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deal_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_code VARCHAR(30) UNIQUE NOT NULL,
        deal_id INTEGER NOT NULL,
        supplier_id INTEGER NOT NULL,
        payment_date DATE NOT NULL,
        payment_type VARCHAR(30) NOT NULL,
        amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
        payment_method VARCHAR(30) NOT NULL DEFAULT 'Bank Transfer',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (deal_id) REFERENCES raw_material_purchases(id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM deal_payments")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id, purchase_code, purchase_date, supplier_id, total_cost, amount_paid FROM raw_material_purchases WHERE amount_paid > 0")
        purchases = cursor.fetchall()
        for idx, p in enumerate(purchases, 1):
            cursor.execute("""
                INSERT INTO deal_payments (payment_code, deal_id, supplier_id, payment_date, payment_type, amount, payment_method, notes)
                VALUES (?, ?, ?, ?, 'Payment', ?, 'Bank Transfer', 'Initial settlement')
            """, (f"DPAY-{idx:04d}", p[0], p[3], p[2], p[5]))
        print(f"Populated {len(purchases)} initial deal payments.")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
