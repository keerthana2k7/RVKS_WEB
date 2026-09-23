from flask import Blueprint, request, jsonify, g
from datetime import datetime
from database.db import get_db, log_audit
from routes.auth import login_required, admin_required

workers_bp = Blueprint("workers", __name__, url_prefix="/api/workers")

# ----------------- WORKERS CRUD ----------------- #

@workers_bp.route("", methods=["GET"])
@login_required
def get_workers():
    status = request.args.get("status")
    search = request.args.get("search", "").strip()
    
    query = "SELECT * FROM workers WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (name LIKE ? OR worker_code LIKE ? OR job_role LIKE ? OR phone LIKE ?)"
        like_search = f"%{search}%"
        params.extend([like_search, like_search, like_search, like_search])
        
    query += " ORDER BY status ASC, name ASC"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        workers = cursor.fetchall()
        
    return jsonify({"workers": workers})

@workers_bp.route("", methods=["POST"])
@admin_required
def create_worker():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    job_role = data.get("job_role", "").strip()
    date_of_joining = data.get("date_of_joining", datetime.now().strftime("%Y-%m-%d"))
    salary_type = data.get("salary_type", "Monthly")
    salary_amount = float(data.get("salary_amount", 0.0))
    phone = data.get("phone", "").strip()
    address = data.get("address", "").strip()
    payment_method = data.get("payment_method", "Cash")
    notes = data.get("notes", "").strip()
    
    if not name or not job_role:
        return jsonify({"error": "Worker name and job role are required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM workers")
        next_num = cursor.fetchone()["count"] + 1
        worker_code = f"WRK-{next_num:03d}"
        
        cursor.execute("""
            INSERT INTO workers (worker_code, name, phone, address, date_of_joining, job_role, salary_type, salary_amount, payment_method, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
        """, (worker_code, name, phone, address, date_of_joining, job_role, salary_type, salary_amount, payment_method, notes))
        
        worker_id = cursor.lastrowid
        log_audit("Worker Added", "Workers", worker_code, f"Added worker {name} ({job_role})", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Worker {name} ({worker_code}) added successfully", "worker_id": worker_id, "worker_code": worker_code}), 201

@workers_bp.route("/<int:worker_id>", methods=["PUT"])
@admin_required
def update_worker(worker_id):
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    job_role = data.get("job_role", "").strip()
    phone = data.get("phone", "").strip()
    address = data.get("address", "").strip()
    salary_type = data.get("salary_type", "Monthly")
    salary_amount = float(data.get("salary_amount", 0.0))
    payment_method = data.get("payment_method", "Cash")
    notes = data.get("notes", "").strip()
    
    if not name or not job_role:
        return jsonify({"error": "Worker name and job role are required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE workers 
            SET name = ?, job_role = ?, phone = ?, address = ?, salary_type = ?, salary_amount = ?, payment_method = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (name, job_role, phone, address, salary_type, salary_amount, payment_method, notes, worker_id))
        
        log_audit("Worker Updated", "Workers", worker_id, f"Updated details for worker {name}", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": "Worker updated successfully"})

@workers_bp.route("/<int:worker_id>/status", methods=["PATCH"])
@admin_required
def toggle_worker_status(worker_id):
    data = request.get_json() or {}
    new_status = data.get("status")
    if new_status not in ["Active", "Inactive"]:
        return jsonify({"error": "Status must be 'Active' or 'Inactive'"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE workers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, worker_id))
        log_audit("Worker Status Changed", "Workers", worker_id, f"Worker status changed to {new_status}", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Worker marked as {new_status}"})

# ----------------- ATTENDANCE ----------------- #

@workers_bp.route("/attendance", methods=["GET"])
@login_required
def get_attendance():
    date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT w.id as worker_id, w.worker_code, w.name, w.job_role, w.status as worker_status,
                   a.id as attendance_id, a.date, 
                   COALESCE(a.status, 'Pending') as status, 
                   a.check_in_time, a.check_out_time, a.notes
            FROM workers w
            LEFT JOIN attendance a ON w.id = a.worker_id AND a.date = ?
            WHERE w.status = 'Active'
            ORDER BY w.name ASC
        """, (date,))
        records = cursor.fetchall()
    return jsonify({"date": date, "records": records})

@workers_bp.route("/attendance", methods=["POST"])
@login_required
def mark_single_attendance():
    data = request.get_json() or {}
    worker_id = data.get("worker_id")
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    status = data.get("status", "Present")
    check_in_time = data.get("check_in_time")
    check_out_time = data.get("check_out_time")
    notes = data.get("notes", "").strip()
    
    if not worker_id:
        return jsonify({"error": "Worker ID is required"}), 400
    if status not in ["Present", "Absent", "Half Day", "Leave"]:
        return jsonify({"error": "Invalid attendance status"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attendance (worker_id, date, status, check_in_time, check_out_time, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(worker_id, date) DO UPDATE SET
                status = excluded.status,
                check_in_time = excluded.check_in_time,
                check_out_time = excluded.check_out_time,
                notes = excluded.notes
        """, (worker_id, date, status, check_in_time, check_out_time, notes))
        
        log_audit("Attendance Marked", "Attendance", f"W-{worker_id}:{date}", f"Marked {status} on {date}", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": "Attendance recorded successfully"})

@workers_bp.route("/attendance/bulk", methods=["POST"])
@login_required
def mark_bulk_attendance():
    data = request.get_json() or {}
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    records = data.get("records", []) # List of { worker_id, status, check_in_time, check_out_time, notes }
    
    if not records:
        return jsonify({"error": "No attendance records provided"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        for r in records:
            w_id = r.get("worker_id")
            st = r.get("status", "Present")
            cin = r.get("check_in_time", "07:00") if st in ["Present", "Half Day"] else None
            cout = r.get("check_out_time", "17:30") if st in ["Present", "Half Day"] else None
            nt = r.get("notes", "").strip()
            
            cursor.execute("""
                INSERT INTO attendance (worker_id, date, status, check_in_time, check_out_time, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(worker_id, date) DO UPDATE SET
                    status = excluded.status,
                    check_in_time = excluded.check_in_time,
                    check_out_time = excluded.check_out_time,
                    notes = excluded.notes
            """, (w_id, date, st, cin, cout, nt))
            
        log_audit("Bulk Attendance Marked", "Attendance", date, f"Marked attendance for {len(records)} workers on {date}", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Successfully updated attendance for {len(records)} workers on {date}"})

@workers_bp.route("/attendance/stats", methods=["GET"])
@login_required
def get_attendance_stats():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT w.id as worker_id, w.name, w.worker_code, w.job_role,
                   COUNT(CASE WHEN a.status = 'Present' THEN 1 END) as present_days,
                   COUNT(CASE WHEN a.status = 'Absent' THEN 1 END) as absent_days,
                   COUNT(CASE WHEN a.status = 'Half Day' THEN 1 END) as half_days,
                   COUNT(CASE WHEN a.status = 'Leave' THEN 1 END) as leave_days,
                   COUNT(a.id) as total_marked
            FROM workers w
            LEFT JOIN attendance a ON w.id = a.worker_id AND strftime('%Y-%m', a.date) = ?
            WHERE w.status = 'Active'
            GROUP BY w.id
            ORDER BY w.name ASC
        """, (month,))
        stats = cursor.fetchall()
        
        for s in stats:
            total = s["total_marked"]
            effective_present = s["present_days"] + (0.5 * s["half_days"])
            s["attendance_percentage"] = round((effective_present / total * 100), 1) if total > 0 else 0.0
            
    return jsonify({"month": month, "stats": stats})

# ----------------- PAYMENTS ----------------- #

@workers_bp.route("/payments", methods=["GET"])
@admin_required
def get_payments():
    worker_id = request.args.get("worker_id")
    status = request.args.get("status")
    
    query = """
        SELECT wp.*, w.name as worker_name, w.worker_code, w.salary_type, w.salary_amount as default_salary
        FROM worker_payments wp
        JOIN workers w ON wp.worker_id = w.id
        WHERE 1=1
    """
    params = []
    if worker_id:
        query += " AND wp.worker_id = ?"
        params.append(worker_id)
    if status:
        query += " AND wp.status = ?"
        params.append(status)
        
    query += " ORDER BY wp.payment_date DESC, wp.id DESC"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        payments = cursor.fetchall()
        
        # Summary statistics
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total_paid FROM worker_payments WHERE status = 'Paid'")
        total_paid = cursor.fetchone()["total_paid"]
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total_pending FROM worker_payments WHERE status = 'Pending'")
        total_pending = cursor.fetchone()["total_pending"]
        
        cursor.execute("SELECT MAX(payment_date) as last_payment FROM worker_payments WHERE status = 'Paid'")
        last_payment = cursor.fetchone()["last_payment"]
        
    return jsonify({
        "payments": payments,
        "summary": {
            "total_paid": total_paid,
            "total_pending": total_pending,
            "last_payment_date": last_payment
        }
    })

@workers_bp.route("/payments", methods=["POST"])
@admin_required
def record_payment():
    data = request.get_json() or {}
    worker_id = data.get("worker_id")
    salary_period = data.get("salary_period", "").strip()
    payment_date = data.get("payment_date", datetime.now().strftime("%Y-%m-%d"))
    amount = float(data.get("amount", 0.0))
    payment_method = data.get("payment_method", "Cash")
    status = data.get("status", "Paid")
    notes = data.get("notes", "").strip()
    
    if not worker_id or not salary_period or amount <= 0:
        return jsonify({"error": "Worker, salary period, and valid positive amount are required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM worker_payments")
        next_num = cursor.fetchone()["count"] + 1
        payment_code = f"PMT-{next_num:03d}"
        
        cursor.execute("""
            INSERT INTO worker_payments (payment_code, worker_id, salary_period, payment_date, amount, payment_method, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (payment_code, worker_id, salary_period, payment_date, amount, payment_method, status, notes))
        
        # If marked as paid, record automatically in expenses table
        if status == "Paid":
            cursor.execute("SELECT name FROM workers WHERE id = ?", (worker_id,))
            w_name = cursor.fetchone()["name"]
            cursor.execute("""
                INSERT INTO expenses (expense_code, date, category, description, amount, payment_method, paid_by, reference_id, notes)
                VALUES (?, ?, 'Worker Salary', ?, ?, ?, 'Owner', ?, ?)
            """, (f"EXP-{payment_code}", payment_date, f"Salary to {w_name} ({salary_period})", amount, payment_method, payment_code, notes))
            
        log_audit("Worker Payment Recorded", "Payroll", payment_code, f"Payment of ₹{amount} to worker #{worker_id} ({status})", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Payment {payment_code} recorded successfully", "payment_code": payment_code}), 201
