from datetime import date
from ..database import db
from ..models.core import User, LeaveRequest

def create_leave(requester_email: str, start_iso: str, end_iso: str, leave_type: str, reason: str = ""):
    req = User.query.filter_by(email=requester_email).first()
    if not req: raise ValueError("Requester not found")
    lr = LeaveRequest(requester_id=req.id, start_date=date.fromisoformat(start_iso),
                      end_date=date.fromisoformat(end_iso), type=leave_type, reason=reason, status='pending')
    db.session.add(lr); db.session.commit()
    return lr

def decide_leave(leave_id: int, approver_email: str, decision: str):
    if decision not in ('approved', 'rejected', 'cancelled'):
        raise ValueError("Decision must be approved/rejected/cancelled")
    lr = LeaveRequest.query.get(leave_id)
    if not lr: raise ValueError("Leave request not found")
    approver = User.query.filter_by(email=approver_email).first()
    if not approver: raise ValueError("Approver not found")
    lr.approver_id = approver.id; lr.status = decision
    db.session.commit(); return lr
