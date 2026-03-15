import csv
import json
import io
import os
import re
from flask import Flask, request, redirect, url_for, render_template, flash, Response, jsonify

app = Flask(__name__)
app.secret_key = "workforce-secret"

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "employees.json")

FIELD_MAP = {
    "Employee ID": "employee_id",
    "Last Name, First Name": "employee_name",
    "Job Profile": "job_profile",
    "Supervisory Organization": "supervisor_organization",
    "Current Hourly Rate": "hourly_rate",
    "Current Annual Salary": "annual_salary",
    "Location City, State": "location",
    "Grade Profile Minimum": "salary_min",
    "Grade Profile Midpoint": "salary_mid",
    "Grade Profile Maximum": "salary_max",
}


def load_employees():
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, "r") as f:
        return json.load(f)


def save_employees(employees):
    with open(DB_PATH, "w") as f:
        json.dump(employees, f, indent=2)


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
                   "annual_salary", "hourly_rate", "location",
                   "salary_min", "salary_mid", "salary_max"]

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
        "annual_salary", "hourly_rate", "location", "salary_min", "salary_mid", "salary_max"
    ]]
    all_headers = core_headers + attr_keys

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_headers, extrasaction="ignore")
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

    attr_keys, seen = [], set()
    for emp in export_employees:
        for attr in emp.get("attributes", []):
            if attr["key"] not in seen:
                attr_keys.append(attr["key"])
                seen.add(attr["key"])

    reverse_map = {v: k for k, v in FIELD_MAP.items()}
    core_headers = [reverse_map[f] for f in [
        "employee_id", "employee_name", "job_profile", "supervisor_organization",
        "annual_salary", "hourly_rate", "location", "salary_min", "salary_mid", "salary_max"
    ]]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=core_headers + attr_keys, extrasaction="ignore")
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


@app.route("/organization/chart")
def organization_chart():
    all_employees = load_employees()
    roots, children_map = build_org_tree(all_employees)
    emp_map = {e["employee_id"]: e for e in all_employees}
    return render_template("organization_chart.html", roots=roots, children_map=children_map, emp_map=emp_map)


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
