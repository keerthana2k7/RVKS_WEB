from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from database.db import get_db
from routes.auth import login_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

@dashboard_bp.route("/summary", methods=["GET"])
@login_required
def get_summary():
    today = datetime.now().strftime("%Y-%m-%d")
    first_day_of_month = datetime.now().strftime("%Y-%m-01")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Bird Summary
        cursor.execute("SELECT COALESCE(SUM(current_quantity), 0) as total FROM bird_batches WHERE status = 'Active'")
        total_birds = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COALESCE(SUM(current_quantity), 0) as count FROM bird_batches WHERE status = 'Active' AND bird_type = 'Chick'")
        chick_birds = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COALESCE(SUM(current_quantity), 0) as count FROM bird_batches WHERE status = 'Active' AND bird_type = 'Layer'")
        layer_birds = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COALESCE(SUM(current_quantity), 0) as count FROM bird_batches WHERE status = 'Active' AND bird_type = 'EDD'")
        edd_birds = cursor.fetchone()["count"]
        
        # Specific EDD Batches
        cursor.execute("SELECT batch_name, current_quantity FROM bird_batches WHERE status = 'Active' ORDER BY id ASC")
        all_batches = cursor.fetchall()
        
        edd_batch_1 = next((b["current_quantity"] for b in all_batches if "EDD Batch 1" in b["batch_name"]), 0)
        edd_batch_2 = next((b["current_quantity"] for b in all_batches if "EDD Batch 2" in b["batch_name"]), 0)
        edd_batch_3 = next((b["current_quantity"] for b in all_batches if "EDD Batch 3" in b["batch_name"]), 0)
        
        # 2. Worker Summary
        cursor.execute("SELECT COUNT(*) as total FROM workers")
        total_workers = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as active FROM workers WHERE status = 'Active'")
        active_workers = cursor.fetchone()["active"]
        
        cursor.execute("SELECT COUNT(*) as present FROM attendance WHERE date = ? AND status = 'Present'", (today,))
        present_today = cursor.fetchone()["present"]
        
        cursor.execute("SELECT COUNT(*) as absent FROM attendance WHERE date = ? AND status = 'Absent'", (today,))
        absent_today = cursor.fetchone()["absent"]
        
        cursor.execute("SELECT COUNT(*) as leave FROM attendance WHERE date = ? AND status = 'Leave'", (today,))
        leave_today = cursor.fetchone()["leave"]
        
        cursor.execute("SELECT COUNT(*) as pending_count, COALESCE(SUM(amount), 0) as pending_amount FROM worker_payments WHERE status = 'Pending'")
        pending_pay = cursor.fetchone()
        
        # 3. Feed Summary
        cursor.execute("SELECT COALESCE(SUM(current_stock), 0) as total FROM feed_stock")
        current_feed_stock = cursor.fetchone()["total"]
        
        cursor.execute("SELECT feed_type, current_stock, minimum_stock_level FROM feed_stock")
        feed_stock_list = cursor.fetchall()
        
        cursor.execute("SELECT COALESCE(SUM(quantity), 0) as today_used FROM feed_usage WHERE date = ?", (today,))
        today_feed_usage = cursor.fetchone()["today_used"]
        
        cursor.execute("SELECT COALESCE(SUM(quantity_produced), 0) as month_prod FROM feed_production WHERE date >= ?", (first_day_of_month,))
        month_feed_production = cursor.fetchone()["month_prod"]
        
        low_feed_stock_count = sum(1 for f in feed_stock_list if f["current_stock"] <= f["minimum_stock_level"])
        
        # 4. Raw Material Summary
        cursor.execute("SELECT COALESCE(SUM(current_stock), 0) as total FROM raw_materials WHERE status != 'Inactive'")
        current_material_stock = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COALESCE(SUM(quantity), 0) as today_qty, COALESCE(SUM(total_cost), 0) as today_cost FROM raw_material_purchases WHERE purchase_date = ?", (today,))
        today_purchases = cursor.fetchone()
        
        cursor.execute("SELECT COALESCE(SUM(total_cost), 0) as month_cost FROM raw_material_purchases WHERE purchase_date >= ?", (first_day_of_month,))
        month_purchase_cost = cursor.fetchone()["month_cost"]
        
        cursor.execute("SELECT COUNT(*) as low_count FROM raw_materials WHERE current_stock <= minimum_stock_level")
        low_material_count = cursor.fetchone()["low_count"]
        
        # 5. Egg Summary
        cursor.execute("SELECT COALESCE(SUM(total_eggs), 0) as total, COALESCE(SUM(sold_eggs), 0) as sold, COALESCE(SUM(total_income), 0) as income FROM egg_production WHERE date = ?", (today,))
        today_egg = cursor.fetchone()
        
        cursor.execute("SELECT COALESCE(SUM(total_eggs), 0) as total FROM egg_production WHERE date >= ?", (week_ago,))
        this_week_eggs = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COALESCE(SUM(total_eggs), 0) as total, COALESCE(SUM(sold_eggs), 0) as sold, COALESCE(SUM(total_income), 0) as income FROM egg_production WHERE date >= ?", (first_day_of_month,))
        month_egg = cursor.fetchone()
        
        # 6. Expense Summary
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date = ?", (today,))
        today_expenses = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ?", (first_day_of_month,))
        month_expenses = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ? AND category = 'Worker Salary'", (first_day_of_month,))
        worker_payments_exp = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ? AND category = 'Raw Materials'", (first_day_of_month,))
        raw_materials_exp = cursor.fetchone()["total"]
        
        other_expenses = month_expenses - (worker_payments_exp + raw_materials_exp)
        
        # 7. Financial Balance
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM income WHERE date >= ?", (first_day_of_month,))
        month_income = cursor.fetchone()["total"]
        net_balance = month_income - month_expenses

        return jsonify({
            "birds": {
                "total_birds": total_birds,
                "chick_birds": chick_birds,
                "layer_birds": layer_birds,
                "edd_birds": edd_birds,
                "edd_batch_1": edd_batch_1,
                "edd_batch_2": edd_batch_2,
                "edd_batch_3": edd_batch_3,
                "batches": all_batches
            },
            "workers": {
                "total_workers": total_workers,
                "active_workers": active_workers,
                "present_today": present_today,
                "absent_today": absent_today,
                "leave_today": leave_today,
                "pending_payments_count": pending_pay["pending_count"],
                "pending_payments_amount": pending_pay["pending_amount"]
            },
            "feed": {
                "current_feed_stock": current_feed_stock,
                "feed_stock_list": feed_stock_list,
                "today_feed_usage": today_feed_usage,
                "month_feed_production": month_feed_production,
                "low_feed_stock_alerts": low_feed_stock_count
            },
            "raw_materials": {
                "current_stock": current_material_stock,
                "today_purchases_qty": today_purchases["today_qty"],
                "today_purchases_cost": today_purchases["today_cost"],
                "month_purchase_cost": month_purchase_cost,
                "low_stock_materials": low_material_count
            },
            "eggs": {
                "today_eggs": today_egg["total"],
                "today_eggs_sold": today_egg["sold"],
                "this_week_eggs": this_week_eggs,
                "this_month_eggs": month_egg["total"],
                "month_eggs_sold": month_egg["sold"],
                "month_egg_income": month_egg["income"]
            },
            "expenses": {
                "today_expenses": today_expenses,
                "this_month_expenses": month_expenses,
                "worker_payments": worker_payments_exp,
                "raw_material_expenses": raw_materials_exp,
                "other_expenses": max(0, other_expenses)
            },
            "finances": {
                "month_income": month_income,
                "month_expenses": month_expenses,
                "net_balance": net_balance
            }
        })

