# Rostering App (Flask)



1) Install dependencies
pip install -r requirements.txt

2) Initialize DB
flask init db

3) Seed DB
flask init seed

4) Run the app
flask run


Assumes you ran `flask init` and want to try common flows. All demo passwords are `pass`.

1) Login as admin and assign a shift

flask auth login admin@example.com pass
flask roster assign staff1@example.com 2025-10-01T09:00 2025-10-01T17:00
flask init seed
flask auth logout


2) Staff clocks in/out

flask auth login staff1@example.com pass
flask roster clock-in staff1@example.com 1
flask roster clock-out staff1@example.com 1
flask auth logout


3) Leave request + approval

flask auth login staff1@example.com pass
flask leave create staff1@example.com 2025-10-03 2025-10-03 annual --reason "Personal"
flask auth logout

flask auth login supervisor@example.com pass
flask leave decide 1 supervisor@example.com approved
flask auth logout


4) Swap a shift

flask auth login staff1@example.com pass
flask swap request staff1@example.com 1 staff2@example.com --note "Need swap"
flask auth logout

flask auth login supervisor@example.com pass
flask swap decide 1 supervisor@example.com approved
flask auth logout


5) Run payroll

flask auth login hr@example.com pass
flask payroll run 2025-10-01 2025-10-01 admin@example.com
flask auth logout


## Running tests


pytest




## Troubleshooting

- If initializing:
   Use:

    flask init db
    flask init seed
    
- If schema changed and you need a clean slate:
  - Use:
    
    flask init db --drop
    flask init seed
    
