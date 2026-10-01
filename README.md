# RVKS WEB
### Poultry Farm Management System

A production-grade, practical livestock and on-farm feed mill operations platform for **RVKS WEB**, specifically designed for real family poultry farm management and feed production.

---

## 🌟 Key Highlights & Features

### 1. Simple User Experience for Farm Owners
- **Touch-Optimized Large Action Buttons**: Common daily operations (Mortality, Egg Production, Attendance, Feed Usage, Feed Production) require just 1–2 clicks.
- **Clear Labels & Clean Visual Hierarchy**: High contrast text, pre-filled sensible defaults, clear confirmation dialogs, and instant visual status indicators.
- **Localized Standards**:
  - Currency: **₹ INR**
  - Dates: **DD-MM-YYYY** (Asia/Kolkata timezone)
  - Plain English (structured for upcoming Tamil language i18n support)

### 2. Live Flock Population & Mortality Management
- **Flock Categorization**: Chicks, Layers, EDD (Early Development / Dual-purpose), and custom breeds.
- **Dynamic Batches**: Unlimited batches (including pre-configured **EDD Batch 1**, **EDD Batch 2**, and **EDD Batch 3**).
- **Audit-Proof Bird Movements**: Tracks Initial Stock, Birds Received, Mortality, Sales, Transfers, and Adjustments.
- **Atomic Mortality Logging**: Automatically deducts from flock batch count, prevents negative bird counts with database check constraints, and generates high-mortality alerts when daily losses cross safety thresholds.

### 3. Egg Production & Sales
- Daily egg collection logs tracking **Good Eggs**, **Broken Eggs**, **Damaged Eggs**, **Eggs Sold**, and **Remaining Trays**.
- Automatic revenue calculations based on current market selling price per egg.
- Production and sales trends visualized through interactive 14-day charts.

### 4. Feed Mill & Self-Formulated Feed Production
- **Custom Feed Recipes**: Configurable ingredient percentages for Layer Mash, EDD High-Yield Recipe, Chick Starter, and custom mixes.
- **Stock Shortage Prevention Engine**: Validates raw material reserves (Maize, Soybean Meal, Rice Bran, DCP, Limestone, Minerals & Salt) before milling starts.
  - If any ingredient is insufficient, the system halts and presents exact required vs available vs shortage quantities (e.g., *"Maize required: 500 kg, Available: 300 kg, Shortage: 200 kg"*).
- **Automated Cost-Per-Kg Accounting**: Aggregates grain costs, milling labour, and electricity into total production cost and cost-per-kg.
- **Feed Usage Tracking**: Records daily feed distributed to each shed and deducts from finished feed reserves in real time.

### 5. Raw Material Supply & Supplier Tracking
- Tracks purchases, invoices, unit rates, transport costs, and payment settlements.
- Supplier history view answering: *What did we get? From whom? When? How much did it cost? How much has been paid? How much is pending?*

### 6. Workers & Payroll
- Worker profiles with daily, weekly, and monthly wage settings.
- Daily attendance tracking (Present, Absent, Half Day, Leave) with duplicate prevention (1 record per worker per day) and monthly percentage summaries.
- Historical wage payment records preserved permanently without overwriting past paystubs.

### 7. Farm Financial Summary & 360° Reports
- Net balance calculation: **`Net Balance = Total Income - Total Expenses`**.
- Multi-dimensional reporting with date range and category filters for Workers, Attendance, Birds, Eggs, Raw Materials, Feed, Expenses, and Financial statements.
- One-click export to **CSV (Excel compatible)** and **Print / PDF**.

### 8. Mobile / Android & Offline Sync
- **Progressive Web App (PWA)**: Works natively on Android devices (Chrome / Android browser -> *Add to Home Screen*).
- **Offline Storage Queue**: If shed or field internet is lost, records for Attendance, Mortality, Egg Production, and Feed Usage are saved locally in **IndexedDB**.
- **Auto Sync**: When internet reconnects, queued records are automatically dispatched to `/api/sync` without duplicate entries.
- Status badges: `Online`, `Offline`, `Pending Sync (N)`, and `Synced ✓`.

---

## 🔐 Access Credentials (Admin / Farm Owner Only)

| Role | Username | Password | System Access Level |
| :--- | :--- | :--- | :--- |
| **Farm Owner (Admin)** | `admin` | `admin123` | **Single System Administrator**: Complete control over livestock batches, feed mill, raw materials, inventory, worker records, payroll settlements, farm expenses, and financial balance. |

> [!NOTE]
> **Strict Access Control Requirement**: Only the Farm Owner (Admin) has system login credentials. There is **NO worker login or worker account system**. Workers exist purely as internal employee records created, edited, and monitored by the Farm Owner.

---

## 🚀 Getting Started

### Option A: Local Development (Windows / Linux / Mac)

1. **Prerequisites**: Python 3.10+ installed.
2. **Install Python Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Start the Application Server**:
   ```powershell
   python backend/app.py
   ```
