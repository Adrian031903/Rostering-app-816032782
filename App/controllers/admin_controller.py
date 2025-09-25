from datetime import datetime
from ..database import db
from ..models.core import User, Shift

def create_staff(name: str, email: str):
    staff = User(name=name, email=email, role='staff')
    db.session.add(staff); db.session.commit()
    return staff

def assign_shift(user_email: str, start_iso: str, end_iso: str):
    user = User.query.filter_by(email=user_email, role='staff').first()
    if not user: raise ValueError("Staff not found")
    start_dt, end_dt = datetime.fromisoformat(start_iso), datetime.fromisoformat(end_iso)
    sh = Shift(user_id=user.id, work_date=start_dt.date(), start_time=start_dt, end_time=end_dt, status='scheduled')
    db.session.add(sh); db.session.commit()
    return sh
