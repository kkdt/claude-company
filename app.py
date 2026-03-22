import csv
import hashlib
import json
import io
import os
import re
import sys
from flask import Flask, request, redirect, url_for, render_template, flash, Response, jsonify, session
from flask.sessions import SecureCookieSessionInterface
from itsdangerous import URLSafeTimedSerializer

# When frozen by PyInstaller (--onefile), bundled files are extracted to a
# temporary directory pointed to by sys._MEIPASS.  At runtime the binary
# itself sits next to the data/ directory, so data paths use the executable's
# location rather than __file__ (which resolves inside the temp bundle).
_BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
_RUNTIME_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))

class SHA512SessionInterface(SecureCookieSessionInterface):
    def get_signing_serializer(self, app):
        signer_kwargs = dict(
            key_derivation=self.key_derivation,
            digest_method=hashlib.sha512,
        )
        return URLSafeTimedSerializer(
            app.secret_key,
            salt=self.salt,
            serializer=self.serializer,
            signer_kwargs=signer_kwargs,
        )


app = Flask(__name__, template_folder=os.path.join(_BUNDLE_DIR, 'templates'))
app.secret_key = "workforce-secret"
app.session_interface = SHA512SessionInterface()

CHALLENGE_WORD = os.environ.get("CHALLENGE_WORD", "")

PUBLIC_ENDPOINTS = {
    "public_projects", "public_organization", "public_staffing_projections",
    "projects_export", "public_staffing_export",
    "login", "logout", "static", "favicon",
}

@app.before_request
def require_login():
    if request.endpoint and request.endpoint not in PUBLIC_ENDPOINTS:
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))

DB_PATH       = os.path.join(_RUNTIME_DIR, "data", "employees.json")
PROJECTS_PATH = os.path.join(_RUNTIME_DIR, "data", "projects.json")
STAFFING_PATH = os.path.join(_RUNTIME_DIR, "data", "staffing.json")

PROJECT_FIELD_MAP = {
    "Project": "project_id",
    "Description": "project_description",
    "Color": "project_color",
    "Color Label": "color_label",
    "Active": "active",
}

FIELD_MAP = {
    "Employee ID": "employee_id",
    "Last Name, First Name": "employee_name",
    "Job Profile": "job_profile",
    "Supervisory Organization": "supervisor_organization",
    "Current Hourly Rate": "hourly_rate",
    "Current Annual Salary": "annual_salary",
    "Location City, State": "location",
}


def load_employees():
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, "r") as f:
        return json.load(f)


def save_employees(employees):
    with open(DB_PATH, "w") as f:
        json.dump(employees, f, indent=2)


def load_projects():
    if not os.path.exists(PROJECTS_PATH):
        return []
    with open(PROJECTS_PATH, "r") as f:
        return json.load(f)


def save_projects(projects):
    os.makedirs(os.path.dirname(PROJECTS_PATH), exist_ok=True)
    with open(PROJECTS_PATH, "w") as f:
        json.dump(projects, f, indent=2)


def load_staffing():
    if not os.path.exists(STAFFING_PATH):
        return []
    with open(STAFFING_PATH, "r") as f:
        return json.load(f)


def save_staffing(records):
    os.makedirs(os.path.dirname(STAFFING_PATH), exist_ok=True)
    with open(STAFFING_PATH, "w") as f:
        json.dump(records, f, indent=2)


def get_staffing_month(records, year, month):
    return next((r for r in records if r["year"] == year and r["month"] == month), None)


def parse_projects_csv(file_stream):
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    projects = []
    for row in reader:
        project = {}
        attributes = []
        for header, value in row.items():
            if header in PROJECT_FIELD_MAP:
                key = PROJECT_FIELD_MAP[header]
                if key == "active":
                    project[key] = value.strip().lower() in ("1", "true", "yes")
                else:
                    project[key] = value
            else:
                attributes.append({"key": header, "value": value})
        project["attributes"] = attributes
        projects.append(project)
    return projects