@dashboard_bp.route("/charts", methods=["GET"])
@login_required
def get_charts():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Birds by Type
        cursor.execute("SELECT bird_type, SUM(current_quantity) as count FROM bird_batches WHERE status = 'Active' GROUP BY bird_type")
        birds_by_type = cursor.fetchall()
        
        # 2. Birds by Batch
        cursor.execute("SELECT batch_name, current_quantity FROM bird_batches WHERE status = 'Active' ORDER BY id ASC")
        birds_by_batch = cursor.fetchall()
        
        # 3. Mortality Trend (Last 14 days)
        fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT date, SUM(number_of_birds) as count 
            FROM mortality 
            WHERE date >= ? 
            GROUP BY date 
            ORDER BY date ASC
        """, (fourteen_days_ago,))
        mortality_trend = cursor.fetchall()
        
        # 4. Egg Production Trend (Last 14 days)
        cursor.execute("""
            SELECT date, SUM(total_eggs) as total, SUM(good_eggs) as good, SUM(sold_eggs) as sold 
            FROM egg_production 
            WHERE date >= ? 
            GROUP BY date 
            ORDER BY date ASC
        """, (fourteen_days_ago,))
        egg_trend = cursor.fetchall()
        
        # 5. Feed Production vs Consumption (Last 14 days)
        cursor.execute("""
            SELECT date, SUM(quantity) as consumed 
            FROM feed_usage 
            WHERE date >= ? 
            GROUP BY date 
            ORDER BY date ASC
        """, (fourteen_days_ago,))
        feed_usage_trend = {row["date"]: row["consumed"] for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT date, SUM(quantity_produced) as produced 
            FROM feed_production 
            WHERE date >= ? 
            GROUP BY date 
            ORDER BY date ASC
        """, (fourteen_days_ago,))
        feed_prod_trend = {row["date"]: row["produced"] for row in cursor.fetchall()}
        
        # Merge dates for feed
        all_feed_dates = sorted(list(set(list(feed_usage_trend.keys()) + list(feed_prod_trend.keys()))))
        feed_comparison = [
            {"date": d, "produced": feed_prod_trend.get(d, 0), "consumed": feed_usage_trend.get(d, 0)}
            for d in all_feed_dates
        ]
        
        # 6. Expenses Breakdown by Category (This Month)
        first_day_of_month = datetime.now().strftime("%Y-%m-01")
        cursor.execute("""
            SELECT category, SUM(amount) as total 
            FROM expenses 
            WHERE date >= ? 
            GROUP BY category 
            ORDER BY total DESC
        """, (first_day_of_month,))
        expenses_by_cat = cursor.fetchall()
        
        # 7. Income vs Expenses (Last 6 Months)
        six_months_ago = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-01")
        cursor.execute("""
            SELECT strftime('%Y-%m', date) as month, SUM(amount) as total 
            FROM income 
            WHERE date >= ? 
            GROUP BY month 
            ORDER BY month ASC
        """, (six_months_ago,))
        income_by_month = {row["month"]: row["total"] for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT strftime('%Y-%m', date) as month, SUM(amount) as total 
            FROM expenses 
            WHERE date >= ? 
            GROUP BY month 
            ORDER BY month ASC
        """, (six_months_ago,))
        expenses_by_month = {row["month"]: row["total"] for row in cursor.fetchall()}
        
        all_months = sorted(list(set(list(income_by_month.keys()) + list(expenses_by_month.keys()))))
        income_vs_expense = [
            {
                "month": m,
                "income": income_by_month.get(m, 0),
                "expenses": expenses_by_month.get(m, 0),
                "net": income_by_month.get(m, 0) - expenses_by_month.get(m, 0)
            }
            for m in all_months
        ]

        return jsonify({
            "birds_by_type": birds_by_type,
            "birds_by_batch": birds_by_batch,
            "mortality_trend": mortality_trend,
            "egg_trend": egg_trend,
            "feed_comparison": feed_comparison,
            "expenses_by_cat": expenses_by_cat,
            "income_vs_expense": income_vs_expense
        })

@dashboard_bp.route("/alerts", methods=["GET"])
@login_required
def get_alerts():
    today = datetime.now().strftime("%Y-%m-%d")
    alerts = []
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Low Raw Materials
        cursor.execute("""
            SELECT material_name, current_stock, minimum_stock_level, unit 
            FROM raw_materials 
            WHERE current_stock <= minimum_stock_level AND status != 'Inactive'
        """)
        for r in cursor.fetchall():
            alerts.append({
                "type": "warning",
                "category": "Raw Material",
                "title": f"Low Raw Material: {r['material_name']}",
                "message": f"{r['material_name']} stock is {r['current_stock']} {r['unit']}, below minimum level ({r['minimum_stock_level']} {r['unit']})."
            })
            
        # 2. Low Feed Stock
        cursor.execute("""
            SELECT feed_type, current_stock, minimum_stock_level, unit 
            FROM feed_stock 
            WHERE current_stock <= minimum_stock_level
        """)
        for f in cursor.fetchall():
            alerts.append({
                "type": "warning",
                "category": "Feed",
                "title": f"Low Feed Stock: {f['feed_type']}",
                "message": f"{f['feed_type']} stock is {f['current_stock']} {f['unit']}, below minimum level ({f['minimum_stock_level']} {f['unit']})."
            })
            
        # 3. Pending Worker Payments
        cursor.execute("""
            SELECT wp.payment_code, wp.amount, wp.salary_period, w.name 
            FROM worker_payments wp 
            JOIN workers w ON wp.worker_id = w.id 
            WHERE wp.status = 'Pending'
        """)
        for p in cursor.fetchall():
            alerts.append({
                "type": "info",
                "category": "Payroll",
                "title": f"Pending Worker Payment: {p['name']}",
                "message": f"Salary payment of ₹{p['amount']} for {p['salary_period']} is pending."
            })
            
        # 4. Missing Attendance Today
        cursor.execute("""
            SELECT COUNT(*) as missing 
            FROM workers 
            WHERE status = 'Active' 
            AND id NOT IN (SELECT worker_id FROM attendance WHERE date = ?)
        """, (today,))
        missing_count = cursor.fetchone()["missing"]
        if missing_count > 0:
            alerts.append({
                "type": "warning",
                "category": "Attendance",
                "title": "Missing Attendance Today",
                "message": f"Attendance has not been marked for {missing_count} worker{'s' if missing_count > 1 else ''} today."
            })
            
        # 5. High Mortality Alert (threshold >= 5 birds per batch in single day)
        cursor.execute("""
            SELECT b.batch_name, SUM(m.number_of_birds) as total_dead 
            FROM mortality m 
            JOIN bird_batches b ON m.batch_id = b.id 
            WHERE m.date = ? 
            GROUP BY m.batch_id 
            HAVING total_dead >= 5
        """, (today,))
        for h in cursor.fetchall():
            alerts.append({
                "type": "danger",
                "category": "Mortality",
                "title": f"High Mortality Alert: {h['batch_name']}",
                "message": f"{h['total_dead']} birds died today in {h['batch_name']}! Immediate shed check required."
            })
            
    return jsonify({"alerts": alerts, "count": len(alerts)})

@dashboard_bp.route("/recent-activities", methods=["GET"])
@login_required
def get_recent_activities():
    limit = int(request.args.get("limit", 20))
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, username, action, module, record_id, details 
            FROM audit_logs 
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
        activities = cursor.fetchall()
    return jsonify({"activities": activities})
