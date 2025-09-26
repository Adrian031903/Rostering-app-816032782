import os
import json
import click
from functools import wraps
from flask.cli import AppGroup, with_appcontext
from App import create_app
from App.models.core import LeaveRequest, SwapRequest, User, Shift, TimeLog
from sqlalchemy import or_ 
from App.database import db
from App.controllers import admin_controller as admin
from App.controllers import staff_controller as staff
from App.controllers import leave_controller as leave
from App.controllers import swap_controller as swap
from App.controllers import notify_controller as notify
from datetime import datetime, timedelta

app = create_app()

# -------- session helpers for demo CLI auth --------
SESSION_FILE = ".session.json"

def _session_get():
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE) as f:
            return json.load(f).get("email")
    except Exception:
        return None

def _session_set(email):
    with open(SESSION_FILE, "w") as f:
        json.dump({"email": email}, f)

def _session_clear():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

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

# -------------------- CLI Groups --------------------
init = AppGroup('init', help='DB init & seed')
user_cli = AppGroup('user', help='User/staff admin')
roster_cli = AppGroup('roster', help='Roster & attendance')
leave_cli = AppGroup('leave', help='Leave requests')
swap_cli = AppGroup('swap', help='Shift swaps')
notify_cli = AppGroup('notify', help='Notifications')
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
    # users only (no payroll)
    def ensure(name, email, role):
        if not User.query.filter_by(email=email).first():
            u = User(name=name, email=email, role=role)
            u.set_password("pass")
            db.session.add(u)

    ensure('Admin','admin@example.com','admin')
    ensure('Supervisor','supervisor@example.com','supervisor')
    ensure('HR Clerk','hr@example.com','hr')
    for i in range(1, 4):
        ensure(f'Staff {i}', f'staff{i}@example.com', 'staff')
    db.session.commit()
    click.echo("Seeded users (password = 'pass').")

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
@require_roles('admin', 'supervisor')
@with_appcontext
def assign(email, start_iso, end_iso):
    sh = admin.assign_shift(email, start_iso, end_iso)
    click.echo(f"Shift #{sh.id} for {email} {start_iso}→{end_iso}")

@roster_cli.command('view')
@with_appcontext
def view():
    for sh in Shift.query.order_by(Shift.start_time).all():
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

@roster_cli.command('report-week')
@require_roles('admin', 'supervisor')
@click.argument('week_start')  # e.g., 2025-10-01
@with_appcontext
def report_week(week_start):
    start_dt = datetime.fromisoformat(f"{week_start}T00:00:00")
    end_dt = start_dt + timedelta(days=7) - timedelta(seconds=1)

    # Shifts in the week
    shifts = (Shift.query
              .filter(Shift.start_time >= start_dt, Shift.end_time <= end_dt)
              .all())

    # Aggregate shift counts per user
    stats = {}
    def ensure(uid):
        if uid not in stats:
            u = User.query.get(uid)
            stats[uid] = {
                "name": (u.name if u else f"User {uid}"),
                "scheduled": 0,
                "completed": 0,
                "missed": 0,
                "worked_minutes": 0,
            }

    for sh in shifts:
        ensure(sh.user_id)
        stats[sh.user_id]["scheduled"] += 1
        if sh.status == "completed":
            stats[sh.user_id]["completed"] += 1
        elif sh.status == "missed":
            stats[sh.user_id]["missed"] += 1

    # Worked minutes from timelogs for the week
    logs = (TimeLog.query
            .filter(TimeLog.clock_out != None)  # noqa: E711
            .filter(TimeLog.clock_in >= start_dt, TimeLog.clock_out <= end_dt)
            .all())

    for tl in logs:
        ensure(tl.user_id)
        mins = 0
        if tl.clock_in and tl.clock_out and tl.clock_out > tl.clock_in:
            mins = int((tl.clock_out - tl.clock_in).total_seconds() // 60)
        stats[tl.user_id]["worked_minutes"] += max(0, mins)

    # Print
    click.echo(f"Weekly report {week_start} to {(start_dt + timedelta(days=6)).date()}")
    if not stats:
        click.echo("No data.")
        return
    for uid, row in sorted(stats.items(), key=lambda kv: kv[1]["name"].lower()):
        hours = row["worked_minutes"] / 60.0
        click.echo(f"- {row['name']}: scheduled={row['scheduled']} completed={row['completed']} missed={row['missed']} worked_hours={hours:.2f}")

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
@require_roles('admin', 'supervisor')
@click.argument('leave_id', type=int)
@click.argument('approver_email')
@click.argument('decision')
@with_appcontext
def leave_decide(leave_id, approver_email, decision):
    lr = leave.decide_leave(leave_id, approver_email, decision)
    click.echo(f"Leave #{lr.id} now {lr.status}")

@leave_cli.command('list')
@click.option('--status', default=None, help='pending/approved/rejected/cancelled')
@click.option('--email', default=None, help='Filter by requester email')
def leave_list(status, email):
    q = LeaveRequest.query
    if status:
        q = q.filter_by(status=status)
    if email:
        u = User.query.filter_by(email=email).first()
        if not u:
            click.echo("No such user"); return
        q = q.filter_by(requester_id=u.id)

    rows = q.order_by(LeaveRequest.id.asc()).all()
    if not rows:
        click.echo("No leave requests found"); return

    for lr in rows:
        req = User.query.get(lr.requester_id)
        appr = User.query.get(lr.approver_id) if lr.approver_id else None
        click.echo(
            f"#{lr.id} {lr.start_date}→{lr.end_date} {lr.type:6} "
            f"[{lr.status}] requester={req.email} approver={(appr.email if appr else '-')}"
        )


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
@require_roles('admin', 'supervisor')
@click.argument('swap_id', type=int)
@click.argument('approver_email')
@click.argument('decision')
@with_appcontext
def swap_decide(swap_id, approver_email, decision):
    sr = swap.approve_swap(swap_id, approver_email, decision)
    click.echo(f"Swap #{sr.id} now {sr.status}")

@swap_cli.command('list')
@click.option('--status', default=None, help='pending/approved/rejected/cancelled')
@click.option('--email', default=None, help='Filter by user email (requester or target)')
def swap_list(status, email):
    q = SwapRequest.query
    if status:
        q = q.filter_by(status=status)
    if email:
        u = User.query.filter_by(email=email).first()
        if not u:
            click.echo("No such user"); return
        q = q.filter(or_(SwapRequest.from_user_id == u.id,
                         SwapRequest.to_user_id == u.id))

    rows = q.order_by(SwapRequest.id.asc()).all()
    if not rows:
        click.echo("No swap requests found"); return

    for sr in rows:
        from_u = User.query.get(sr.from_user_id)
        to_u = User.query.get(sr.to_user_id)
        sh = Shift.query.get(sr.shift_id)
        when = (sh.start_time.strftime("%Y-%m-%d %H:%M") if sh and sh.start_time else "")
        click.echo(
            f"#{sr.id} shift={sr.shift_id} {when} "
            f"[{sr.status}] from={from_u.email} -> to={to_u.email} note={sr.note or ''}"
        )

app.cli.add_command(swap_cli)

@notify_cli.command('send')
@require_roles('admin', 'supervisor', 'hr')
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

if __name__ == "__main__":
    app.run()
