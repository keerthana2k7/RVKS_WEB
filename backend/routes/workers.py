from flask import Blueprint, request, jsonify, g
from datetime import datetime
from database.db import get_db, log_audit
from routes.auth import admin_required, login_required

workers_bp = Blueprint("workers", __name__, url_prefix="/api/workers")

# ----------------- WORKERS CRUD (ADMIN ONLY) ----------------- #

@workers_bp.route("", methods=["GET"])
@admin_required
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

@workers_bp.route("/<int:worker_id>", methods=["GET"])
@admin_required
def get_worker_detail(worker_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
        worker = cursor.fetchone()
        if not worker:
            return jsonify({"error": "Worker record not found"}), 404
            
        # Attendance summary
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN status = 'Present' THEN 1 END) as present_days,
                COUNT(CASE WHEN status = 'Absent' THEN 1 END) as absent_days,
                COUNT(CASE WHEN status = 'Half Day' THEN 1 END) as half_days,
                COUNT(CASE WHEN status = 'Leave' THEN 1 END) as leave_days,
                COUNT(id) as total_attendance_marked
            FROM attendance
            WHERE worker_id = ?
        """, (worker_id,))
        att_summary = cursor.fetchone()
        
        # Payment summary
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN status = 'Paid' THEN amount END), 0) as total_paid,
                COALESCE(SUM(CASE WHEN status = 'Pending' THEN amount END), 0) as total_pending,
                MAX(CASE WHEN status = 'Paid' THEN payment_date END) as last_payment_date
            FROM worker_payments
            WHERE worker_id = ?
        """, (worker_id,))
        pay_summary = cursor.fetchone()
        
    return jsonify({
        "worker": worker,
        "attendance_summary": att_summary,
        "payment_summary": pay_summary
    })

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
    payment_status = data.get("payment_status", "Pending")
    payment_date = data.get("payment_date")
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
            INSERT INTO workers (worker_code, name, phone, address, date_of_joining, job_role, salary_type, salary_amount, payment_status, payment_date, payment_method, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
        """, (worker_code, name, phone, address, date_of_joining, job_role, salary_type, salary_amount, payment_status, payment_date, payment_method, notes))
        
        worker_id = cursor.lastrowid
        log_audit("Worker Added", "Workers", worker_code, f"Added worker record {name} ({job_role})", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Worker record {name} ({worker_code}) added successfully", "worker_id": worker_id, "worker_code": worker_code}), 201

@workers_bp.route("/<int:worker_id>", methods=["PUT"])
@admin_required
def update_worker(worker_id):
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    job_role = data.get("job_role", "").strip()
    phone = data.get("phone", "").strip()
    address = data.get("address", "").strip()
    date_of_joining = data.get("date_of_joining")
    salary_type = data.get("salary_type", "Monthly")
    salary_amount = float(data.get("salary_amount", 0.0))
    payment_status = data.get("payment_status", "Pending")
    payment_date = data.get("payment_date")
    payment_method = data.get("payment_method", "Cash")
    status = data.get("status", "Active")
    notes = data.get("notes", "").strip()
    
    if not name or not job_role:
        return jsonify({"error": "Worker name and job role are required"}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE workers 
            SET name = ?, job_role = ?, phone = ?, address = ?, date_of_joining = COALESCE(?, date_of_joining),
                salary_type = ?, salary_amount = ?, payment_status = ?, payment_date = ?, payment_method = ?,
                status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (name, job_role, phone, address, date_of_joining, salary_type, salary_amount, payment_status, payment_date, payment_method, status, notes, worker_id))
        
        log_audit("Worker Updated", "Workers", worker_id, f"Updated details for worker {name}", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Worker record {name} updated successfully"})

@workers_bp.route("/<int:worker_id>", methods=["DELETE"])
@admin_required
def delete_worker(worker_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, worker_code FROM workers WHERE id = ?", (worker_id,))
        worker = cursor.fetchone()
        if not worker:
            return jsonify({"error": "Worker record not found"}), 404
            
        cursor.execute("DELETE FROM attendance WHERE worker_id = ?", (worker_id,))
        cursor.execute("DELETE FROM worker_payments WHERE worker_id = ?", (worker_id,))
        cursor.execute("DELETE FROM workers WHERE id = ?", (worker_id,))
        
        log_audit("Worker Deleted", "Workers", worker["worker_code"], f"Deleted worker record {worker['name']} ({worker['worker_code']})", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({"message": f"Worker {worker['name']} ({worker['worker_code']}) deleted successfully"})

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

@workers_bp.route("/<int:worker_id>/history", methods=["GET"])
@admin_required
def get_worker_history(worker_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
        worker = cursor.fetchone()
        if not worker:
            return jsonify({"error": "Worker not found"}), 404
            
        cursor.execute("SELECT * FROM attendance WHERE worker_id = ? ORDER BY date DESC LIMIT 60", (worker_id,))
        attendance_logs = cursor.fetchall()
        
        cursor.execute("SELECT * FROM worker_payments WHERE worker_id = ? ORDER BY payment_date DESC, id DESC", (worker_id,))
        payments = cursor.fetchall()
        
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN status = 'Present' THEN 1 END) as present_days,
                COUNT(CASE WHEN status = 'Absent' THEN 1 END) as absent_days,
                COUNT(CASE WHEN status = 'Half Day' THEN 1 END) as half_days,
                COUNT(CASE WHEN status = 'Leave' THEN 1 END) as leave_days,
                COUNT(id) as total_days
            FROM attendance WHERE worker_id = ?
        """, (worker_id,))
        att_stats = cursor.fetchone()
        
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN status = 'Paid' THEN amount END), 0) as total_paid,
                COALESCE(SUM(CASE WHEN status = 'Pending' THEN amount END), 0) as total_pending
            FROM worker_payments WHERE worker_id = ?
        """, (worker_id,))
        pay_stats = cursor.fetchone()
        
    return jsonify({
        "worker": worker,
        "attendance": attendance_logs,
        "payments": payments,
        "attendance_stats": att_stats,
        "payment_stats": pay_stats
    })

# ----------------- ATTENDANCE (ADMIN ONLY) ----------------- #

@workers_bp.route("/attendance", methods=["GET"])
@admin_required
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
@admin_required
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
@admin_required
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
@admin_required
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

# ----------------- PAYROLL & PAYMENTS (ADMIN ONLY) ----------------- #

@workers_bp.route("/payroll", methods=["GET"])
@admin_required
def get_payroll_overview():
    """
    Direct Payroll Management Endpoint.
    Returns per-worker real-time payment calculations:
    Salary, Advance, Regular Paid, Extra Paid, Total Received, Remaining, Status, Due Date.
    """
    import calendar
    month_param = request.args.get("month") # e.g. "2026-10" or "Oct 2026"
    status_filter = request.args.get("status") # "All", "Paid", "Pending", "Partially Paid", "Overpaid", "Payment Due", "Advance Paid"
    search = request.args.get("search", "").strip().lower()
    
    today = datetime.now()
    if not month_param:
        target_year = today.year
        target_month = today.month
        salary_period = today.strftime("%b %Y")
        month_iso = today.strftime("%Y-%m")
    else:
        try:
            if "-" in month_param:
                dt = datetime.strptime(month_param, "%Y-%m")
            else:
                dt = datetime.strptime(month_param, "%b %Y")
            target_year = dt.year
            target_month = dt.month
            salary_period = dt.strftime("%b %Y")
            month_iso = dt.strftime("%Y-%m")
        except Exception:
            target_year = today.year
            target_month = today.month
            salary_period = today.strftime("%b %Y")
            month_iso = today.strftime("%Y-%m")
            
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM workers WHERE status = 'Active' ORDER BY name ASC")
        workers = cursor.fetchall()
        
        payroll_list = []
        total_salary_due_sum = 0.0
        total_paid_sum = 0.0
        total_pending_sum = 0.0
        total_advance_paid_sum = 0.0
        total_extra_paid_sum = 0.0
        
        for w in workers:
            w_id = w["id"]
            salary_type = w.get("salary_type", "Monthly")
            base_salary = float(w.get("salary_amount", 0.0))
            
            if salary_type == "Monthly":
                salary_due = base_salary
            elif salary_type == "Weekly":
                salary_due = round(base_salary * 4, 2)
            else: # Daily
                salary_due = round(base_salary * 30, 2)
                
            due_day = w.get("payment_due_day") or 30
            actual_due_day = min(due_day, calendar.monthrange(target_year, target_month)[1])
            worker_due_date = f"{target_year:04d}-{target_month:02d}-{actual_due_day:02d}"
            
            cursor.execute("""
                SELECT * FROM worker_payments 
                WHERE worker_id = ? AND (salary_period = ? OR strftime('%Y-%m', payment_date) = ?)
                ORDER BY payment_date ASC, id ASC
            """, (w_id, salary_period, month_iso))
            payments = cursor.fetchall()
            
            regular_paid = 0.0
            advance_paid = 0.0
            extra_paid = 0.0
            
            for p in payments:
                amt = float(p.get("amount") or 0.0)
                ext = float(p.get("extra_amount") or 0.0)
                p_type = p.get("payment_type") or "Salary"
                is_adv = bool(p.get("is_advance"))
                is_ext = bool(p.get("is_extra"))
                
                # The explicit extra amount column always counts towards extra_paid
                extra_paid += ext
                
                if p_type == "Advance" or is_adv:
                    advance_paid += amt
                elif p_type in ("Extra", "Bonus"):
                    extra_paid += amt
                else:
                    regular_paid += amt
                    
            regular_paid = round(regular_paid, 2)
            advance_paid = round(advance_paid, 2)
            extra_paid = round(extra_paid, 2)
            
            total_paid = round(regular_paid + advance_paid + extra_paid, 2)
            effective_salary_paid = round(regular_paid + advance_paid, 2)
            remaining_amount = round(max(0.0, salary_due - effective_salary_paid), 2)
            
            if effective_salary_paid == 0:
                payment_status = "Pending"
            elif effective_salary_paid < salary_due:
                payment_status = "Partially Paid"
            elif effective_salary_paid == salary_due:
                payment_status = "Paid"
            else:
                payment_status = "Overpaid"
                
            cursor.execute("""
                SELECT payment_date, amount, payment_type 
                FROM worker_payments 
                WHERE worker_id = ? 
                ORDER BY payment_date DESC, id DESC LIMIT 1
            """, (w_id,))
            last_p = cursor.fetchone()
            last_payment_date = last_p["payment_date"] if last_p else (w.get("payment_date") or "-")
            
            today_str = today.strftime("%Y-%m-%d")
            is_payment_due = (today_str >= worker_due_date) and (payment_status != "Paid")
            
            item = {
                "worker_id": w_id,
                "worker_code": w["worker_code"],
                "name": w["name"],
                "job_role": w["job_role"],
                "phone": w.get("phone") or "",
                "salary_type": salary_type,
                "salary_amount": base_salary,
                "regular_salary_due": salary_due,
                "payment_due_date": worker_due_date,
                "next_due_date": worker_due_date,
                "amount_already_paid": regular_paid,
                "advance_paid": advance_paid,
                "extra_amount_paid": extra_paid,
                "total_amount_paid": total_paid,
                "remaining_amount": remaining_amount,
                "payment_status": payment_status,
                "last_payment_date": last_payment_date,
                "is_payment_due": is_payment_due,
                "notes": w.get("notes") or ""
            }
            
            if search:
                w_text = f"{w['name']} {w['worker_code']} {w['job_role']} {w.get('phone', '')}".lower()
                if search not in w_text:
                    continue
                    
            if status_filter and status_filter != "All":
                if status_filter == "Payment Due" and not is_payment_due:
                    continue
                elif status_filter == "Advance Paid" and advance_paid <= 0:
                    continue
                elif status_filter in ("Paid", "Pending", "Partially Paid", "Overpaid") and payment_status != status_filter:
                    continue
                    
            payroll_list.append(item)
            
            total_salary_due_sum += salary_due
            total_paid_sum += total_paid
            total_pending_sum += remaining_amount
            total_advance_paid_sum += advance_paid
            total_extra_paid_sum += extra_paid
            
        summary = {
            "total_workers": len(workers),
            "filtered_workers": len(payroll_list),
            "total_salary_due": round(total_salary_due_sum, 2),
            "total_paid": round(total_paid_sum, 2),
            "total_pending": round(total_pending_sum, 2),
            "total_advance_paid": round(total_advance_paid_sum, 2),
            "total_extra_paid": round(total_extra_paid_sum, 2),
            "salary_period": salary_period,
            "month_iso": month_iso
        }
        
    return jsonify({
        "payroll": payroll_list,
        "summary": summary
    })

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
        
        cursor.execute("SELECT COALESCE(SUM(amount + COALESCE(extra_amount, 0)), 0) as total_paid FROM worker_payments WHERE status = 'Paid'")
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

@workers_bp.route("/<int:worker_id>/payments", methods=["GET"])
@admin_required
def get_worker_payment_history(worker_id):
    """Returns full historical payment transactions for a specific worker."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
        worker = cursor.fetchone()
        if not worker:
            return jsonify({"error": "Worker not found"}), 404
            
        cursor.execute("""
            SELECT * FROM worker_payments 
            WHERE worker_id = ? 
            ORDER BY payment_date DESC, id DESC
        """, (worker_id,))
        payments = cursor.fetchall()
        
        cursor.execute("""
            SELECT 
                COALESCE(SUM(amount), 0) as total_base_paid,
                COALESCE(SUM(extra_amount), 0) as total_extra_paid,
                COALESCE(SUM(CASE WHEN is_advance = 1 OR payment_type = 'Advance' THEN amount END), 0) as total_advance_paid,
                COALESCE(SUM(amount + COALESCE(extra_amount, 0)), 0) as total_received
            FROM worker_payments
            WHERE worker_id = ?
        """, (worker_id,))
        stats = cursor.fetchone()
        
    return jsonify({
        "worker": worker,
        "payments": payments,
        "stats": stats
    })

