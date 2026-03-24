# additional-features

## Overview

The following are instructions history given to Claude Code to build upon the basic functionality for this application.

## Phase 3 - Convenience Features

(New Claude Session)

1. Analayze CLAUDE.md
2. Add assignment filters to Staffing Projections — Added "Has Assignments" and "No Assignments" toggle buttons to the employee filter bar, wired into applyFilters().
3. Remove the "Assignments" label — Removed the label, kept the two filter buttons; fixed a duplicate style attribute introduced in the process.
4. Add "Export to CSV" — Added button to the toolbar exporting: Employee ID, Employee Name, Supervisor Organization, Job Profile, and one column per month. Exported only visible (filtered) rows.
5. Change CSV to one row per assignment — Switched to flat format: Employee ID, Employee Name, Supervisor Organization, Job Profile, Month, Project — one row per assignment, employees with multiple projects in a onth get multiple rows.
6. Revert to months-as-headers format — Switched back to month columns; employees with no assignment get an empty cell; multiple projects in a month joined with ; in one cell.
7. Duplicate rows for multiple assignments, months as headers — Each month remains a column header; if an employee has N projects in their busiest month, they get N rows — row i shows projects[i] for each month, empty if that month has fewer than i+1 assignments.
8. Add color filter buttons to Staffing Projections — Added a Color filter bar below the Project filter bar, one button per unique color among active projects. Buttons are color-styled with auto-contrasted text and a tooltip listing project IDs. Color filter stacks with all other filters; includes a Clear button.
9. Restrict color filter to active projects only — Added active field to PROJ_META and filtered the color bar builder to skip inactive projects.

(New Claude Session)

1. Analyze CLAUDE.md — reviewed project overview, data models, screen list, and deployment config.
2. For screens with supervisory org filter, allow the filter to be multi-selection — replaced single `<select>` dropdowns with toggle pill buttons across staffing_month.html, staffing_projections.html, and public_staffing_projections.html.
3. Multi-selection filter should be a drop down with checkbox selections for supervisory org — replaced toggle pill buttons with a custom dropdown button containing checkboxes (count badge + "Clear all") across all three staffing templates. 
4. The "Supervisory Org" drop down filter is not working; does not drop down and show selections — fixed toggleOrgDropdown() bug: menu.style.display vs window.getComputedStyle(menu).display.
5. Add "Supervisory Org" multi-select drop down filter to the "Employees" page — added filter bar, org dropdown, data-org row attributes, and JS to employees.html.
6. Change "View Employees" navigation to "Employees" — updated base.html.
7. Update "Upload CSV" in navigation to "Upload" — updated base.html.
8. Add "Export" button to Public Projects screen — added Export button to public_projects.html toolbar linking to existing projects_export route.
9. Can we make the Public Projects "Export to CSV" not require login? — added projects_export to PUBLIC_ENDPOINTS in app.py.
10. Add "Export to CSV" button to Public Staffing Projections screen — created new public_staffing_export route, added to PUBLIC_ENDPOINTS, added button to public_staffing_projections.html.
11. Update Staffing Projections "Export to CSV" to export all employees in current filter, even those with no assignments — updated route to apply date range filter params and include all known employees (not just those with assignments); updated button to pass filter params. 
12. Update the Export to CSV for Public Staffing Projections format to the same as exporting from the authenticated Staffing Projections — updated route to output Employee ID, Employee Name, Supervisor Organization, Job Profile + month columns, with multiple rows per employee for multiple project assignments per month.
13. Update all "Export to CSV" to double-quote all entries — added quoting=csv.QUOTE_ALL to all four server-side csv.DictWriter/csv.writer calls; client-side JS export was already quoting all fields.

(New Claude Session) - Add install process and single-file executable build proces

