import click, sys, json, os
from flask.cli import AppGroup, with_appcontext
from App import create_app
from App.database import db
from App.models.core import User, Shift, TimeLog, PayRate
from App.controllers import admin_controller as admin
from App.controllers import staff_controller as staff
from App.controllers import leave_controller as leave
from App.controllers import swap_controller as swap
from App.controllers import notify_controller as notify
from App.controllers import payroll_controller as payroll
from functools import wraps

app = create_app()

# -------- tiny demo login stored in .session.json (optional polish) --------
SESSION_FILE = ".session.json"
def _session_get(): 
    if not os.path.exists(SESSION_FILE): return None
    try: return json.load(open(SESSION_FILE)).get("email")
    except Exception: return None
def _session_set(email): open(SESSION_FILE, "w").write(json.dumps({"email": email}))
def _session_clear(): 
    if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
def _current_user(): 
    email = _session_get()
    return User.query.filter_by(email=email).first() if email else None
def require_roles(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = _current_user()
            if not u:
                raise click.ClickException("Not logged in. Use: flask auth login <email> <password>")
            if roles and u.role not in roles:
                raise click.ClickException(f"Forbidden (need one of {roles}, you are {u.role})")
            return fn(*args, **kwargs)
        return wrapper
    return deco

# -------------------- CLI Groups (template style) --------------------
init = AppGroup('init', help='DB init & seed')
user_cli = AppGroup('user', help='User/staff admin')
roster_cli = AppGroup('roster', help='Roster & attendance')
leave_cli = AppGroup('leave', help='Leave requests')
swap_cli = AppGroup('swap', help='Shift swaps')
notify_cli = AppGroup('notify', help='Notifications')
payroll_cli = AppGroup('payroll', help='Payroll')

auth_cli = AppGroup('auth', help='Demo login')

@auth_cli.command('login')
@click.argument('email')
@click.argument('password')
@with_appcontext
def login(email, password):
    u = User.query.filter_by(email=email).first()
    if not u or not u.check_password(password):
        raise click.ClickException("Invalid credentials")
    _session_set(email)
    click.echo(f"Logged in as {email} ({u.role})")

@auth_cli.command('logout')
@with_appcontext
def logout():
    _session_clear()
    click.echo("Logged out")

app.cli.add_command(auth_cli)

@init.command('db')
@click.option('--drop', is_flag=True, help='Drop then recreate')
@with_appcontext
def init_db(drop):
    if drop:
        db.drop_all()
    db.create_all()
    click.echo("DB ready.")

@init.command('seed')
@with_appcontext
def seed():
    # users
    def ensure(name,email,role):
        if not User.query.filter_by(email=email).first():
            u = User(name=name,email=email,role=role)
            u.set_password("pass")
            db.session.add(u)
    ensure('Admin','admin@example.com','admin')
    ensure('Supervisor','supervisor@example.com','supervisor')
    ensure('HR Clerk','hr@example.com','hr')
    for i in range(1,4):
        ensure(f'Staff {i}', f'staff{i}@example.com', 'staff')
    db.session.commit()
    # pay rates for staff
    for u in User.query.filter_by(role='staff').all():
        if not PayRate.query.filter_by(user_id=u.id).first():
            db.session.add(PayRate(user_id=u.id, hourly_rate=20.00))
    db.session.commit()
    click.echo("Seeded users (password = 'pass') and pay rates.")

app.cli.add_command(init)

@user_cli.command('create-staff')
@click.argument('name')
@click.argument('email')
@require_roles('admin')
@with_appcontext
def create_staff(name, email):
    s = admin.create_staff(name, email)
    s.set_password("pass")
    db.session.commit()
    click.echo(f"Created staff: {s.email}")

app.cli.add_command(user_cli)

@roster_cli.command('assign')
@click.argument('email')
@click.argument('start_iso')
@click.argument('end_iso')
@require_roles('admin','supervisor')
@with_appcontext
def assign(email, start_iso, end_iso):
    sh = admin.assign_shift(email, start_iso, end_iso)
    click.echo(f"Shift #{sh.id} for {email} {start_iso}→{end_iso}")

@roster_cli.command('view')
@with_appcontext
def view():
    for sh in staff.view_roster():
        click.echo(f"#{sh.id} {sh.user.email} {sh.start_time} → {sh.end_time} [{sh.status}]")

@roster_cli.command('clock-in')
@click.argument('email')
@click.argument('shift_id', type=int)
@require_roles('staff')
@with_appcontext
def clock_in(email, shift_id):
    tl = staff.clock_in(email, shift_id)
    click.echo(f"Clock-in #{tl.id} at {tl.clock_in}")

@roster_cli.command('clock-out')
@click.argument('email')
@click.argument('timelog_id', type=int)
@require_roles('staff')
@with_appcontext
def clock_out(email, timelog_id):
    tl = staff.clock_out(email, timelog_id)
    click.echo(f"Clock-out #{tl.id} at {tl.clock_out}")

app.cli.add_command(roster_cli)

@leave_cli.command('create')
@require_roles('staff')
@click.argument('requester_email')
@click.argument('start_date')
@click.argument('end_date')
@click.argument('leave_type')
@click.option('--reason', default='')
@with_appcontext
def leave_create(requester_email, start_date, end_date, leave_type, reason):
    lr = leave.create_leave(requester_email, start_date, end_date, leave_type, reason)
    click.echo(f"Leave #{lr.id} [{lr.status}] {start_date}→{end_date}")

@leave_cli.command('decide')
@require_roles('admin','supervisor')
@click.argument('leave_id', type=int)
@click.argument('approver_email')
@click.argument('decision')
@with_appcontext
def leave_decide(leave_id, approver_email, decision):
    lr = leave.decide_leave(leave_id, approver_email, decision)
    click.echo(f"Leave #{lr.id} now {lr.status}")

app.cli.add_command(leave_cli)

@swap_cli.command('request')
@require_roles('staff')
@click.argument('from_email')
@click.argument('shift_id', type=int)
@click.argument('to_email')
@click.option('--note', default='')
@with_appcontext
def swap_request(from_email, shift_id, to_email, note):
    sr = swap.request_swap(from_email, shift_id, to_email, note)
    click.echo(f"Swap #{sr.id} from {from_email} -> {to_email} for shift #{shift_id}")

@swap_cli.command('decide')
@require_roles('admin','supervisor')
@click.argument('swap_id', type=int)
@click.argument('approver_email')
@click.argument('decision')
@with_appcontext
def swap_decide(swap_id, approver_email, decision):
    sr = swap.approve_swap(swap_id, approver_email, decision)
    click.echo(f"Swap #{sr.id} now {sr.status}")

app.cli.add_command(swap_cli)

@notify_cli.command('send')
@require_roles('admin','supervisor','hr')
@click.argument('recipient_email')
@click.argument('message')
@click.option('--channel', default='inapp')
@click.option('--etype', default=None)
@click.option('--eid', default=None, type=int)
@with_appcontext
def notify_send(recipient_email, message, channel, etype, eid):
    n = notify.send_notification(recipient_email, message, channel, etype, eid)
    click.echo(f"Notification #{n.id} to {recipient_email} [{channel}]")

app.cli.add_command(notify_cli)

@payroll_cli.command('run')
@require_roles('admin','hr')
@click.argument('period_start')
@click.argument('period_end')
@click.argument('admin_email')
@with_appcontext
def payroll_run(period_start, period_end, admin_email):
    run = payroll.create_payroll_run(period_start, period_end, admin_email)
    run = payroll.generate_lines(run.id)
    click.echo(f"Payroll #{run.id} {run.period_start}→{run.period_end} status={run.status}")
    for line in run.lines:
        click.echo(f"  {line.user.email}: minutes={line.total_minutes} gross=${line.gross_pay}")

app.cli.add_command(payroll_cli)

if __name__ == "__main__":
    app.run()
