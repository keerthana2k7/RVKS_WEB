from flask import Blueprint, request, jsonify, g
from datetime import datetime
from database.db import get_db, log_audit
from routes.auth import login_required, admin_required

raw_materials_bp = Blueprint("raw_materials", __name__, url_prefix="/api/raw-materials")

# ----------------- RAW MATERIALS ----------------- #

@raw_materials_bp.route("", methods=["GET"])
@login_required
def get_raw_materials():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM raw_materials ORDER BY current_stock <= minimum_stock_level DESC, material_name ASC")
        materials = cursor.fetchall()
        
        for m in materials:
            if m["current_stock"] <= 0:
                m["status"] = "Out of Stock"
            elif m["current_stock"] <= m["minimum_stock_level"]:
                m["status"] = "Low Stock"
            else:
                m["status"] = "Normal"
                
    return jsonify({"materials": materials})

@raw_materials_bp.route("", methods=["POST"])
@admin_required
def create_raw_material():
    data = request.get_json() or {}
    material_name = data.get("material_name", "").strip()
    category = data.get("category", "Feed Ingredient").strip()
    unit = data.get("unit", "Kg").strip()
    minimum_stock_level = float(data.get("minimum_stock_level", 100.0))
    initial_stock = float(data.get("initial_stock", 0.0))
    notes = data.get("notes", "").strip()
    
    if not material_name:
        return jsonify({"error": "Material name is required"}), 400
        
    status = "Normal"
    if initial_stock <= 0:
        status = "Out of Stock"
    elif initial_stock <= minimum_stock_level:
        status = "Low Stock"
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM raw_materials")
        next_num = cursor.fetchone()["count"] + 1
        material_code = f"MAT-{next_num:03d}"
        
        cursor.execute("""
            INSERT INTO raw_materials (material_code, material_name, category, unit, minimum_stock_level, current_stock, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (material_code, material_name, category, unit, minimum_stock_level, initial_stock, status, notes))
        
        mat_id = cursor.lastrowid
        
        if initial_stock > 0:
            cursor.execute("""
                INSERT INTO raw_material_movements (date, material_id, movement_type, quantity, balance_after, reference_id, notes)
                VALUES (date('now'), ?, 'Opening Stock', ?, ?, ?, 'Initial inventory setup')
            """, (mat_id, initial_stock, initial_stock, material_code))
            
        log_audit("Raw Material Added", "Inventory", material_code, f"Added material {material_name} with {initial_stock} {unit}", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Material {material_name} created successfully", "material_id": mat_id, "material_code": material_code}), 201

@raw_materials_bp.route("/<int:mat_id>", methods=["PUT"])
@admin_required
def update_raw_material(mat_id):
    data = request.get_json() or {}
    material_name = data.get("material_name", "").strip()
    category = data.get("category", "Feed Ingredient").strip()
    unit = data.get("unit", "Kg").strip()
    minimum_stock_level = float(data.get("minimum_stock_level", 100.0))
    notes = data.get("notes", "").strip()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE raw_materials 
            SET material_name = ?, category = ?, unit = ?, minimum_stock_level = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (material_name, category, unit, minimum_stock_level, notes, mat_id))
        
        log_audit("Raw Material Updated", "Inventory", mat_id, f"Updated {material_name}", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": "Material updated successfully"})

# ----------------- SUPPLIERS ----------------- #

@raw_materials_bp.route("/suppliers", methods=["GET"])
@login_required
def get_suppliers():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, 
                   COALESCE(COUNT(p.id), 0) as total_purchases_count,
                   COALESCE(SUM(p.total_cost), 0) as total_purchase_amount,
                   COALESCE(SUM(CASE WHEN p.payment_status = 'Pending' THEN p.total_cost ELSE 0 END), 0) as pending_payments,
                   MAX(p.purchase_date) as last_purchase_date
            FROM suppliers s
            LEFT JOIN raw_material_purchases p ON s.id = p.supplier_id
            GROUP BY s.id
            ORDER BY s.supplier_name ASC
        """)
        suppliers = cursor.fetchall()
    return jsonify({"suppliers": suppliers})