@app.template_filter("currency")
def currency_filter(value):
    try:
        return "${:,.2f}".format(float(str(value).replace(",", "")))
    except (ValueError, TypeError):
        return value or ""


def extract_supervisor_id(supervisor_organization):
    """Parse employee ID from supervisor_organization, e.g. 'Dept Name (E001)' -> 'E001'"""
    if not supervisor_organization:
        return None
    match = re.search(r'\(([^)]+)\)\s*$', supervisor_organization)
    return match.group(1) if match else None


def build_org_tree(employees):
    """Return (roots, children_map) where children_map[emp_id] = [direct report employees]"""
    emp_map = {e["employee_id"]: e for e in employees}
    children_map = {e["employee_id"]: [] for e in employees}
    roots = []
    for emp in employees:
        supervisor_id = extract_supervisor_id(emp.get("supervisor_organization", ""))
        if supervisor_id and supervisor_id in emp_map:
            children_map[supervisor_id].append(emp)
        else:
            roots.append(emp)
    roots.sort(key=lambda e: e.get("employee_name", ""))
    for key in children_map:
        children_map[key].sort(key=lambda e: e.get("employee_name", ""))
    return roots, children_map


def parse_csv(file_stream):
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    employees = []
    for row in reader:
        employee = {}
        attributes = []
        for header, value in row.items():
            if header in FIELD_MAP:
                employee[FIELD_MAP[header]] = value
            else:
                attributes.append({"key": header, "value": value})
        employee["attributes"] = attributes
        employees.append(employee)
    return employees


@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.svg"), 200, {"Content-Type": "image/svg+xml"}


@app.route("/", methods=["GET"])
def upload():
    return render_template("upload.html")


@app.route("/upload/example", methods=["POST"])
def import_example():
    example_path = os.path.join(os.path.dirname(__file__), "employees.csv")
    if not os.path.exists(example_path):
        flash("Example file not found.")
        return redirect(url_for("upload"))
    with open(example_path, "rb") as f:
        employees = parse_csv(f)
    save_employees(employees)
    flash(f"Successfully imported {len(employees)} employee(s) from the example file.")
    return redirect(url_for("employees"))


@app.route("/upload/preview", methods=["POST"])
def preview_upload():
    file = request.files.get("file")
    if not file or not file.filename.endswith(".csv"):
        return jsonify({"error": "Invalid file."}), 400

    new_employees = parse_csv(file)
    current_map = {e["employee_id"]: e for e in load_employees()}
    new_map = {e["employee_id"]: e for e in new_employees}

    CORE_FIELDS = ["employee_name", "job_profile", "supervisor_organization",
                   "annual_salary", "hourly_rate", "location"]

    added, removed, modified, unchanged = [], [], [], 0
    for eid, emp in new_map.items():
        if eid not in current_map:
            added.append(emp)
        else:
            old = current_map[eid]
            changes = []
            for f in CORE_FIELDS:
                if old.get(f, "") != emp.get(f, ""):
                    changes.append({"field": f, "old": old.get(f, ""), "new": emp.get(f, "")})
            old_attrs = {a["key"]: a["value"] for a in old.get("attributes", [])}
            new_attrs = {a["key"]: a["value"] for a in emp.get("attributes", [])}
            for key in sorted(set(old_attrs) | set(new_attrs)):
                if old_attrs.get(key, "") != new_attrs.get(key, ""):
                    changes.append({"field": key, "old": old_attrs.get(key, ""), "new": new_attrs.get(key, "")})
            if changes:
                modified.append({"employee_id": eid, "employee_name": emp.get("employee_name", ""), "changes": changes})
            else:
                unchanged += 1

    for eid, emp in current_map.items():
        if eid not in new_map:
            removed.append(emp)

    return jsonify({
        "total": len(new_employees),
        "rows": new_employees[:10],
        "diff": {"added": added, "removed": removed, "modified": modified, "unchanged": unchanged}
    })


