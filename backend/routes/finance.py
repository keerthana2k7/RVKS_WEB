from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from database.db import get_db, log_audit
from routes.auth import login_required, admin_required

finance_bp = Blueprint("finance", __name__, url_prefix="/api/finance")

# ----------------- EXPENSES ----------------- #

@finance_bp.route("/expenses", methods=["GET"])
@admin_required
def get_expenses():
    category = request.args.get("category")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if from_date:
        query += " AND date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND date <= ?"
        params.append(to_date)
        
    query += " ORDER BY date DESC, id DESC LIMIT 100"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        expenses = cursor.fetchall()
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses")
        total_all = cursor.fetchone()["total"]
        
    return jsonify({"expenses": expenses, "total": total_all})

@finance_bp.route("/expenses", methods=["POST"])
@admin_required
def add_expense():
    data = request.get_json() or {}
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    category = data.get("category", "Other").strip()
    description = data.get("description", "").strip()
    amount = float(data.get("amount", 0.0))
    payment_method = data.get("payment_method", "Cash")
    paid_by = data.get("paid_by", "Owner")
    notes = data.get("notes", "").strip()
    
    if not description or amount <= 0:
        return jsonify({"error": "Description and valid positive amount are required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM expenses")
        next_num = cursor.fetchone()["count"] + 1
        expense_code = f"EXP-{next_num:03d}"
        
        cursor.execute("""
            INSERT INTO expenses (expense_code, date, category, description, amount, payment_method, paid_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (expense_code, date, category, description, amount, payment_method, paid_by, notes))
        
        exp_id = cursor.lastrowid
        log_audit("Expense Added", "Finance", expense_code, f"Added ₹{amount} for {category}: {description}", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Expense {expense_code} recorded successfully", "expense_code": expense_code}), 201

# ----------------- INCOME ----------------- #

@finance_bp.route("/income", methods=["GET"])
@admin_required
def get_income():
    source = request.args.get("source")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    
    query = "SELECT * FROM income WHERE 1=1"
    params = []
    if source:
        query += " AND source = ?"
        params.append(source)
    if from_date:
        query += " AND date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND date <= ?"
        params.append(to_date)
        
    query += " ORDER BY date DESC, id DESC LIMIT 100"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        incomes = cursor.fetchall()
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM income")
        total_all = cursor.fetchone()["total"]
        
    return jsonify({"incomes": incomes, "total": total_all})

@finance_bp.route("/income", methods=["POST"])
@admin_required
def add_income():
    data = request.get_json() or {}
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    source = data.get("source", "Other Income").strip()
    description = data.get("description", "").strip()
    quantity = float(data.get("quantity", 0.0))
    rate = float(data.get("rate", 0.0))
    amount = float(data.get("amount", 0.0))
    payment_method = data.get("payment_method", "Cash")
    notes = data.get("notes", "").strip()
    
    if amount <= 0 and (quantity > 0 and rate > 0):
        amount = round(quantity * rate, 2)
        
    if not description or amount <= 0:
        return jsonify({"error": "Description and positive amount are required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM income")
        next_num = cursor.fetchone()["count"] + 1
        income_code = f"INC-{next_num:03d}"
        
        cursor.execute("""
            INSERT INTO income (income_code, date, source, description, quantity, rate, amount, payment_method, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (income_code, date, source, description, quantity, rate, amount, payment_method, notes))
        
        inc_id = cursor.lastrowid
        log_audit("Income Added", "Finance", income_code, f"Added ₹{amount} from {source}: {description}", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Income {income_code} recorded successfully", "income_code": income_code}), 201

# ----------------- FINANCIAL SUMMARY & NET BALANCE ----------------- #

@finance_bp.route("/summary", methods=["GET"])
@admin_required
def get_financial_summary():
    period = request.args.get("period", "monthly") # 'daily', 'weekly', 'monthly', 'yearly', 'custom'
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    
    today = datetime.now().date()
    if period == "daily":
        from_date = today.strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")
    elif period == "weekly":
        from_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")
    elif period == "monthly":
        from_date = today.strftime("%Y-%m-01")
        to_date = today.strftime("%Y-%m-%d")
    elif period == "yearly":
        from_date = today.strftime("%Y-01-01")
        to_date = today.strftime("%Y-%m-%d")
        
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Income Query
        inc_query = "SELECT COALESCE(SUM(amount), 0) as total FROM income WHERE 1=1"
        inc_params = []
        if from_date:
            inc_query += " AND date >= ?"
            inc_params.append(from_date)
        if to_date:
            inc_query += " AND date <= ?"
            inc_params.append(to_date)
            
        cursor.execute(inc_query, inc_params)
        total_income = cursor.fetchone()["total"]
        
        # Expense Query
        exp_query = "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE 1=1"
        exp_params = []
        if from_date:
            exp_query += " AND date >= ?"
            exp_params.append(from_date)
        if to_date:
            exp_query += " AND date <= ?"
            exp_params.append(to_date)
            
        cursor.execute(exp_query, exp_params)
        total_expenses = cursor.fetchone()["total"]
        
        net_balance = round(total_income - total_expenses, 2)
        
        # Income by Source
        inc_src_query = "SELECT source, SUM(amount) as total FROM income WHERE 1=1"
        if from_date:
            inc_src_query += " AND date >= ?"
        if to_date:
            inc_src_query += " AND date <= ?"
        inc_src_query += " GROUP BY source ORDER BY total DESC"
        cursor.execute(inc_src_query, inc_params)
        income_by_source = cursor.fetchall()
        
        # Expenses by Category
        exp_cat_query = "SELECT category, SUM(amount) as total FROM expenses WHERE 1=1"
        if from_date:
            exp_cat_query += " AND date >= ?"
        if to_date:
            exp_cat_query += " AND date <= ?"
        exp_cat_query += " GROUP BY category ORDER BY total DESC"
        cursor.execute(exp_cat_query, exp_params)
        expenses_by_category = cursor.fetchall()
        
    return jsonify({
        "period": period,
        "from_date": from_date,
        "to_date": to_date,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_balance": net_balance,
        "income_by_source": income_by_source,
        "expenses_by_category": expenses_by_category
    })