4. **Open in Browser**:
   Open [http://localhost:5000](http://localhost:5000)

The server will automatically initialize the database schema and load realistic seed data on first run.

---

### Option B: Docker Deployment

1. **Start the Container**:
   ```bash
   docker compose up --build -d
   ```
2. **View Logs**:
   ```bash
   docker compose logs -f
   ```
3. **Open Application**:
   Visit [http://localhost:5000](http://localhost:5000)

Database records are persisted in the named Docker volume `farm_data`.

---

## 🧪 Running Automated Tests

The application includes unit and integration test suites validating database constraints, stock deductions, shortage validations, and role restrictions:

```powershell
# Run business logic tests
python -m unittest backend/tests/test_farm_logic.py

# Run API integration tests
python -m unittest backend/tests/test_api.py
```

---

## 📁 Project Architecture

```
RVKS_WEB/
├── backend/
│   ├── database/
│   │   ├── schema.sql           # Complete relational schema (indexes, check constraints, WAL)
│   │   ├── db.py                # Connection manager, transactions & audit logging
│   │   ├── seed_data.py         # Realistic flock, worker, feed and supplier seed data
│   │   └── farm.db              # SQLite production database (auto-created)
│   ├── routes/
│   │   ├── auth.py              # User authentication, tokens & role gates
│   │   ├── dashboard.py         # Real-time KPI summaries, charts & active alert triggers
│   │   ├── workers.py           # Worker directory, daily/bulk attendance, wage payments
│   │   ├── birds.py             # Flocks, batch management, movements & atomic mortality
│   │   ├── eggs.py              # Egg production, grading, sales & income
│   │   ├── raw_materials.py     # Grain inventory, suppliers & purchase invoices
│   │   ├── feed.py              # Recipes, milling validation engine, feed stock & usage
│   │   ├── finance.py           # Expenses, revenue & net financial balance
│   │   ├── reports.py           # Multi-dimensional reports & CSV/Excel export
│   │   └── sync.py              # Offline sync batch processor
│   ├── tests/
│   │   ├── test_farm_logic.py   # Business logic & constraint unit tests
│   │   └── test_api.py          # API integration and security tests
│   └── app.py                   # Master Flask server & static asset host
├── frontend/
│   ├── pages/                   # Modular Page Views
│   │   ├── login.html           # Dedicated Login Card & Quick-Role Fill
│   │   ├── dashboard.html       # Live KPI Summary & Charts
│   │   ├── workers.html         # Worker Directory & Actions
│   │   ├── attendance.html      # Daily Attendance Marking Table
│   │   ├── payments.html        # Wage Settlements & Payroll
│   │   ├── batches.html         # Bird Batches & Shed Allocation
│   │   ├── mortality.html       # Mortality Log & Alerts
│   │   ├── eggs.html            # Egg Collection, Grading & Sales
│   │   ├── suppliers.html       # Raw Material Suppliers
│   │   ├── raw_materials.html   # Grain & Ingredient Reserves
│   │   ├── purchases.html       # Supplier Purchase Invoices
│   │   ├── feed_recipes.html    # Feed Formulations & Mash Ratios
│   │   ├── feed_production.html # Feed Milling Batches & Cost/Kg
│   │   ├── feed_stock.html      # Finished Feed Inventory
│   │   ├── feed_usage.html      # Daily Feeding Distribution
│   │   ├── expenses.html        # Operational Farm Expenses
│   │   ├── income.html          # Revenue & Sales Dispatches
│   │   ├── reports.html         # 360° Reports & CSV/PDF Export
│   │   ├── audit.html           # System Audit Logs
│   │   └── profile.html         # Farm Owner Settings & Access Control
│   ├── components/              # Reusable Shared Components
│   │   ├── navbar.html          # Header with Brand, Sync & User Status
│   │   ├── sidebar.html         # 18-View Navigation Menu & Roles
│   │   ├── footer.html          # Responsive Application Footer
│   │   ├── modals.html          # 11 Operational Action Forms
│   │   └── toast.html           # Toast Notification Container
│   ├── css/                     # Modular CSS Stylesheets
│   │   ├── style.css            # Tokens, Themes & Layout Fundamentals
│   │   ├── components.css       # Buttons, Cards, Modals & Forms
│   │   ├── pages.css            # Page-Specific Layouts & Charts
│   │   ├── responsive.css       # Tablet, Mobile & Print Queries
│   │   └── index.css            # Master Bundle (Backward Compatibility)
│   ├── js/                      # Modular JavaScript Architecture
│   │   ├── main.js              # Central App Router & Coordinator
│   │   ├── components.js        # Component Loader & Event Delegator
│   │   ├── auth.js              # Login, Role Gating & Permissions
│   │   ├── dashboard.js         # Real-Time Dashboard KPI Loader
│   │   ├── api.js               # REST Client & Token Interceptor
│   │   ├── utils.js             # Date, Currency & Modal Helpers
│   │   ├── charts.js            # Interactive Chart.js Visualizations
│   │   ├── offline_sync.js      # IndexedDB Offline Sync Queue
│   │   └── app.js               # Master Export (Backward Compatibility)
│   ├── assets/                  # Media & Static Assets
│   │   ├── icons/               # PWA Icons (192x192, 512x512)
│   │   ├── images/              # Farm Visuals & Documentation Images
│   │   └── fonts/               # Typography Assets
│   ├── manifest.json            # PWA Manifest for Android Installation
│   ├── sw.js                    # Service Worker for Offline Asset Caching
│   └── index.html               # Streamlined SPA Shell & Layout Mounts
├── Dockerfile                   # Production Docker container build
├── docker-compose.yml           # Multi-platform Docker Compose deployment
├── requirements.txt             # Python backend dependencies
└── README.md                    # System documentation
```

---

## 💾 Database Backup & Restore

### Backup
To create a live point-in-time backup:
```powershell
copy backend\database\farm.db backend\database\farm_backup_%date%.db
```

### Restore
To restore from backup:
```powershell
copy backend\database\farm_backup_YYYY-MM-DD.db backend\database\farm.db
```

---

## 📱 Android Installation Instructions
1. Connect your Android phone to the same local WiFi network as the server (or host on a farm cloud/LAN IP).
2. Open Chrome on the Android device and browse to `http://<SERVER_IP>:5000`.
3. Tap the Chrome menu (three dots `⋮`) and select **"Add to Home Screen"** or **"Install App"**.
4. Launch **RVKS Farm** directly from the home screen icon for full-screen touch operation.