@app.route("/upload", methods=["POST"])
def do_upload():
    if "file" not in request.files or request.files["file"].filename == "":
        flash("No file selected.")
        return redirect(url_for("upload"))

    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        flash("Please upload a CSV file.")
        return redirect(url_for("upload"))

    employees = parse_csv(file)
    save_employees(employees)
    flash(f"Successfully imported {len(employees)} employee(s).")
    return redirect(url_for("employees"))


@app.route("/employees")
def employees():
    all_employees = load_employees()
    return render_template("employees.html", employees=all_employees)


@app.route("/employees/export")
def export_csv():
    employees = load_employees()
    if not employees:
        flash("No employee data to export.")
        return redirect(url_for("employees"))

    # Collect all attribute keys in order of first appearance
    attr_keys = []
    seen = set()
    for emp in employees:
        for attr in emp.get("attributes", []):
            if attr["key"] not in seen:
                attr_keys.append(attr["key"])
                seen.add(attr["key"])

    reverse_map = {v: k for k, v in FIELD_MAP.items()}
    core_headers = [reverse_map[f] for f in [
        "employee_id", "employee_name", "job_profile", "supervisor_organization",
        "annual_salary", "hourly_rate", "location"
    ]]
    all_headers = core_headers + attr_keys

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_headers, extrasaction="ignore", quoting=csv.QUOTE_ALL)
    writer.writeheader()

    for emp in employees:
        row = {reverse_map[k]: emp.get(k, "") for k in FIELD_MAP.values() if k in reverse_map}
        for attr in emp.get("attributes", []):
            row[attr["key"]] = attr["value"]
        writer.writerow(row)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"}
    )


@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    results = []
    if query:
        for emp in load_employees():
            searchable = " ".join([
                emp.get("employee_id", ""),
                emp.get("employee_name", ""),
                emp.get("job_profile", ""),
                emp.get("supervisor_organization", ""),
                emp.get("location", ""),
            ]).lower()
            if query in searchable:
                results.append(emp)
    return render_template("search.html", query=request.args.get("q", ""), results=results)


@app.route("/organization")
def organization():
    all_employees = load_employees()
    roots, children_map = build_org_tree(all_employees)
    emp_map = {e["employee_id"]: e for e in all_employees}
    return render_template("organization.html", roots=roots, children_map=children_map, emp_map=emp_map)


@app.route("/organization/export", methods=["POST"])
def organization_export():
    import copy
    try:
        moves = json.loads(request.form.get("moves", "{}"))
    except Exception:
        moves = {}
    try:
        removals = set(json.loads(request.form.get("removals", "[]")))
    except Exception:
        removals = set()
    try:
        edits = json.loads(request.form.get("edits", "{}"))
    except Exception:
        edits = {}

    employees = [e for e in load_employees() if e["employee_id"] not in removals]
    emp_map = {e["employee_id"]: e for e in employees}
    export_employees = copy.deepcopy(employees)
    export_map = {e["employee_id"]: e for e in export_employees}

    for emp_id, new_sup_id in moves.items():
        if emp_id not in export_map:
            continue
        if new_sup_id and new_sup_id in emp_map:
            new_sup = emp_map[new_sup_id]
            export_map[emp_id]["supervisor_organization"] = f"{new_sup['employee_name']} ({new_sup_id})"
        else:
            export_map[emp_id]["supervisor_organization"] = ""

    for emp_id, changes in edits.items():
        if emp_id not in export_map:
            continue
        for field in ("job_profile", "annual_salary"):
            if field in changes and changes[field]:
                export_map[emp_id][field] = changes[field]

    attr_keys, seen = [], set()
    for emp in export_employees:
        for attr in emp.get("attributes", []):
            if attr["key"] not in seen:
                attr_keys.append(attr["key"])
                seen.add(attr["key"])

    reverse_map = {v: k for k, v in FIELD_MAP.items()}
    core_headers = [reverse_map[f] for f in [
        "employee_id", "employee_name", "job_profile", "supervisor_organization",
        "annual_salary", "hourly_rate", "location"
    ]]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=core_headers + attr_keys, extrasaction="ignore", quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for emp in export_employees:
        row = {reverse_map[k]: emp.get(k, "") for k in FIELD_MAP.values() if k in reverse_map}
        for attr in emp.get("attributes", []):
            row[attr["key"]] = attr["value"]
        writer.writerow(row)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=organization_export.csv"}
    )


