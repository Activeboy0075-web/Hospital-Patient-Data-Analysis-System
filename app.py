"""Flask API starter for Hospital Patient Data Analysis System."""
import csv
import io
import math
import os
import random
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime, timedelta
from uuid import uuid4
from flask import Flask, Response, jsonify, request, render_template
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from analytics import summarize, create_chart

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "local-dev-key-change-me")
TABLE = "visits"
PRIMARY_KEY = "visit_id"
ALLOWED_FIELDS = ['patient_code', 'department', 'visit_date', 'visit_type']
RECORD_COLUMNS = ["visit_id", "patient_code", "department", "visit_date", "visit_type"]
SORTABLE_FIELDS = set(RECORD_COLUMNS)

def db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "hospital_patient_data_analysis_system"),
    )

def json_safe(value):
    if isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, Decimal): return float(value)
    return value

def fetch_records():
    conn = db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"SELECT * FROM {TABLE} ORDER BY {PRIMARY_KEY} DESC LIMIT 1000")
        return [{k: json_safe(v) for k, v in row.items()} for row in cur.fetchall()]
    finally:
        conn.close()

def parse_record_query(args):
    search = args.get("q", "").strip()
    department = args.get("department", "").strip()
    visit_type = args.get("visit_type", "").strip()
    start_date = args.get("start_date", "").strip()
    end_date = args.get("end_date", "").strip()
    sort = args.get("sort", "visit_date")
    direction = args.get("direction", "desc").lower()

    if len(search) > 100:
        return None, "Search text must be 100 characters or fewer."
    if sort not in SORTABLE_FIELDS:
        return None, "Unsupported sort column."
    if direction not in {"asc", "desc"}:
        return None, "Sort direction must be 'asc' or 'desc'."

    try:
        page = int(args.get("page", "1"))
        per_page = int(args.get("per_page", "25"))
    except ValueError:
        return None, "Page and page size must be integers."
    if page < 1 or per_page < 1 or per_page > 100:
        return None, "Page must be positive and page size must be between 1 and 100."

    parsed_dates = {}
    for key, value in (("start_date", start_date), ("end_date", end_date)):
        if value:
            try:
                parsed_dates[key] = datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None, f"{key} must use YYYY-MM-DD format."
    if (
        parsed_dates.get("start_date")
        and parsed_dates.get("end_date")
        and parsed_dates["start_date"] > parsed_dates["end_date"]
    ):
        return None, "Start date must not be after end date."

    conditions = []
    parameters = []
    if search:
        conditions.append(
            "(patient_code LIKE %s OR department LIKE %s OR visit_type LIKE %s)"
        )
        parameters.extend([f"%{search}%"] * 3)
    if department:
        conditions.append("department = %s")
        parameters.append(department)
    if visit_type:
        conditions.append("visit_type = %s")
        parameters.append(visit_type)
    if start_date:
        conditions.append("visit_date >= %s")
        parameters.append(start_date)
    if end_date:
        conditions.append("visit_date <= %s")
        parameters.append(end_date)

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    return {
        "where_clause": where_clause,
        "parameters": parameters,
        "page": page,
        "per_page": per_page,
        "sort": sort,
        "direction": direction.upper(),
    }, None

def query_records(options, paginate=True):
    conn = db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            f"SELECT COUNT(*) AS total FROM {TABLE}{options['where_clause']}",
            tuple(options["parameters"]),
        )
        total = cur.fetchone()["total"]

        sql = (
            f"SELECT * FROM {TABLE}{options['where_clause']} "
            f"ORDER BY {options['sort']} {options['direction']}"
        )
        parameters = list(options["parameters"])
        if paginate:
            sql += " LIMIT %s OFFSET %s"
            parameters.extend([
                options["per_page"],
                (options["page"] - 1) * options["per_page"],
            ])
        cur.execute(sql, tuple(parameters))
        rows = [
            {key: json_safe(value) for key, value in row.items()}
            for row in cur.fetchall()
        ]
        return rows, total
    finally:
        conn.close()

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/health")
def health():
    try:
        conn = db_connection(); conn.close()
        return jsonify({"status": "ok", "database": "connected", "project": 'Hospital Patient Data Analysis System'})
    except Error as exc:
        return jsonify({"status": "error", "database": "unavailable", "detail": str(exc)}), 503

@app.get("/api/records")
def list_records():
    try: return jsonify(fetch_records())
    except Error as exc: return jsonify({"error": "Database query failed", "detail": str(exc)}), 503

