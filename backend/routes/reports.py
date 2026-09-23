from flask import Blueprint, request, jsonify, Response
from datetime import datetime
import io
import csv
from database.db import get_db
from routes.auth import login_required, admin_required

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")

@reports_bp.route("/<report_type>", methods=["GET"])
@login_required
def generate_report(report_type):
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    worker_id = request.args.get("worker_id")
    batch_id = request.args.get("batch_id")
    supplier_id = request.args.get("supplier_id")
    material_id = request.args.get("material_id")
    feed_type = request.args.get("feed_type")
    export_format = request.args.get("format") # 'csv' or None
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        data = []
        columns = []
        title = "Farm Report"
        totals = {}
        
        # 1. WORKER REPORT
        if report_type == "workers":
            title = "Worker & Payroll Report"
            query = """
                SELECT w.worker_code, w.name, w.phone, w.job_role, w.salary_type, w.salary_amount, w.status,
                       COALESCE(SUM(CASE WHEN wp.status = 'Paid' THEN wp.amount ELSE 0 END), 0) as total_paid,
                       COALESCE(SUM(CASE WHEN wp.status = 'Pending' THEN wp.amount ELSE 0 END), 0) as total_pending
                FROM workers w
                LEFT JOIN worker_payments wp ON w.id = wp.worker_id
                WHERE 1=1
            """
            params = []
            if worker_id:
                query += " AND w.id = ?"
                params.append(worker_id)
            query += " GROUP BY w.id ORDER BY w.name ASC"
            cursor.execute(query, params)
            data = cursor.fetchall()
            columns = ["Worker ID", "Name", "Phone", "Role", "Salary Type", "Salary (₹)", "Status", "Total Paid (₹)", "Pending (₹)"]
            totals = {
                "total_paid": sum(d["total_paid"] for d in data),
                "total_pending": sum(d["total_pending"] for d in data)
            }
            
        # 2. ATTENDANCE REPORT
        elif report_type == "attendance":
            title = "Worker Attendance Report"
            query = """
                SELECT a.date, w.worker_code, w.name, a.status, a.check_in_time, a.check_out_time, a.notes
                FROM attendance a
                JOIN workers w ON a.worker_id = w.id
                WHERE 1=1
            """
            params = []
            if from_date:
                query += " AND a.date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND a.date <= ?"
                params.append(to_date)
            if worker_id:
                query += " AND a.worker_id = ?"
                params.append(worker_id)
            query += " ORDER BY a.date DESC, w.name ASC"
            cursor.execute(query, params)
            data = cursor.fetchall()
            columns = ["Date", "Worker ID", "Name", "Status", "Check In", "Check Out", "Notes"]
            
        # 3. BIRD REPORT
        elif report_type == "birds":
            title = "Bird Population & Mortality Report"
            query = """
                SELECT b.batch_code, b.batch_name, b.bird_type, b.arrival_date, b.initial_quantity, b.current_quantity,
                       b.shed_location, b.age_weeks, b.status,
                       COALESCE((SELECT SUM(number_of_birds) FROM mortality WHERE batch_id = b.id), 0) as total_mortality
                FROM bird_batches b
                WHERE 1=1
            """
            params = []
            if batch_id:
                query += " AND b.id = ?"
                params.append(batch_id)
            query += " ORDER BY b.id ASC"
            cursor.execute(query, params)
            data = cursor.fetchall()
            columns = ["Batch Code", "Batch Name", "Bird Type", "Arrival Date", "Initial Qty", "Current Qty", "Shed", "Age (Wks)", "Status", "Total Mortality"]
            totals = {
                "initial_quantity": sum(d["initial_quantity"] for d in data),
                "current_quantity": sum(d["current_quantity"] for d in data),
                "total_mortality": sum(d["total_mortality"] for d in data)
            }
            
        # 4. EGG REPORT
        elif report_type == "eggs":
            title = "Egg Production & Sales Report"
            query = """
                SELECT ep.date, b.batch_name, ep.total_eggs, ep.good_eggs, ep.broken_eggs, ep.damaged_eggs,
                       ep.sold_eggs, ep.remaining_eggs, ep.selling_price, ep.total_income
                FROM egg_production ep
                JOIN bird_batches b ON ep.batch_id = b.id
                WHERE 1=1
            """
            params = []
            if from_date:
                query += " AND ep.date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND ep.date <= ?"
                params.append(to_date)
            if batch_id:
                query += " AND ep.batch_id = ?"
                params.append(batch_id)
            query += " ORDER BY ep.date DESC, ep.id DESC"
            cursor.execute(query, params)
            data = cursor.fetchall()
            columns = ["Date", "Batch", "Total Eggs", "Good Eggs", "Broken", "Damaged", "Sold", "Remaining", "Rate (₹)", "Income (₹)"]
            totals = {
                "total_eggs": sum(d["total_eggs"] for d in data),
                "good_eggs": sum(d["good_eggs"] for d in data),
                "sold_eggs": sum(d["sold_eggs"] for d in data),
                "total_income": sum(d["total_income"] for d in data)
            }
            
        # 5. RAW MATERIAL REPORT
        elif report_type == "raw_materials":
            title = "Raw Material Purchases & Inventory Report"
            query = """
                SELECT p.purchase_code, p.purchase_date, s.supplier_name, m.material_name, p.quantity, p.unit,
                       p.rate_per_unit, p.material_cost, p.transport_cost, p.total_cost, p.payment_status, p.invoice_number
                FROM raw_material_purchases p
                JOIN suppliers s ON p.supplier_id = s.id
                JOIN raw_materials m ON p.material_id = m.id
                WHERE 1=1
            """
            params = []
            if from_date:
                query += " AND p.purchase_date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND p.purchase_date <= ?"
                params.append(to_date)
            if supplier_id:
                query += " AND p.supplier_id = ?"
                params.append(supplier_id)
            if material_id:
                query += " AND p.material_id = ?"
                params.append(material_id)
            query += " ORDER BY p.purchase_date DESC"
            cursor.execute(query, params)
            data = cursor.fetchall()
            columns = ["Purchase ID", "Date", "Supplier", "Material", "Qty", "Unit", "Rate (₹)", "Material Cost", "Transport", "Total Cost (₹)", "Status", "Invoice"]
            totals = {
                "total_quantity": sum(d["quantity"] for d in data),
                "total_cost": sum(d["total_cost"] for d in data)
            }
            
        # 6. FEED REPORT
        elif report_type == "feed":
            title = "Feed Production & Usage Report"
            query = """
                SELECT fp.production_code, fp.date, fp.feed_type, fp.batch_number, fp.quantity_produced, fp.unit,
                       fp.raw_material_cost, fp.labour_cost, fp.electricity_cost, fp.total_cost, fp.cost_per_kg, fp.produced_by
                FROM feed_production fp
                WHERE 1=1
            """
            params = []
            if from_date:
                query += " AND fp.date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND fp.date <= ?"
                params.append(to_date)
            if feed_type:
                query += " AND fp.feed_type = ?"
                params.append(feed_type)
            query += " ORDER BY fp.date DESC"
            cursor.execute(query, params)
            data = cursor.fetchall()
            columns = ["Production ID", "Date", "Feed Type", "Batch No", "Quantity", "Unit", "Raw Material Cost", "Labour Cost", "Electricity Cost", "Total Cost (₹)", "Cost/Kg (₹)", "Produced By"]
            totals = {
                "total_produced": sum(d["quantity_produced"] for d in data),
                "total_cost": sum(d["total_cost"] for d in data)
            }
            
        # 7. FINANCIAL REPORT
        elif report_type == "financial":
            title = "Farm Financial Summary Report"
            # Return high level combined financial lines
            query = """
                SELECT date, 'Income' as type, source as category, description, amount, payment_method
                FROM income
                WHERE 1=1
            """
            params = []
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
            query += " UNION ALL SELECT date, 'Expense' as type, category, description, amount, payment_method FROM expenses WHERE 1=1"
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
            query += " ORDER BY date DESC"
            cursor.execute(query, params)
            data = cursor.fetchall()
            columns = ["Date", "Type", "Category/Source", "Description", "Amount (₹)", "Payment Method"]
            total_inc = sum(d["amount"] for d in data if d["type"] == "Income")
            total_exp = sum(d["amount"] for d in data if d["type"] == "Expense")
            totals = {
                "total_income": total_inc,
                "total_expenses": total_exp,
                "net_balance": total_inc - total_exp
            }
            
        # 8. COMPLETE FARM REPORT
        elif report_type == "complete":
            title = "Complete 360° Farm Status Report"
            cursor.execute("SELECT COALESCE(SUM(current_quantity), 0) as birds FROM bird_batches WHERE status = 'Active'")
            total_birds = cursor.fetchone()["birds"]
            cursor.execute("SELECT COALESCE(SUM(current_stock), 0) as feed FROM feed_stock")
            total_feed = cursor.fetchone()["feed"]
            cursor.execute("SELECT COALESCE(SUM(current_stock), 0) as mats FROM raw_materials")
            total_mats = cursor.fetchone()["mats"]
            cursor.execute("SELECT COALESCE(SUM(total_eggs), 0) as eggs, COALESCE(SUM(total_income), 0) as egg_rev FROM egg_production")
            egg_tot = cursor.fetchone()
            cursor.execute("SELECT COALESCE(SUM(amount), 0) as exp FROM expenses")
            tot_exp = cursor.fetchone()["exp"]
            cursor.execute("SELECT COALESCE(SUM(amount), 0) as inc FROM income")
            tot_inc = cursor.fetchone()["inc"]
            
            data = [
                {"metric": "Active Birds Flock", "value": f"{total_birds:,} birds"},
                {"metric": "Finished Feed in Stock", "value": f"{total_feed:,.1f} kg"},
                {"metric": "Raw Materials in Stock", "value": f"{total_mats:,.1f} kg"},
                {"metric": "Total Eggs Produced", "value": f"{egg_tot['eggs']:,} eggs"},
                {"metric": "Total Egg Sales Revenue", "value": f"₹{egg_tot['egg_rev']:,.2f}"},
                {"metric": "All-Time Farm Income", "value": f"₹{tot_inc:,.2f}"},
                {"metric": "All-Time Farm Expenses", "value": f"₹{tot_exp:,.2f}"},
                {"metric": "Net Farm Balance", "value": f"₹{tot_inc - tot_exp:,.2f}"}
            ]
            columns = ["Farm Metric", "Current Value / Status"]
            totals = {"net_balance": tot_inc - tot_exp}
            
        else:
            return jsonify({"error": f"Unknown report type '{report_type}'"}), 400

        # Handle CSV Export if requested
        if export_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            # RVKS WEB Header
            writer.writerow(["RVKS WEB - Poultry Farm Management System"])
            writer.writerow([title])
            writer.writerow([f"Date Range: {from_date or 'All Time'} to {to_date or 'All Time'}"])
            writer.writerow([f"Generated Date: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"])
            writer.writerow([])
            
            # Table Header
            writer.writerow(columns)
            
            # Rows
            for row in data:
                writer.writerow(list(row.values()) if isinstance(row, dict) else row)
                
            # Totals
            if totals:
                writer.writerow([])
                writer.writerow(["TOTALS:"])
                for k, v in totals.items():
                    writer.writerow([k.replace("_", " ").title(), v])
                    
            response = Response(output.getvalue(), mimetype="text/csv")
            response.headers["Content-Disposition"] = f"attachment; filename=RVKS_Farm_{report_type}_{datetime.now().strftime('%Y%m%d')}.csv"
            return response
            
        return jsonify({
            "title": title,
            "report_type": report_type,
            "generated_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "date_range": {"from": from_date, "to": to_date},
            "columns": columns,
            "data": data,
            "totals": totals
        })
