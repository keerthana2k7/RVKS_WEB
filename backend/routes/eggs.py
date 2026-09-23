from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from database.db import get_db, log_audit
from routes.auth import login_required

eggs_bp = Blueprint("eggs", __name__, url_prefix="/api/eggs")

@eggs_bp.route("", methods=["GET"])
@login_required
def get_egg_records():
    batch_id = request.args.get("batch_id")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    
    query = """
        SELECT ep.*, b.batch_name, b.batch_code, b.bird_type 
        FROM egg_production ep 
        JOIN bird_batches b ON ep.batch_id = b.id 
        WHERE 1=1
    """
    params = []
    if batch_id:
        query += " AND ep.batch_id = ?"
        params.append(batch_id)
    if from_date:
        query += " AND ep.date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND ep.date <= ?"
        params.append(to_date)
        
    query += " ORDER BY ep.date DESC, ep.id DESC LIMIT 100"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        records = cursor.fetchall()
        
    return jsonify({"records": records})

@eggs_bp.route("", methods=["POST"])
@login_required
def record_egg_production():
    data = request.get_json() or {}
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    batch_id = data.get("batch_id")
    total_eggs = int(data.get("total_eggs", 0))
    good_eggs = int(data.get("good_eggs", 0))
    broken_eggs = int(data.get("broken_eggs", 0))
    damaged_eggs = int(data.get("damaged_eggs", 0))
    sold_eggs = int(data.get("sold_eggs", 0))
    selling_price = float(data.get("selling_price", 5.50))
    notes = data.get("notes", "").strip()
    
    if not batch_id or total_eggs <= 0:
        return jsonify({"error": "Batch and positive total eggs are required"}), 400
        
    # Auto-adjust if good_eggs not explicitly passed
    if good_eggs == 0 and (broken_eggs + damaged_eggs < total_eggs):
        good_eggs = total_eggs - (broken_eggs + damaged_eggs)
        
    if (good_eggs + broken_eggs + damaged_eggs) != total_eggs:
        return jsonify({
            "error": f"Egg count mismatch: Good ({good_eggs}) + Broken ({broken_eggs}) + Damaged ({damaged_eggs}) must equal Total ({total_eggs})"
        }), 400
        
    if sold_eggs > good_eggs:
        return jsonify({
            "error": f"Cannot sell {sold_eggs} eggs. Only {good_eggs} good eggs available."
        }), 400
        
    remaining_eggs = good_eggs - sold_eggs
    total_income = round(sold_eggs * selling_price, 2)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify batch
        cursor.execute("SELECT batch_name FROM bird_batches WHERE id = ?", (batch_id,))
        batch = cursor.fetchone()
        if not batch:
            return jsonify({"error": "Batch not found"}), 404
            
        cursor.execute("""
            INSERT INTO egg_production (date, batch_id, total_eggs, good_eggs, broken_eggs, damaged_eggs, sold_eggs, remaining_eggs, selling_price, total_income, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, batch_id, total_eggs, good_eggs, broken_eggs, damaged_eggs, sold_eggs, remaining_eggs, selling_price, total_income, notes))
        
        prod_id = cursor.lastrowid
        
        # Record income if eggs sold
        if total_income > 0:
            inc_code = f"INC-EGG-{date}-{batch_id}"
            cursor.execute("""
                INSERT INTO income (income_code, date, source, description, quantity, rate, amount, payment_method, reference_id, notes)
                VALUES (?, ?, 'Egg Sales', ?, ?, ?, ?, 'Cash', ?, ?)
            """, (inc_code, date, f"Egg Sales: {batch['batch_name']} ({sold_eggs} eggs)", sold_eggs, selling_price, total_income, f"EGG-{prod_id}", notes))
            
        log_audit(
            "Egg Production Recorded",
            "Eggs",
            f"EGG-{prod_id}",
            f"Recorded {total_eggs} eggs for {batch['batch_name']} ({sold_eggs} sold, income ₹{total_income})",
            user_id=g.user["user_id"],
            username=g.user["username"],
            conn=conn
        )
        
    return jsonify({
        "message": f"Recorded {total_eggs} eggs successfully for {batch['batch_name']}",
        "record": {
            "id": prod_id,
            "total_eggs": total_eggs,
            "good_eggs": good_eggs,
            "sold_eggs": sold_eggs,
            "remaining_eggs": remaining_eggs,
            "total_income": total_income
        }
    }), 201

@eggs_bp.route("/stats", methods=["GET"])
@login_required
def get_egg_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        month_start = datetime.now().strftime("%Y-%m-01")
        
        cursor.execute("SELECT COALESCE(SUM(total_eggs), 0) as total, COALESCE(SUM(sold_eggs), 0) as sold, COALESCE(SUM(total_income), 0) as income FROM egg_production WHERE date = ?", (today,))
        today_stats = cursor.fetchone()
        
        cursor.execute("SELECT COALESCE(SUM(total_eggs), 0) as total, COALESCE(SUM(sold_eggs), 0) as sold, COALESCE(SUM(total_income), 0) as income FROM egg_production WHERE date >= ?", (week_ago,))
        week_stats = cursor.fetchone()
        
        cursor.execute("SELECT COALESCE(SUM(total_eggs), 0) as total, COALESCE(SUM(sold_eggs), 0) as sold, COALESCE(SUM(total_income), 0) as income FROM egg_production WHERE date >= ?", (month_start,))
        month_stats = cursor.fetchone()
        
        cursor.execute("""
            SELECT b.batch_name, SUM(ep.total_eggs) as total, SUM(ep.sold_eggs) as sold, SUM(ep.total_income) as income 
            FROM egg_production ep 
            JOIN bird_batches b ON ep.batch_id = b.id 
            WHERE ep.date >= ? 
            GROUP BY ep.batch_id 
            ORDER BY total DESC
        """, (month_start,))
        batch_wise = cursor.fetchall()
        
    return jsonify({
        "today": today_stats,
        "week": week_stats,
        "month": month_stats,
        "batch_wise": batch_wise
    })
