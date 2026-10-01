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

# ----------------- FEED RAW MATERIAL DEALS & PURCHASES ----------------- #

@raw_materials_bp.route("/purchases", methods=["GET"])
@raw_materials_bp.route("/deals", methods=["GET"])
@login_required
def get_purchases():
    supplier_id = request.args.get("supplier_id")
    material_id = request.args.get("material_id")
    payment_status = request.args.get("payment_status")
    search = request.args.get("search", "").strip().lower()
    
    query = """
        SELECT p.*, 
               s.supplier_name, s.supplier_code, s.phone as supplier_phone, s.address as supplier_address,
               m.material_name, m.material_code, m.category as material_category, m.unit as material_unit
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
    if payment_status and payment_status != "All":
        if payment_status in ["Partial", "Partially Paid"]:
            query += " AND p.payment_status IN ('Partial', 'Partially Paid')"
        else:
            query += " AND p.payment_status = ?"
            params.append(payment_status)
        
    query += " ORDER BY COALESCE(p.deal_date, p.purchase_date) DESC, p.id DESC"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        all_deals = cursor.fetchall()
        
        # Apply optional text search
        filtered_deals = []
        for d in all_deals:
            d_dict = dict(d)
            # Ensure proper deal_date and calculations
            d_dict["deal_date"] = d_dict.get("deal_date") or d_dict.get("purchase_date")
            d_dict["total_deal_amount"] = d_dict.get("total_cost", 0.0)
            d_dict["advance_paid"] = d_dict.get("advance_paid") or 0.0
            d_dict["amount_paid"] = d_dict.get("amount_paid") or 0.0
            d_dict["amount_pending"] = d_dict.get("amount_pending") if d_dict.get("amount_pending") is not None else max(0.0, d_dict["total_deal_amount"] - d_dict["amount_paid"])
            
            # Normalize status
            if d_dict["payment_status"] == "Partial":
                d_dict["payment_status"] = "Partially Paid"
                
            if search:
                text_corpus = f"{d_dict.get('purchase_code', '')} {d_dict.get('supplier_name', '')} {d_dict.get('material_name', '')} {d_dict.get('notes', '')}".lower()
                if search not in text_corpus:
                    continue
            filtered_deals.append(d_dict)
            
        summary = {
            "total_deals": len(filtered_deals),
            "total_deal_amount": round(sum(d["total_deal_amount"] for d in filtered_deals), 2),
            "total_amount_paid": round(sum(d["amount_paid"] for d in filtered_deals), 2),
            "total_advance_paid": round(sum(d["advance_paid"] for d in filtered_deals), 2),
            "total_amount_pending": round(sum(d["amount_pending"] for d in filtered_deals), 2)
        }
        
    return jsonify({
        "purchases": filtered_deals,
        "deals": filtered_deals,
        "summary": summary
    })

@raw_materials_bp.route("/purchases", methods=["POST"])
@raw_materials_bp.route("/deals", methods=["POST"])
@admin_required
def record_purchase():
    data = request.get_json() or {}
    deal_date = data.get("deal_date") or data.get("purchase_date") or datetime.now().strftime("%Y-%m-%d")
    purchase_date = data.get("purchase_date") or deal_date
    expected_delivery_date = data.get("expected_delivery_date") or None
    actual_delivery_date = data.get("actual_delivery_date") or None
    payment_due_date = data.get("payment_due_date") or None
    
    supplier_id = data.get("supplier_id")
    material_id = data.get("material_id")
    quantity = float(data.get("quantity", 0.0))
    rate_per_unit = float(data.get("rate_per_unit", 0.0))
    transport_cost = float(data.get("transport_cost", 0.0))
    other_cost = float(data.get("other_cost", 0.0))
    advance_paid = float(data.get("advance_paid", 0.0))
    amount_paid_input = data.get("amount_paid")
    payment_method = data.get("payment_method", "Bank Transfer").strip()
    invoice_number = data.get("invoice_number", "").strip()
    notes = data.get("notes", "").strip()
    
    if not supplier_id or not material_id or quantity <= 0 or rate_per_unit <= 0:
        return jsonify({"error": "Supplier, Raw Material, positive Quantity and Rate are required"}), 400
        
    # Automatic Calculations (Sections 6 & 7)
    # Quantity * Rate per Unit = Total Material Cost
    material_cost = round(quantity * rate_per_unit, 2)
    total_deal_amount = round(material_cost + transport_cost + other_cost, 2)
    
    if amount_paid_input is not None:
        amount_paid = float(amount_paid_input)
    else:
        amount_paid = advance_paid
        
    amount_pending = max(0.0, round(total_deal_amount - amount_paid, 2))
    
    # Automated Payment Status: Pending, Partially Paid, Paid
    if amount_pending <= 0:
        payment_status = "Paid"
    elif amount_paid > 0:
        payment_status = "Partially Paid"
    else:
        payment_status = "Pending"
        
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify supplier and material
        cursor.execute("SELECT supplier_name, phone, supplier_code FROM suppliers WHERE id = ?", (supplier_id,))
        sup = cursor.fetchone()
        if not sup:
            return jsonify({"error": "Supplier not found"}), 404
            
        cursor.execute("SELECT material_name, material_code, current_stock, minimum_stock_level, unit FROM raw_materials WHERE id = ?", (material_id,))
        mat = cursor.fetchone()
        if not mat:
            return jsonify({"error": "Raw material not found"}), 404
            
        cursor.execute("SELECT COUNT(*) as count FROM raw_material_purchases")
        next_num = cursor.fetchone()["count"] + 1
        purchase_code = f"DEAL-{next_num:03d}"
        
        # 1. Insert Raw Material Deal
        cursor.execute("""
            INSERT INTO raw_material_purchases (
                purchase_code, deal_date, purchase_date, expected_delivery_date, actual_delivery_date,
                supplier_id, material_id, quantity, unit, rate_per_unit,
                material_cost, transport_cost, other_cost, total_cost,
                advance_paid, amount_paid, amount_pending, payment_due_date,
                payment_status, payment_method, invoice_number, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            purchase_code, deal_date, purchase_date, expected_delivery_date, actual_delivery_date,
            supplier_id, material_id, quantity, mat["unit"], rate_per_unit,
            material_cost, transport_cost, other_cost, total_deal_amount,
            advance_paid, amount_paid, amount_pending, payment_due_date,
            payment_status, payment_method, invoice_number, notes
        ))
        deal_id = cursor.lastrowid
        
        # 2. Record Initial Payment / Advance in deal_payments history
        if advance_paid > 0:
            cursor.execute("SELECT COUNT(*) as count FROM deal_payments")
            dpay_num = cursor.fetchone()["count"] + 1
            cursor.execute("""
                INSERT INTO deal_payments (payment_code, deal_id, supplier_id, payment_date, payment_type, amount, payment_method, notes)
                VALUES (?, ?, ?, ?, 'Advance', ?, ?, ?)
            """, (f"DPAY-{dpay_num:04d}", deal_id, supplier_id, deal_date, advance_paid, payment_method, "Booking advance payment"))
            
        if amount_paid > advance_paid:
            extra_paid = round(amount_paid - advance_paid, 2)
            cursor.execute("SELECT COUNT(*) as count FROM deal_payments")
            dpay_num = cursor.fetchone()["count"] + 1
            cursor.execute("""
                INSERT INTO deal_payments (payment_code, deal_id, supplier_id, payment_date, payment_type, amount, payment_method, notes)
                VALUES (?, ?, ?, ?, 'Payment', ?, ?, ?)
            """, (f"DPAY-{dpay_num:04d}", deal_id, supplier_id, deal_date, extra_paid, payment_method, "Initial payment"))
            
        # 3. Update Stock in raw_materials
        new_stock = mat["current_stock"] + quantity
        new_status = "Normal" if new_stock > mat["minimum_stock_level"] else "Low Stock"
        cursor.execute("""
            UPDATE raw_materials 
            SET current_stock = ?, status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (new_stock, new_status, material_id))
        
        # 4. Log Inventory Movement
        cursor.execute("""
            INSERT INTO raw_material_movements (date, material_id, movement_type, quantity, balance_after, reference_id, notes)
            VALUES (?, ?, 'Purchase', ?, ?, ?, ?)
        """, (purchase_date, material_id, quantity, new_stock, purchase_code, f"Feed deal from {sup['supplier_name']}"))
        
        # 5. Insert into Expenses for paid amount
        if amount_paid > 0:
            cursor.execute("""
                INSERT INTO expenses (expense_code, date, category, description, amount, payment_method, paid_by, reference_id, notes)
                VALUES (?, ?, 'Raw Materials', ?, ?, ?, 'Owner', ?, ?)
            """, (f"EXP-{purchase_code}", deal_date, f"Feed Raw Material Deal {purchase_code}: {quantity} {mat['unit']} of {mat['material_name']} from {sup['supplier_name']}", amount_paid, payment_method, purchase_code, notes))
            
        log_audit(
            "Raw Material Deal Created",
            "Feed Deals",
            purchase_code,
            f"Deal {purchase_code} for {quantity} {mat['unit']} of {mat['material_name']} from {sup['supplier_name']} @ ₹{rate_per_unit}/{mat['unit']}. Total: ₹{total_deal_amount}, Paid: ₹{amount_paid}, Pending: ₹{amount_pending}",
            user_id=g.user["user_id"],
            username=g.user["username"],
            conn=conn
        )
        
    return jsonify({
        "message": f"Raw material deal {purchase_code} recorded successfully.",
        "deal_id": deal_id,
        "purchase_code": purchase_code,
        "total_deal_amount": total_deal_amount,
        "amount_paid": amount_paid,
        "amount_pending": amount_pending,
        "payment_status": payment_status,
        "new_stock": new_stock
    }), 201

# ----------------- DEAL PAYMENTS & PAYMENT HISTORY ----------------- #

@raw_materials_bp.route("/deals/<int:deal_id>/payments", methods=["GET"])
@raw_materials_bp.route("/purchases/<int:deal_id>/payments", methods=["GET"])
@login_required
def get_deal_payment_history(deal_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, s.supplier_name, s.supplier_code, s.phone as supplier_phone,
                   m.material_name, m.unit as material_unit
            FROM raw_material_purchases p
            JOIN suppliers s ON p.supplier_id = s.id
            JOIN raw_materials m ON p.material_id = m.id
            WHERE p.id = ?
        """, (deal_id,))
        deal = cursor.fetchone()
        if not deal:
            return jsonify({"error": "Deal not found"}), 404
            
        cursor.execute("""
            SELECT * FROM deal_payments 
            WHERE deal_id = ? 
            ORDER BY payment_date ASC, id ASC
        """, (deal_id,))
        payments = cursor.fetchall()
        
    return jsonify({
        "deal": deal,
        "payments": payments
    })