1. Analyze CLAUDE.md
2. Create Linux/Unix installer — prompts for install location (default `$HOME/claude-company`) and data directory (default `$HOME/claude-company/data`)
3. Create Linux/Unix installer (repeated) — stopped by user
4. Create Windows installer — same prompts with Windows defaults (`%USERPROFILE%`\claude-company)
5. How to build a single-file executable on Linux/Unix — answered with PyInstaller instructions
6. Create build.sh — packages binary + data/ folder, creates .tar.gz
7. Update build.sh to also package using tar — automated the tar step
8. Update build.sh to check for Git tag — include tag version in folder and archive names
9. Remove the "v" from the version — strip leading v from Git tag
10. Update build.sh to clean up with --clean flag
11. How to build a single-file executable on Windows — answered with PyInstaller + PowerShell instructions
12. Create build.ps1 — Windows equivalent of build.sh with -Clean, Git tag versioning, .zip archive
13. Generate build instructions — created BUILDING.md
14. Change "All Orgs" label to "Select supervisor(s)" on the Employees page supervisory org filter

(New Claude Session) - Update install.sh / install.ps1 process

1. Analyze CLAUDE.md
2. Fix install.sh stalling at "Installation Paths" prompt — added user instruction before the first read
3. Fix install.ps1 for the same issue — added the same instruction text
4. Fix install.sh prompts not showing — echo -ne captured by `$(...)`, redirected to `>&2`
5. Confirm install.ps1 was not affected by the same issue
6. Confirm venv builds at installation directory — already correct, no change needed
7. Fix install.sh failing with "pip is not available" — removed system pip pre-flight check
8. Add CHALLENGE_WORD prompt to install.sh — hidden input, confirmation, match check, saved to .challenge_word with chmod 600, launcher reads from file
9. Update install.ps1 with the same changes — Read-Host -AsSecureString, confirmation loop, hidden file, both launchers updated
10. Show challenge word storage path in install.sh Summary
11. Update install.ps1 with the same changes as install.sh
12. Create INSTALL.md — installation instructions for both platforms
13. Make "Export to CSV" buttons consistent — added .btn-export to base.html, updated all 5 templates
14. Confirm systemd service already defaults to No — no change needed
15. Add "Import Example" button to Projects screen — new route projects_import_example in app.py, btn-secondary button in projects.html
16. Restrict projects_import_example (and projects_upload) to authenticated sessions — explicit session.get("logged_in") check added to both routes
17. Make "Import Example" buttons consistent — added .btn-example to base.html, updated projects.html to use it, removed local definition from upload.html
18. Add table of contents to INSTALL.md

(New Claude Session) - Update Organization, Render feature

1. Analyze CLAUDE.md
2. Render button shows move details — When employees are moved, the Render modal displays "previously reported to: [old supervisor]" under the moved employee in the terminal tree.
3. Add Print to Render popup — Added a Print button to the Organization Render modal; prints plain-text tree respecting current zoom level.
4. Allow Salary and Job Profile editing from Organization screen — Added inline pencil (✏) edit buttons next to Job Profile and Annual Salary on each employee card; tracks edits in a pending changes panel with undo; included in CSV export.
5. Pencil not showing up — Fixed: darkened .btn-field-edit color from `#ccc` to `#999` (was invisible on white background).
6. Reset All clears Pending Changes — Fixed: added .slice() to prevent mutation-during-iteration bugs and added explicit updatePanel() call at the end of resetAll.
7. Reset All not resetting tree nor clearing Pending Changes — Fixed: undoMove was throwing NotFoundError when origNext was itself a moved node no longer in origParent; guarded with origNext?.parentElement === origParent check.
8. Do not render pencil in terminal tree output — buildTreeData now clones the .emp-meta node and strips `<button>` elements before reading textContent.
9. Do not render Employee ID in terminal tree output — buildTreeData now reads directly from `.field-val[data-field="job_profile"]` instead of the whole .emp-meta span.
10. Format salary as currency when editing — Added formatCurrency() JS helper; salary input shows plain number; display shows formatted $X,XXX.XX after commit; undo restores original formatted display.
11. Disable salary edit when Show Salary is not active — Salary pencil buttons are hidden/disabled on page load and toggled with the Show Salary button.
12. Include edited details in Render — Render modal shows `[edited]` tag and detail lines for changed fields (e.g., Job Profile: "old" → "new").
13. Include old salary and old job profile in Render details — Edit details now show both old and new values: "old value" → "new value".
14. Zoom in/out on Render popup — Added − / 100% / + zoom controls to the Organization Render modal (50%–150%); zoom resets on open; print respects zoom level.
15. Add zoom in/out to Public Organization Render popup — Same zoom controls added to the public-facing Render modal.
16. Add Print to Public Organization Render popup — Added Print button with renderTreeText and printRender functions, zoom-aware print sizing.
27. Add a "Render" button next to each employee in the Organization screen — added a per-employee Render button that opens the existing render modal scoped to that employee's subtree. 