@app.route("/employees/<employee_id>")
def employee_detail(employee_id):
    all_employees = load_employees()
    employee = next((e for e in all_employees if e.get("employee_id") == employee_id), None)
    if employee is None:
        flash(f"Employee '{employee_id}' not found.")
        return redirect(url_for("employees"))
    emp_map = {e["employee_id"]: e for e in all_employees}
    supervisor_id = extract_supervisor_id(employee.get("supervisor_organization", ""))
    supervisor = emp_map.get(supervisor_id) if supervisor_id else None
    return render_template("employee_detail.html", employee=employee, supervisor=supervisor)


@app.route("/projects")
def projects():
    all_projects = load_projects()
    return render_template("projects.html", projects=all_projects)


@app.route("/projects/upload", methods=["POST"])
def projects_upload():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    file = request.files.get("file")
    if not file or not file.filename.endswith(".csv"):
        flash("Please upload a CSV file.")
        return redirect(url_for("projects"))
    parsed = parse_projects_csv(file)
    save_projects(parsed)
    flash(f"Successfully imported {len(parsed)} project(s).")
    return redirect(url_for("projects"))


@app.route("/projects/import-example", methods=["POST"])
def projects_import_example():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    example_path = os.path.join(os.path.dirname(__file__), "projects.csv")
    if not os.path.exists(example_path):
        flash("Example file not found.")
        return redirect(url_for("projects"))
    with open(example_path, "rb") as f:
        parsed = parse_projects_csv(f)
    save_projects(parsed)
    flash(f"Successfully imported {len(parsed)} project(s) from the example file.")
    return redirect(url_for("projects"))


@app.route("/projects/create", methods=["POST"])
def projects_create():
    project_id = request.form.get("project_id", "").strip()
    project_description = request.form.get("project_description", "").strip()
    if not project_id:
        flash("Project ID is required.")
        return redirect(url_for("projects"))
    all_projects = load_projects()
    if any(p.get("project_id") == project_id for p in all_projects):
        flash(f"Project '{project_id}' already exists.")
        return redirect(url_for("projects"))
    project_color = request.form.get("project_color", "").strip()
    color_label = request.form.get("color_label", "").strip()
    active = True
    keys = request.form.getlist("attr_key")
    values = request.form.getlist("attr_value")
    attributes = [{"key": k.strip(), "value": v.strip()} for k, v in zip(keys, values) if k.strip()]
    project = {"project_id": project_id, "project_description": project_description, "project_color": project_color, "color_label": color_label, "active": active, "attributes": attributes}
    all_projects.append(project)
    save_projects(all_projects)
    flash(f"Project '{project_id}' created.")
    return redirect(url_for("projects"))


@app.route("/projects/export")
def projects_export():
    all_projects = load_projects()
    if not all_projects:
        flash("No projects to export.")
        return redirect(url_for("projects"))

    reverse_map = {v: k for k, v in PROJECT_FIELD_MAP.items()}
    core_headers = [reverse_map[f] for f in ["project_id", "project_description", "project_color", "color_label", "active"]]

    attr_keys, seen = [], set()
    for p in all_projects:
        for attr in p.get("attributes", []):
            if attr["key"] not in seen:
                attr_keys.append(attr["key"])
                seen.add(attr["key"])

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=core_headers + attr_keys, extrasaction="ignore", quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for p in all_projects:
        row = {
            reverse_map["project_id"]: p.get("project_id", ""),
            reverse_map["project_description"]: p.get("project_description", ""),
            reverse_map["project_color"]: p.get("project_color", ""),
            reverse_map["color_label"]: p.get("color_label", ""),
            reverse_map["active"]: "true" if p.get("active") else "false",
        }
        for attr in p.get("attributes", []):
            row[attr["key"]] = attr["value"]
        writer.writerow(row)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=projects.csv"}
    )


