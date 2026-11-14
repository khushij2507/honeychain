from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file
import sqlite3, hashlib, json, os, csv, io
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("HONEYCHAIN_DB", str(BASE_DIR / "honeychain.db"))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS batches(
          id INTEGER PRIMARY KEY AUTOINCREMENT, batch_code TEXT UNIQUE NOT NULL,
          beekeeper TEXT NOT NULL, apiary TEXT NOT NULL, floral_source TEXT NOT NULL,
          harvest_date TEXT NOT NULL, quantity_kg REAL NOT NULL, moisture_pct REAL,
          status TEXT NOT NULL DEFAULT 'Harvested', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events(
          id INTEGER PRIMARY KEY AUTOINCREMENT, batch_code TEXT NOT NULL,
          event_type TEXT NOT NULL, actor TEXT NOT NULL, location TEXT NOT NULL,
          details TEXT NOT NULL, created_at TEXT NOT NULL, prev_hash TEXT NOT NULL,
          event_hash TEXT UNIQUE NOT NULL,
          FOREIGN KEY(batch_code) REFERENCES batches(batch_code)
        );
        CREATE TABLE IF NOT EXISTS telemetry(
          id INTEGER PRIMARY KEY AUTOINCREMENT, apiary TEXT NOT NULL,
          temperature_c REAL NOT NULL, humidity_pct REAL NOT NULL,
          hive_weight_kg REAL NOT NULL, recorded_at TEXT NOT NULL
        );
        """)
        count = con.execute("SELECT COUNT(*) n FROM batches").fetchone()["n"]
        if count == 0:
            samples = [
              ("HC-2026-001","Asha Devi","Sirmaur Cluster A","Mustard","2026-10-12",42.5,17.2,"Packed"),
              ("HC-2026-002","Ravi Kumar","Paonta Cluster B","Eucalyptus","2026-10-18",28.0,18.1,"Harvested"),
              ("HC-2026-003","Meera Singh","Nahan Cluster C","Multifloral","2026-10-22",35.0,17.6,"Quality Check")
            ]
            for code, beekeeper, apiary, floral, date, qty, moisture, status in samples:
                con.execute("""INSERT INTO batches(batch_code,beekeeper,apiary,floral_source,harvest_date,
                  quantity_kg,moisture_pct,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                  (code,beekeeper,apiary,floral,date,qty,moisture,status,now()))
                add_event(con, code, "Batch created", beekeeper, apiary,
                          {"floral_source": floral, "quantity_kg": qty, "status": status})
            for row in [
              ("Sirmaur Cluster A",32.4,68.0,18.2),
              ("Paonta Cluster B",35.1,72.0,16.7),
              ("Nahan Cluster C",30.2,64.0,21.4),
              ("Sirmaur Cluster A",33.8,70.0,18.7),
              ("Paonta Cluster B",34.5,75.0,17.1)
            ]:
                con.execute("INSERT INTO telemetry(apiary,temperature_c,humidity_pct,hive_weight_kg,recorded_at) VALUES(?,?,?,?,?)",
                            (*row, now()))

def canonical_event(batch_code, event_type, actor, location, details, created_at, prev_hash):
    payload = {"batch_code": batch_code, "event_type": event_type, "actor": actor,
               "location": location, "details": details, "created_at": created_at,
               "prev_hash": prev_hash}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def add_event(con, batch_code, event_type, actor, location, details):
    last = con.execute("SELECT event_hash FROM events ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = last["event_hash"] if last else "GENESIS"
    created_at = now()
    details_json = json.dumps(details, sort_keys=True)
    event_hash = canonical_event(batch_code, event_type, actor, location, details_json, created_at, prev_hash)
    con.execute("""INSERT INTO events(batch_code,event_type,actor,location,details,created_at,prev_hash,event_hash)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (batch_code,event_type,actor,location,details_json,created_at,prev_hash,event_hash))

def verify_chain():
    with db() as con:
        rows = con.execute("SELECT * FROM events ORDER BY id").fetchall()
    expected_prev = "GENESIS"
    for row in rows:
        if row["prev_hash"] != expected_prev:
            return False, f"Broken link at event #{row['id']}"
        recalculated = canonical_event(row["batch_code"], row["event_type"], row["actor"],
            row["location"], row["details"], row["created_at"], row["prev_hash"])
        if recalculated != row["event_hash"]:
            return False, f"Hash mismatch at event #{row['id']}"
        expected_prev = row["event_hash"]
    return True, f"{len(rows)} events verified"

def insights():
    with db() as con:
        rows = con.execute("SELECT * FROM telemetry ORDER BY id DESC LIMIT 20").fetchall()
    if not rows:
        return {"risk":"No data","message":"Add telemetry to generate a basic hive-health indicator.","avg_temp":None,"avg_humidity":None}
    temps = [r["temperature_c"] for r in rows]
    hums = [r["humidity_pct"] for r in rows]
    avg_t, avg_h = sum(temps)/len(temps), sum(hums)/len(hums)
    # Transparent baseline heuristic; replace with validated local models for deployment.
    risk = "Low"
    reasons = []
    if avg_t < 20 or avg_t > 36:
        risk = "Elevated"; reasons.append("average temperature outside the demo target range (20–36°C)")
    if avg_h > 80 or avg_h < 35:
        risk = "Elevated"; reasons.append("average humidity outside the demo target range (35–80%)")
    if not reasons: reasons.append("recent readings are inside the demo target ranges")
    return {"risk":risk,"message":"; ".join(reasons),"avg_temp":round(avg_t,1),"avg_humidity":round(avg_h,1)}

@app.route("/")
def index():
    with db() as con:
        batches = con.execute("SELECT * FROM batches ORDER BY id DESC").fetchall()
        event_count = con.execute("SELECT COUNT(*) n FROM events").fetchone()["n"]
        apiaries = con.execute("SELECT COUNT(DISTINCT apiary) n FROM telemetry").fetchone()["n"]
    valid, chain_msg = verify_chain()
    return render_template("index.html", batches=batches, event_count=event_count,
                           apiaries=apiaries, chain_valid=valid, chain_msg=chain_msg, insight=insights())

@app.route("/batch/new", methods=["POST"])
def new_batch():
    fields = {k: request.form.get(k, "").strip() for k in
              ["batch_code","beekeeper","apiary","floral_source","harvest_date","quantity_kg","moisture_pct"]}
    try:
        qty = float(fields["quantity_kg"])
        moisture = float(fields["moisture_pct"]) if fields["moisture_pct"] else None
        if qty <= 0: raise ValueError()
        if not all(fields[k] for k in ["batch_code","beekeeper","apiary","floral_source","harvest_date"]):
            raise ValueError()
    except ValueError:
        flash("Check required fields and enter a positive quantity.", "error")
        return redirect(url_for("index"))
    try:
        with db() as con:
            con.execute("""INSERT INTO batches(batch_code,beekeeper,apiary,floral_source,harvest_date,
                quantity_kg,moisture_pct,status,created_at) VALUES(?,?,?,?,?,?,?,'Harvested',?)""",
                (fields["batch_code"],fields["beekeeper"],fields["apiary"],fields["floral_source"],
                 fields["harvest_date"],qty,moisture,now()))
            add_event(con, fields["batch_code"], "Batch created", fields["beekeeper"], fields["apiary"],
                      {"quantity_kg":qty,"floral_source":fields["floral_source"]})
        flash("Batch created and traceability event recorded.", "success")
    except sqlite3.IntegrityError:
        flash("That batch code already exists. Use a unique code.", "error")
    return redirect(url_for("index"))

@app.route("/batch/<batch_code>")
def batch_detail(batch_code):
    with db() as con:
        batch = con.execute("SELECT * FROM batches WHERE batch_code=?", (batch_code,)).fetchone()
        events = con.execute("SELECT * FROM events WHERE batch_code=? ORDER BY id", (batch_code,)).fetchall()
    if not batch:
        return render_template("not_found.html", batch_code=batch_code), 404
    valid, chain_msg = verify_chain()
    return render_template("batch.html", batch=batch, events=events, chain_valid=valid, chain_msg=chain_msg)

@app.route("/batch/<batch_code>/event", methods=["POST"])
def add_batch_event(batch_code):
    event_type = request.form.get("event_type","").strip()
    actor = request.form.get("actor","").strip()
    location = request.form.get("location","").strip()
    details = request.form.get("details","").strip()
    allowed = {"Quality check","Packed","Dispatched","Retail received","Storage inspection"}
    if event_type not in allowed or not actor or not location:
        flash("Choose a valid event type and provide actor and location.", "error")
        return redirect(url_for("batch_detail", batch_code=batch_code))
    with db() as con:
        exists = con.execute("SELECT 1 FROM batches WHERE batch_code=?", (batch_code,)).fetchone()
        if not exists: return render_template("not_found.html", batch_code=batch_code), 404
        add_event(con, batch_code, event_type, actor, location, {"notes":details})
        status_map = {"Quality check":"Quality Check","Packed":"Packed","Dispatched":"In Transit",
                      "Retail received":"Retail Received","Storage inspection":"Storage Inspected"}
        con.execute("UPDATE batches SET status=? WHERE batch_code=?", (status_map[event_type],batch_code))
    flash("Traceability event added.", "success")
    return redirect(url_for("batch_detail", batch_code=batch_code))

@app.route("/verify/<batch_code>")
def verify(batch_code):
    with db() as con:
        batch = con.execute("SELECT * FROM batches WHERE batch_code=?", (batch_code,)).fetchone()
        events = con.execute("SELECT * FROM events WHERE batch_code=? ORDER BY id", (batch_code,)).fetchall()
    valid, chain_msg = verify_chain()
    return render_template("verify.html", batch=batch, events=events, chain_valid=valid, chain_msg=chain_msg)

@app.route("/batch/<batch_code>/qr.png")
def batch_qr(batch_code):
    with db() as con:
        exists = con.execute("SELECT 1 FROM batches WHERE batch_code=?", (batch_code,)).fetchone()
    if not exists:
        return render_template("not_found.html", batch_code=batch_code), 404
    try:
        import qrcode
        from io import BytesIO
        from flask import make_response
        image = qrcode.make(request.url_root.rstrip("/") + url_for("verify", batch_code=batch_code))
        output = BytesIO()
        image.save(output, format="PNG")
        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "image/png"
        response.headers["Cache-Control"] = "no-store"
        return response
    except ImportError:
        return jsonify({"error":"QR dependency missing. Install requirements.txt to enable QR generation."}), 503

@app.route("/api/telemetry", methods=["GET","POST"])
def telemetry_api():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        try:
            apiary = str(data["apiary"]).strip()
            temp, humidity, weight = float(data["temperature_c"]), float(data["humidity_pct"]), float(data["hive_weight_kg"])
            if not apiary or not (-20 <= temp <= 70) or not (0 <= humidity <= 100) or weight < 0:
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            return jsonify({"error":"Provide apiary, temperature_c (-20..70), humidity_pct (0..100), hive_weight_kg (>=0)."}), 400
        with db() as con:
            con.execute("INSERT INTO telemetry(apiary,temperature_c,humidity_pct,hive_weight_kg,recorded_at) VALUES(?,?,?,?,?)",
                        (apiary,temp,humidity,weight,now()))
        return jsonify({"ok":True,"insight":insights()}), 201
    with db() as con:
        rows = con.execute("SELECT * FROM telemetry ORDER BY id DESC LIMIT 100").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/insights")
def insights_api():
    return jsonify(insights())

@app.route("/admin/verify-chain")
def verify_chain_api():
    valid, message = verify_chain()
    return jsonify({"valid":valid,"message":message})

@app.route("/export/events.csv")
def export_events():
    with db() as con:
        rows = con.execute("SELECT * FROM events ORDER BY id").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","batch_code","event_type","actor","location","details","created_at","prev_hash","event_hash"])
    for row in rows: writer.writerow([row[k] for k in ["id","batch_code","event_type","actor","location","details","created_at","prev_hash","event_hash"]])
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv",
                     as_attachment=True, download_name="honeychain-events.csv")

@app.route("/health")
def health():
    return jsonify({"status":"ok","app":"Honey Chain MVP","time":now()})

init_db()
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("DEBUG") == "1")