(New Claude Session) - Employee schema change

1. Analyze CLAUDE.md and code base — Explored the full project structure, architecture, routes, data model, and key design decisions.
2. Update Employee schema so that salary_min, salary_mid, and salary_max is not part of the core JSON attributes — Moved those three fields from the core schema into the attributes list by removing them from FIELD_MAP and all downstream references in app.py, upload.html, employee_detail.html, and CLAUDE.md.
3. Login received "Unsupported digestmod" error — Diagnosed as an itsdangerous < 2.0 compatibility issue with Python 3.9+. Pinned itsdangerous>=2.1.2 in requirements.txt.
4. Can Flask sign using a more secure hashing algorithm? — Added SHA512SessionInterface to app.py overriding Flask's default SHA-1 session cookie signing with SHA-512 via itsdangerous.
5. Update install.sh to not fail if the data directory has data — Replaced the die on non-empty directory with a warn; added logic to skip re-linking if the symlink already points to the correct target.
6. Update install.ps1 to do the same — Applied the same logic to the Windows installer: warn instead of abort on non-empty directory, skip junction creation if already pointing to the correct target.
7. Receive 404 for favicon.ico — Added /favicon.ico route serving favicon.svg, added favicon to PUBLIC_ENDPOINTS, and uncommented + updated the <link> tags in base.html. 

(New Claude Session) - Add "Color Label" to Projects schema

1. Added color_label to Project schema — PROJECT_FIELD_MAP, create/edit/export routes in app.py; schema table, create form in projects.html; detail view and edit form in project_detail.html; CLAUDE.md updated.
2. Fixed staffing projections crash when no staffing data — Guarded all_record_months[-1] index access in staffing_projections.html:235.
3. Color filter bar (JS): use color_label for button text — Added color_label to PROJ_META JSON; updated colorMap to track {pids, label} per color; button text now uses color_label if set, else falls back to the hex color value.

(New Claude Session) - Add Statistics pages

1. Analyze CLAUDE.md and source code
2. On "Staffing" screen, create a sub navigation "Statistics" with a 3rd level navigation with one being for Projects
3. Make the 3rd-level nav a different color and inline with the 2nd-level navigation
4. For "Statistics Projects", left align the "Project" column and make it sortable
5. Add a description to "Statistics Projects"
6. Add Export to CSV to "Statistics Projects"
7. Update Export to CSV button to match look and feel of other Export buttons
8. Create "Statistics Employee" screen counting project assignments per employee per month
9. On "Statistics Projects", display Project summary data in a modal
10. Fix: modal not showing
11. For "Statistics Employees" Export to CSV, include job_profile and supervisor_organization, double-quote all values
12. "Statistics Projects" Export to CSV should double-quote all values
13. "Statistics Projects" — display all projects including inactive ones for the month range filter
14. Make "Statistics Projects" handle large number of projects better (max-height, search, active filter)
15. "Statistics Projects" Export to CSV — include active and color_label, double-quote all values
16. "Statistics Projects" Export to CSV — respect "Active Only" quick filter
17. "Statistics Projects" — include all projects including inactive for the month range filter
18. On "Statistics Employees", add quick filters: employee name search and supervisory org multiselect dropdown
19. Added Statistics modal to Project Details (link, modal, /projects/<id>/statistics API route)
20. Changed modal month format to YYYY-MM
21. Fixed modal scrolling to handle large number of months (flex column, body-only scroll)
22. Answered question about Delete behavior with staffing assignments
23. Added description to Delete button (tooltip + updated confirm dialog)
24. Updated statistics API to only show months with assignments
25. Added Project ID editing with cascading staffing assignment updates
26. Added confirmation dialog when renaming a Project ID
27. Update the banner for "Project ID already in use" message to be warning
28. Update the banner for "Project ID already in use" message to be error
29. From "Statistics Projects" screen, add a column "Net Change" next to the "Project" column that is fixed and does not scroll that is net change from the start month to the end month filter client-side calculated.
30. Can we include the "net change column" to the Export to CSV?