@app.route("/projects/<project_id>")
def projects_detail(project_id):
    project = next((p for p in load_projects() if p.get("project_id") == project_id), None)
    if project is None:
        flash(f"Project '{project_id}' not found.")
        return redirect(url_for("projects"))
    return render_template("project_detail.html", project=project)


@app.route("/projects/<project_id>/edit", methods=["POST"])
def projects_edit(project_id):
    all_projects = load_projects()
    project = next((p for p in all_projects if p.get("project_id") == project_id), None)
    if project is None:
        flash(f"Project '{project_id}' not found.")
        return redirect(url_for("projects"))
    project["project_description"] = request.form.get("project_description", "").strip()
    project["project_color"] = request.form.get("project_color", "").strip()
    project["color_label"] = request.form.get("color_label", "").strip()
    project["active"] = "1" in request.form.getlist("active")
    keys = request.form.getlist("attr_key")
    values = request.form.getlist("attr_value")
    project["attributes"] = [{"key": k.strip(), "value": v.strip()} for k, v in zip(keys, values) if k.strip()]
    save_projects(all_projects)
    flash(f"Project '{project_id}' updated.")
    return redirect(url_for("projects_detail", project_id=project_id))


@app.route("/projects/<project_id>/delete", methods=["POST"])
def projects_delete(project_id):
    all_projects = [p for p in load_projects() if p.get("project_id") != project_id]
    save_projects(all_projects)
    records = load_staffing()
    for record in records:
        record["assignments"] = [a for a in record["assignments"] if a.get("project_id") != project_id]
    save_staffing(records)
    flash(f"Project '{project_id}' deleted and removed from all staffing entries.")
    return redirect(url_for("projects"))


@app.route("/public/projects")
def public_projects():
    if session.get("logged_in"):
        return redirect(url_for("projects"))
    all_projects = load_projects()
    return render_template("public_projects.html", projects=all_projects)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("upload"))
    if request.method == "POST":
        word = request.form.get("challenge_word", "").strip()
        if CHALLENGE_WORD and word == CHALLENGE_WORD:
            session["logged_in"] = True
            next_url = request.form.get("next") or url_for("upload")
            return redirect(next_url)
        flash("Incorrect challenge word.")
    return render_template("login.html", next=request.args.get("next", ""))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("public_organization"))


@app.route("/public/staffing-projections")
def public_staffing_projections():
    if session.get("logged_in"):
        return redirect(url_for("staffing_projections"))
    from datetime import date
    today = date.today()
    records = load_staffing()
    employees = load_employees()
    all_projects = load_projects()
    proj_map = {p["project_id"]: p for p in all_projects}
    active_proj_ids = {p["project_id"] for p in all_projects if p.get("active", True)}

    all_record_months = sorted({(r["year"], r["month"]) for r in records})
    if today.month == 12:
        default_to_year, default_to_month = today.year + 1, 1
    else:
        default_to_year, default_to_month = today.year, today.month + 1
    try:
        from_year = int(request.args.get("from_year", today.year))
        from_month = int(request.args.get("from_month", today.month))
        to_year = int(request.args.get("to_year", default_to_year))
        to_month = int(request.args.get("to_month", default_to_month))
    except (ValueError, TypeError):
        from_year, from_month = today.year, today.month
        to_year, to_month = default_to_year, default_to_month

    filtered = sorted(
        [r for r in records if (from_year, from_month) <= (r["year"], r["month"]) <= (to_year, to_month)],
        key=lambda r: (r["year"], r["month"])
    )

    month_assignments = {}
    for r in filtered:
        key = (r["year"], r["month"])
        emp_proj = {}
        for a in r["assignments"]:
            if a["project_id"] in active_proj_ids:
                emp_proj.setdefault(a["employee_id"], []).append(a["project_id"])
        month_assignments[key] = emp_proj

    months = [(r["year"], r["month"]) for r in filtered]
    all_record_months = sorted({(r["year"], r["month"]) for r in records})

    known_ids = {e["employee_id"] for e in employees}
    ghost_ids = set()
    for emp_proj in month_assignments.values():
        for eid in emp_proj:
            if eid not in known_ids:
                ghost_ids.add(eid)
    ghost_employees = [{"employee_id": eid, "employee_name": eid,
                        "job_profile": "", "supervisor_organization": "", "location": "",
                        "_missing": True}
                       for eid in sorted(ghost_ids)]
    employees_all = employees + ghost_employees

    return render_template(
        "public_staffing_projections.html",
        months=months,
        employees=employees_all,
        proj_map=proj_map,
        month_assignments=month_assignments,
        today_year=today.year,
        today_month=today.month,
        from_year=from_year,
        from_month=from_month,
        to_year=to_year,
        to_month=to_month,
        all_record_months=all_record_months,
    )


