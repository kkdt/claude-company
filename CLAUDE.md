# claude-company

## Overview

This project allows the user to input a CSV file of all employees that will be stored in a non-relational, JSON format backend datastore.

## Database

The database supports JSON. 

## Employee - CSV headers

The following represent an Employee from the CSV header file.

* Header "Employee ID" maps to JSON key `employee_id`
* Header "Last Name, First Name" maps to JSON key `employee_name`
* Header "Job Profile" maps to JSON key `job_profile`
* Header "Supervisory Organization" maps to JSON key `supervisor_organization` - This is the supervisor name with their Employee ID in parenthsis at the end, example `Peter Parker (EMP00001)`
* Header "Current Hourly Rate" maps to JSON key `hourly_rate`
* Header "Current Annual Salary" maps to JSON key `annual_salary`
* Header "Location City, State" maps to JSON key `location`

All other CSV headers maps to a JSON key `attributes` that is a JSON list of tuples of key-value pairs.

## Project - CSV Headers

* Header "Project" maps to JSON key `project_id`
* Header "Description" maps to JSON key `project_description`
* Header "Color" maps to json key `project_color` - HTML color codes
* Header "Active" maps to json key `active`

All other CSV headers maps to a JSON key `attributes` that is a JSON list of tuples of key-value pairs.

## Screens

All screens require a challenge-word login to access except for the "Public" navigation screens. The Public screens are read-only data without
sensitive information such as hourly rate and salary data.

1. Upload employee CSV file (all CSV exports will be wrapped in double-quoted)

2. View all employees

3. View employee details

4. Organization

5. Projects - Manage projects

6. Staffing - Manage monthly staffing profiles for projects

    - An employee is matrixed across different projects
    - An employee can support multiple projects in a single month
    - Screens to project staffing assignments for future months while preserving past assignments in JSON format

7. Public - Public view that includes read-only to Organization, Projects, and Staffing Projections; will be hidden when the user logs with the challenge word.

## Application Deployment

The application will run on port 8080.

## Installation Instructions for Windows and Linux / Unix

@INSTALL.md