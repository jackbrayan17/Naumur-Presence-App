# Naumur Presence App

Naumur Presence App is a Django attendance platform with role-based access, daily
check-in/out, supervisor verification, and weekly history exports.

## Highlights
- Daily attendance submission per day row (employees can only edit today).
- Supervisor verification workflow for employees who checked in.
- Justification requests with approval workflow (pending/approved/rejected) and file uploads.
- Admin analytics by department and employee, plus weekly/monthly trend charts.
- History exports to CSV and XLSX with department tabs.
- Activity timeline per user (logins, edits, approvals).
- FR/EN language toggle, light/dark mode, and responsive UI.

## Roles and permissions
- Superuser / Admin
  - Full access to dashboards, history, exports, and verification.
  - Can deactivate/restore users and departments.
  - Only admin can assign the supervisor role (enforced in Django admin).
- Supervisor
  - Must check in to access daily verification.
  - Can verify employees present today.
  - Can create employees and departments.
  - Can add justifications and approve/reject them.
- Employee
  - Can only submit attendance for the current day.
  - Can view weekly summary and personal activity timeline.

## Attendance workflow
- Each day row has its own submit button.
- Employees can only edit the current day.
- Supervisors/admins can edit past days when needed.

## Justification workflow
- Create justification with reason, optional details, and receipt upload.
- Status: pending, approved, or rejected.
- Files are stored under `media/justifications/<employee>/<period>/`.

## Admin dashboard
- Department presence rates.
- Employee cards with modal summary.
- Department trend charts (weekly/monthly) with snapshot download.
- Soft delete / restore for users and departments.

## History
- Weekly tables with department grouping.
- Export weekly data to CSV or XLSX.
- Filters by date range, department, and search.

## Activity and session logging
- Tracks logins, logouts, edits, approvals, and verification.
- Stores session details, IP address, first/last login of day, and online status.
- Uses cached DB sessions and database-backed cache.

## Setup
1. Create a virtual environment and install dependencies:
   - `pip install -r requirements.txt`
2. Run migrations:
   - `python manage.py migrate`
3. Create cache table (required for sessions + cache):
   - `python manage.py createcachetable`
4. Start the server:
   - `python manage.py runserver`

## Seed data
- `python manage.py seed_data`
  - Creates 1 superuser, 1 admin, 2 supervisors, 20 employees, 5 departments.
  - Generates attendance data from 2026-01-01 to 2026-02-28.
- `python manage.py clear_seed_data`
  - Removes seeded users, attendance records, justifications, logs, and inactive seed departments.

## Backup
- `python manage.py backup_db`
  - Creates a timestamped SQLite backup.

## Deployment notes
- Run `python manage.py collectstatic` before deploying.
- Gunicorn and WhiteNoise are included in `requirements.txt`.
- Set `DJANGO_SECRET_KEY` and `DJANGO_DEBUG` as needed.

## Files and models
Key models:
- `User` (role, department, start_date, profile_image)
- `Department` (code, name, is_active)
- `AttendanceDay` (arrival/departure, verified_by)
- `AbsenceJustification` (status, reason, receipt)
- `UserSession`, `UserDailyLogin`, `SystemLog`, `UserActivity`

## Translations
- Update translations in `locale/` and run:
  - `python manage.py compilemessages`
