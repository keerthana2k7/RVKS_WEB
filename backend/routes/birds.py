from flask import Blueprint, request, jsonify, g
from datetime import datetime
from database.db import get_db, log_audit
from routes.auth import login_required, admin_required

birds_bp = Blueprint("birds", __name__, url_prefix="/api/birds")

# ----------------- BATCHES ----------------- #

@birds_bp.route("/types", methods=["GET"])
@login_required
def get_bird_types():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bird_types ORDER BY id ASC")
        types = cursor.fetchall()
    return jsonify({"types": types})

@birds_bp.route("/batches", methods=["GET"])
@login_required
def get_batches():
    status = request.args.get("status")
    bird_type = request.args.get("bird_type")
    
    query = "SELECT * FROM bird_batches WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if bird_type:
        query += " AND bird_type = ?"
        params.append(bird_type)
        
    query += " ORDER BY status ASC, id ASC"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        batches = cursor.fetchall()
    return jsonify({"batches": batches})

@birds_bp.route("/batches", methods=["POST"])
@admin_required
def create_batch():
    data = request.get_json() or {}
    batch_name = data.get("batch_name", "").strip()
    bird_type = data.get("bird_type", "EDD")
    arrival_date = data.get("arrival_date", datetime.now().strftime("%Y-%m-%d"))
    initial_quantity = int(data.get("initial_quantity", 0))
    source_supplier = data.get("source_supplier", "").strip()
    shed_location = data.get("shed_location", "").strip()
    age_weeks = int(data.get("age_weeks", 0))
    notes = data.get("notes", "").strip()
    
    if not batch_name or initial_quantity <= 0:
        return jsonify({"error": "Batch name and a positive initial quantity are required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM bird_batches")
        next_num = cursor.fetchone()["count"] + 1
        batch_code = f"BATCH-{next_num:03d}"
        
        # 1. Insert Batch
        cursor.execute("""
            INSERT INTO bird_batches (batch_code, batch_name, bird_type, arrival_date, initial_quantity, current_quantity, source_supplier, shed_location, age_weeks, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
        """, (batch_code, batch_name, bird_type, arrival_date, initial_quantity, initial_quantity, source_supplier, shed_location, age_weeks, notes))
        
        batch_id = cursor.lastrowid
        
        # 2. Record Initial Stock transaction
        cursor.execute("""
            INSERT INTO bird_transactions (batch_id, date, tx_type, quantity, balance_after, reference_id, notes)
            VALUES (?, ?, 'Initial Stock', ?, ?, ?, 'Initial flock arrival recorded')
        """, (batch_id, arrival_date, initial_quantity, initial_quantity, batch_code))
        
        log_audit("Bird Batch Created", "Birds", batch_code, f"Created {batch_name} ({bird_type}) with {initial_quantity} birds", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Batch {batch_name} created successfully", "batch_id": batch_id, "batch_code": batch_code}), 201

@birds_bp.route("/batches/<int:batch_id>", methods=["PUT"])
@admin_required
def update_batch(batch_id):
    data = request.get_json() or {}
    batch_name = data.get("batch_name", "").strip()
    shed_location = data.get("shed_location", "").strip()
    age_weeks = int(data.get("age_weeks", 0))
    status = data.get("status", "Active")
    notes = data.get("notes", "").strip()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bird_batches 
            SET batch_name = ?, shed_location = ?, age_weeks = ?, status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (batch_name, shed_location, age_weeks, status, notes, batch_id))
        
        log_audit("Bird Batch Updated", "Birds", batch_id, f"Updated batch {batch_name} ({status})", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": "Batch updated successfully"})

# ----------------- BIRD TRANSACTIONS / AUDIT TRAIL ----------------- #

@birds_bp.route("/transactions", methods=["GET"])
@login_required
def get_transactions():
    batch_id = request.args.get("batch_id")
    tx_type = request.args.get("tx_type")
    
    query = """
        SELECT bt.*, b.batch_name, b.bird_type, b.batch_code 
        FROM bird_transactions bt 
        JOIN bird_batches b ON bt.batch_id = b.id 
        WHERE 1=1
    """
    params = []
    if batch_id:
        query += " AND bt.batch_id = ?"
        params.append(batch_id)
    if tx_type:
        query += " AND bt.tx_type = ?"
        params.append(tx_type)
        
    query += " ORDER BY bt.date DESC, bt.id DESC LIMIT 100"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        transactions = cursor.fetchall()
        
    return jsonify({"transactions": transactions})

# ----------------- MORTALITY MANAGEMENT ----------------- #

@birds_bp.route("/mortality", methods=["GET"])
@login_required
def get_mortality():
    batch_id = request.args.get("batch_id")
    date = request.args.get("date")
    
    query = """
        SELECT m.*, b.batch_name, b.batch_code 
        FROM mortality m 
        JOIN bird_batches b ON m.batch_id = b.id 
        WHERE 1=1
    """
    params = []
    if batch_id:
        query += " AND m.batch_id = ?"
        params.append(batch_id)
    if date:
        query += " AND m.date = ?"
        params.append(date)
        
    query += " ORDER BY m.date DESC, m.id DESC LIMIT 100"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        records = cursor.fetchall()
        
    return jsonify({"records": records})

@birds_bp.route("/mortality", methods=["POST"])
@login_required
def record_mortality():
    data = request.get_json() or {}
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    batch_id = data.get("batch_id")
    number_of_birds = int(data.get("number_of_birds", 0))
    reason = data.get("reason", "Weakness")
    shed_location = data.get("shed_location", "").strip()
    notes = data.get("notes", "").strip()
    
    if not batch_id or number_of_birds <= 0:
        return jsonify({"error": "Batch and a positive number of birds are required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Check Batch and Current Quantity
        cursor.execute("SELECT batch_name, bird_type, current_quantity, shed_location as default_shed FROM bird_batches WHERE id = ?", (batch_id,))
        batch = cursor.fetchone()
        if not batch:
            return jsonify({"error": "Batch not found"}), 404
            
        current_qty = batch["current_quantity"]
        if current_qty < number_of_birds:
            return jsonify({
                "error": f"Cannot record mortality of {number_of_birds} birds. Current batch population is only {current_qty}."
            }), 400
            
        new_qty = current_qty - number_of_birds
        shed = shed_location or batch["default_shed"]
        
        # 2. Insert Mortality Record
        cursor.execute("""
            INSERT INTO mortality (date, batch_id, bird_type, number_of_birds, reason, shed_location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date, batch_id, batch["bird_type"], number_of_birds, reason, shed, notes))
        
        # 3. Deduct from Batch current_quantity
        cursor.execute("""
            UPDATE bird_batches 
            SET current_quantity = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (new_qty, batch_id))
        
        # 4. Insert Bird Movement Transaction
        cursor.execute("""
            INSERT INTO bird_transactions (batch_id, date, tx_type, quantity, balance_after, reference_id, notes)
            VALUES (?, ?, 'Mortality', ?, ?, 'MORT', ?)
        """, (batch_id, date, -number_of_birds, new_qty, f"Mortality: {reason} ({notes})"))
        
        # 5. Check High Mortality Alert Condition
        cursor.execute("""
            SELECT SUM(number_of_birds) as total_today 
            FROM mortality 
            WHERE batch_id = ? AND date = ?
        """, (batch_id, date))
        today_mort = cursor.fetchone()["total_today"] or 0
        high_mortality_alert = today_mort >= 5
        
        log_audit(
            "Mortality Recorded",
            "Birds",
            f"BATCH-{batch_id}",
            f"Recorded {number_of_birds} bird mortality ({reason}) in {batch['batch_name']}. New balance: {new_qty}",
            user_id=g.user["user_id"],
            username=g.user["username"],
            conn=conn
        )
        
    return jsonify({
        "message": f"Successfully recorded mortality of {number_of_birds} birds in {batch['batch_name']}.",
        "new_balance": new_qty,
        "high_mortality_alert": high_mortality_alert
    }), 201
