from datetime import datetime
from ..database import db
from ..models.core import User, Shift, TimeLog

def view_roster():
    return Shift.query.order_by(Shift.start_time.asc()).all()

def clock_in(user_email: str, shift_id: int):
    user = User.query.filter_by(email=user_email, role='staff').first()
    if not user: raise ValueError("Staff not found")
    shift = Shift.query.get(shift_id)
    if not shift or shift.user_id != user.id: raise ValueError("Shift not found for this user")
    tl = TimeLog(user_id=user.id, shift_id=shift.id, clock_in=datetime.now(), source='app')
    db.session.add(tl); db.session.commit()
    return tl

def clock_out(user_email: str, timelog_id: int):
    user = User.query.filter_by(email=user_email, role='staff').first()
    if not user: raise ValueError("Staff not found")
    tl = TimeLog.query.get(timelog_id)
    if not tl or tl.user_id != user.id: raise ValueError("TimeLog not found for this user")
    tl.clock_out = datetime.now(); tl.shift.status = 'completed'
    db.session.commit()
    return tl