@app.get("/api/records/search")
def search_records():
    options, error = parse_record_query(request.args)
    if error:
        return jsonify({"error": error}), 400
    try:
        rows, total = query_records(options)
        return jsonify({
            "records": rows,
            "page": options["page"],
            "per_page": options["per_page"],
            "total": total,
            "pages": math.ceil(total / options["per_page"]),
        })
    except Error as exc:
        return jsonify({"error": "Database query failed", "detail": str(exc)}), 503

@app.get("/api/records/export")
def export_records():
    options, error = parse_record_query(request.args)
    if error:
        return jsonify({"error": error}), 400
    try:
        rows, _ = query_records(options, paginate=False)
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(RECORD_COLUMNS)
        for row in rows:
            values = [row.get(column, "") for column in RECORD_COLUMNS]
            writer.writerow([
                f"'{value}" if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
                else value
                for value in values
            ])
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=visits.csv"},
        )
    except Error as exc:
        return jsonify({"error": "Could not export records", "detail": str(exc)}), 503

@app.get("/api/record-options")
def record_options():
    conn = None
    try:
        conn = db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT department FROM visits WHERE department IS NOT NULL ORDER BY department")
        departments = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT DISTINCT visit_type FROM visits WHERE visit_type IS NOT NULL ORDER BY visit_type")
        visit_types = [row[0] for row in cur.fetchall()]
        return jsonify({"departments": departments, "visit_types": visit_types})
    except Error as exc:
        return jsonify({"error": "Could not load filter options", "detail": str(exc)}), 503
    finally:
        if conn is not None:
            conn.close()

@app.route("/api/patients", methods=["GET", "POST"])
def patients():
    if request.method == "POST":
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or set(payload) != {"patient_code"}:
            return jsonify({"error": "Send a JSON object with only a patient_code field."}), 400
        patient_code = payload["patient_code"]
        if not isinstance(patient_code, str) or not patient_code.strip():
            return jsonify({"error": "Patient code is required."}), 400
        patient_code = patient_code.strip()
        if len(patient_code) > 40:
            return jsonify({"error": "Patient code must be 40 characters or fewer."}), 400

        conn = None
        try:
            conn = db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO patients (patient_code) VALUES (%s)", (patient_code,))
            conn.commit()
            return jsonify({"message": "Patient registered", "patient_code": patient_code}), 201
        except Error as exc:
            if conn is not None:
                conn.rollback()
            return jsonify({"error": "Could not register patient", "detail": str(exc)}), 400
        finally:
            if conn is not None:
                conn.close()

    conn = None
    try:
        conn = db_connection()
        cur = conn.cursor()
        cur.execute("SELECT patient_code FROM patients ORDER BY patient_code")
        return jsonify([row[0] for row in cur.fetchall()])
    except Error as exc:
        return jsonify({"error": "Could not load patients", "detail": str(exc)}), 503
    finally:
        if conn is not None:
            conn.close()

@app.post("/api/demo-data")
def create_demo_data():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) - {"patient_count"}:
        return jsonify({"error": "Send a JSON object with an optional patient_count field."}), 400
    patient_count = payload.get("patient_count", 20)
    if type(patient_count) is not int or not 1 <= patient_count <= 100:
        return jsonify({"error": "patient_count must be an integer between 1 and 100."}), 400

    departments = [
        "Cardiology", "Emergency", "General Medicine", "Neurology",
        "Orthopedics", "Pediatrics",
    ]
    visit_types = ["Consultation", "Emergency", "Follow-up", "Screening"]
    today = date.today()
    patient_codes = [f"DEMO-{uuid4().hex}" for _ in range(patient_count)]
    visits = []
    for patient_code in patient_codes:
        for _ in range(random.randint(1, 4)):
            visits.append((
                patient_code,
                random.choice(departments),
                today - timedelta(days=random.randint(0, 365)),
                random.choice(visit_types),
            ))

    conn = None
    try:
        conn = db_connection()
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO patients (patient_code) VALUES (%s)",
            [(patient_code,) for patient_code in patient_codes],
        )
        cur.executemany(
            "INSERT INTO visits (patient_code, department, visit_date, visit_type) "
            "VALUES (%s, %s, %s, %s)",
            visits,
        )
        conn.commit()
        return jsonify({
            "message": "Synthetic demo data created.",
            "patients_created": len(patient_codes),
            "visits_created": len(visits),
        }), 201
    except Error as exc:
        if conn is not None:
            conn.rollback()
        return jsonify({"error": "Could not create demo data", "detail": str(exc)}), 503
    finally:
        if conn is not None:
            conn.close()