@app.route("/public/staffing-projections/export")
def public_staffing_export():
    from datetime import date
    today = date.today()
    records = load_staffing()
    employees = load_employees()
    all_projects = load_projects()
    active_proj_ids = {p["project_id"] for p in all_projects if p.get("active", True)}

    if today.month == 12:
        default_to_year, default_to_month = today.year + 1, 1
    else:
        default_to_year, default_to_month = today.year, today.month + 1
    try:
        from_year = int(request.args.get("from_year", today.year))
        from_month = int(request.args.get("from_month", today.month))
        to_year = int(request.args.get("to_year", default_to_year))
        to_month = int(request.args.get("to_month", default_to_month))
    except (ValueError, TypeError):
        from_year, from_month = today.year, today.month
        to_year, to_month = default_to_year, default_to_month

    filtered = sorted(
        [r for r in records if (from_year, from_month) <= (r["year"], r["month"]) <= (to_year, to_month)],
        key=lambda r: (r["year"], r["month"])
    )

    months = [(r["year"], r["month"]) for r in filtered]
    month_labels = [f"{yr}-{mo:02d}" for yr, mo in months]

    emp_map = {e["employee_id"]: e for e in employees}

    month_assignments = {}
    for r in filtered:
        key = (r["year"], r["month"])
        for a in r["assignments"]:
            if a["project_id"] in active_proj_ids:
                month_assignments.setdefault(key, {}).setdefault(a["employee_id"], []).append(a["project_id"])

    known_ids = {e["employee_id"] for e in employees}
    ghost_ids = {eid for ma in month_assignments.values() for eid in ma if eid not in known_ids}
    all_eids = sorted(known_ids | ghost_ids)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["Employee ID", "Employee Name", "Supervisor Organization", "Job Profile"] + month_labels)
    for eid in all_eids:
        emp = emp_map.get(eid, {})
        name = emp.get("employee_name", "")
        supervisor = emp.get("supervisor_organization", "")
        job_profile = emp.get("job_profile", "")
        month_projs = [sorted(month_assignments.get(key, {}).get(eid, [])) for key in months]
        max_slots = max((len(p) for p in month_projs), default=1)
        for i in range(max(max_slots, 1)):
            row = [eid, name, supervisor, job_profile]
            for projs in month_projs:
                row.append(projs[i] if i < len(projs) else "")
            writer.writerow(row)

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=staffing_projections.csv"},
    )


@app.route("/public/organization")
def public_organization():
    if session.get("logged_in"):
        return redirect(url_for("organization"))
    all_employees = load_employees()
    # Strip compensation fields before exposing publicly
    SALARY_FIELDS = ("annual_salary", "hourly_rate")
    public_employees = [
        {k: v for k, v in emp.items() if k not in SALARY_FIELDS}
        for emp in all_employees
    ]
    roots, children_map = build_org_tree(public_employees)
    emp_map = {e["employee_id"]: e for e in public_employees}
    return render_template("public_organization.html", roots=roots, children_map=children_map, emp_map=emp_map)


