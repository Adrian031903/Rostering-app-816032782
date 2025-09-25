from ..database import db
from ..models.core import User, Shift, SwapRequest

def request_swap(from_email: str, shift_id: int, to_email: str, note: str = ""):
    from_user = User.query.filter_by(email=from_email).first()
    to_user = User.query.filter_by(email=to_email).first()
    if not from_user or not to_user: raise ValueError("From or To user not found")
    shift = Shift.query.get(shift_id)
    if not shift or shift.user_id != from_user.id: raise ValueError("Shift not found for requesting user")
    sr = SwapRequest(shift_id=shift_id, from_user_id=from_user.id, to_user_id=to_user.id, note=note, status='pending')
    db.session.add(sr); db.session.commit()
    return sr

def approve_swap(swap_id: int, approver_email: str, decision: str):
    if decision not in ('approved', 'rejected', 'cancelled'):
        raise ValueError("Decision must be approved/rejected/cancelled")
    sr = SwapRequest.query.get(swap_id)
    if not sr: raise ValueError("Swap request not found")
    if decision == 'approved': sr.shift.user_id = sr.to_user_id
    sr.status = decision; db.session.commit()
    return sr