@app.post("/api/records")
def create_record():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict): return jsonify({"error": "Send a JSON object in the request body."}), 400
    unknown = sorted(set(payload) - set(ALLOWED_FIELDS))
    if unknown: return jsonify({"error": "Unknown field(s)", "fields": unknown}), 400
    if not payload: return jsonify({"error": "At least one field is required."}), 400
    missing = [
        field for field in ("patient_code", "department", "visit_date")
        if not isinstance(payload.get(field), str) or not payload[field].strip()
    ]
    if missing:
        return jsonify({"error": "Required field(s) are missing or empty.", "fields": missing}), 400
    for field, max_length in (("patient_code", 40), ("department", 100)):
        payload[field] = payload[field].strip()
        if len(payload[field]) > max_length:
            return jsonify({"error": f"{field} must be {max_length} characters or fewer."}), 400
    try:
        datetime.strptime(payload["visit_date"], "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "visit_date must use YYYY-MM-DD format."}), 400
    if payload.get("visit_type") is not None:
        if not isinstance(payload["visit_type"], str):
            return jsonify({"error": "visit_type must be text or null."}), 400
        payload["visit_type"] = payload["visit_type"].strip() or None
        if payload["visit_type"] and len(payload["visit_type"]) > 60:
            return jsonify({"error": "visit_type must be 60 characters or fewer."}), 400
    # Basic numeric validation for values that must not be negative. Customize per project rules.
    for key, value in payload.items():
        if key in {"amount", "quantity", "unit_price", "marks_obtained", "rating", "litres", "total_cost", "production", "cultivated_area", "cumulative_kwh", "odometer_km", "package_lpa", "completion_percent", "stock_quantity", "unit_cost", "order_value", "average_rating"} and value is not None:
            try:
                if float(value) < 0: return jsonify({"error": f"{key} cannot be negative."}), 400
            except (ValueError, TypeError): return jsonify({"error": f"{key} must be numeric."}), 400
    columns = list(payload.keys())
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {TABLE} ({', '.join(columns)}) VALUES ({placeholders})"
    conn = None
    try:
        conn = db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT patient_code FROM patients WHERE patient_code = %s",
            (payload["patient_code"],),
        )
        if cur.fetchone() is None:
            return jsonify({"error": "Register the patient code before adding a visit."}), 400
        cur.execute(sql, tuple(payload[c] for c in columns))
        conn.commit()
        return jsonify({"message": "Record created", "id": cur.lastrowid}), 201
    except Error as exc:
        if conn is not None:
            conn.rollback()
        return jsonify({"error": "Could not create record", "detail": str(exc)}), 400
    finally:
        if conn is not None:
            conn.close()

@app.get("/api/analytics")
def analytics():
    conn = None
    try:
        conn = db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT COUNT(*) AS total_visits, "
            "COUNT(DISTINCT department) AS department_count, "
            "COUNT(DISTINCT patient_code) AS patient_count, "
            "COUNT(DISTINCT visit_type) AS visit_type_count FROM visits"
        )
        metrics = cur.fetchone()
        cur.execute(
            "SELECT department, COUNT(*) AS visits FROM visits "
            "GROUP BY department ORDER BY visits DESC, department"
        )
        department_counts = cur.fetchall()
        cur.execute(
            "SELECT visit_type, COUNT(*) AS visits FROM visits "
            "GROUP BY visit_type ORDER BY visits DESC, visit_type"
        )
        visit_type_counts = cur.fetchall()
        cur.execute(
            "SELECT DATE_FORMAT(visit_date, '%Y-%m') AS month, COUNT(*) AS visits "
            "FROM visits GROUP BY month ORDER BY month"
        )
        monthly_counts = cur.fetchall()
        rows = fetch_records()
        return jsonify({
            "project_focus": "Department workload and patient visit trends",
            "summary": summarize(rows),
            "metrics": {key: int(value or 0) for key, value in metrics.items()},
            "department_counts": department_counts,
            "visit_type_counts": visit_type_counts,
            "monthly_counts": monthly_counts,
        })
    except Error as exc:
        return jsonify({"error": "Analytics query failed", "detail": str(exc)}), 503
    finally:
        if conn is not None:
            conn.close()

@app.post("/api/chart")
def chart():
    try:
        rows = fetch_records()
        path = BASE_DIR / "static" / "charts" / "summary.png"
        result = create_chart(rows, str(path))
        if not result: return jsonify({"message": "No numeric data available to chart. Add records first."}), 200
        return jsonify({"message": "Chart generated", "url": "/static/charts/summary.png"})
    except Error as exc: return jsonify({"error": "Chart query failed", "detail": str(exc)}), 503

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG", "0") == "1")
