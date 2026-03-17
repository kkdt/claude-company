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
* Header "Supervisory Organization" maps to JSON key `supervisor_organization` - This is the supervisor name with their Employee ID in parenthsis at the end
* Header "Current Hourly Rate" maps to JSON key `hourly_rate`
* Header "Current Annual Salary" maps to JSON key `annual_salary`
* Header "Location City, State" maps to JSON key `location`
* Header "Grade Profile Minimum" maps to JSON key `salary_min`
* Header "Grade Profile Midpoint" maps to JSON key `salary_mid`
* Header "Grade Profile Maximum" maps to JSON key `salary_max`

All other CSV headers maps to a JSON key `attributes` that is a JSON list of tuples of key-value pairs.

## Screens

1. Upload employee CSV file

2. View all employees

3. View employee details

4. Organization

## Application Deployment

The application will run on port 8080.