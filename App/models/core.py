from datetime import datetime, date
from ..database import db
from werkzeug.security import generate_password_hash, check_password_hash

# ===== Users =====
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, staff, supervisor, hr
    password_hash = db.Column(db.String(255))

    # Convenience alias used by some tests
    @property
    def hashed_password(self):
        return self.password_hash

    def set_password(self, pwd: str):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd: str) -> bool:
        return bool(self.password_hash) and check_password_hash(self.password_hash, pwd)

    def get_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
        }

    shifts = db.relationship("Shift", backref="user", lazy=True)
    timelogs = db.relationship("TimeLog", backref="user", lazy=True)

# ===== Scheduling =====
class Shift(db.Model):
    __tablename__ = "shifts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="scheduled")  # scheduled, completed, missed

    timelogs = db.relationship("TimeLog", backref="shift", lazy=True)
    exception_flags = db.relationship("ExceptionFlag", backref="shift", lazy=True)
    swap_requests = db.relationship("SwapRequest", backref="shift", lazy=True)

# ===== Attendance =====
class TimeLog(db.Model):
    __tablename__ = "timelogs"
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey("shifts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False)
    clock_out = db.Column(db.DateTime)
    source = db.Column(db.String(20), default="app")  # app, kiosk

    breaklogs = db.relationship("BreakLog", backref="timelog", lazy=True)

    def worked_minutes(self) -> int:
        if not self.clock_out:
            return 0
        total = (self.clock_out - self.clock_in).total_seconds()
        for b in self.breaklogs:
            if b.break_end:
                total -= (b.break_end - b.break_start).total_seconds()
        return max(0, int(total // 60))

class BreakLog(db.Model):
    __tablename__ = "breaklogs"
    id = db.Column(db.Integer, primary_key=True)
    timelog_id = db.Column(db.Integer, db.ForeignKey("timelogs.id"), nullable=False)
    break_start = db.Column(db.DateTime, nullable=False)
    break_end = db.Column(db.DateTime)

class ExceptionFlag(db.Model):
    __tablename__ = "exception_flags"
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey("shifts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    kind = db.Column(db.String(20), nullable=False)  # late, early, no_show, overtime
    reason = db.Column(db.String(255))
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===== Leave =====
class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # annual, sick, other
    status = db.Column(db.String(20), default="pending")
    reason = db.Column(db.String(255))

    requester = db.relationship("App.models.core.User", foreign_keys=[requester_id], backref="leave_requests_made")
    approver = db.relationship("App.models.core.User", foreign_keys=[approver_id], backref="leave_requests_approved")

# ===== Swaps =====
class SwapRequest(db.Model):
    __tablename__ = "swap_requests"
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey("shifts.id"), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected, cancelled
    note = db.Column(db.String(255))

    from_user = db.relationship("App.models.core.User", foreign_keys=[from_user_id], backref="swap_sent")
    to_user = db.relationship("App.models.core.User", foreign_keys=[to_user_id], backref="swap_received")

# ===== Notifications =====
class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    channel = db.Column(db.String(20), default="inapp")
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    recipient = db.relationship("App.models.core.User", backref="notifications")