@raw_materials_bp.route("/suppliers", methods=["POST"])
@admin_required
def create_supplier():
    data = request.get_json() or {}
    supplier_name = data.get("supplier_name", "").strip()
    phone = data.get("phone", "").strip()
    address = data.get("address", "").strip()
    materials_supplied = data.get("materials_supplied", "").strip()
    notes = data.get("notes", "").strip()
    
    if not supplier_name:
        return jsonify({"error": "Supplier name is required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM suppliers")
        next_num = cursor.fetchone()["count"] + 1
        supplier_code = f"SUP-{next_num:03d}"
        
        cursor.execute("""
            INSERT INTO suppliers (supplier_code, supplier_name, phone, address, materials_supplied, status, notes)
            VALUES (?, ?, ?, ?, ?, 'Active', ?)
        """, (supplier_code, supplier_name, phone, address, materials_supplied, notes))
        
        sup_id = cursor.lastrowid
        log_audit("Supplier Added", "Suppliers", supplier_code, f"Added supplier {supplier_name}", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Supplier {supplier_name} created successfully", "supplier_id": sup_id, "supplier_code": supplier_code}), 201

@raw_materials_bp.route("/suppliers/<int:sup_id>/history", methods=["GET"])
@login_required
def get_supplier_history(sup_id):
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM suppliers WHERE id = ?", (sup_id,))
        supplier = cursor.fetchone()
        if not supplier:
            return jsonify({"error": "Supplier not found"}), 404
            
        query = """
            SELECT p.*, m.material_name, m.unit as material_unit 
            FROM raw_material_purchases p 
            JOIN raw_materials m ON p.material_id = m.id 
            WHERE p.supplier_id = ?
        """
        params = [sup_id]
        if from_date:
            query += " AND p.purchase_date >= ?"
            params.append(from_date)
        if to_date:
            query += " AND p.purchase_date <= ?"
            params.append(to_date)
            
        query += " ORDER BY p.purchase_date DESC"
        cursor.execute(query, params)
        purchases = cursor.fetchall()
        
        # Summary by material
        cursor.execute("""
            SELECT m.material_name, SUM(p.quantity) as total_qty, m.unit, SUM(p.total_cost) as total_spent 
            FROM raw_material_purchases p 
            JOIN raw_materials m ON p.material_id = m.id 
            WHERE p.supplier_id = ?
            GROUP BY m.id
        """, (sup_id,))
        materials_breakdown = cursor.fetchall()
        
        total_spent = sum(p["total_cost"] for p in purchases)
        pending_amount = sum(p["total_cost"] for p in purchases if p["payment_status"] == "Pending")
        
    return jsonify({
        "supplier": supplier,
        "purchases": purchases,
        "materials_breakdown": materials_breakdown,
        "total_spent": total_spent,
        "pending_amount": pending_amount
    })

# ----------------- PURCHASES ----------------- #

@raw_materials_bp.route("/purchases", methods=["GET"])
@login_required
def get_purchases():
    supplier_id = request.args.get("supplier_id")
    material_id = request.args.get("material_id")
    payment_status = request.args.get("payment_status")
    
    query = """
        SELECT p.*, s.supplier_name, s.supplier_code, m.material_name, m.category as material_category
        FROM raw_material_purchases p
        JOIN suppliers s ON p.supplier_id = s.id
        JOIN raw_materials m ON p.material_id = m.id
        WHERE 1=1
    """
    params = []
    if supplier_id:
        query += " AND p.supplier_id = ?"
        params.append(supplier_id)
    if material_id:
        query += " AND p.material_id = ?"
        params.append(material_id)
    if payment_status:
        query += " AND p.payment_status = ?"
        params.append(payment_status)
        
    query += " ORDER BY p.purchase_date DESC, p.id DESC LIMIT 100"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        purchases = cursor.fetchall()
        
    return jsonify({"purchases": purchases})

@raw_materials_bp.route("/purchases", methods=["POST"])
@admin_required
def record_purchase():
    data = request.get_json() or {}
    purchase_date = data.get("purchase_date", datetime.now().strftime("%Y-%m-%d"))
    supplier_id = data.get("supplier_id")
    material_id = data.get("material_id")
    quantity = float(data.get("quantity", 0.0))
    rate_per_unit = float(data.get("rate_per_unit", 0.0))
    transport_cost = float(data.get("transport_cost", 0.0))
    other_cost = float(data.get("other_cost", 0.0))
    payment_status = data.get("payment_status", "Paid")
    payment_date = data.get("payment_date", purchase_date if payment_status == "Paid" else None)
    invoice_number = data.get("invoice_number", "").strip()
    notes = data.get("notes", "").strip()
    
    if not supplier_id or not material_id or quantity <= 0 or rate_per_unit <= 0:
        return jsonify({"error": "Supplier, Material, and valid positive Quantity and Rate are required"}), 400
        
    material_cost = round(quantity * rate_per_unit, 2)
    total_cost = round(material_cost + transport_cost + other_cost, 2)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify supplier and material
        cursor.execute("SELECT supplier_name FROM suppliers WHERE id = ?", (supplier_id,))
        sup = cursor.fetchone()
        if not sup:
            return jsonify({"error": "Supplier not found"}), 404
            
        cursor.execute("SELECT material_name, current_stock, minimum_stock_level, unit FROM raw_materials WHERE id = ?", (material_id,))
        mat = cursor.fetchone()
        if not mat:
            return jsonify({"error": "Raw material not found"}), 404
            
        cursor.execute("SELECT COUNT(*) as count FROM raw_material_purchases")
        next_num = cursor.fetchone()["count"] + 1
        purchase_code = f"PUR-{next_num:03d}"
        
        # 1. Insert Purchase
        cursor.execute("""
            INSERT INTO raw_material_purchases (purchase_code, purchase_date, supplier_id, material_id, quantity, unit, rate_per_unit, material_cost, transport_cost, other_cost, total_cost, payment_status, payment_date, invoice_number, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (purchase_code, purchase_date, supplier_id, material_id, quantity, mat["unit"], rate_per_unit, material_cost, transport_cost, other_cost, total_cost, payment_status, payment_date, invoice_number, notes))
        
        # 2. Update Stock in raw_materials
        new_stock = mat["current_stock"] + quantity
        new_status = "Normal" if new_stock > mat["minimum_stock_level"] else "Low Stock"
        
        cursor.execute("""
            UPDATE raw_materials 
            SET current_stock = ?, status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (new_stock, new_status, material_id))
        
        # 3. Log Inventory Movement
        cursor.execute("""
            INSERT INTO raw_material_movements (date, material_id, movement_type, quantity, balance_after, reference_id, notes)
            VALUES (?, ?, 'Purchase', ?, ?, ?, ?)
        """, (purchase_date, material_id, quantity, new_stock, purchase_code, f"Purchased from {sup['supplier_name']}"))
        
        # 4. Insert into Expenses
        cursor.execute("""
            INSERT INTO expenses (expense_code, date, category, description, amount, payment_method, paid_by, reference_id, notes)
            VALUES (?, ?, 'Raw Materials', ?, ?, 'Bank Transfer', 'Owner', ?, ?)
        """, (f"EXP-{purchase_code}", purchase_date, f"Purchase {purchase_code}: {quantity} {mat['unit']} of {mat['material_name']} from {sup['supplier_name']}", total_cost, purchase_code, notes))
        
        log_audit(
            "Raw Material Purchased",
            "Purchases",
            purchase_code,
            f"Purchased {quantity} {mat['unit']} of {mat['material_name']} from {sup['supplier_name']} for ₹{total_cost}. New stock: {new_stock} {mat['unit']}",
            user_id=g.user["user_id"],
            username=g.user["username"],
            conn=conn
        )
        
    return jsonify({
        "message": f"Recorded purchase {purchase_code} for {mat['material_name']}.",
        "purchase_code": purchase_code,
        "new_stock": new_stock,
        "total_cost": total_cost
    }), 201
