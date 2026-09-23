-- RVKS WEB: Poultry Farm Management System Schema
-- SQLite / PostgreSQL compatible SQL schema

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'worker', -- 'owner_admin' or 'worker'
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_code VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    date_of_joining DATE NOT NULL,
    job_role VARCHAR(100) NOT NULL,
    salary_type VARCHAR(20) NOT NULL DEFAULT 'Monthly', -- 'Daily', 'Weekly', 'Monthly'
    salary_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    payment_method VARCHAR(50) DEFAULT 'Cash',
    status VARCHAR(20) NOT NULL DEFAULT 'Active', -- 'Active', 'Inactive' (Soft deletion)
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Present', -- 'Present', 'Absent', 'Half Day', 'Leave'
    check_in_time VARCHAR(10),
    check_out_time VARCHAR(10),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE,
    UNIQUE(worker_id, date)
);

CREATE TABLE IF NOT EXISTS worker_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_code VARCHAR(30) UNIQUE NOT NULL,
    worker_id INTEGER NOT NULL,
    salary_period VARCHAR(50) NOT NULL, -- e.g. "Sep 2026" or "10-09-2026 to 17-09-2026"
    payment_date DATE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL CHECK (amount >= 0),
    payment_method VARCHAR(50) NOT NULL DEFAULT 'Cash', -- 'Cash', 'UPI', 'Bank Transfer', 'Other'
    status VARCHAR(20) NOT NULL DEFAULT 'Paid', -- 'Paid', 'Pending', 'Partial'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES workers(id)
);

CREATE TABLE IF NOT EXISTS bird_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bird_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_code VARCHAR(30) UNIQUE NOT NULL,
    batch_name VARCHAR(100) NOT NULL,
    bird_type VARCHAR(50) NOT NULL,
    arrival_date DATE NOT NULL,
    initial_quantity INTEGER NOT NULL CHECK (initial_quantity >= 0),
    current_quantity INTEGER NOT NULL CHECK (current_quantity >= 0),
    source_supplier VARCHAR(100),
    shed_location VARCHAR(100),
    age_weeks INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'Active', -- 'Active', 'Culled', 'Sold', 'Completed'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bird_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    date DATE NOT NULL,
    tx_type VARCHAR(30) NOT NULL, -- 'Initial Stock', 'Birds Received', 'Transfer In', 'Transfer Out', 'Mortality', 'Sale', 'Adjustment'
    quantity INTEGER NOT NULL, -- Can be positive or negative
    balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
    reference_id VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES bird_batches(id)
);

CREATE TABLE IF NOT EXISTS mortality (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    batch_id INTEGER NOT NULL,
    bird_type VARCHAR(50) NOT NULL,
    number_of_birds INTEGER NOT NULL CHECK (number_of_birds > 0),
    reason VARCHAR(50) NOT NULL, -- 'Disease', 'Weakness', 'Accident', 'Unknown', 'Other'
    shed_location VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES bird_batches(id)
);

CREATE TABLE IF NOT EXISTS egg_production (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    batch_id INTEGER NOT NULL,
    total_eggs INTEGER NOT NULL CHECK (total_eggs >= 0),
    good_eggs INTEGER NOT NULL CHECK (good_eggs >= 0),
    broken_eggs INTEGER NOT NULL DEFAULT 0 CHECK (broken_eggs >= 0),
    damaged_eggs INTEGER NOT NULL DEFAULT 0 CHECK (damaged_eggs >= 0),
    sold_eggs INTEGER NOT NULL DEFAULT 0 CHECK (sold_eggs >= 0),
    remaining_eggs INTEGER NOT NULL DEFAULT 0 CHECK (remaining_eggs >= 0),
    selling_price DECIMAL(10, 2) DEFAULT 0.00 CHECK (selling_price >= 0),
    total_income DECIMAL(10, 2) DEFAULT 0.00 CHECK (total_income >= 0),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES bird_batches(id)
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_code VARCHAR(30) UNIQUE NOT NULL,
    supplier_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    materials_supplied TEXT, -- Comma separated or list
    status VARCHAR(20) NOT NULL DEFAULT 'Active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_code VARCHAR(30) UNIQUE NOT NULL,
    material_name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) DEFAULT 'Feed Ingredient',
    unit VARCHAR(20) NOT NULL DEFAULT 'Kg', -- 'Kg', 'Ton', 'Litre', 'Bag', 'Piece'
    minimum_stock_level DECIMAL(10, 2) NOT NULL DEFAULT 100.00 CHECK (minimum_stock_level >= 0),
    current_stock DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (current_stock >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'Normal', -- 'Normal', 'Low Stock', 'Out of Stock'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_material_purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_code VARCHAR(30) UNIQUE NOT NULL,
    purchase_date DATE NOT NULL,
    supplier_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    quantity DECIMAL(10, 2) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(20) NOT NULL DEFAULT 'Kg',
    rate_per_unit DECIMAL(10, 2) NOT NULL CHECK (rate_per_unit >= 0),
    material_cost DECIMAL(10, 2) NOT NULL CHECK (material_cost >= 0),
    transport_cost DECIMAL(10, 2) DEFAULT 0.00 CHECK (transport_cost >= 0),
    other_cost DECIMAL(10, 2) DEFAULT 0.00 CHECK (other_cost >= 0),
    total_cost DECIMAL(10, 2) NOT NULL CHECK (total_cost >= 0),
    payment_status VARCHAR(20) NOT NULL DEFAULT 'Paid', -- 'Paid', 'Pending', 'Partial'
    payment_date DATE,
    invoice_number VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (material_id) REFERENCES raw_materials(id)
);

