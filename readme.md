# Rostering App

A Flask-based rostering, attendance, leave, swap, and notification demo. All operations are available via the Flask CLI.

## Quick Start

1. **Install dependencies**
   pip install -r requirements.txt

2. **Initialize the database and seed demo data**
   flask init db
   flask init seed

3. **Run the web server**
   flask run

## CLI Commands & Examples

### 1. Auth Commands

- **Login**
  flask auth login admin@example.com pass
- **Logout**
  flask auth logout

### 2. User Management

- **Create a staff user**
  flask user create-staff "Alice Smith" alice@example.com

### 3. Roster & Attendance

- **Assign a shift**
  flask roster assign staff1@example.com 2025-10-01T09:00 2025-10-01T17:00
- **View all shifts**
  flask roster view
- **Clock in for a shift**
  flask roster clock-in staff1@example.com 1
- **Clock out for a shift**
  flask roster clock-out staff1@example.com 1
- **Weekly report (admin/supervisor)**
  flask roster report-week 2025-10-01

### 4. Leave Requests

- **Create a leave request**
  flask leave create staff1@example.com 2025-10-03 2025-10-03 annual --reason "Personal"
- **Approve or reject a leave request**
  flask leave decide 1 supervisor@example.com approved
- **List leave requests**
  flask leave list
  example:
  flask leave list --status pending
  flask leave list --email staff1@example.com

### 5. Shift Swaps

- **Request a shift swap**
  flask swap request staff1@example.com 1 staff2@example.com --note "Need swap"
- **Approve or reject a swap**
  flask swap decide 1 supervisor@example.com approved
- **List swap requests**
  flask swap list
  example:
  flask swap list --status pending
  flask swap list --email staff1@example.com

### 6. Notifications

- **Send a notification**
  
  flask notify send staff1@example.com "Your shift has changed"
  

## Demo Workflow

1. **Assign a shift as admin**
   flask auth login admin@example.com pass
   flask roster assign staff1@example.com 2025-10-01T09:00 2025-10-01T17:00
   flask auth logout

2. **Staff clocks in/out at start/end of shift**
   flask auth login staff1@example.com pass
   flask roster clock-in staff1@example.com 1
   flask roster clock-out staff1@example.com 1
   flask auth logout

3. **Leave request and approval**
   flask auth login staff1@example.com pass
   flask leave create staff1@example.com 2025-10-03 2025-10-03 annual --reason "Personal"
   flask auth logout

   flask auth login supervisor@example.com pass
   flask leave decide 1 supervisor@example.com approved
   flask auth logout

4. **Swap a shift**
   flask auth login staff1@example.com pass
   flask swap request staff1@example.com 1 staff2@example.com --note "Need swap"
   flask auth logout

   flask auth login supervisor@example.com pass
   flask swap decide 1 supervisor@example.com approved
   flask auth logout

5. **Weekly report**
   flask auth login admin@example.com pass
   flask roster report-week 2025-10-01
   flask auth logout

## Testing

Run all tests:
pytest

## Notes

- Default demo users: admin@example.com, supervisor@example.com, hr@example.com, staff1@example.com, staff2@example.com, staff3@example.com (password: `pass`)
- All commands are idempotent and safe to re-run.
- For more help, use `flask <group> --help` (e.g., `flask roster --help`).