@raw_materials_bp.route("/deals/<int:deal_id>/payments", methods=["POST"])
@raw_materials_bp.route("/purchases/<int:deal_id>/payments", methods=["POST"])
@admin_required
def record_deal_payment(deal_id):
    data = request.get_json() or {}
    payment_date = data.get("payment_date") or datetime.now().strftime("%Y-%m-%d")
    payment_type = data.get("payment_type", "Payment").strip() # Advance, Payment, Final Payment, Other
    amount = float(data.get("amount", 0.0))
    payment_method = data.get("payment_method", "Bank Transfer").strip()
    notes = data.get("notes", "").strip()
    
    if amount <= 0:
        return jsonify({"error": "Valid positive payment amount is required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, s.supplier_name, m.material_name 
            FROM raw_material_purchases p
            JOIN suppliers s ON p.supplier_id = s.id
            JOIN raw_materials m ON p.material_id = m.id
            WHERE p.id = ?
        """, (deal_id,))
        deal = cursor.fetchone()
        if not deal:
            return jsonify({"error": "Deal not found"}), 404
            
        cursor.execute("SELECT COUNT(*) as count FROM deal_payments")
        dpay_num = cursor.fetchone()["count"] + 1
        payment_code = f"DPAY-{dpay_num:04d}"
        
        # 1. Insert payment record
        cursor.execute("""
            INSERT INTO deal_payments (payment_code, deal_id, supplier_id, payment_date, payment_type, amount, payment_method, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (payment_code, deal_id, deal["supplier_id"], payment_date, payment_type, amount, payment_method, notes))
        
        # 2. Recalculate totals
        current_amount_paid = deal["amount_paid"] or 0.0
        current_advance = deal["advance_paid"] or 0.0
        new_amount_paid = round(current_amount_paid + amount, 2)
        new_advance_paid = round(current_advance + amount, 2) if payment_type == "Advance" else current_advance
        new_pending = max(0.0, round(deal["total_cost"] - new_amount_paid, 2))
        
        if new_pending <= 0:
            new_status = "Paid"
        elif new_amount_paid > 0:
            new_status = "Partially Paid"
        else:
            new_status = "Pending"
            
        cursor.execute("""
            UPDATE raw_material_purchases
            SET amount_paid = ?, advance_paid = ?, amount_pending = ?, payment_status = ?, payment_date = ?
            WHERE id = ?
        """, (new_amount_paid, new_advance_paid, new_pending, new_status, payment_date, deal_id))
        
        # 3. Log to Expenses
        cursor.execute("""
            INSERT INTO expenses (expense_code, date, category, description, amount, payment_method, paid_by, reference_id, notes)
            VALUES (?, ?, 'Raw Materials', ?, ?, ?, 'Owner', ?, ?)
        """, (f"EXP-{payment_code}", payment_date, f"{payment_type} for Deal {deal['purchase_code']}: {deal['supplier_name']}", amount, payment_method, deal['purchase_code'], notes))
        
        log_audit(
            "Supplier Deal Payment Recorded",
            "Supplier Payments",
            payment_code,
            f"Paid ₹{amount} ({payment_type}) via {payment_method} to {deal['supplier_name']} for deal {deal['purchase_code']}. New remaining: ₹{new_pending}",
            user_id=g.user["user_id"],
            username=g.user["username"],
            conn=conn
        )
        
    return jsonify({
        "message": f"Payment of ₹{amount} recorded for deal {deal['purchase_code']}",
        "payment_code": payment_code,
        "new_amount_paid": new_amount_paid,
        "new_amount_pending": new_pending,
        "new_status": new_status
    }), 201

