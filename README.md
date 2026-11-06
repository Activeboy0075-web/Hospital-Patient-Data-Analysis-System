# Hospital Patient Data Analysis System

**Level:** Intermediate

## Objective
Department workload and patient visit trends. This project follows the supplied project specification and uses Flask, MySQL, Pandas, NumPy and Matplotlib.

## Main features in this starter
- Flask health endpoint and REST-style record endpoints.
- Dashboard search, department/visit-type/date filters, sortable and paginated records, and CSV export.
- Patient-code registration and visit creation from the dashboard.
- Dashboard generation of synthetic patient codes and randomized visit history.
- Visit totals and department, visit-type, and monthly trend analytics.
- MySQL persistence using parameterized SQL.
- Input type/basic non-negative validation and JSON error responses.
- Pandas/NumPy descriptive analytics and a chart endpoint.
- A visits table plus a patient-code registry; departments and visit types are stored with visits.

## Folder structure
```text
07_hospital_patient_data_analysis_system/
├── app.py
├── analytics.py
├── schema.sql
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── static/charts/  (generated at runtime)
```

## Setup (Windows + VS Code)
1. Install Python 3.11+ and MySQL Server. Open this folder in VS Code.
2. Create environment: `py -m venv .venv`
3. Activate PowerShell environment: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` then ` .\.venv\Scripts\Activate.ps1`
4. Install: `python -m pip install -r requirements.txt`
5. Open MySQL Workbench and run `schema.sql`. The script creates the patient-code registry and imports existing visit patient codes. The database name is `hospital_patient_data_analysis_system`.
6. Copy `.env.example` to `.env`. Set `DB_USER`, `DB_PASSWORD`, and `DB_NAME` to your local MySQL settings.
7. Run `python app.py`. Test `http://127.0.0.1:5000/api/health`.

## API quick test
- `GET /` — project info
- `GET /api/health` — database connection check
- `GET /api/records` — latest records
- `GET /api/records/search` — paginated records; supports `q`, `department`, `visit_type`, `start_date`, `end_date`, `sort`, `direction`, `page`, and `per_page`
- `GET /api/records/export` — CSV export using the same search and filter parameters
- `POST /api/records` — create a record with JSON body using fields from `schema.sql`
- `GET /api/record-options` — available departments and visit types for filters
- `GET /api/patients` / `POST /api/patients` — list or register a patient code
- `POST /api/demo-data` — create synthetic patient codes and randomized visits; optional JSON body: `{"patient_count": 20}` (1–100)
- `GET /api/analytics` — visit totals plus department, visit-type, and monthly aggregations
- `POST /api/chart` — create a chart; then open `/static/charts/summary.png`

Example `POST /api/records` body:
```json
{
  "patient_code": "P-1001",
  "department": "Cardiology",
  "visit_date": "2026-11-04",
  "visit_type": "Consultation"
}
```
Register the patient code with `POST /api/patients` before adding a visit.

## Extend to match full specification
The patient registry intentionally stores patient codes only; it does not collect personal or clinical details. A separate departments table and relational foreign keys may still be needed if required by the supplied specification. Add tests for normal, invalid, empty and boundary inputs, and project-specific formulas beyond generic descriptive statistics.

## Safety and limitations
Use fictional or approved data. For healthcare/banking/fraud projects, use synthetic/de-identified data only; risk flags are educational indicators, not diagnoses or confirmed fraud. Forecasting/clustering are optional extensions and should be evaluated against simple baselines. Never commit `.env` or secrets.