CREATE TABLE IF NOT EXISTS raw_material_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    material_id INTEGER NOT NULL,
    movement_type VARCHAR(30) NOT NULL, -- 'Purchase', 'Production Usage', 'Adjustment', 'Opening Stock'
    quantity DECIMAL(10, 2) NOT NULL, -- Positive for in, negative for out
    balance_after DECIMAL(10, 2) NOT NULL CHECK (balance_after >= 0),
    reference_id VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (material_id) REFERENCES raw_materials(id)
);

CREATE TABLE IF NOT EXISTS feed_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feed_recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_code VARCHAR(30) UNIQUE NOT NULL,
    feed_type VARCHAR(50) NOT NULL,
    recipe_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feed_recipe_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    percentage DECIMAL(5, 2) NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
    quantity_per_100kg DECIMAL(8, 2) NOT NULL CHECK (quantity_per_100kg >= 0),
    unit VARCHAR(20) NOT NULL DEFAULT 'Kg',
    FOREIGN KEY (recipe_id) REFERENCES feed_recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES raw_materials(id)
);

CREATE TABLE IF NOT EXISTS feed_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_type VARCHAR(50) UNIQUE NOT NULL,
    current_stock DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (current_stock >= 0),
    minimum_stock_level DECIMAL(10, 2) NOT NULL DEFAULT 200.00 CHECK (minimum_stock_level >= 0),
    unit VARCHAR(20) NOT NULL DEFAULT 'Kg',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feed_production (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_code VARCHAR(30) UNIQUE NOT NULL,
    date DATE NOT NULL,
    feed_type VARCHAR(50) NOT NULL,
    batch_number VARCHAR(50) NOT NULL,
    quantity_produced DECIMAL(10, 2) NOT NULL CHECK (quantity_produced > 0),
    unit VARCHAR(20) NOT NULL DEFAULT 'Kg',
    recipe_id INTEGER,
    raw_material_cost DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (raw_material_cost >= 0),
    labour_cost DECIMAL(10, 2) DEFAULT 0.00 CHECK (labour_cost >= 0),
    electricity_cost DECIMAL(10, 2) DEFAULT 0.00 CHECK (electricity_cost >= 0),
    other_cost DECIMAL(10, 2) DEFAULT 0.00 CHECK (other_cost >= 0),
    total_cost DECIMAL(10, 2) NOT NULL CHECK (total_cost >= 0),
    cost_per_kg DECIMAL(10, 2) NOT NULL CHECK (cost_per_kg >= 0),
    produced_by VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES feed_recipes(id)
);

CREATE TABLE IF NOT EXISTS feed_stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    feed_type VARCHAR(50) NOT NULL,
    movement_type VARCHAR(30) NOT NULL, -- 'Produced', 'Used', 'Sold', 'Adjustment'
    quantity DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL CHECK (balance_after >= 0),
    reference_id VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feed_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usage_code VARCHAR(30) UNIQUE NOT NULL,
    date DATE NOT NULL,
    batch_id INTEGER NOT NULL,
    bird_type VARCHAR(50) NOT NULL,
    feed_type VARCHAR(50) NOT NULL,
    quantity DECIMAL(10, 2) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(20) NOT NULL DEFAULT 'Kg',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES bird_batches(id)
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_code VARCHAR(30) UNIQUE NOT NULL,
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL, -- 'Worker Salary', 'Raw Materials', 'Feed Production', 'Electricity', 'Water', 'Medicine', 'Transport', 'Maintenance', 'Equipment', 'Bird Purchase', 'Packaging', 'Other'
    description TEXT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL CHECK (amount >= 0),
    payment_method VARCHAR(50) DEFAULT 'Cash',
    paid_by VARCHAR(100),
    reference_id VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    income_code VARCHAR(30) UNIQUE NOT NULL,
    date DATE NOT NULL,
    source VARCHAR(50) NOT NULL, -- 'Egg Sales', 'Bird Sales', 'Feed Sales', 'Other Income'
    description TEXT NOT NULL,
    quantity DECIMAL(10, 2) DEFAULT 0.00,
    rate DECIMAL(10, 2) DEFAULT 0.00,
    amount DECIMAL(10, 2) NOT NULL CHECK (amount >= 0),
    payment_method VARCHAR(50) DEFAULT 'Cash',
    reference_id VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    username VARCHAR(50),
    action VARCHAR(50) NOT NULL, -- e.g. 'Worker Added', 'Mortality Recorded', 'Feed Produced'
    module VARCHAR(50) NOT NULL, -- 'Workers', 'Birds', 'Feed', etc.
    record_id VARCHAR(50),
    details TEXT
);

CREATE TABLE IF NOT EXISTS farm_alerts_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_key VARCHAR(50) UNIQUE NOT NULL,
    threshold_value DECIMAL(10, 2) NOT NULL,
    description TEXT
);

-- Indexes for lightning fast searches and queries
CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_attendance_worker_date ON attendance(worker_id, date);
CREATE INDEX IF NOT EXISTS idx_worker_payments_date ON worker_payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_bird_batches_status ON bird_batches(status);
CREATE INDEX IF NOT EXISTS idx_bird_tx_batch ON bird_transactions(batch_id);
CREATE INDEX IF NOT EXISTS idx_mortality_date ON mortality(date);
CREATE INDEX IF NOT EXISTS idx_egg_prod_date ON egg_production(date);
CREATE INDEX IF NOT EXISTS idx_raw_mat_purchases_date ON raw_material_purchases(purchase_date);
CREATE INDEX IF NOT EXISTS idx_feed_prod_date ON feed_production(date);
CREATE INDEX IF NOT EXISTS idx_feed_usage_date ON feed_usage(date);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
CREATE INDEX IF NOT EXISTS idx_income_date ON income(date);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