@workers_bp.route("/payments", methods=["POST"])
@admin_required
def record_payment():
    data = request.get_json() or {}
    worker_id = data.get("worker_id")
    payment_date = data.get("payment_date", datetime.now().strftime("%Y-%m-%d"))
    amount = float(data.get("amount", 0.0))
    extra_amount = float(data.get("extra_amount", 0.0))
    payment_type = data.get("payment_type", "Salary")
    extra_reason = data.get("extra_reason", "").strip() or None
    payment_method = data.get("payment_method", "Cash")
    salary_period = data.get("salary_period", "").strip()
    notes = data.get("notes", "").strip()
    
    # Auto-fill salary_period if missing
    if not salary_period:
        try:
            p_dt = datetime.strptime(payment_date, "%Y-%m-%d")
            salary_period = p_dt.strftime("%b %Y")
        except Exception:
            salary_period = datetime.now().strftime("%b %Y")
            
    total_transaction_amount = amount + extra_amount
    if not worker_id or total_transaction_amount <= 0:
        return jsonify({"error": "Worker and a valid positive amount are required"}), 400
        
    is_advance = 1 if (payment_type == "Advance" or data.get("is_advance")) else 0
    is_extra = 1 if (extra_amount > 0 or payment_type in ("Extra", "Bonus") or data.get("is_extra")) else 0
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
        worker = cursor.fetchone()
        if not worker:
            return jsonify({"error": "Worker record not found"}), 404
            
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 as next_id FROM worker_payments")
        next_id = cursor.fetchone()["next_id"]
        payment_code = f"PMT-{next_id:04d}"
        cursor.execute("SELECT id FROM worker_payments WHERE payment_code = ?", (payment_code,))
        if cursor.fetchone():
            payment_code = f"PMT-{next_id:04d}-{int(datetime.now().timestamp())}"
        
        cursor.execute("""
            INSERT INTO worker_payments 
            (payment_code, worker_id, salary_period, payment_date, payment_type, amount, extra_amount, is_advance, is_extra, extra_reason, payment_method, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Paid', ?)
        """, (payment_code, worker_id, salary_period, payment_date, payment_type, amount, extra_amount, is_advance, is_extra, extra_reason, payment_method, notes))
        
        # Recompute worker's current cycle payment status
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN (payment_type = 'Salary' OR payment_type IS NULL) AND is_advance = 0 THEN amount END), 0) as reg_paid,
                COALESCE(SUM(CASE WHEN is_advance = 1 OR payment_type = 'Advance' THEN amount END), 0) as adv_paid
            FROM worker_payments 
            WHERE worker_id = ? AND salary_period = ?
        """, (worker_id, salary_period))
        p_row = cursor.fetchone()
        eff_paid = p_row["reg_paid"] + p_row["adv_paid"]
        
        salary_due = float(worker.get("salary_amount", 0.0))
        if worker.get("salary_type") == "Weekly":
            salary_due *= 4
        elif worker.get("salary_type") == "Daily":
            salary_due *= 30
            
        if eff_paid == 0:
            new_status = "Pending"
        elif eff_paid < salary_due:
            new_status = "Partially Paid"
        elif eff_paid == salary_due:
            new_status = "Paid"
        else:
            new_status = "Overpaid"
            
        cursor.execute("""
            UPDATE workers 
            SET payment_status = ?, payment_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, payment_date, worker_id))
        
        # Record in expenses table for accounting
        w_name = worker["name"]
        desc_parts = [f"Salary payment to {w_name} ({salary_period}) - ₹{amount}"]
        if extra_amount > 0:
            desc_parts.append(f"Extra ({extra_reason or 'Bonus'}): ₹{extra_amount}")
        full_desc = " | ".join(desc_parts)
        
        exp_code = f"EXP-{payment_code}"
        cursor.execute("SELECT id FROM expenses WHERE expense_code = ?", (exp_code,))
        if cursor.fetchone():
            exp_code = f"EXP-{payment_code}-{int(datetime.now().timestamp())}"
            
        cursor.execute("""
            INSERT INTO expenses (expense_code, date, category, description, amount, payment_method, paid_by, reference_id, notes)
            VALUES (?, ?, 'Worker Salary', ?, ?, ?, 'Owner', ?, ?)
        """, (exp_code, payment_date, full_desc, total_transaction_amount, payment_method, payment_code, notes))
        
        log_audit("Worker Payment Recorded", "Payroll", payment_code, f"Paid ₹{amount} (+ ₹{extra_amount} extra) to {w_name} [{payment_type}]", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({
        "message": f"Payment {payment_code} recorded successfully",
        "payment_code": payment_code,
        "new_status": new_status,
        "total_paid": total_transaction_amount
    }), 201