@app.route("/staffing")
def staffing():
    from datetime import date
    records = load_staffing()
    today = date.today()
    # Build a sorted list of (year, month) that exist, plus current month if missing
    existing = {(r["year"], r["month"]) for r in records}
    if (today.year, today.month) not in existing:
        existing.add((today.year, today.month))
    months = sorted(existing, reverse=True)
    return render_template("staffing.html", months=months, today_year=today.year, today_month=today.month)


@app.route("/staffing/projections")
def staffing_projections():
    from datetime import date
    today = date.today()
    records = load_staffing()
    employees = load_employees()
    all_projects = load_projects()
    proj_map = {p["project_id"]: p for p in all_projects}
    active_proj_ids = {p["project_id"] for p in all_projects if p.get("active", True)}

    # Determine from/to month range filter (default: current month to next month)
    all_record_months = sorted({(r["year"], r["month"]) for r in records})
    if today.month == 12:
        default_to_year, default_to_month = today.year + 1, 1
    else:
        default_to_year, default_to_month = today.year, today.month + 1
    try:
        from_year = int(request.args.get("from_year", today.year))
        from_month = int(request.args.get("from_month", today.month))
        to_year = int(request.args.get("to_year", default_to_year))
        to_month = int(request.args.get("to_month", default_to_month))
    except (ValueError, TypeError):
        from_year, from_month = today.year, today.month
        to_year, to_month = default_to_year, default_to_month

    filtered = sorted(
        [r for r in records if (from_year, from_month) <= (r["year"], r["month"]) <= (to_year, to_month)],
        key=lambda r: (r["year"], r["month"])
    )

    month_assignments = {}
    stored_names = {}
    for r in filtered:
        key = (r["year"], r["month"])
        emp_proj = {}
        for a in r["assignments"]:
            if "employee_name" in a:
                stored_names[a["employee_id"]] = a["employee_name"]
            if a["project_id"] in active_proj_ids:
                emp_proj.setdefault(a["employee_id"], []).append(a["project_id"])
        month_assignments[key] = emp_proj

    months = [(r["year"], r["month"]) for r in filtered]
    all_record_months = sorted({(r["year"], r["month"]) for r in records})

    # Add ghost rows for assigned employee_ids not found in the employee list
    known_ids = {e["employee_id"] for e in employees}
    ghost_ids = set()
    for emp_proj in month_assignments.values():
        for eid in emp_proj:
            if eid not in known_ids:
                ghost_ids.add(eid)
    ghost_employees = [{"employee_id": eid, "employee_name": stored_names.get(eid, eid),
                        "job_profile": "", "supervisor_organization": "", "location": "",
                        "_missing": True}
                       for eid in sorted(ghost_ids)]
    employees_all = employees + ghost_employees

    return render_template(
        "staffing_projections.html",
        months=months,
        employees=employees_all,
        proj_map=proj_map,
        month_assignments=month_assignments,
        today_year=today.year,
        today_month=today.month,
        from_year=from_year,
        from_month=from_month,
        to_year=to_year,
        to_month=to_month,
        all_record_months=all_record_months,
    )


