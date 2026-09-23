from flask import Blueprint, request, jsonify, g
from datetime import datetime
from database.db import get_db, log_audit
from routes.auth import login_required, admin_required

feed_bp = Blueprint("feed", __name__, url_prefix="/api/feed")

# ----------------- FEED TYPES & RECIPES ----------------- #

@feed_bp.route("/types", methods=["GET"])
@login_required
def get_feed_types():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feed_types ORDER BY id ASC")
        types = cursor.fetchall()
    return jsonify({"types": types})

@feed_bp.route("/recipes", methods=["GET"])
@login_required
def get_recipes():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feed_recipes ORDER BY id ASC")
        recipes = cursor.fetchall()
        
        for r in recipes:
            cursor.execute("""
                SELECT fri.*, rm.material_name, rm.unit as material_unit, rm.current_stock
                FROM feed_recipe_items fri
                JOIN raw_materials rm ON fri.material_id = rm.id
                WHERE fri.recipe_id = ?
            """, (r["id"],))
            r["items"] = cursor.fetchall()
            
    return jsonify({"recipes": recipes})

@feed_bp.route("/recipes", methods=["POST"])
@admin_required
def create_recipe():
    data = request.get_json() or {}
    recipe_name = data.get("recipe_name", "").strip()
    feed_type = data.get("feed_type", "").strip()
    description = data.get("description", "").strip()
    items = data.get("items", []) # [{ material_id, percentage }]
    
    if not recipe_name or not feed_type or not items:
        return jsonify({"error": "Recipe name, feed type, and ingredient items are required"}), 400
        
    total_pct = sum(float(i.get("percentage", 0)) for i in items)
    if abs(total_pct - 100.0) > 0.5:
        return jsonify({"error": f"Recipe ingredient percentages must total 100% (currently {total_pct:.1f}%)"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM feed_recipes")
        next_num = cursor.fetchone()["count"] + 1
        recipe_code = f"RCP-{next_num:03d}"
        
        cursor.execute("""
            INSERT INTO feed_recipes (recipe_code, feed_type, recipe_name, description)
            VALUES (?, ?, ?, ?)
        """, (recipe_code, feed_type, recipe_name, description))
        recipe_id = cursor.lastrowid
        
        for itm in items:
            pct = float(itm["percentage"])
            cursor.execute("""
                INSERT INTO feed_recipe_items (recipe_id, material_id, percentage, quantity_per_100kg, unit)
                VALUES (?, ?, ?, ?, 'Kg')
            """, (recipe_id, itm["material_id"], pct, pct))
            
        log_audit("Feed Recipe Created", "Feed", recipe_code, f"Created {recipe_name} ({feed_type}) with {len(items)} ingredients", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Recipe {recipe_name} created successfully", "recipe_id": recipe_id, "recipe_code": recipe_code}), 201

# ----------------- FEED PRODUCTION ENGINE ----------------- #

@feed_bp.route("/produce", methods=["POST"])
@login_required
def produce_feed():
    data = request.get_json() or {}
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    feed_type = data.get("feed_type", "").strip()
    quantity_produced = float(data.get("quantity_produced", 0.0))
    recipe_id = data.get("recipe_id")
    labour_cost = float(data.get("labour_cost", 0.0))
    electricity_cost = float(data.get("electricity_cost", 0.0))
    other_cost = float(data.get("other_cost", 0.0))
    produced_by = data.get("produced_by", g.user.get("full_name", "Staff"))
    notes = data.get("notes", "").strip()
    
    if not feed_type or quantity_produced <= 0 or not recipe_id:
        return jsonify({"error": "Feed type, quantity produced, and recipe are required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch recipe and its ingredients
        cursor.execute("SELECT * FROM feed_recipes WHERE id = ?", (recipe_id,))
        recipe = cursor.fetchone()
        if not recipe:
            return jsonify({"error": "Recipe not found"}), 404
            
        cursor.execute("""
            SELECT fri.material_id, fri.percentage, rm.material_name, rm.current_stock, rm.unit,
                   COALESCE((SELECT rate_per_unit FROM raw_material_purchases WHERE material_id = rm.id ORDER BY id DESC LIMIT 1), 20.0) as latest_rate
            FROM feed_recipe_items fri
            JOIN raw_materials rm ON fri.material_id = rm.id
            WHERE fri.recipe_id = ?
        """, (recipe_id,))
        recipe_items = cursor.fetchall()
        
        if not recipe_items:
            return jsonify({"error": "Recipe contains no raw material items"}), 400
            
        # 2. Check stock availability for every raw material
        shortages = []
        ingredient_deductions = []
        total_raw_material_cost = 0.0
        
        for item in recipe_items:
            req_qty = round((item["percentage"] / 100.0) * quantity_produced, 2)
            avail_stock = item["current_stock"]
            
            if avail_stock < req_qty:
                shortage = round(req_qty - avail_stock, 2)
                shortages.append({
                    "material_name": item["material_name"],
                    "required": req_qty,
                    "available": avail_stock,
                    "shortage": shortage,
                    "unit": item["unit"]
                })
            else:
                mat_cost = round(req_qty * item["latest_rate"], 2)
                total_raw_material_cost += mat_cost
                ingredient_deductions.append({
                    "material_id": item["material_id"],
                    "material_name": item["material_name"],
                    "deduct_qty": req_qty,
                    "new_stock": avail_stock - req_qty,
                    "cost": mat_cost,
                    "unit": item["unit"]
                })
                
        # If any shortage, abort feed production with clear message
        if shortages:
            shortage_lines = [
                f"{s['material_name']} required: {s['required']} {s['unit']}, Available: {s['available']} {s['unit']}, Shortage: {s['shortage']} {s['unit']}"
                for s in shortages
            ]
            detailed_msg = "Feed production cannot continue.\n" + "\n".join(shortage_lines)
            return jsonify({
                "error": detailed_msg,
                "shortages": shortages
            }), 400
            
        # 3. All stocks sufficient -> Execute Atomic Production
        cursor.execute("SELECT COUNT(*) as count FROM feed_production")
        next_num = cursor.fetchone()["count"] + 1
        prod_code = f"FPR-{next_num:03d}"
        batch_number = f"PROD-{datetime.now().strftime('%y%m')}-{next_num:02d}"
        
        total_cost = round(total_raw_material_cost + labour_cost + electricity_cost + other_cost, 2)
        cost_per_kg = round(total_cost / quantity_produced, 2)
        
        # Deduct each raw material
        for ing in ingredient_deductions:
            cursor.execute("""
                UPDATE raw_materials 
                SET current_stock = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (ing["new_stock"], ing["material_id"]))
            
            cursor.execute("""
                INSERT INTO raw_material_movements (date, material_id, movement_type, quantity, balance_after, reference_id, notes)
                VALUES (?, ?, 'Production Usage', ?, ?, ?, ?)
            """, (date, ing["material_id"], -ing["deduct_qty"], ing["new_stock"], prod_code, f"Used in {prod_code} ({quantity_produced} kg {feed_type})"))
            
        # Increase Feed Stock
        cursor.execute("SELECT current_stock FROM feed_stock WHERE feed_type = ?", (feed_type,))
        f_stock = cursor.fetchone()
        new_feed_stock = quantity_produced
        if f_stock:
            new_feed_stock = f_stock["current_stock"] + quantity_produced
            cursor.execute("""
                UPDATE feed_stock 
                SET current_stock = ?, last_updated = CURRENT_TIMESTAMP 
                WHERE feed_type = ?
            """, (new_feed_stock, feed_type))
        else:
            cursor.execute("""
                INSERT INTO feed_stock (feed_type, current_stock, minimum_stock_level, unit)
                VALUES (?, ?, 300.0, 'Kg')
            """, (feed_type, new_feed_stock))
            
        # Feed Stock Movement
        cursor.execute("""
            INSERT INTO feed_stock_movements (date, feed_type, movement_type, quantity, balance_after, reference_id, notes)
            VALUES (?, ?, 'Produced', ?, ?, ?, ?)
        """, (date, feed_type, quantity_produced, new_feed_stock, prod_code, f"Produced via {recipe['recipe_name']}"))
        
        # Record Production
        cursor.execute("""
            INSERT INTO feed_production (production_code, date, feed_type, batch_number, quantity_produced, unit, recipe_id, raw_material_cost, labour_cost, electricity_cost, other_cost, total_cost, cost_per_kg, produced_by, notes)
            VALUES (?, ?, ?, ?, ?, 'Kg', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (prod_code, date, feed_type, batch_number, quantity_produced, recipe_id, total_raw_material_cost, labour_cost, electricity_cost, other_cost, total_cost, cost_per_kg, produced_by, notes))
        
        # Record Labour & Electricity in Expenses if entered
        if labour_cost > 0:
            cursor.execute("""
                INSERT INTO expenses (expense_code, date, category, description, amount, payment_method, paid_by, reference_id, notes)
                VALUES (?, ?, 'Feed Production', ?, ?, 'Cash', 'Supervisor', ?, 'Milling and mixer labour')
            """, (f"EXP-LBR-{prod_code}", date, f"Labour for feed production {prod_code}", labour_cost, prod_code))
        if electricity_cost > 0:
            cursor.execute("""
                INSERT INTO expenses (expense_code, date, category, description, amount, payment_method, paid_by, reference_id, notes)
                VALUES (?, ?, 'Electricity', ?, ?, 'Bank Transfer', 'Owner', ?, 'Power for feed mill')
            """, (f"EXP-PWR-{prod_code}", date, f"Electricity for feed production {prod_code}", electricity_cost, prod_code))
            
        log_audit(
            "Feed Produced",
            "Feed",
            prod_code,
            f"Produced {quantity_produced} kg of {feed_type} via {recipe['recipe_name']}. Total Cost: ₹{total_cost} (₹{cost_per_kg}/kg). New feed stock: {new_feed_stock} kg",
            user_id=g.user["user_id"],
            username=g.user["username"],
            conn=conn
        )
        
    return jsonify({
        "message": f"Successfully produced {quantity_produced} kg of {feed_type}!",
        "production_code": prod_code,
        "batch_number": batch_number,
        "total_cost": total_cost,
        "cost_per_kg": cost_per_kg,
        "new_feed_stock": new_feed_stock
    }), 201

# ----------------- FEED STOCK & USAGE ----------------- #

@feed_bp.route("/stock", methods=["GET"])
@login_required
def get_feed_stock():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feed_stock ORDER BY feed_type ASC")
        stocks = cursor.fetchall()
        for s in stocks:
            s["is_low_stock"] = s["current_stock"] <= s["minimum_stock_level"]
    return jsonify({"stocks": stocks})

@feed_bp.route("/usage", methods=["GET"])
@login_required
def get_feed_usage():
    batch_id = request.args.get("batch_id")
    feed_type = request.args.get("feed_type")
    
    query = """
        SELECT fu.*, b.batch_name, b.batch_code 
        FROM feed_usage fu 
        JOIN bird_batches b ON fu.batch_id = b.id 
        WHERE 1=1
    """
    params = []
    if batch_id:
        query += " AND fu.batch_id = ?"
        params.append(batch_id)
    if feed_type:
        query += " AND fu.feed_type = ?"
        params.append(feed_type)
        
    query += " ORDER BY fu.date DESC, fu.id DESC LIMIT 100"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        usages = cursor.fetchall()
        
    return jsonify({"usages": usages})

@feed_bp.route("/usage", methods=["POST"])
@login_required
def record_feed_usage():
    data = request.get_json() or {}
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    batch_id = data.get("batch_id")
    feed_type = data.get("feed_type", "").strip()
    quantity = float(data.get("quantity", 0.0))
    notes = data.get("notes", "").strip()
    
    if not batch_id or not feed_type or quantity <= 0:
        return jsonify({"error": "Batch, feed type, and positive quantity are required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify batch
        cursor.execute("SELECT batch_name, bird_type FROM bird_batches WHERE id = ?", (batch_id,))
        batch = cursor.fetchone()
        if not batch:
            return jsonify({"error": "Batch not found"}), 404
            
        # Check feed stock
        cursor.execute("SELECT current_stock FROM feed_stock WHERE feed_type = ?", (feed_type,))
        stock_row = cursor.fetchone()
        if not stock_row or stock_row["current_stock"] < quantity:
            avail = stock_row["current_stock"] if stock_row else 0
            return jsonify({"error": f"Insufficient {feed_type} stock. Available: {avail} kg, Requested: {quantity} kg"}), 400
            
        new_feed_stock = stock_row["current_stock"] - quantity
        
        # 1. Update Feed Stock
        cursor.execute("""
            UPDATE feed_stock 
            SET current_stock = ?, last_updated = CURRENT_TIMESTAMP 
            WHERE feed_type = ?
        """, (new_feed_stock, feed_type))
        
        # 2. Insert Usage Record
        cursor.execute("SELECT COUNT(*) as count FROM feed_usage")
        next_num = cursor.fetchone()["count"] + 1
        usage_code = f"FUS-{next_num:03d}"
        
        cursor.execute("""
            INSERT INTO feed_usage (usage_code, date, batch_id, bird_type, feed_type, quantity, unit, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'Kg', ?)
        """, (usage_code, date, batch_id, batch["bird_type"], feed_type, quantity, notes))
        
        # 3. Insert Movement
        cursor.execute("""
            INSERT INTO feed_stock_movements (date, feed_type, movement_type, quantity, balance_after, reference_id, notes)
            VALUES (?, ?, 'Used', ?, ?, ?, ?)
        """, (date, feed_type, -quantity, new_feed_stock, usage_code, f"Consumed by {batch['batch_name']}"))
        
        log_audit(
            "Feed Consumed",
            "Feed",
            usage_code,
            f"Consumed {quantity} kg of {feed_type} for {batch['batch_name']}. Remaining stock: {new_feed_stock} kg",
            user_id=g.user["user_id"],
            username=g.user["username"],
            conn=conn
        )
        
    return jsonify({
        "message": f"Successfully recorded {quantity} kg feed consumption for {batch['batch_name']}",
        "usage_code": usage_code,
        "remaining_feed_stock": new_feed_stock
    }), 201
