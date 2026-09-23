from flask import Blueprint, request, jsonify, g
from datetime import datetime
from database.db import get_db, log_audit
from routes.auth import login_required

sync_bp = Blueprint("sync", __name__, url_prefix="/api/sync")

@sync_bp.route("", methods=["POST"])
@login_required
def process_sync_queue():
    data = request.get_json() or {}
    queue = data.get("records", [])
    
    results = []
    synced_count = 0
    error_count = 0
    
    if not queue:
        return jsonify({"message": "Empty queue. Nothing to sync.", "synced_count": 0, "error_count": 0, "results": []})
        
    with get_db() as conn:
        cursor = conn.cursor()
        
        for item in queue:
            queue_id = item.get("queue_id")
            rec_type = item.get("type")
            p = item.get("payload", {})
            
            try:
                # 1. Attendance Sync
                if rec_type == "attendance":
                    w_id = p.get("worker_id")
                    dt = p.get("date", datetime.now().strftime("%Y-%m-%d"))
                    st = p.get("status", "Present")
                    cin = p.get("check_in_time")
                    cout = p.get("check_out_time")
                    nt = p.get("notes", "Offline synced")
                    
                    cursor.execute("""
                        INSERT INTO attendance (worker_id, date, status, check_in_time, check_out_time, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(worker_id, date) DO UPDATE SET
                            status = excluded.status,
                            check_in_time = excluded.check_in_time,
                            check_out_time = excluded.check_out_time,
                            notes = excluded.notes
                    """, (w_id, dt, st, cin, cout, nt))
                    
                    results.append({"queue_id": queue_id, "status": "synced", "message": f"Attendance recorded for worker {w_id}"})
                    synced_count += 1
                    
                # 2. Mortality Sync
                elif rec_type == "mortality":
                    b_id = p.get("batch_id")
                    birds = int(p.get("number_of_birds", 0))
                    dt = p.get("date", datetime.now().strftime("%Y-%m-%d"))
                    rsn = p.get("reason", "Weakness")
                    shed = p.get("shed_location", "")
                    nt = p.get("notes", "Offline synced")
                    
                    cursor.execute("SELECT current_quantity, bird_type, batch_name FROM bird_batches WHERE id = ?", (b_id,))
                    b = cursor.fetchone()
                    if not b:
                        raise Exception("Batch not found")
                    if b["current_quantity"] < birds:
                        raise Exception(f"Insufficient bird population. Available: {b['current_quantity']}")
                        
                    new_qty = b["current_quantity"] - birds
                    cursor.execute("""
                        INSERT INTO mortality (date, batch_id, bird_type, number_of_birds, reason, shed_location, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (dt, b_id, b["bird_type"], birds, rsn, shed, nt))
                    
                    cursor.execute("UPDATE bird_batches SET current_quantity = ? WHERE id = ?", (new_qty, b_id))
                    cursor.execute("""
                        INSERT INTO bird_transactions (batch_id, date, tx_type, quantity, balance_after, reference_id, notes)
                        VALUES (?, ?, 'Mortality', ?, ?, 'MORT-OFFLINE', ?)
                    """, (b_id, dt, -birds, new_qty, f"Offline sync mortality: {rsn}"))
                    
                    results.append({"queue_id": queue_id, "status": "synced", "message": f"Recorded {birds} mortality in {b['batch_name']}"})
                    synced_count += 1
                    
                # 3. Egg Production Sync
                elif rec_type == "egg_production":
                    b_id = p.get("batch_id")
                    dt = p.get("date", datetime.now().strftime("%Y-%m-%d"))
                    tot = int(p.get("total_eggs", 0))
                    good = int(p.get("good_eggs", tot))
                    broken = int(p.get("broken_eggs", 0))
                    dam = int(p.get("damaged_eggs", 0))
                    sold = int(p.get("sold_eggs", 0))
                    price = float(p.get("selling_price", 5.50))
                    rem = good - sold
                    inc = round(sold * price, 2)
                    nt = p.get("notes", "Offline synced")
                    
                    cursor.execute("""
                        INSERT INTO egg_production (date, batch_id, total_eggs, good_eggs, broken_eggs, damaged_eggs, sold_eggs, remaining_eggs, selling_price, total_income, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (dt, b_id, tot, good, broken, dam, sold, rem, price, inc, nt))
                    
                    if inc > 0:
                        cursor.execute("""
                            INSERT INTO income (income_code, date, source, description, quantity, rate, amount, payment_method, notes)
                            VALUES (?, ?, 'Egg Sales', ?, ?, ?, ?, 'Cash', ?)
                        """, (f"INC-SYNC-{dt}-{b_id}", dt, f"Offline Egg sales ({sold} eggs)", sold, price, inc, nt))
                        
                    results.append({"queue_id": queue_id, "status": "synced", "message": f"Recorded {tot} eggs for batch {b_id}"})
                    synced_count += 1
                    
                # 4. Feed Usage Sync
                elif rec_type == "feed_usage":
                    b_id = p.get("batch_id")
                    ft = p.get("feed_type")
                    qty = float(p.get("quantity", 0))
                    dt = p.get("date", datetime.now().strftime("%Y-%m-%d"))
                    nt = p.get("notes", "Offline synced")
                    
                    cursor.execute("SELECT current_stock FROM feed_stock WHERE feed_type = ?", (ft,))
                    f_st = cursor.fetchone()
                    if not f_st or f_st["current_stock"] < qty:
                        raise Exception(f"Insufficient {ft} feed stock")
                        
                    new_st = f_st["current_stock"] - qty
                    cursor.execute("UPDATE feed_stock SET current_stock = ? WHERE feed_type = ?", (new_st, ft))
                    
                    cursor.execute("SELECT COUNT(*) as count FROM feed_usage")
                    usg_code = f"FUS-{cursor.fetchone()['count'] + 1:03d}"
                    
                    cursor.execute("SELECT bird_type FROM bird_batches WHERE id = ?", (b_id,))
                    b_row = cursor.fetchone()
                    b_type = b_row["bird_type"] if b_row else "Layer"
                    
                    cursor.execute("""
                        INSERT INTO feed_usage (usage_code, date, batch_id, bird_type, feed_type, quantity, unit, notes)
                        VALUES (?, ?, ?, ?, ?, ?, 'Kg', ?)
                    """, (usg_code, dt, b_id, b_type, ft, qty, nt))
                    
                    cursor.execute("""
                        INSERT INTO feed_stock_movements (date, feed_type, movement_type, quantity, balance_after, reference_id, notes)
                        VALUES (?, ?, 'Used', ?, ?, ?, 'Offline feed usage')
                    """, (dt, ft, -qty, new_st, usg_code))
                    
                    results.append({"queue_id": queue_id, "status": "synced", "message": f"Recorded {qty} kg {ft} usage"})
                    synced_count += 1
                    
                else:
                    results.append({"queue_id": queue_id, "status": "error", "message": f"Unknown record type '{rec_type}'"})
                    error_count += 1
                    
            except Exception as e:
                results.append({"queue_id": queue_id, "status": "error", "message": str(e)})
                error_count += 1
                
        log_audit("Offline Queue Synced", "Sync", "SYNC", f"Processed {len(queue)} items ({synced_count} succeeded, {error_count} failed)", user_id=g.user["user_id"], username=g.user["username"], conn=conn)
        
    return jsonify({
        "synced_count": synced_count,
        "error_count": error_count,
        "results": results
    })