@app.route("/staffing/<int:year>/<int:month>")
def staffing_month(year, month):
    from datetime import date
    today = date.today()
    is_past = (year, month) < (today.year, today.month)
    records = load_staffing()
    record = get_staffing_month(records, year, month)
    assignments = record["assignments"] if record else []
    employees = load_employees()
    projects = sorted([p for p in load_projects() if p.get("active", True)], key=lambda p: p.get("project_id", ""))
    emp_map = {e["employee_id"]: e for e in employees}
    proj_map = {p["project_id"]: p for p in projects}
    # Build per-employee assignment lookup: {employee_id: [project_id, ...]}
    # Also capture stored employee_name from assignments for ghost resolution
    emp_assignments = {}
    stored_names = {}
    for a in assignments:
        emp_assignments.setdefault(a["employee_id"], []).append(a["project_id"])
        if "employee_name" in a:
            stored_names[a["employee_id"]] = a["employee_name"]
    # Add ghost rows for assigned employee_ids not found in the employee list
    ghost_employees = []
    for eid in emp_assignments:
        if eid not in emp_map:
            name = stored_names.get(eid, eid)
            ghost = {"employee_id": eid, "employee_name": name, "job_profile": "",
                     "supervisor_organization": "", "_missing": True}
            ghost_employees.append(ghost)
            emp_map[eid] = ghost
    employees_all = employees + sorted(ghost_employees, key=lambda e: e["employee_id"])
    return render_template(
        "staffing_month.html",
        year=year, month=month,
        is_past=is_past,
        employees=employees_all,
        projects=projects,
        emp_map=emp_map,
        proj_map=proj_map,
        emp_assignments=emp_assignments,
        today_year=today.year,
        today_month=today.month,
    )


@app.route("/staffing/<int:year>/<int:month>/save", methods=["POST"])
def staffing_month_save(year, month):
    from datetime import date
    today = date.today()
    # Form sends: assign_<employee_id> = [project_id, ...]  (checkboxes)
    employees = load_employees()
    assignments = []
    for emp in employees:
        eid = emp["employee_id"]
        project_ids = request.form.getlist(f"assign_{eid}")
        for pid in project_ids:
            assignments.append({"employee_id": eid, "employee_name": emp.get("employee_name", eid), "project_id": pid})
    records = load_staffing()
    existing = get_staffing_month(records, year, month)
    if existing:
        existing["assignments"] = assignments
    else:
        records.append({"year": year, "month": month, "assignments": assignments})
    save_staffing(records)
    flash("Staffing saved.")
    return redirect(url_for("staffing_month", year=year, month=month))


@app.route("/staffing/<int:year>/<int:month>/copy", methods=["POST"])
def staffing_month_copy(year, month):
    import calendar
    records = load_staffing()
    source = get_staffing_month(records, year, month)
    assignments = source["assignments"] if source else []
    # Advance one month
    if month == 12:
        t_year, t_month = year + 1, 1
    else:
        t_year, t_month = year, month + 1
    existing = get_staffing_month(records, t_year, t_month)
    if existing:
        existing["assignments"] = list(assignments)
    else:
        records.append({"year": t_year, "month": t_month, "assignments": list(assignments)})
    save_staffing(records)
    flash(f"Copied to {calendar.month_name[t_month]} {t_year}.")
    return redirect(url_for("staffing_month", year=t_year, month=t_month))


@app.route("/staffing/new", methods=["POST"])
def staffing_new_month():
    try:
        year = int(request.form["year"])
        month = int(request.form["month"])
    except (KeyError, ValueError):
        flash("Invalid month.")
        return redirect(url_for("staffing"))
    return redirect(url_for("staffing_month", year=year, month=month))


@app.route("/staffing/<int:year>/<int:month>/delete", methods=["POST"])
def staffing_month_delete(year, month):
    records = load_staffing()
    records = [r for r in records if not (r["year"] == year and r["month"] == month)]
    save_staffing(records)
    flash(f"Deleted staffing month {year}-{month:02d}.")
    return redirect(url_for("staffing"))


@app.route("/staffing/remove-ghost/<employee_id>", methods=["POST"])
def staffing_remove_ghost(employee_id):
    records = load_staffing()
    emp_map = {e["employee_id"]: e for e in load_employees()}
    if employee_id in emp_map:
        flash("Employee exists in the system; cannot remove via this action.")
        return redirect(url_for("staffing"))
    for record in records:
        record["assignments"] = [
            a for a in record["assignments"] if a["employee_id"] != employee_id
        ]
    save_staffing(records)
    flash(f"Removed all assignments for unknown employee '{employee_id}'.")
    next_url = request.form.get("next") or url_for("staffing")
    return redirect(next_url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
