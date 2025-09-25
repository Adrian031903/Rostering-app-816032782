from datetime import datetime, date
from ..database import db
from werkzeug.security import generate_password_hash, check_password_hash

# ===== Users =====
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)                   # admin, staff, supervisor, hr
    password_hash = db.Column(db.String(255))

    def set_password(self, pwd: str): self.password_hash = generate_password_hash(pwd)
    def check_password(self, pwd: str) -> bool: return check_password_hash(self.password_hash or "", pwd)

    shifts = db.relationship("Shift", backref="user", lazy=True)
    timelogs = db.relationship("TimeLog", backref="user", lazy=True)

# ===== Scheduling =====
class Shift(db.Model):
    __tablename__ = "shifts"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # FK
    work_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="scheduled")            # scheduled, completed, missed

    timelogs = db.relationship("TimeLog", backref="shift", lazy=True)
    exception_flags = db.relationship("ExceptionFlag", backref="shift", lazy=True)
    swap_requests = db.relationship("SwapRequest", backref="shift", lazy=True)

# ===== Attendance =====
class TimeLog(db.Model):
    __tablename__ = "timelogs"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    shift_id = db.Column(db.Integer, db.ForeignKey("shifts.id"), nullable=False)  # FK
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)    # FK
    clock_in = db.Column(db.DateTime, nullable=False)
    clock_out = db.Column(db.DateTime)
    source = db.Column(db.String(20), default="app")                  # app, kiosk

    breaklogs = db.relationship("BreakLog", backref="timelog", lazy=True)

    def worked_minutes(self) -> int:
        if not self.clock_out: return 0
        return int((self.clock_out - self.clock_in).total_seconds() // 60)

class BreakLog(db.Model):
    __tablename__ = "breaklogs"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    timelog_id = db.Column(db.Integer, db.ForeignKey("timelogs.id"), nullable=False)  # FK
    break_start = db.Column(db.DateTime, nullable=False)
    break_end = db.Column(db.DateTime)

class ExceptionFlag(db.Model):
    __tablename__ = "exception_flags"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    shift_id = db.Column(db.Integer, db.ForeignKey("shifts.id"), nullable=False)  # FK
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)    # FK
    kind = db.Column(db.String(20), nullable=False)                   # late, early, no_show, overtime
    reason = db.Column(db.String(255))
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===== Leave =====
class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # FK
    approver_id = db.Column(db.Integer, db.ForeignKey("users.id"))    # FK (nullable until decided)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(20), nullable=False)                   # annual, sick, other
    status = db.Column(db.String(20), default="pending")
    reason = db.Column(db.String(255))

    requester = db.relationship("App.models.core.User", foreign_keys=[requester_id], backref="leave_requests_made")
    approver = db.relationship("App.models.core.User", foreign_keys=[approver_id], backref="leave_requests_approved")

# ===== Swaps =====
class SwapRequest(db.Model):
    __tablename__ = "swap_requests"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    shift_id = db.Column(db.Integer, db.ForeignKey("shifts.id"), nullable=False)      # FK
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)   # FK
    to_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)     # FK
    status = db.Column(db.String(20), default="pending")              # pending, approved, rejected, cancelled
    note = db.Column(db.String(255))

    from_user = db.relationship("App.models.core.User", foreign_keys=[from_user_id], backref="swap_sent")
    to_user = db.relationship("App.models.core.User", foreign_keys=[to_user_id], backref="swap_received")

# ===== Notifications =====
class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)   # FK
    channel = db.Column(db.String(10), default="inapp")               # email, sms, inapp
    message = db.Column(db.String(255), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    entity_type = db.Column(db.String(30))                            # Shift, LeaveRequest, SwapRequest
    entity_id = db.Column(db.Integer)

    recipient = db.relationship("App.models.core.User", backref="notifications")

# ===== Payroll =====
class PayRate(db.Model):
    __tablename__ = "pay_rates"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)        # FK
    hourly_rate = db.Column(db.Numeric(10, 2), nullable=False)
    effective_from = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    effective_to = db.Column(db.DateTime)

    user = db.relationship("App.models.core.User", backref="pay_rates")

class PayrollRun(db.Model):
    __tablename__ = "payroll_runs"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    generated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)   # FK (admin)
    status = db.Column(db.String(20), default="draft")

    lines = db.relationship("PayrollLine", backref="run", lazy=True)

class PayrollLine(db.Model):
    __tablename__ = "payroll_lines"
    id = db.Column(db.Integer, primary_key=True)                      # PK
    payroll_run_id = db.Column(db.Integer, db.ForeignKey("payroll_runs.id"), nullable=False)  # FK
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)                # FK
    total_minutes = db.Column(db.Integer, default=0)
    gross_pay = db.Column(db.Numeric(12, 2), default=0)

    user = db.relationship("App.models.core.User", backref="payroll_lines")
